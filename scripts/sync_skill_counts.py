#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步文档里的技能计数到台账实际值。

背景：每新增/移除一个技能，需要同步 3 个文档里共 13 处计数（SKILL.md 4 处、
README.md 6 处、capability-map.md 3 处）。靠人眼扫必然遗漏，_test_registry.py 只能事后报错，
本脚本把「报错」变成「修好」。

用法：
    python scripts/sync_skill_counts.py            # 检查并修复（默认）
    python scripts/sync_skill_counts.py --check    # 只检查，有差异则 exit 1（供测试/CI 调用）
    python scripts/sync_skill_counts.py --dry-run  # 同 --check，但打印将要写入的内容
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "tools" / "registry.json"

# (rel_path, 前缀, 后缀) —— 三元组就是一条计数位置：中间只允许是数字。
# 前后缀必须足够长以唯一定位（避免误改「30天滚动清理」这类无关数字）。
RULES = [
    ("SKILL.md", "Bundles ", " top-tier"),
    ("SKILL.md", "**", " 个顶流高星通用 Agent Skills**"),
    ("SKILL.md", "内部完全自洽收拢的 ", " 大核心通用工具集"),
    ("SKILL.md", "# ", " 大成员能力全景映射表与冲突优先级"),
    ("README.md", "自洽收拢 ", " 大顶流核心技能"),
    ("README.md", "badge/Members-", "%20Self--Contained"),
    ("README.md", "自洽收拢 ", " 个高星通用技能"),
    ("README.md", "## 🏗️ 架构与 ", " 大内置成员"),
    ("README.md", "内部收拢的 ", " 大核心专业工具集"),
    ("README.md", "# ", " 大成员能力全景映射表与冲突优先级"),
    ("references/capability-map.md", "# auto-skills ", " 大核心成员能力映射矩阵"),
    ("references/capability-map.md", "完整收拢 ", " 个顶尖高星通用成员技能"),
    ("references/capability-map.md", "## 1. ", " 大成员能力全景矩阵"),
]


def actual_count():
    """台账里的技能数（唯一真相源）。"""
    with open(REGISTRY, encoding="utf-8") as f:
        return int(json.load(f)["tools_count"])


def sync(apply=False):
    """返回 (changed_count, details)。apply=False 时只检查不写入。"""
    n = actual_count()
    details = []
    changed = 0
    cache = {}
    for rel, prefix, suffix in RULES:
        p = ROOT / rel
        if rel not in cache:
            cache[rel] = p.read_text(encoding="utf-8")
        s = cache[rel]
        pat = re.compile(re.escape(prefix) + r"(\d{1,3})" + re.escape(suffix))
        hits = pat.findall(s)
        if not hits:
            details.append(("MISS", rel, prefix[:24] + "..." + suffix[:18], "-", n))
            continue
        if all(h == str(n) for h in hits):
            continue
        for old in hits:
            details.append(("FIX", rel, prefix[:24] + "..." + suffix[:18], old, n))
        changed += len(hits)
        cache[rel] = pat.sub(lambda m: prefix + str(n) + suffix, s)
    if apply and changed:
        for rel, s in cache.items():
            (ROOT / rel).write_text(s, encoding="utf-8", newline="\n")
    return changed, details


def main():
    ap = argparse.ArgumentParser(description="同步文档里的技能计数")
    ap.add_argument("--check", action="store_true", help="只检查，有差异则 exit 1")
    ap.add_argument("--dry-run", action="store_true", help="同 --check，额外打印将要写入的内容")
    args = ap.parse_args()

    n = actual_count()
    print("[台账] 公共技能数 = %d（共 %d 个文档位置）" % (n, len(RULES)))
    check_only = args.check or args.dry_run
    changed, details = sync(apply=not check_only)

    if not details:
        print("[✓] 全部一致，无需修改")
        return 0

    for kind, rel, ctx, old, new in details:
        if kind == "MISS":
            print("  [!] %s | 未找到锚点: %s" % (rel, ctx))
        else:
            print("  [修] %s | %s | %s -> %s" % (rel, ctx, old, new))
    if check_only:
        print("[✗] 发现 %d 处计数脱节（运行不带 --check 可修复）" % changed)
        return 1
    print("[✓] 已修复 %d 处" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
