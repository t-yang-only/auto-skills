#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nm_register 全部子命令的冒烟测试 —— 最广也最快的一层回归守卫。

为什么需要
==========
其余测试各自盯着一个契约（互斥、并发、失败容错…），但没有一条覆盖
「每个子命令还能不能跑」。

2026-10-02 我改了 FileMutex、把落库移出临界区、改了 gc 的过期判据、
调了 claim/done 的结构 —— 这些改动横跨几乎所有子命令，而当时唯一的
验证是「跑一下看看吧」。这个文件把那次的临时检查固定下来。

它盯三件事，都是 agent 日常真正会踩的：
  1. **不能有裸 traceback**。子命令抛栈对使用者毫无帮助，等于没做错误处理。
  2. **退出码要能区分结果**。`check-file` 有冲突必须非零（否则调用方会
     以为可以安全编辑），无冲突必须为零。
  3. **正向路径要有可读的输出**，不能静默成功。

刻意不写死输出文案的全文，只断言「含某个关键标记」与「退出码」——
文案会改，行为契约不该跟着漂。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "nm_register.py"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if (detail and not ok) else ""))


def run(root, args, timeout=90):
    p = subprocess.run([sys.executable, str(SCRIPT), "--root", root] + args,
                       capture_output=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    if not SCRIPT.exists():
        print("  [SKIP] 找不到 %s" % SCRIPT)
        print("\nRESULT: SKIP (1/1)")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        # 装置：先认领一个任务，后续子命令才有东西可操作
        rc, out = run(tmp, ["claim", "--task-id", "T-SMOKE",
                            "--task", "冒烟测试用任务",
                            "--client", "S", "--files", "scripts/smoke_target.py"])
        check("装置：claim 成功（否则后续判据不具判别力）",
              rc == 0 and "认领成功" in out, "rc=%s" % rc)

        cases = [
            # (名称, 参数, 期望rc, 必须出现的标记)
            ("board 能列出看板", ["board"], 0, "看板"),
            ("whoami 能报当前身份", ["whoami"], 0, "agent_word"),
            ("log 能列工作日志", ["log", "--limit", "5"], 0, "登记"),
            ("renew 能续租", ["renew", "--task-id", "T-SMOKE",
                             "--extend", "10"], 0, "续期"),
            ("gc 能跑（无可清理时也要正常收尾）", ["gc"], 0, "僵尸锁"),
            ("check-file 检出已占用文件", ["check-file",
                                        "--files", "scripts/smoke_target.py"], 1, "冲突"),
            ("check-file 对空闲文件放行", ["check-file",
                                        "--files", "scripts/definitely_free.py"], 0, "检查通过"),
            ("release 能释放", ["release", "--task-id", "T-SMOKE"], 0, "释放"),
        ]

        for name, args, want_rc, marker in cases:
            rc, out = run(tmp, args)
            check(name, rc == want_rc and marker in out,
                  "rc=%s(期望%s) 含'%s'=%s" % (rc, want_rc, marker, marker in out))

        # 全部子命令都不得抛裸 traceback
        # （标签带上参数，否则两条 check-file 用例会同名 —— 真失败时分不清是哪条）
        for name, args, _, _ in cases:
            rc, out = run(tmp, args)
            check("%s %s 不抛裸 traceback" % (args[0], " ".join(args[1:])[:24]),
                  "Traceback (most recent call last)" not in out,
                  out[-160:] if "Traceback" in out else "")

        # 重复操作：同一任务连释放两次，第二次应明确说「无活跃锁」而非报错
        rc, out = run(tmp, ["release", "--task-id", "T-SMOKE"])
        check("重复释放给出明确提示（幂等、不崩）",
              rc == 0 and ("并无活跃锁" in out or "已释放" in out),
              "rc=%s %s" % (rc, out.strip()[:100]))

        # 无参数运行：应给帮助而不是静默退出或抛栈
        rc, out = run(tmp, [])
        check("无参数运行给出帮助（不静默、不抛栈）",
              "usage" in out.lower() and "Traceback" not in out,
              "rc=%s 输出长度=%d" % (rc, len(out)))

    # ── CLI 契约：--help 必须可调用且**零副作用**（2026-10-02 新增） ──
    # 由来：审计 CLI 可调用性时用 `--help` 逐个探，结果
    # `pull_persona_traits.py` 把 `--help` 当成"知识库路径"参数、**真的跑了一次
    # 人格特性拉取并覆写缓存**；`hk_link_live.py` 也照跑了一次自检。
    # 「探索即执行」与此前修过的「写操作没有标记」是同一类问题：
    # 使用者（人或 agent）看一眼用法，不该产生任何后果。
    #
    # 判据必须锚**副作用**而不是 rc —— 只看 rc 的话，"跑了一遍还给 0" 会假绿。
    ROOT_HERE = Path(__file__).resolve().parent.parent
    WATCH = [ROOT_HERE / ".evolution" / "profile",
             ROOT_HERE / ".evolution"]

    def _snap():
        """快照「可能被副作用改到」的文件 → (路径, mtime_ns, size)。"""
        out = {}
        for d in WATCH:
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.is_file():
                    try:
                        st = f.stat()
                        out[str(f)] = (st.st_mtime_ns, st.st_size)
                    except OSError:
                        pass
        return out

    import glob as _glob
    entries = []
    for _p in sorted(_glob.glob(str(ROOT_HERE / "scripts" / "*.py"))):
        _n = Path(_p).name
        if _n.startswith("_test_"):
            continue
        try:
            if "__main__" in Path(_p).read_text(encoding="utf-8"):
                entries.append(_p)
        except OSError:
            pass

    bad_rc, dirty = [], []
    for _p in entries:
        before = _snap()
        r = subprocess.run([sys.executable, _p, "--help"],
                           capture_output=True, encoding="utf-8",
                           errors="replace", timeout=90)
        after = _snap()
        if r.returncode != 0:
            bad_rc.append("%s(rc=%s)" % (Path(_p).name, r.returncode))
        if before != after:
            changed = [Path(k).name for k in set(before) | set(after)
                       if before.get(k) != after.get(k)]
            dirty.append("%s→%s" % (Path(_p).name, changed[:3]))

    check("扫到了 CLI 入口（否则本条不具判别力）", len(entries) > 0,
          "扫到 %d 个" % len(entries))
    check("每个 CLI 入口 `--help` 都以 rc=0 退出", not bad_rc, bad_rc)
    check("每个 CLI 入口 `--help` 都**不产生副作用**（文件未被改写）",
          not dirty, dirty)

    # ── 通知契约：给人看的通知必须简洁（2026-10-02 新增） ──
    # 见 SKILL.md 7.4。通知是给人看的，混进机器细节的后果是"人干脆不读了"——
    # 那比不发还糟。判据锚**可见内容**（字符数/行数/不该出现的形态），
    # 不锚实现细节（改模板措辞不该让判据变红，超出长度才该）。
    import importlib.util as _ilu
    _np = None
    try:
        _spec = _ilu.spec_from_file_location(
            "_np_probe", str(ROOT_HERE / "scripts" / "notify_push.py"))
        _np = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_np)
    except Exception as e:
        check("能加载 notify_push（否则通知契约不具判别力）", False,
              "%s: %s" % (type(e).__name__, e))

    if _np is not None:
        _cap = {}
        # 拦下真正的发送，只看它**准备发什么**
        _np.broadcast_message = lambda title, desp, tags=None, target_channel=None: (
            _cap.update(t=title, d=desp) or {"ok": True})
        _np.notify_task_complete(
            task_name="契约探针",
            project_name="probe",
            summary="这是一段特意写得很长的说明文字，用来验证通知正文会被截断。" * 4,
            deliverables=["第一条交付物", "第二条交付物", "第三条不该出现"],
            git_commit="abcdef1234567890",
        )
        _d = _cap.get("d", "")
        check("通知正文 ≤280 字符（超了人就不读了）", len(_d) <= 280,
              "%d 字符" % len(_d))
        check("通知正文 ≤5 行", len(_d.splitlines()) <= 5,
              "%d 行" % len(_d.splitlines()))
        _bad = [k for k in ("## ", "**", "```", "自动化广播", "SUCCESS") if k in _d]
        check("通知正文不含重标题/加粗/代码块/固定签名/恒真状态行",
              not _bad, _bad)
        check("通知正文确实有内容（判据不恒绿）", len(_d.strip()) > 0,
              "%d 字符" % len(_d))

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())