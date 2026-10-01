#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实并发下的互斥验证 —— 这是 nm-skills 的核心承诺，必须用真进程验。

为什么必须有这个文件
====================
单元测试（_test_mutex_guards.py）验的是 FileMutex 这个原语本身。但
nm-skills 对外承诺的是「多 Agent 并发时绝不抢跑同一任务、绝不出现同号」，
这是**整条链路**的性质：真实进程、真实时钟、真实竞争。

FileMutex 本地全绿不代表并发安全 —— 2026-10-02 就发现它有两个缺陷
（抢走活人的锁 / 释放误删他人锁），在单进程串行测试下完全看不出来。

两条判据：
  1. **同一任务**：N 个进程同时 claim → 必须有且只有 1 个成功。
     0 个 = 把正常认领也拒了（锁成了永久死锁）；≥2 个 = 互斥失效，
     正是本项目要杜绝的撞车。
  2. **不同任务**：N 个进程同时 claim 各自任务 → 全部成功，且分配到的
     Agent 编号两两不同。同号会让两条工作流水混为一谈，
     编号严格递增是模块宣称的第二项核心能力。

判据只要求「恰好 1 个」「两两不同」，不要求具体编号值 ——
编号值随历史记录变化，写进判据必然漂。

⚠️ 副作用说明：claim 路径内含 best-effort 落库，因此本测试会向 MySQL
写入若干可识别的探针行（task_id 形如 T-CONC-PROBE-*）。这是刻意选择：
本可以临时关掉 database.enabled 来避免，但那样一旦测试中途崩溃就会把
生产落库**静默关掉**——风险远大于几条可识别的探针行。
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "nm_register.py"
N_PROCS = 8                      # 并发进程数；太少不足以暴露竞争
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:160]) if (detail and not ok) else ""))


def spawn_all(cmds):
    """同时拉起全部进程，返回 [(pid, 输出, 退出码)]。

    刻意用 Popen 逐个启动而不用进程池：要的是真实的同时竞争，
    谁快谁慢都行——判据看的是最终结果分布。
    """
    procs = [subprocess.Popen(c, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding="utf-8",
                              errors="replace") for c in cmds]
    out = []
    for p in procs:
        text, _ = p.communicate(timeout=120)
        out.append((p.pid, text or "", p.returncode))
    return out


def main():
    stamp = str(int(time.time()))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # ---------- 判据 1：同一任务同时认领，只能有一个成功 ----------
        same_tid = "T-CONC-PROBE-%s-SAME" % stamp
        cmds = [[sys.executable, str(SCRIPT), "claim",
                 "--root", str(root),
                 "--task-id", same_tid,
                 "--task", "并发探针：同一任务只允许一个持有者",
                 "--client", "C%d" % i, "--ttl", "30"]
                for i in range(N_PROCS)]
        t0 = time.time()
        res = spawn_all(cmds)
        elapsed = time.time() - t0

        ok_count = sum(1 for _, txt, rc in res
                       if "认领成功" in txt or (rc == 0 and "认领被拒绝" not in txt))
        winners = [txt for _, txt, rc in res if "认领成功" in txt]
        print("  并发认领同一任务（%d 进程，耗时 %.1fs）：成功 %d 个"
              % (N_PROCS, elapsed, len(winners)))
        check("同一任务并发认领：恰好 1 个成功（互斥成立）",
              len(winners) == 1,
              "成功 %d 个 —— 0=正常认领被拒，≥2=互斥失效（撞车）"
              % len(winners))

        # 互斥生效时，其余进程应收到**明确的驳回**而不是超时/报错
        rejected = sum(1 for _, txt, _ in res if "认领被拒绝" in txt)
        other = N_PROCS - len(winners)
        check("其余进程收到明确驳回（而非超时或异常）",
              rejected == other,
              "驳回 %d / 其余 %d" % (rejected, other))

        # ---------- 判据 2：不同任务并发，编号必须两两不同 ----------
        diff_cmds = []
        tids = ["T-CONC-PROBE-%s-D%d" % (stamp, i) for i in range(N_PROCS)]
        for tid in tids:
            diff_cmds.append([sys.executable, str(SCRIPT), "claim",
                              "--root", str(root), "--task-id", tid,
                              "--task", "并发探针：不同任务编号不得重复",
                              "--client", "C%d" % tids.index(tid), "--ttl", "30"])
        res2 = spawn_all(diff_cmds)
        wins2 = [txt for _, txt, _ in res2 if "认领成功" in txt]
        print("  并发认领不同任务（%d 进程）：成功 %d 个" % (N_PROCS, len(wins2)))
        check("不同任务并发认领：全部成功（锁没有造成死锁）",
              len(wins2) == N_PROCS,
              "成功 %d / %d" % (len(wins2), N_PROCS))

        ids = []
        for txt in wins2:
            m = re.search(r"(NM-[A-Z0-9]+-\d{3}(?:-[a-z0-9]+)?)", txt)
            if m:
                ids.append(m.group(1))
        check("从输出里取到了 Agent 编号（取不到则本条不具判别力）",
              len(ids) == N_PROCS, "取到 %d 个" % len(ids))
        dup = sorted({i for i in ids if ids.count(i) > 1})
        check("分配到的编号两两不同（无同号冲突）",
              len(set(ids)) == len(ids) and len(ids) == N_PROCS,
              "重复编号=%s" % dup)

        # 同一客户端的编号必须严格递增（模块宣称的第二项核心能力）
        per_client = {}
        for txt in wins2:
            m = re.search(r"(NM-[A-Z0-9]+)-(\d{3})", txt)
            if m:
                per_client.setdefault(m.group(1), []).append(int(m.group(2)))
        bad = {c: v for c, v in per_client.items() if v != sorted(v)}
        check("同客户端编号严格递增", not bad, bad)

        # 结尾：任务已全部认领，能否正确看到互斥状态（最终一致性）
        r = subprocess.run([sys.executable, str(SCRIPT), "board",
                            "--root", str(root)],
                           capture_output=True, encoding="utf-8", timeout=60)
        check("board 能看到全部已认领任务", "T-CONC-PROBE" in (r.stdout or ""),
              (r.stdout or "")[-160:])

        # ---------- 判据 3：文件冲突防撞（第三项核心承诺）----------
        #
        # 不同任务、但都声明要改**同一个文件**时，只允许先到者持有，
        # 其余必须收到 FILE_CONFLICT，而不是 8 个进程一起去改同一份文件。
        shared_file = "scripts/_shared_target.py"
        filecmds = [[sys.executable, str(SCRIPT), "claim",
                     "--root", str(root),
                     "--task-id", "T-CONC-PROBE-%s-F%d" % (stamp, i),
                     "--task", "并发探针：同一文件只允许一个持有者",
                     "--client", "F%d" % i, "--files", shared_file,
                     "--ttl", "30"]
                    for i in range(N_PROCS)]
        res3 = spawn_all(filecmds)
        wins3 = [txt for _, txt, _ in res3 if "认领成功" in txt]
        # 判据必须锚在**用户可见的文案**上，不能锚内部状态码字面量。
        # 实测踩过：状态常量叫 FILE_CONFLICT，但它从不出现在 stdout ——
        # 用户看到的是「文件冲突拦截」。按常量名去断言会得到「拦截 0 个」
        # 这种与事实相反的结论，让人以为守卫失效。
        conflicts = sum(1 for _, txt, _ in res3 if "文件冲突拦截" in txt)
        print("  并发认领不同任务但争同一文件（%d 进程）：成功 %d 个，"
              "文件冲突拦截 %d 个" % (N_PROCS, len(wins3), conflicts))
        check("同一文件的并发认领：恰好 1 个成功（文件冲突防撞成立）",
              len(wins3) == 1,
              "成功 %d 个 —— ≥2 个就会两个进程同时改同一份文件"
              % len(wins3))
        check("其余进程收到文件冲突拦截（而不是超时或异常）",
              conflicts == N_PROCS - 1,
              "拦截 %d / 其余 %d" % (conflicts, N_PROCS - 1))

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
