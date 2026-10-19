#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aoci_inventory.py — AOCI-CODE 代码项目规模探测、有效源码筛选与阈值判定引擎
=============================================================================
功能：
1. 识别代码项目物理根目录（Git 根或工作目录）；
2. 尊重 .gitignore 标准忽略规则，安全枚举受管有效源码；
3. 硬安全排除私有区、依赖包、构建产物与敏感凭据；
4. 统计有效源码文件数、物理非空代码行、源码字节量与语言分布；
5. 根据可配置的阈值规则进行三值规模评估 (eligible / below_threshold / unknown)；
6. 为 auto_router / aoci_cognition 提供纯只读、无副作用的项目认知决策输入。
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set

# 默认有效源码/脚本后缀
DEFAULT_SOURCE_EXTENSIONS: Set[str] = {
    ".py", ".pyw",
    ".js", ".mjs", ".cjs", ".jsx",
    ".ts", ".mts", ".cts", ".tsx",
    ".go",
    ".rs",
    ".java", ".kt", ".scala",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    ".cs",
    ".sh", ".bash", ".zsh", ".ps1", ".psm1",
    ".sql",
    ".vue", ".svelte",
    ".rb", ".php",
    ".swift",
    ".lua",
    ".yaml", ".yml", ".json", ".toml"
}

# 独立特别文件（无后缀或特殊名）
SPECIAL_FILENAMES: Set[str] = {
    "dockerfile", "makefile", "cmakelists.txt", "gemfile", "rakefile"
}

# 硬安全排除目录名（全深度过滤，防止误入依赖海或私有敏感区）
HARD_EXCLUDE_DIR_NAMES: Set[str] = {
    ".git", ".evolution", "agent_word", ".dist", ".aoci",
    "node_modules", "vendor", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist", "out", "target", "bin", "obj",
    ".idea", ".vscode", ".vs"
}

# 敏感文件检测正则（排除真实私钥和凭据进入源码度量）
SENSITIVE_FILE_PATTERN = re.compile(
    r"(id_rsa|id_ed25519|\.pem|\.key|\.pfx|\.p12|db\.password|gateway\.token)$",
    re.IGNORECASE
)


def resolve_project_root(target: Optional[str] = None) -> Path:
    """
    解析项目物理根目录。
    优先级：显式传入路径 -> 从当前目录向上寻找包含 .git 的目录 -> 当前工作目录。
    """
    if target and str(target).strip():
        p = Path(target).resolve()
        if p.exists() and p.is_dir():
            return p
        raise FileNotFoundError(f"指定的项目目录不存在或不是目录: {target}")

    cwd = Path.cwd().resolve()
    curr = cwd
    while curr.parent != curr:
        if (curr / ".git").is_dir():
            return curr
        curr = curr.parent

    return cwd


def is_safe_source_file(rel_path: str, extra_extensions: Optional[Set[str]] = None) -> bool:
    """判断相对路径是否为符合安全与语言标准的有效源码/配置。"""
    posix = rel_path.replace("\\", "/")
    parts = posix.split("/")

    # 1. 检查各级目录名是否在硬排除名单中
    for part in parts[:-1]:
        if part in HARD_EXCLUDE_DIR_NAMES:
            return False

    filename = parts[-1]
    if not filename:
        return False

    # 2. 过滤明显凭据/私钥文件
    if SENSITIVE_FILE_PATTERN.search(filename):
        return False

    # 3. 检查特殊文件名（如 Dockerfile, Makefile）
    lower_name = filename.lower()
    if lower_name in SPECIAL_FILENAMES:
        return True

    # 4. 后缀匹配
    ext = Path(filename).suffix.lower()
    allowed = DEFAULT_SOURCE_EXTENSIONS
    if extra_extensions:
        allowed = allowed | {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extra_extensions}

    return ext in allowed


def scan_source_files(
    project_root: Path,
    extra_excludes: Optional[List[str]] = None,
    extra_extensions: Optional[List[str]] = None
) -> Tuple[List[Path], str]:
    """
    安全枚举项目有效源码文件列表。
    返回: (文件绝对路径列表, 扫描机制权威标识 git/walk)
    """
    ext_set = set(extra_extensions) if extra_extensions else None
    files: List[Path] = []
    authority = "walk"

    # 尝试优先使用 Git 权威忽略列表
    git_dir = project_root / ".git"
    if git_dir.is_dir():
        try:
            cmd = ["git", "-C", str(project_root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
            res = subprocess.run(cmd, capture_output=True, timeout=15)
            if res.returncode == 0:
                authority = "git"
                raw_entries = [e for e in res.stdout.split(b"\0") if e]
                for raw in raw_entries:
                    try:
                        rel = raw.decode("utf-8", errors="replace").strip()
                        if not rel:
                            continue
                        if is_safe_source_file(rel, ext_set):
                            full = project_root / rel
                            if full.is_file():
                                files.append(full)
                    except Exception:
                        continue
                return sorted(files), authority
        except Exception:
            pass

    # 降级备用：标准文件系统安全遍历
    for root, dirs, filenames in os.walk(str(project_root), followlinks=False):
        # 实时原地剪枝，防止进入巨型依赖目录
        dirs[:] = [d for d in dirs if d not in HARD_EXCLUDE_DIR_NAMES and not d.startswith(".")]

        rel_dir = os.path.relpath(root, str(project_root))
        for fn in filenames:
            rel_file = fn if rel_dir == "." else os.path.join(rel_dir, fn)
            if is_safe_source_file(rel_file, ext_set):
                p = Path(root) / fn
                if p.is_file():
                    files.append(p)

    return sorted(files), authority


def count_file_nonblank_lines(file_path: Path, max_bytes: int = 1048576) -> int:
    """流式统计单个文件的物理非空代码行（超过 1MB 自动截断保护，避免卡死）。"""
    lines = 0
    try:
        if file_path.stat().st_size > max_bytes:
            # 超大文件保守估算，防止耗尽内存
            with open(file_path, "rb") as f:
                chunk = f.read(max_bytes)
                return chunk.count(b"\n")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    lines += 1
    except Exception:
        pass
    return lines


def calculate_metrics(files: List[Path], project_root: Path) -> Dict[str, Any]:
    """汇总计算源码度量数据。"""
    total_bytes = 0
    total_lines = 0
    lang_dist: Dict[str, int] = {}

    for fp in files:
        try:
            st = fp.stat()
            sz = st.st_size
            total_bytes += sz
            total_lines += count_file_nonblank_lines(fp)

            ext = fp.suffix.lower() or fp.name.lower()
            lang_dist[ext] = lang_dist.get(ext, 0) + 1
        except OSError:
            continue

    return {
        "project_root": str(project_root),
        "source_files": len(files),
        "source_bytes": total_bytes,
        "code_lines": total_lines,
        "language_distribution": dict(sorted(lang_dist.items(), key=lambda x: x[1], reverse=True)[:8]),
    }


def evaluate_thresholds(
    metrics: Dict[str, Any],
    thresholds: Optional[Dict[str, Any]] = None
) -> Tuple[str, List[str]]:
    """
    根据度量数据与配置阈值，进行三值状态评估。
    返回: (status: 'eligible' | 'below_threshold' | 'unknown', reasons: List[str])
    """
    n_files = int(metrics.get("source_files", 0))
    n_lines = int(metrics.get("code_lines", 0))
    n_bytes = int(metrics.get("source_bytes", 0))

    if n_files <= 0:
        return "unknown", ["未扫描到有效源码文件"]

    # 默认阈值口径：中大型项目标准
    cfg = thresholds or {}
    th_files = int(cfg.get("source_files", 40))
    th_lines = int(cfg.get("code_lines", 4000))
    th_bytes = int(cfg.get("source_bytes", 1048576))  # 1MB
    min_files_bytes = int(cfg.get("min_files_for_bytes", 20))

    reasons: List[str] = []

    # 判定规则 1: 文件数达标
    if n_files >= th_files:
        reasons.append(f"有效源码数达到阈值 ({n_files} >= {th_files})")

    # 判定规则 2: 代码行达标
    if n_lines >= th_lines:
        reasons.append(f"代码行数达到阈值 ({n_lines} >= {th_lines})")

    # 判定规则 3: 源码体积达标（配合最小文件数，防大单文件误触）
    if n_bytes >= th_bytes and n_files >= min_files_bytes:
        reasons.append(f"源码体积与分布达到阈值 ({n_bytes // 1024}KB >= {th_bytes // 1024}KB 且文件数 {n_files} >= {min_files_bytes})")

    if reasons:
        return "eligible", reasons

    return "below_threshold", [
        f"项目规模未达认知索引门槛 (文件数: {n_files}/{th_files}, 行数: {n_lines}/{th_lines}, 体积: {n_bytes // 1024}KB)"
    ]
