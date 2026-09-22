# -*- coding: utf-8 -*-
"""台账与文档一致性回归测试。

覆盖 2026-09-22 修复的真实缺陷，防止复发：
  1. SKILL.md 带 UTF-8 BOM 会让 frontmatter 正则 ^--- 匹配失败，
     表现为 registry.json 里该技能 description = "无描述"。
  2. 文档里的技能计数与 tools/ 实际目录数脱节。

用法：python scripts/_test_registry.py
退出码：0 = 全部通过；1 = 有失败项。
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
REGISTRY = os.path.join(TOOLS, "registry.json")

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))


def has_bom(path):
    with open(path, "rb") as f:
        return f.read(3) == b"\xef\xbb\xbf"


def main():
    print("=" * 72)
    print("  台账与文档一致性回归测试")
    print("=" * 72)

    # ---- 1. registry.json 可解析 ----
    print("\n[1] registry.json 可解析")
    if not os.path.isfile(REGISTRY):
        check("registry.json 存在", False, REGISTRY)
        return report()
    reg = json.load(io.open(REGISTRY, encoding="utf-8"))
    check("registry.json 存在且可解析", True, "%d 条" % len(reg.get("tools", {})))

    tools = reg.get("tools", {})

    # ---- 2. 计数一致 ----
    print("\n[2] 技能计数一致")
    dirs = sorted(
        d for d in os.listdir(TOOLS)
        if os.path.isdir(os.path.join(TOOLS, d)) and not d.startswith((".", "_"))
    )
    check("tools_count 与实际目录数一致", reg.get("tools_count") == len(dirs),
          "registry=%s 实际=%d" % (reg.get("tools_count"), len(dirs)))
    check("注册条目数与目录数一致", len(tools) == len(dirs),
          "注册=%d 目录=%d" % (len(tools), len(dirs)))
    missing = [d for d in dirs if d not in tools]
    check("每个目录都已注册", not missing, "未注册: %s" % (", ".join(missing) if missing else "无"))

    # ---- 3. description 完整性（BOM bug 的回归判据）----
    print("\n[3] description 完整性（防 BOM 复发）")
    empty = [k for k, v in tools.items() if not v.get("description") or v["description"] == "无描述"]
    check("无 description 为空的技能", not empty, "异常: %s" % (", ".join(empty) if empty else "无"))

    # 占位描述守卫：description 是 agent 判断「何时加载」的唯一依据，
    # 形如 "Auto-onboarded skill x" 的占位等于技能不可被发现，必须拦在库外。
    placeholder = [k for k, v in tools.items()
                   if re.search(r"Auto-onboarded skill|^TODO|自动纳管占位|^目录 ", v.get("description", ""))]
    check("无占位/待完善 description", not placeholder,
          "占位: %s" % (", ".join(placeholder) if placeholder else "无"))

    bom_files = []
    for d in dirs:
        md = os.path.join(TOOLS, d, "SKILL.md")
        if os.path.isfile(md) and has_bom(md):
            bom_files.append(d + "/SKILL.md")
    check("无带 UTF-8 BOM 的 SKILL.md", not bom_files,
          "带 BOM: %s" % (", ".join(bom_files) if bom_files else "无"))

    # ---- 3b. 私有区占位守卫（与公共区是两份独立台账）----
    print("\n[3b] 私有区 description 占位守卫")
    cust_reg = os.path.join(ROOT, ".evolution", "custom_skills", "registry.json")
    if os.path.isfile(cust_reg):
        try:
            ctools = json.load(io.open(cust_reg, encoding="utf-8")).get("tools", {}) or {}
            cph = [k for k, v in ctools.items()
                   if re.search(r"Auto-onboarded skill|^TODO|自动纳管占位|^目录 ", (v or {}).get("description", ""))]
            check("私有区无占位 description（%d 条）" % len(ctools), not cph,
                  "占位: %s" % (", ".join(cph) if cph else "无"))
        except Exception as e:
            check("私有区 registry 可解析", False, str(e))
    else:
        check("私有区 registry 不存在（跳过）", True, cust_reg)

    # ---- 4. 每个技能都有 SKILL.md ----
    print("\n[4] SKILL.md 齐备")
    no_md = [d for d in dirs if not os.path.isfile(os.path.join(TOOLS, d, "SKILL.md"))]
    check("每个技能目录都有 SKILL.md", not no_md,
          "缺失: %s" % (", ".join(no_md) if no_md else "无"))

    # ---- 5. 文档计数与实现一致 ----
    print("\n[5] 文档计数与实现一致")
    n = len(dirs)
    for fn in ("SKILL.md", "README.md", "references/capability-map.md"):
        p = os.path.join(ROOT, fn)
        if not os.path.isfile(p):
            check("%s 存在" % fn, False)
            continue
        text = io.open(p, encoding="utf-8").read()
        # 抓「NN 个/大」形式的计数，排除年份等噪声
        counts = set()
        # 中文形式：「30 大顶流」「30 个高星」
        for m in re.finditer(r"(\d{2,3})\s*(?:个|大)\s*(?:顶流|高星|核心|成员|内置|通用)", text):
            counts.add(int(m.group(1)))
        # 英文形式：「Bundles 30 top-tier」「Members 30」
        for m in re.finditer(r"(?:Bundles|Members|skills?)\s+(\d{2,3})\b", text):
            counts.add(int(m.group(1)))
        for m in re.finditer(r"\b(\d{2,3})\s+(?:top-tier|Self-Contained|universal workflow)", text):
            counts.add(int(m.group(1)))
        # 徽章 URL 形式：badge/Members-30%20Self--Contained
        for m in re.finditer(r"badge/[A-Za-z]+-(\d{2,3})(?:%20|\b)", text):
            counts.add(int(m.group(1)))
        stale = sorted(c for c in counts if c != n)
        check("%s 计数与 %d 一致" % (fn, n), not stale,
              "发现过时计数: %s" % (stale if stale else "无"))

    # ---- 6. capability-map 表格行数 ----
    print("\n[6] capability-map 表格行数")
    cm = os.path.join(ROOT, "references", "capability-map.md")
    if os.path.isfile(cm):
        rows = [ln for ln in io.open(cm, encoding="utf-8").read().split("\n")
                if re.match(r"^\|\s*\d{2}\s*\|", ln)]
        check("矩阵行数等于技能数", len(rows) == n, "表格 %d 行 vs 技能 %d 个" % (len(rows), n))
        # 序号唯一
        seqs = [re.match(r"^\|\s*(\d{2})\s*\|", ln).group(1) for ln in rows]
        dup = sorted({s for s in seqs if seqs.count(s) > 1})
        check("序号无重复", not dup, "重复: %s" % (", ".join(dup) if dup else "无"))

    return report()


def report():
    print("\n" + "=" * 72)
    total = len(PASS) + len(FAIL)
    if FAIL:
        print("  验收：%d/%d 通过  —— 有 %d 项失败" % (len(PASS), total, len(FAIL)))
        for name, detail in FAIL:
            print("    FAIL: %s  %s" % (name, detail))
        print("=" * 72)
        return 1
    print("  验收：%d/%d 通过" % (len(PASS), total))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
