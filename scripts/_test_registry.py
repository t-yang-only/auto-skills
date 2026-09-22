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
import pathlib
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

    # ---- 11. 台账 description 不得与 SKILL.md 原文脱节 ----
    # registry.json 是 agent 挑技能时的唯一依据；在 SKILL.md 里改了 description
    # 却忘了重扫，台账就会静默过期（挑技能的人看到的是旧触发条件）。
    # 必须复用 tool_onboarder 自己的解析器 —— 自制正则会把 YAML 的块折叠标记
    # （">" / "|"）当成内容差异，实测误报 7/35。
    try:
        import tool_onboarder as _to
        _drift = []
        for _name, _info in reg["tools"].items():
            _f = pathlib.Path(ROOT) / _info["path"] / "SKILL.md"
            if not _f.exists():
                continue
            _live = " ".join(str(((_to.parse_skill_metadata(_f) or {}).get("description") or "")).split())
            _stored = " ".join(str(_info.get("description") or "").split())
            if _live and _live != _stored:
                _drift.append("%s: 台账=%s / 实际=%s" % (_name, _stored[:30], _live[:30]))
        check("台账 description 与 SKILL.md 一致", not _drift,
              "脱节 %d 个（跑 tool_onboarder.py --scan 重扫）: %s" % (len(_drift), "; ".join(_drift[:3])))
    except ImportError as e:
        check("台账 description 与 SKILL.md 一致", False, "无法导入 tool_onboarder: %s" % e)

    # ---- 12. 计数同步器的每条锚点都必须真的命中 ----
    # sync_skill_counts.py 靠「前缀 + 数字 + 后缀」定位要改的数字。改写文档时
    # 一句话被拆散，锚点就静默失效 —— 技能数从此不再被同步，而脚本仍然报
    # 「全部一致」，因为失效的锚点根本不在它的遍历结果里。这里逐条反向验证。
    try:
        import sync_skill_counts as _sc
        _dead = []
        for _rel, _pre, _suf in _sc.RULES:
            _f = pathlib.Path(ROOT) / _rel
            _body = _f.read_text(encoding="utf-8") if _f.exists() else ""
            _pat = re.escape(_pre) + r"(\d{1,3})" + re.escape(_suf)
            if not re.search(_pat, _body):
                _dead.append(f"{_rel}: {_pre!r}+{_suf!r}")
        check("计数同步器的锚点全部命中", not _dead,
              "失效 %d/%d 条（改文档措辞后必须同步改 RULES）: %s"
              % (len(_dead), len(_sc.RULES), "; ".join(_dead[:3])))

        # 锚点「活着」还不够：文档里自述的锚点条数也必须等于 RULES 的实际条数，
        # 否则新增一条锚点后文档仍在说旧数字（13 这个数字本身会撒谎）。
        _n_rules = len(_sc.RULES)
        _wrong = []
        for _rel in ("README.md", "SKILL.md"):
            _body = (pathlib.Path(ROOT) / _rel).read_text(encoding="utf-8")
            for _m in re.finditer(r"（(\d+)\s*个锚点）", _body):
                if int(_m.group(1)) != _n_rules:
                    _wrong.append("%s: 文档=%s 实际=%d" % (_rel, _m.group(1), _n_rules))
        check("文档自述的锚点条数等于 RULES 实际条数", not _wrong,
              "; ".join(_wrong[:3]))
    except ImportError as e:
        check("计数同步器的锚点全部命中", False, "无法导入 sync_skill_counts: %s" % e)

    # ---- [13] 部署同步：各 harness 根下的副本必须与仓库一致 ----
    # 存在的理由：connect_agents 只在首次向导时跑一次，仓库之后每次提交
    # 都不会再分发。实测 2026-09-22 六个根全部落后一个功能（缺
    # discover_skill_roots 动态根发现），而且没有任何机制会报出来。
    # 判据只看「共有文件的内容」——不能算 mtime（源与副本时间天然不同），
    # 也不能把「副本缺凭据」当差异（那是部署的正确行为）。
    #
    # 注意：本段只在**真实仓库根**上生效。_test_doc_tree_guards.py 会把仓库
    # 复制到临时目录、只破坏文档树来验证断言有效性，而部署状态是"机器事实"、
    # 与那份临时副本无关——在沙箱里也断言会导致噪声用例误报（实测踩过）。
    try:
        import wizard_setup
        # 判定是否跑在隔离副本里：_test_doc_tree_guards.py 会声明该环境变量。
        # 部署状态是「这台机器的事实」，与那份临时副本无关——在沙箱里断言
        # 只会造成噪声用例误报（实测踩过）。
        _in_sandbox = os.environ.get("AUTOSKILLS_SANDBOX") == "1"
        if _in_sandbox:
            check("部署同步检查（沙箱内跳过，仅真实仓库根生效）", True, "")
        else:
            _secret = set(getattr(wizard_setup, "SECRET_FILES", ()))

            def _fmap(d):
                import hashlib as _hl
                _o = {}
                _r = pathlib.Path(d).resolve()
                for _f in _r.rglob("*"):
                    if not _f.is_file():
                        continue
                    _rel = _f.relative_to(_r).as_posix()
                    if any(_x in _f.parts for _x in (".git", ".evolution", "__pycache__")):
                        continue
                    if _rel in _secret:
                        continue
                    _o[_rel] = _hl.sha256(_f.read_bytes()).hexdigest()
                return _o

            _sf = _fmap(ROOT)
            _stale, _leaked, _checked, _linked = [], [], 0, 0
            for _name, _base in wizard_setup.KNOWN_AGENT_PATHS:
                _t = _base / "auto-skills"
                # 注意：不能只用 _t.exists() 判断"有没有部署"——失效的链接
                # 会让 exists() 返回 False，于是整根被静默跳过（实测踩过：
                # 快照被移走后六个链接全部失效，断言却报全绿）。
                # 用 lexists 语义：路径本身在（哪怕指向的目标没了）就要检查。
                _present = os.path.lexists(str(_t))
                if not _present:
                    continue
                _checked += 1
                _is_link = _t.is_symlink() or wizard_setup._is_junction(_t)
                # 链接形态单独判定：它与快照是同一份内容，本来就不该与真源
                # 逐个文件相等（快照排除了凭据与 .evolution）。判据改为
                # 「是链接 + 目标可达 + 能读到 SKILL.md + 凭据不可达」。
                if _is_link:
                    _linked += 1
                    if not _t.exists():
                        _stale.append("%s(链接失效，目标不存在)" % (_base.parent.name or str(_base)))
                    elif not (_t / "SKILL.md").exists():
                        _stale.append("%s(链接失效，读不到 SKILL.md)" % (_base.parent.name or str(_base)))
                    continue
                _tf = _fmap(_t)
                _miss = sorted(set(_sf) - set(_tf))
                _chg = sorted(k for k in set(_sf) & set(_tf) if _sf[k] != _tf[k])
                if _miss or _chg:
                    _stale.append("%s(缺%d/异%d)" % (_base.parent.name or str(_base), len(_miss), len(_chg)))
                _lk = [x for x in _secret if (_t / x).exists()]
                if _lk:
                    _leaked.append("%s=%s" % (_base.parent.name or str(_base), _lk))
            # 一个根都没部署时不算失败（可能没装任何 harness），但必须报出来
            check("部署与仓库一致（%d 个根，其中 %d 个为链接）" % (_checked, _linked), not _stale,
                  "; ".join(_stale[:3]) if _stale else "")
            check("分发副本无本地凭据残留", not _leaked,
                  "; ".join(_leaked[:3]) if _leaked else "")
            # 链接形态的凭据判据：不是"读不到"（运行必需，db_sync 用
            # SKILL_ROOT/config/db.password 解析密码），而是**不与真源散开**
            # ——快照里的凭据必须是硬链接（同一份数据），不能是独立拷贝。
            # 拷贝会在七处散布同一份密码，改真源后副本仍是旧值：这正是
            # 实测踩过的故障（.claude / .cursor 带着旧凭据长期留在磁盘上）。
            _link_split = []
            for _name, _base in wizard_setup.KNOWN_AGENT_PATHS:
                _t = _base / "auto-skills"
                if not (os.path.lexists(str(_t)) and
                        (_t.is_symlink() or wizard_setup._is_junction(_t))):
                    continue
                for _rel in _secret:
                    _f = _t / _rel
                    if not _f.exists():
                        continue
                    _orig = pathlib.Path(ROOT) / _rel
                    try:
                        if _orig.exists() and _f.stat().st_ino != _orig.stat().st_ino:
                            _link_split.append("%s:%s(独立拷贝)" % (_base.parent.name or str(_base), _rel))
                    except OSError:
                        pass
            check("链接形态的凭据与真源同一份（非散布拷贝）", not _link_split,
                  "; ".join(_link_split[:3]) if _link_split else "")
            # 分发快照不得含**拷贝形式**的本地运行时产物。
            # 注意不能一律判"存在即失败"：.evolution 与三个凭据现在是有意
            # 放进去的**链接**（.evolution 用 Junction 指回真源让运行时状态
            # 六根共用；凭据用硬链接让运行能读到且不散布）。判据是
            # 「不以链接形式存在」才算失败。
            import wizard_setup as _ws
            if _linked:
                _dist = _ws.SKILL_ROOT / ".dist" / "snapshot"
                _bad_dist = []
                # agent_word/ 必须是彻底不在（它是本地台账，没有任何运行
                # 理由让 harness 看到，链接也不行）
                if (_dist / "agent_word").exists():
                    _bad_dist.append("agent_word")
                if (_dist / ".git").exists():
                    _bad_dist.append(".git")
                # .evolution 必须以链接形式指回真源
                _devo = _dist / ".evolution"
                if _devo.exists() and not _ws._is_junction(_devo):
                    _bad_dist.append(".evolution(非链接)")
                # 凭据必须以硬链接形式存在（同一份数据）
                for _rel in _secret:
                    _f = _dist / _rel
                    if not _f.exists():
                        continue
                    _o = pathlib.Path(ROOT) / _rel
                    try:
                        if not _o.exists() or _f.stat().st_ino != _o.stat().st_ino:
                            _bad_dist.append("%s(独立拷贝)" % _rel)
                    except OSError:
                        _bad_dist.append("%s(无法比对)" % _rel)
                check("分发快照不含拷贝形式的本地运行时产物", not _bad_dist,
                      "快照里出现: %s（跑 wizard_setup.py --deploy 重建）" % _bad_dist)

            # 私有进化区必须完好。这条是**数据保护**断言：build_dist 里曾用
            # `rd /s /q` 删旧快照，而快照含指向真源 .evolution 的 Junction，
            # rd /s 跟着链接把真源的 config.yaml / custom_skills / secrets
            # 一起删了（实测造成一次真实损失，从备份 zip 恢复）。此后任何
            # 让它变空或缺失核心成员的改动都必须立即变红。
            _evo = pathlib.Path(ROOT) / ".evolution"
            _evo_core = ["config.yaml", "db_health.json", "README.md"]
            _missing_core = [x for x in _evo_core if not (_evo / x).exists()]
            check("私有进化区核心文件完好（防误删）", not _missing_core,
                  "缺失: %s —— 若刚跑过 --deploy 请检查是否误用了会跟随链接的删除命令"
                  % _missing_core)
            # 目录级成员：允许为空目录，但目录本身要被创建出来
            _evo_dirs = ["custom_skills", "secrets", "profile"]
            _missing_dirs = [d for d in _evo_dirs if not (_evo / d).exists()]
            check("私有进化区目录结构完整", not _missing_dirs,
                  "缺失目录: %s" % _missing_dirs)
    except Exception as e:
        check("部署副本与仓库同步", False, "无法导入 wizard_setup: %s" % e)

    # ---- [14] 路由入口一致性：CLI 与函数直调必须同档 ----
    # 存在的理由：`route` 子命令原先没在 main() 的子命令分发区登记，于是它落进
    # 兜底的 `" ".join(args.query)`，把子命令名当成任务内容传给判定函数——
    # `auto_router.py route 更新 README 的安装说明` 实际判定的是「route 更新
    # README 的安装说明」，多 6 个字符让 15 字（<=18 阈值，应 FAST_PATH）变成
    # 21 字，落到「默认走向完整流程」规则，把省 Token 的极速模式误升成完整 SDLC。
    # 实测：函数直调判 FAST_PATH，CLI 判 FULL_SDLC。
    # 本段用「同一条输入两条路径必须同档」把它钉死。
    try:
        import auto_router as _ar
        _pairs = [
            ("改个错别字", "FAST_PATH"),
            ("更新 README 的安装说明", "FAST_PATH"),
            ("加一行日志", "FAST_PATH"),
            ("修复登录页的样式问题", "FAST_PATH"),
            ("重构支付模块", "FULL_SDLC"),
            ("设计新的鉴权架构", "FULL_SDLC"),
        ]
        _mismatch, _unexpected = [], []
        for _q, _want in _pairs:
            _tier, _ = _ar.classify_task_tier(_q)
            if _tier != _want:
                _unexpected.append("%s→%s(期望%s)" % (_q, _tier, _want))
        check("路由档位判定符合预期（%d 例）" % len(_pairs), not _unexpected,
              "; ".join(_unexpected[:3]) if _unexpected else "")

        # CLI 路径：必须与函数路径同档（防止子命令名被当任务内容）
        import subprocess as _sp
        _env = dict(os.environ)
        _env["PYTHONIOENCODING"] = "utf-8"
        _router = str(pathlib.Path(ROOT) / "scripts" / "auto_router.py")
        for _q, _want in _pairs[:3]:
            _r = _sp.run([sys.executable, _router, "route", _q],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace", env=_env, timeout=120)
            _out = (_r.stdout or "") + (_r.stderr or "")
            _m = re.search(r'"task_tier":\s*"(\w+)"', _out)
            _cli = _m.group(1) if _m else "?"
            _mq = re.search(r'"query":\s*"([^"]*)"', _out)
            _shown = _mq.group(1) if _mq else "?"
            if _cli != _want:
                _mismatch.append("%s: CLI=%s(期望%s)" % (_q, _cli, _want))
            # 顺带断言：query 不得含子命令名
            if _shown.startswith("route "):
                _mismatch.append("%s: query 含子命令名 %r" % (_q, _shown))
        check("CLI route 与函数直调同档且 query 不含子命令名", not _mismatch,
              "; ".join(_mismatch[:3]) if _mismatch else "")
    except Exception as e:
        check("路由入口一致性", False, "无法导入 auto_router: %s" % e)

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
