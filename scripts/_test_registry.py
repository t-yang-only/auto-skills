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
import shutil
import subprocess
import sys
import tempfile

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

    # ---- 3c. description 必须含触发条件 ----
    # description 是 agent 判断「何时加载本技能」的唯一依据；只写「能力是什么」
    # 而不写「什么时候用」，会让技能在真正需要时想不起来被加载。
    print("\n[3c] description 含触发条件线索")
    TRIG = re.compile(r"Use when|Use (this )?(after|before|for|on|during|to)|Triggers|Trigger only|"
                      r"Activate when|whenever|when the user|MUST use this|"
                      r"当|触发|适用于|用于", re.I)
    notrig = [k for k, v in tools.items() if not TRIG.search(v.get("description", ""))]
    check("每个 description 都有触发条件", not notrig,
          "缺触发: %s" % (", ".join(notrig) if notrig else "无"))

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

    # ---- 7. 文档目录树与实际顶层结构一致 ----
    # 目录树是读者理解项目布局的唯一入口；新增目录没写进树会长期不被发现。
    # .evolution 是私有进化区、agent_word 是 nm-skills 运行时台账，
    # 两者都是本地状态、文档有意不列；.git 是版本库元数据。
    print("\n[7] 文档目录树与实际顶层结构一致")
    ALLOW_OMIT = {".evolution", ".git", "agent_word"}
    # 备份/临时产物不是交付物：不写进文档树是正常的，不能因此报「树里缺」。
    # 实测教训：一旦有人在仓库根留了 .bak-* 或 .orig，本段会在任何真实破坏之前
    # 就变红，把「破坏被抓住」误报成「备份文件没写进文档」——负向测试因此失效。
    # 只排除「备份/临时后缀」与「未在树中声明的隐藏文件」两类；
    # .gitignore / .gitattributes 这类会写进树的隐藏文件必须保留在 actual 里，
    # 否则会反过来报「树里多出」。
    NOISE = re.compile(r"\.(bak|orig|tmp|temp|old|new|rej|patch|log)([-.].*)?$", re.I)
    actual = {d for d in os.listdir(ROOT)
              if d not in ALLOW_OMIT and not NOISE.search(d)}
    # 隐藏文件只在「树里明确列了它」时才参与比对（.gitattributes/.gitignore 属交付物，
    # 而编辑器残留的 .foo.swp 之类不该逼着文档去补条目）。
    listed_hidden = set()
    for _fn in ("README.md", "SKILL.md"):
        _p = os.path.join(ROOT, _fn)
        if not os.path.isfile(_p):
            continue
        _t = io.open(_p, encoding="utf-8").read().replace("\r\n", "\n")
        _m = re.search(r"```text\n(.*?)```", _t, re.DOTALL)
        if _m:
            for _ln in _m.group(1).split("\n"):
                _mm = re.match(r"^[├└]──\s+([^\s/]+)", _ln)
                if _mm and _mm.group(1).startswith("."):
                    listed_hidden.add(_mm.group(1))
    actual = {d for d in actual if not d.startswith(".")} | (listed_hidden & set(os.listdir(ROOT)))
    for fn in ("README.md", "SKILL.md"):
        p = os.path.join(ROOT, fn)
        if not os.path.isfile(p):
            check("%s 存在" % fn, False)
            continue
        # 容忍 CRLF：core.autocrlf=true 的机器上检出可能是 CRLF
        text = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")
        m = re.search(r"```text\n(.*?)```", text, re.DOTALL)
        if not m:
            check("%s 有目录树代码块" % fn, False)
            continue
        listed = set()
        for ln in m.group(1).split("\n"):
            mm = re.match(r"^[├└]──\s+([^\s/]+)/?", ln)
            if mm:
                listed.add(mm.group(1))
        missing = sorted(actual - listed)
        extra = sorted(listed - actual)
        check("%s 目录树覆盖全部顶层" % fn, not missing,
              "树里缺: %s" % (", ".join(missing) if missing else "无"))
        check("%s 目录树无虚构条目" % fn, not extra,
              "树里多出: %s" % (", ".join(extra) if extra else "无"))


    # ---- 8. tools/ 目录树成员数等于台账技能数 ----
    # tools/ 段逐条列出全部成员；新增技能只改台账不改树，读者会以为项目里没有它。
    print("\n[8] tools/ 目录树成员数与台账一致")
    for fn in ("README.md", "SKILL.md"):
        fp = os.path.join(ROOT, fn)
        if not os.path.isfile(fp):
            continue
        text = io.open(fp, encoding="utf-8").read().replace("\r\n", "\n")
        m = re.search(r"```text\n(.*?)```", text, re.DOTALL)
        if not m:
            continue
        names, in_tools = [], False
        for ln in m.group(1).split("\n"):
            if re.match(r"^[\u251c\u2514]\u2500\u2500\s+tools/", ln):
                in_tools = True
                continue
            if in_tools and re.match(r"^[\u251c\u2514]\u2500\u2500\s+", ln):
                break
            if in_tools:
                mm = re.match(r"^\u2502\s*[\u251c\u2514]\u2500\u2500\s+([^\s/]+)/", ln)
                if mm:
                    names.append(mm.group(1))
        check("%s 工具树成员数等于台账" % fn, len(names) == n,
              "树里 %d 个 vs 台账 %d 个" % (len(names), n))
    # ---- 9. scripts/ 目录树覆盖全部脚本 ----
    # 2026-09-22 实测：树里只列了 13 个脚本，实际有 17 个——opinion_request.py
    # 是用户可见功能却没进树，两个回归测试也不见踪影。
    print("\n[9] scripts/ 目录树覆盖全部脚本")
    scripts_dir = os.path.join(ROOT, "scripts")
    actual_scripts = set()
    if os.path.isdir(scripts_dir):
        actual_scripts = {f for f in os.listdir(scripts_dir) if f.endswith(".py")}
    for fn in ("README.md", "SKILL.md"):
        fp = os.path.join(ROOT, fn)
        if not os.path.isfile(fp):
            continue
        text = io.open(fp, encoding="utf-8").read().replace("\r\n", "\n")
        m = re.search(r"```text\n(.*?)```", text, re.DOTALL)
        if not m:
            continue
        listed, in_scripts = set(), False
        for ln in m.group(1).split("\n"):
            if re.match(r"^[\u251c\u2514]\u2500\u2500\s+scripts/", ln):
                in_scripts = True
                continue
            if in_scripts and re.match(r"^[\u251c\u2514]\u2500\u2500\s+", ln):
                break
            if in_scripts:
                mm = re.match(r"^\u2502\s*[\u251c\u2514]\u2500\u2500\s+([\w_]+\.py)", ln)
                if mm:
                    listed.add(mm.group(1))
        missing = sorted(actual_scripts - listed)
        check("%s 脚本树覆盖全部 .py" % fn, not missing,
              "未列出: %s" % (missing or "无"))

    # ---- 10. 技能多根寻址：固定根优先 + 动态发现去重 ----
    # 只靠硬编码根会漏掉用户真正在用的 harness（实测本机 20+ 个根里有 17 个盲区），
    # 但「发现了根」和「解析优先级还对」是两件事，必须都断言。
    print("\n[10] 技能多根寻址（固定根优先 + 动态发现去重）")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import auto_router as _ar

        fixed = [os.path.normcase(os.path.abspath(str(r))) for r in _ar.CANDIDATE_ROOTS]
        discovered = [os.path.normcase(os.path.abspath(str(r))) for r in _ar.discover_skill_roots()]
        allroots = [os.path.normcase(os.path.abspath(str(r))) for r in _ar.all_skill_roots()]

        # 隔离 HOME：里面放一个「只在非固定根里存在」的技能，用来证明动态发现真的生效。
        _fake_home = tempfile.mkdtemp(prefix="as-fakehome-")
        _probe_skill = os.path.join(_fake_home, ".fakeharness", "skills", "fake-harness-skill")
        os.makedirs(_probe_skill, exist_ok=True)
        with io.open(os.path.join(_probe_skill, "SKILL.md"), "w", encoding="utf-8", newline="\n") as _f:
            _f.write("---\nname: fake-harness-skill\ndescription: probe\n---\n")

        dup_all = sorted({r for r in allroots if allroots.count(r) > 1})
        check("全部技能根无重复", not dup_all,
              "重复: %s" % (", ".join(dup_all[:3]) if dup_all else "无"))
        check("动态根不与固定根重叠", not (set(discovered) & set(fixed)),
              "重叠: %s" % (", ".join(sorted(set(discovered) & set(fixed))[:3]) or "无"))
        check("固定根排在动态根之前",
              allroots[:len(fixed)] == fixed,
              "前 %d 个不是固定根原序" % len(fixed))
        check("动态发现确实有产出", bool(discovered),
              "发现 %d 个（若本机确实只装一个 harness 可忽略）" % len(discovered))

        # 内置 tools/ 必须赢过任何外部同名副本
        if os.path.isdir(_ar.INTERNAL_TOOLS):
            sample = sorted(d for d in os.listdir(_ar.INTERNAL_TOOLS)
                            if os.path.isdir(os.path.join(_ar.INTERNAL_TOOLS, d)))
            if sample:
                _p, _origin = _ar.resolve_member_path(sample[0])
                check("内置 tools 解析优先于外部根", _origin == "internal_tools",
                      "%s -> %s" % (sample[0], _origin))
        check("未知技能名解析为 missing",
              _ar.resolve_member_path("definitely-not-a-skill-xyz")[0] is None)

        # 解析结果必须落在声明的某个根下面 —— 防止「解析到了，但那个路径
        # 根本不在根列表里」（例如被缓存住、或拼出了越界路径）。
        _stray = []
        for _name in ("ponytail", "nm-skills", "test-driven-development"):
            _p, _o = _ar.resolve_member_path(_name)
            if _p is None:
                continue
            _pp = os.path.normcase(os.path.abspath(str(_p)))
            if not any(_pp.startswith(_r + os.sep) for _r in allroots):
                _stray.append("%s -> %s" % (_name, _p))
        check("解析结果都落在已声明的技能根内", not _stray,
              "; ".join(_stray[:2]) if _stray else "无越界")

        # 动态发现必须真的能解析到技能：在隔离 HOME 里造一个只存在于
        # 非固定根（.fakeharness/skills）的技能，要求它被解析到。
        # 只在固定根上断言的话，「动态发现」整个功能可以坏掉而测试全绿。
        _probe = subprocess.run(
            [sys.executable, "-c",
             "import sys, os; sys.path.insert(0, os.path.join(os.environ['AS_ROOT'], 'scripts'));"
             "import auto_router as a;"
             "p, o = a.resolve_member_path('fake-harness-skill');"
             "print(o); print(p)"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "AS_ROOT": ROOT, "HOME": _fake_home, "USERPROFILE": _fake_home},
        )
        _lines = [l for l in (_probe.stdout or "").splitlines() if l.strip()]
        _ok = len(_lines) >= 2 and _lines[0].strip() == "external_hub" and "fakeharness" in _lines[1]
        check("动态发现的根可被解析到", _ok,
              "stdout=%s stderr=%s" % ((_probe.stdout or "").strip()[:60],
                                       (_probe.stderr or "").strip()[:60]))
        shutil.rmtree(_fake_home, ignore_errors=True)
    except Exception as e:
        check("技能多根寻址可自检", False, "导入/执行失败: %s" % e)

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
