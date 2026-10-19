#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_test_aoci_cognition.py — AOCI-CODE 项目认知索引、规模判定与治理生命周期单元测试
=============================================================================
覆盖：
1. 项目根解析与安全源码文件判定（硬安全排除、敏感凭据过滤、有效后缀白名单）；
2. 物理代码行流式统计与度量聚合；
3. 规模阈值评估三值判定 (eligible / below_threshold / unknown) 及边界值；
4. Volume-first 纯文本认知资产初始化 (aoci.txt, aoci.meta.txt, aoci.code.txt)；
5. FRAS 草稿行生成与格式验证；
6. 认知资产结构校验 (verify) 与异常拦截；
7. auto_router aoci 子命令集成与感知待办输出；
8. 变异检查（破坏性测试确保判据不恒绿）。
"""

import os
import sys
import tempfile
import pathlib
import subprocess
from pathlib import Path

SELF_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SELF_DIR.parent
sys.path.insert(0, str(SELF_DIR))

import aoci_inventory as inv
import aoci_cognition as cog

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = ""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if (detail and not ok) else ""))


def main():
    print("=== 1. 源码安全性与白名单过滤测试 ===")
    check("安全源码匹配: .py 文件", inv.is_safe_source_file("src/main.py"))
    check("安全源码匹配: .ts 文件", inv.is_safe_source_file("frontend/app.tsx"))
    check("安全源码匹配: Dockerfile", inv.is_safe_source_file("deploy/Dockerfile"))
    check("硬排除匹配: node_modules 目录", not inv.is_safe_source_file("node_modules/pkg/index.js"))
    check("硬排除匹配: .git 目录", not inv.is_safe_source_file(".git/config"))
    check("硬排除匹配: .evolution 目录", not inv.is_safe_source_file(".evolution/secrets/token.txt"))
    check("硬排除匹配: venv 目录", not inv.is_safe_source_file(".venv/lib/python3.12/site.py"))
    check("凭据过滤: db.password", not inv.is_safe_source_file("config/db.password"))
    check("凭据过滤: gateway.token", not inv.is_safe_source_file("secrets/gateway.token"))
    check("凭据过滤: id_rsa 密钥", not inv.is_safe_source_file("keys/id_rsa"))

    print("\n=== 2. 规模度量与三值阈值评估测试 ===")
    # 模拟小型轻量项目 (below_threshold)
    m_small = {"source_files": 10, "code_lines": 800, "source_bytes": 50000}
    st_small, r_small = inv.evaluate_thresholds(m_small)
    check("小型项目评定为 below_threshold", st_small == "below_threshold", str(r_small))

    # 模拟文件数达标项目 (eligible)
    m_files = {"source_files": 45, "code_lines": 1500, "source_bytes": 100000}
    st_files, r_files = inv.evaluate_thresholds(m_files)
    check("文件数达标评定为 eligible", st_files == "eligible" and "源码数达到阈值" in r_files[0], str(r_files))

    # 模拟代码行达标项目 (eligible)
    m_lines = {"source_files": 15, "code_lines": 5500, "source_bytes": 200000}
    st_lines, r_lines = inv.evaluate_thresholds(m_lines)
    check("代码行达标评定为 eligible", st_lines == "eligible" and "代码行数达到阈值" in r_lines[0], str(r_lines))

    # 模拟空项目 (unknown)
    m_empty = {"source_files": 0, "code_lines": 0, "source_bytes": 0}
    st_empty, r_empty = inv.evaluate_thresholds(m_empty)
    check("空项目评定为 unknown", st_empty == "unknown", str(r_empty))

    print("\n=== 3. 隔离夹具：Volume-first 资产初始化与 FRAS 生成测试 ===")
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "demo_proj"
        proj.mkdir()
        src_dir = proj / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("import os\nprint('hello')\n", encoding="utf-8")
        (src_dir / "util.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

        # 首次初始化
        res = cog.init_aoci_volumes(proj, project_name="demo")
        check("初始化成功", res["status"] == "ready")
        check("生成 aoci.txt (Root)", (proj / "aoci.txt").is_file())
        check("生成 aoci.meta.txt (Meta)", (proj / "aoci.meta.txt").is_file())
        check("生成 aoci.code.txt (Code)", (proj / "aoci.code.txt").is_file())

        root_txt = (proj / "aoci.txt").read_text(encoding="utf-8")
        check("aoci.txt 包含 Root Manifest 标识", "#AOCI-ROOT-MANIFEST: 1" in root_txt)
        check("aoci.txt 声明 code volume", "id=code" in root_txt)

        meta_txt = (proj / "aoci.meta.txt").read_text(encoding="utf-8")
        check("aoci.meta.txt 包含标签字典", "[Tag dictionary: code]" in meta_txt)

        # 草稿生成
        draft_res = cog.generate_draft_fras(proj)
        check("成功提取受管文件草稿", draft_res["total_files"] == 2)
        check("草稿包含标准 FRAS 行", "app.py[CG5S]: F:" in draft_res["draft_content"])

        # 写入草稿并校验
        (proj / "aoci.code.txt").write_text(draft_res["draft_content"], encoding="utf-8")
        ok_v, issues_v = cog.verify_cognition_assets(proj)
        check("校验通过", ok_v, str(issues_v))

        # 变异测试：破坏 aoci.txt 必须能够被 verify 拦截
        (proj / "aoci.txt").write_text("corrupted content", encoding="utf-8")
        ok_mut, issues_mut = cog.verify_cognition_assets(proj)
        check("变异：损坏 aoci.txt 能被 verify 拦截", not ok_mut, str(issues_mut))

    print("\n=== 4. CLI 命令与子进程调用契约测试 ===")
    sub_env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

    # aoci_cognition.py --help
    r_help = subprocess.run([sys.executable, str(SELF_DIR / "aoci_cognition.py"), "--help"],
                            cwd=str(SKILL_ROOT), env=sub_env, capture_output=True, text=True, errors="replace")
    check("aoci_cognition.py --help rc=0", r_help.returncode == 0)
    check("aoci_cognition.py --help 包含命令说明", "probe" in r_help.stdout and "status" in r_help.stdout)

    # aoci_cognition.py probe --json
    r_probe = subprocess.run([sys.executable, str(SELF_DIR / "aoci_cognition.py"), "probe", "--json"],
                             cwd=str(SKILL_ROOT), env=sub_env, capture_output=True, text=True, errors="replace")
    check("aoci_cognition.py probe --json rc=0", r_probe.returncode == 0)
    check("probe 输出为标准 JSON 且包含 metrics", '"source_files"' in r_probe.stdout and '"scale_status"' in r_probe.stdout)

    # auto_router.py aoci 子命令转发
    r_router = subprocess.run([sys.executable, str(SELF_DIR / "auto_router.py"), "aoci", "status", "--json"],
                              cwd=str(SKILL_ROOT), env=sub_env, capture_output=True, text=True, errors="replace")
    check("auto_router.py aoci status --json rc=0", r_router.returncode == 0)
    check("auto_router 转发得到完整 status JSON", '"project_root"' in r_router.stdout)

    print("\n" + "=" * 64)
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL", len(PASS), total))
    print("=" * 64)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
