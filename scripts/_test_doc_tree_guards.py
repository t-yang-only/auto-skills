# -*- coding: utf-8 -*-
"""_test_doc_tree_guards.py — 「守卫的守卫」：证明 _test_registry.py 的文档树断言真的会拦人。

为什么需要这个脚本
------------------
_test_registry.py 的第 7/8/9 段（文档目录树覆盖顶层、tools/ 成员数、scripts/ 覆盖）
是防止「加了目录/技能/脚本却没写进文档」的唯一屏障。但一条**永远为真**的断言
看起来和一条有效的断言完全一样 —— 只有当有人故意破坏、而它拒绝变红时，你才知道
它已经失效。实测踩过：仓库根留了一个 .bak 文件，第 7 段因此常红，于是「破坏后确实
红了」不再证明任何事，负向测试悄悄变成了安慰剂。

本脚本在**临时副本**上做破坏 → 跑真断言 → 要求它变红 → 还原，并额外验证
「噪声文件不该触发断言」。原始文件在任何时刻都不被修改（破坏只发生在临时目录）。

用法：
    python scripts/_test_doc_tree_guards.py            # 全部用例
    python scripts/_test_doc_tree_guards.py --case 2   # 只跑第 2 个用例
退出码：0 = 全部符合预期；1 = 有用例未按预期反应（守卫已失效）。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_TEST = "scripts/_test_registry.py"
WATCHED = ["SKILL.md", "README.md", "references/capability-map.md"]


def _run_registry_test(cwd: Path) -> tuple[int, list[str]]:
    proc = subprocess.run(
        [sys.executable, REGISTRY_TEST],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    fails = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL:")]
    return proc.returncode, fails


def _make_sandbox() -> Path:
    """把仓库复制到临时目录（跳过 .git / .evolution / __pycache__），返回副本根。"""
    tmp = Path(tempfile.mkdtemp(prefix="doctree-guard-"))
    shutil.copytree(
        ROOT, tmp / "repo",
        ignore=shutil.ignore_patterns(".git", ".evolution", "__pycache__", "*.pyc"),
    )
    return tmp / "repo"


def _head_re(block: str) -> re.Pattern:
    return re.compile(r"^[│\s]*[├└]──\s+" + re.escape(block) + r"(/|\s|$)")


def _child_re() -> re.Pattern:
    return re.compile(r"^│\s+[├└]──")


def _drop_one_child(repo: Path, file: str, block: str) -> bool:
    """删掉某个块（如 scripts/）下的一个子条目。"""
    p = repo / file
    lines = p.read_text(encoding="utf-8").splitlines(True)
    start = next((i for i, l in enumerate(lines) if _head_re(block).match(l)), None)
    if start is None:
        return False
    for i in range(start + 1, len(lines)):
        if _child_re().match(lines[i]):
            del lines[i]
            p.write_text("".join(lines), encoding="utf-8", newline="\n")
            return True
        if lines[i].strip() and not _child_re().match(lines[i]):
            break
    return False


def _drop_all_children(repo: Path, file: str, block: str, keep_head: bool) -> bool:
    """删掉某个块下的全部子条目；keep_head=False 时连父行一起删。"""
    p = repo / file
    lines = p.read_text(encoding="utf-8").splitlines(True)
    start = next((i for i, l in enumerate(lines) if _head_re(block).match(l)), None)
    if start is None:
        return False
    end = start + 1
    while end < len(lines) and _child_re().match(lines[end]):
        end += 1
    head = start + 1 if keep_head else start
    p.write_text("".join(lines[:head] + lines[end:]), encoding="utf-8", newline="\n")
    return True


def _drop_last_matrix_row(repo: Path) -> bool:
    p = repo / "references" / "capability-map.md"
    lines = p.read_text(encoding="utf-8").splitlines(True)
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r"^\|\s*\d{2}\s*\|", lines[i]):
            del lines[i]
            p.write_text("".join(lines), encoding="utf-8", newline="\n")
            return True
    return False


def _add_noise(repo: Path) -> list[Path]:
    made = []
    bak = repo / "SKILL.md.bak-guardcheck"
    swp = repo / ".guard-check.swp"
    shutil.copy2(repo / "SKILL.md", bak)
    swp.write_text("x", encoding="utf-8")
    made += [bak, swp]
    return made


def _tamper_ledger_description(repo: Path) -> bool:
    """把 registry.json 里某条 description 改花，模拟「台账与 SKILL.md 脱节」。"""
    import json as _json
    f = repo / "tools" / "registry.json"
    try:
        data = _json.loads(f.read_text(encoding="utf-8"))
        key = sorted(data["tools"])[0]
        # 只在原文后追加一句，保留「触发条件」形态 —— 否则会先被第 3c 段
        # （description 必须有触发条件）抓到，验证不到第 11 段（台账脱节）。
        data["tools"][key]["description"] = (
            str(data["tools"][key].get("description") or "").rstrip() + " Use when tampered.")
        f.write_text(_json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
        return True
    except Exception:
        return False


def _break_count_anchor(repo: Path) -> bool:
    """改掉 sync_skill_counts 的一条锚点前缀，模拟「文档措辞变了、RULES 没跟着改」。"""
    f = repo / "scripts" / "sync_skill_counts.py"
    try:
        s = f.read_text(encoding="utf-8")
        old = '("SKILL.md", "Bundles ", " top-tier")'
        if old not in s:
            return False
        f.write_text(s.replace(old, '("SKILL.md", "BundlesZZ ", " top-tier")'),
                     encoding="utf-8", newline="\n")
        return True
    except Exception:
        return False


CASES = [
    ("删 SKILL.md 树里 scripts/ 的一个子条目",
     lambda r: _drop_one_child(r, "SKILL.md", "scripts")),
    ("删 README.md 里 tools/ 的全部子条目",
     lambda r: _drop_all_children(r, "README.md", "tools", keep_head=True)),
    ("删 SKILL.md 里 scripts/ 的全部子条目",
     lambda r: _drop_all_children(r, "SKILL.md", "scripts", keep_head=True)),
    ("删 SKILL.md 里 scripts/ 整块（含父行）",
     lambda r: _drop_all_children(r, "SKILL.md", "scripts", keep_head=False)),
    ("删 capability-map.md 最后一行矩阵",
     _drop_last_matrix_row),
    ("篡改 registry.json 的一条 description（模拟忘记重扫台账）",
     _tamper_ledger_description),
    ("改掉计数同步器的一条锚点（模拟文档措辞变了、RULES 没跟着改）",
     _break_count_anchor),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="验证文档树守卫是否真的会拦截脱节")
    ap.add_argument("--case", type=int, help="只跑指定用例序号（从 1 起）")
    args = ap.parse_args()

    print("=" * 72)
    print("  守卫的守卫：文档树断言有效性验证（破坏 → 必须变红 → 还原）")
    print("=" * 72)

    failures = []
    selected = [(i + 1, n, f) for i, (n, f) in enumerate(CASES)
                if args.case is None or args.case == i + 1]

    for idx, name, mutate in selected:
        repo = _make_sandbox()
        try:
            if not mutate(repo):
                print(f"[SKIP] #{idx} {name} —— 锚点未命中（文档结构可能已变）")
                failures.append(f"#{idx} {name}: 锚点未命中")
                continue
            rc, fails = _run_registry_test(repo)
            if rc == 0:
                print(f"[FAIL] #{idx} {name} —— 破坏了却没变红，守卫已失效")
                failures.append(f"#{idx} {name}: 未拦截")
            else:
                first = fails[0] if fails else "<无 FAIL 行>"
                print(f"[ OK ] #{idx} {name}")
                print(f"         {first[:110]}")
        finally:
            shutil.rmtree(repo.parent, ignore_errors=True)

    # 噪声用例：加了 .bak / .swp 不应触发断言
    repo = _make_sandbox()
    try:
        _add_noise(repo)
        rc, fails = _run_registry_test(repo)
        if rc == 0:
            print("[ OK ] 噪声文件（*.bak / *.swp）不触发断言")
        else:
            print("[FAIL] 噪声文件触发了断言，负向测试会被它掩盖")
            for f in fails[:2]:
                print(f"         {f[:110]}")
            failures.append("噪声用例: 误报")
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)

    print("=" * 72)
    if failures:
        print(f"  验收：{len(selected) + 1 - len(failures)}/{len(selected) + 1} 通过 —— 有守卫失效")
        for f in failures:
            print(f"    - {f}")
        print("=" * 72)
        return 1
    print(f"  验收：{len(selected) + 1}/{len(selected) + 1} 通过 —— 全部守卫有效")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())