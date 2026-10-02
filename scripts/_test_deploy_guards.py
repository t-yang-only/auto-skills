#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wizard_setup 的两个新守卫的单元测试（2026-10-01 缺陷修复配套）。

覆盖：
  1. **purge 必须跳过链接形态的根** —— 否则它会经 junction 把快照的凭据
     硬链接删掉，落库链路全线失效（实测 P1）。
  2. **KNOWN_AGENT_PATHS 必须含 Gemini CLI** —— 漏一个 harness 会让
     --link / --check-deploy / purge 三处守卫同时失效（实测：纳入后立刻
     从 .gemini 清出 6 个实体凭据残留）。
  3. **check_deployment 的「含凭据」检测必须真的会报**，且
     **--check-deploy 见到 leaked 必须 exit 1**（报出来却不拦住＝没有门禁）。
     含正向对照（无凭据不能报）与链接形态豁免（凭据属快照，是设计使然）。

为什么是单元测试而不是改 harness 根的端到端测试：那需要 unlink/deploy 真实
harness 根，副作用大且不可在 CI 跑。这里用「合成根 + monkeypatch
KNOWN_AGENT_PATHS」把判据本身验穿，不触碰任何真实 harness 根。

⚠️ 一条必须记住的教训（本条目的由来）：本文件曾声称第 3 项
「端到端的负向验证已人工做过一次（副本形态放真凭据 → 守卫报 🔴 含凭据）」，
但那次人工验证把探针放在了 `<root>/skills/_guardtest/config/db.password`，
而守卫查的是 `<root>/skills/auto-skills/config/db.password` —— **路径对不上，
守卫根本没被触发**，当时得到的「全部根内容一致、无凭据残留」是无意义的。
文档里写「验证过了」而实际没验到，比不写更危险：后来人会据此跳过这一步。
现在它由自动化判据守着，且带变异检查。
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "wizard_setup.py"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if detail else ""))


def main():
    spec = importlib.util.spec_from_file_location("wiz", SCRIPT)
    wiz = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wiz)

    # ---- 1. 链接形态跳过 ----
    names = [n for n, _ in wiz.KNOWN_AGENT_PATHS]
    check("KNOWN_AGENT_PATHS 含 Gemini CLI", any("Gemini" in n for n in names), names)

    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp)
        # 造一个「链接形态」的根：target 是指向别处的 junction
        real = home / "real_snapshot"
        (real / "config").mkdir(parents=True)
        (real / "config" / "db.password").write_text("secret", encoding="utf-8")
        link_root = home / "linked_harness"
        link_root.mkdir()
        target = link_root / "auto-skills"
        rc = os.system('cmd /c mklink /J "%s" "%s" >nul 2>&1' % (target, real))
        is_junction = (rc == 0 and wiz._is_junction(target))
        check("测试装置：junction 建成功（否则本条不具判别力）", is_junction,
              "rc=%s" % rc)
        if not is_junction:
            print("    跳过后续判据（非 Windows 或无 junction 权限）")
        else:
            # junction 里的凭据「看起来存在」
            check("经 junction 能看到凭据（正是会被误删的形态）",
                  (target / "config" / "db.password").exists())
            # 调 purge：必须跳过，不能删
            saved = wiz.KNOWN_AGENT_PATHS
            try:
                wiz.KNOWN_AGENT_PATHS = [("测试链接根", link_root)]
                removed = wiz.purge_deployed_secrets(verbose=False)
            finally:
                wiz.KNOWN_AGENT_PATHS = saved
            check("purge 对链接形态的根返回空（不移交任何删除）",
                  removed == [], removed)
            check("purge 后真源凭据仍在（没被顺着链接删掉）",
                  (real / "config" / "db.password").exists())

        # ---- 2. 副本形态必须被清（守卫不能变成永真）----
        copy_root = home / "copy_harness"
        (copy_root / "auto-skills" / "config").mkdir(parents=True)
        (copy_root / "auto-skills" / "config" / "db.password").write_text(
            "stale", encoding="utf-8")
        saved = wiz.KNOWN_AGENT_PATHS
        try:
            wiz.KNOWN_AGENT_PATHS = [("测试副本根", copy_root)]
            removed = wiz.purge_deployed_secrets(verbose=False)
        finally:
            wiz.KNOWN_AGENT_PATHS = saved
        check("purge 对副本形态仍会清（守卫没被改成永真）",
              len(removed) == 1, removed)
        check("清后副本里确实没了",
              not (copy_root / "auto-skills" / "config" / "db.password").exists())

    # ---- 3. check_deployment 的「含凭据」检测必须真的会报 ----
    #
    # 这一条补的是本文件 docstring 曾声称「已人工验证过」但**实际从未有效验证**
    # 的缺口：那次人工验证把探针放在了 <root>/skills/_guardtest/config/db.password，
    # 而守卫查的是 <root>/skills/auto-skills/config/db.password —— 路径对不上，
    # 守卫根本没被触发，得到的「OK」是无意义的。
    # 「校验器自己必须被负向测试打过」这条纪律在这里就是针对这种情况。
    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp)
        saved = wiz.KNOWN_AGENT_PATHS
        try:
            # 3a. 负向：副本形态 + 真凭据 → 必须报 leaked
            leak_root = home / "leak_harness"
            (leak_root / "auto-skills" / "config").mkdir(parents=True)
            (leak_root / "auto-skills" / "config" / "db.password").write_text(
                "leaked-secret", encoding="utf-8")
            wiz.KNOWN_AGENT_PATHS = [("测试副本根", leak_root)]
            rows = wiz.check_deployment(verbose=False)
            st = rows[0]["status"] if rows else "(无行)"
            check("副本形态含凭据 → 判为 leaked", st == "leaked", st)
            check("leaked 行里列出了具体文件",
                  "config/db.password" in (rows[0].get("leaked") or []),
                  rows[0].get("leaked") if rows else None)
            # 凭据残留优先级必须高于「内容不同步」：这个副本缺一大堆文件，
            # 若被降级成 stale，使用者就看不到「这里有真凭据」这句关键信息。
            check("leaked 优先级高于 stale（否则关键信息被淹没）",
                  st == "leaked")

            # 3b. 正向对照：同样的根但**没有**凭据 → 不能报 leaked
            #     （证明判据不是恒红；没有这一条，3a 通过也说明不了什么）
            clean_root = home / "clean_harness"
            (clean_root / "auto-skills" / "config").mkdir(parents=True)
            wiz.KNOWN_AGENT_PATHS = [("测试净副本根", clean_root)]
            rows2 = wiz.check_deployment(verbose=False)
            st2 = rows2[0]["status"] if rows2 else "(无行)"
            check("无凭据的副本不报 leaked（判据不是恒红）",
                  st2 != "leaked", st2)

            # 3c. 链接形态豁免：链接根下的凭据属于快照（设计使然），不能报 leaked
            snap = home / "snap_for_link"
            (snap / "config").mkdir(parents=True)
            (snap / "config" / "db.password").write_text("x", encoding="utf-8")
            (snap / "SKILL.md").write_text("# x", encoding="utf-8")
            linkroot = home / "link_harness"
            linkroot.mkdir()
            lt = linkroot / "auto-skills"
            rc2 = os.system('cmd /c mklink /J "%s" "%s" >nul 2>&1' % (lt, snap))
            if rc2 == 0 and wiz._is_junction(lt):
                wiz.KNOWN_AGENT_PATHS = [("测试链接根", linkroot)]
                rows3 = wiz.check_deployment(verbose=False)
                st3 = rows3[0]["status"] if rows3 else "(无行)"
                check("链接形态不报 leaked（凭据属快照是设计使然）",
                      st3 != "leaked", st3)
            else:
                print("  [SKIP] 链接豁免判据（junction 未建成）")

            # 3d. 退出码：--check-deploy 见到 leaked 必须 exit 1
            #     否则守卫会「报出来但放过去」，等于没有门禁。
            wiz.KNOWN_AGENT_PATHS = [("测试副本根", leak_root)]
            saved_argv = sys.argv
            try:
                sys.argv = ["wizard_setup.py", "--check-deploy"]
                code = None
                try:
                    wiz.main()
                    code = 0
                except SystemExit as e:
                    code = e.code
            finally:
                sys.argv = saved_argv
            check("--check-deploy 见 leaked 退出码为 1", code == 1, "exit=%s" % code)
        finally:
            wiz.KNOWN_AGENT_PATHS = saved

    # ---- 4. 变异检查：把 leaked 计算废掉，3a 必须变红 ----
    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp)
        leak_root = home / "leak2"
        (leak_root / "auto-skills" / "config").mkdir(parents=True)
        (leak_root / "auto-skills" / "config" / "db.password").write_text(
            "s", encoding="utf-8")
        saved = wiz.KNOWN_AGENT_PATHS
        saved_secrets = wiz.SECRET_FILES
        try:
            wiz.KNOWN_AGENT_PATHS = [("测试副本根", leak_root)]
            wiz.SECRET_FILES = ()          # 变异：判据看不到任何凭据
            rows = wiz.check_deployment(verbose=False)
            st = rows[0]["status"] if rows else "(无行)"
            check("变异：清空 SECRET_FILES 后不再报 leaked（证明判据有效）",
                  st != "leaked", st)
        finally:
            wiz.SECRET_FILES = saved_secrets
            wiz.KNOWN_AGENT_PATHS = saved

    # ── 新不变式（2026-10-02）：凭据只存私有层，不得再复制进各 Agent 根 ──
    # 由来：凭据原本在 config/ 下、并被硬链接进部署快照，于是 7 个根各持一份。
    # 现改为只存 .evolution/secrets/（私有层，随私人库多端同步），各根经
    # snapshot→真源 的 junction 读取。这条守卫防的是「以后有人又把凭据拷回
    # config/ 下」——那样会退回"七处各一份、改一处不同步"的老问题。
    LEGACY = ("config/db.password", "config/gateway.token", "config/gateway.url")
    NEWREL = pathlib.Path(".evolution") / "secrets" / "gateway.token"

    def _scan(paths):
        with_legacy, missing_new, n = [], [], 0
        for name, p in paths:
            root = p / "auto-skills"
            if not root.exists():
                continue
            n += 1
            if any((root / r).exists() for r in LEGACY):
                with_legacy.append(name)
            if not (root / NEWREL).exists():
                missing_new.append(name)
        return n, with_legacy, missing_new

    n_scanned, with_legacy, missing_new = _scan(wiz.KNOWN_AGENT_PATHS)
    check("扫到了 Agent 根（否则本条不具判别力）", n_scanned > 0,
          "扫到 %d 个" % n_scanned)
    check("没有任何 Agent 根留存 config/ 下的旧凭据", not with_legacy, with_legacy)
    check("每个 Agent 根都能经私有层读到凭据", not missing_new, missing_new)

    # 变异：造一个「旧路径又有凭据」的假根，扫描必须发现它。
    # 没有这一步，上面两条断言在扫描函数写坏时也会全绿。
    with tempfile.TemporaryDirectory() as tmp:
        fake = pathlib.Path(tmp) / "fake"
        (fake / "auto-skills" / "config").mkdir(parents=True)
        (fake / "auto-skills" / "config" / "gateway.token").write_text(
            "x", encoding="utf-8")
        _n, _wl, _mn = _scan([("变异根", fake)])
        check("变异：旧路径出现凭据时能被发现（证明判据有效）",
              _wl == ["变异根"], _wl)
        check("变异：同时该根被判为缺少新路径凭据（两个方向都在测）",
              _mn == ["变异根"], _mn)

    # ── 私有层（.evolution）的同步边界（2026-10-02） ──
    # 私有库是多端配置同步的核心依赖，它最容易出的两类问题是**方向相反**的：
    #   ① 把「每台机器各自产生」的运行时状态也同步上去 → 多端来回冲突
    #   ② 把 secrets/ 也排除掉 → 凭据根本同步不出去（换设备就配不起来）
    # 因此必须成对断言；只测一条会把另一条放过去。
    ROOT = pathlib.Path(__file__).resolve().parent.parent
    evo = ROOT / ".evolution"
    RUNTIME = ("db_spool", "db_health.json", "db_cleanup.json",
               "db_sync_errors.log", "journal", "archive")
    SECRET_REL = ("secrets/notify_channels.json", "secrets/db.password")

    if not (evo / ".git").exists():
        print("  [SKIP] 私有库未初始化（新装默认状态）—— 私有层断言不具判别力")
    else:
        def _ignored(rel):
            r = subprocess.run(
                ["git", "-C", str(evo), "-c", "safe.directory=*",
                 "check-ignore", "-q", rel],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return r.returncode == 0

        rt_bad = [r for r in RUNTIME if not _ignored(r)]
        check("私有库排除运行期状态（否则多端同步必然互相冲突）",
              not rt_bad, rt_bad)

        sec_bad = [s for s in SECRET_REL
                   if (evo / s).exists() and _ignored(s)]
        check("私有库的 secrets/ 未被排除（凭据必须能同步出去）",
              not sec_bad, sec_bad)

        # 变异：_ignored 必须真的有判别力。README.md 是被跟踪的普通文件，
        # 它**不该**被判为忽略；若 _ignored 恒真，这条会红。
        check("变异：未被忽略的文件被判为「未忽略」（证明 _ignored 有判别力）",
              not _ignored("README.md"), "README.md")

    # ── 公开库：凭据路径必须在 .gitignore 里（结构不变式） ──
    # 不复刻提交钩子的内容扫描（那是另一套职责），这里只钉住"这些路径
    # 结构上不可能被提交"——这条没有任何其它地方覆盖。
    gi = ROOT / ".gitignore"
    if gi.exists():
        gtxt = gi.read_text(encoding="utf-8")
        must_ignore = [".evolution", "config/db.password",
                       "config/gateway.token", "config/gateway.url"]
        miss = [m for m in must_ignore if m not in gtxt]
        check("公开库 .gitignore 覆盖全部凭据路径", not miss, miss)

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
