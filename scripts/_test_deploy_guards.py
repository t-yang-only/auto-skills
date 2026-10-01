#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wizard_setup 的两个新守卫的单元测试（2026-10-01 缺陷修复配套）。

覆盖：
  1. **purge 必须跳过链接形态的根** —— 否则它会经 junction 把快照的凭据
     硬链接删掉，落库链路全线失效（实测 P1）。
  2. **KNOWN_AGENT_PATHS 必须含 Gemini CLI** —— 漏一个 harness 会让
     --link / --check-deploy / purge 三处守卫同时失效（实测：纳入后立刻
     从 .gemini 清出 6 个实体凭据残留）。

为什么是单元测试而不是改 harness 根的端到端测试：那需要 unlink/deploy 真实
harness 根，副作用大且不可在 CI 跑。这里只验证判据本身（不看输出、只看行为），
端到端的负向验证已人工做过一次（副本形态放真凭据 → 守卫报 🔴 含凭据）。
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

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
