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

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
