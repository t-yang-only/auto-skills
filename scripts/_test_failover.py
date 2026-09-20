#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""容错层验收：在隔离副本里模拟「数据库不可用 → 熔断 → 恢复 → 自动补传」。

不碰真实技能目录：整份拷到临时目录改配置，但补传目标是真实 MySQL，
用 FAILOVER-TEST 前缀标记，测完按前缀删干净。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SRC = Path(__file__).resolve().parent.parent   # 仓库根：从本文件位置推导，不写死绝对路径
TESTROOT = Path(tempfile.gettempdir()) / "as-failover-test"
MARK = "FAILOVER-TEST"
DEAD_HOST = "10.255.255.1"          # 黑洞地址：连不上，且会一直等到超时


def _load_mysql_creds():
    """从技能配置读凭据（不硬编码——本文件在公开仓库里）。

    只用日常落库子账户 auto_agent：它有 SELECT/DELETE 权限，够本测试核验与清理。
    """
    sys.path.insert(0, str(SRC / "scripts"))
    import config_manager
    db = config_manager.get_value("database", {}) or {}
    pw = db.get("password") or ""
    pf = db.get("password_file")
    if not pw and pf:
        p = Path(pf)
        if not p.is_absolute():
            p = SRC / pf
        pw = p.read_text(encoding="utf-8").strip()
    if not pw:
        env = db.get("password_env")
        pw = os.environ.get(env, "") if env else ""
    if not pw:
        raise SystemExit("拿不到数据库密码：检查 config/db.password 或 database.password_env")
    return dict(host=db.get("host"), port=int(db.get("port") or 3306),
                user=db.get("user"), password=pw, db=db.get("dbname"))


REAL_MYSQL = _load_mysql_creds()

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  —— {detail}" if detail else ""))


def prep():
    if TESTROOT.exists():
        shutil.rmtree(TESTROOT, ignore_errors=True)
    shutil.copytree(SRC, TESTROOT, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    for d in ("db_spool",):
        p = TESTROOT / ".evolution" / d
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    for f in ("db_health.json",):
        p = TESTROOT / ".evolution" / f
        if p.exists():
            p.unlink()
    print(f"  隔离副本 -> {TESTROOT}")


def set_host(host):
    """改 .evolution/config.yaml 的 database.host（权威覆盖层）"""
    p = TESTROOT / ".evolution" / "config.yaml"
    txt = p.read_text(encoding="utf-8")
    import re
    txt2, n = re.subn(r"(?m)^(\s*)host:\s*\S+", lambda m: f"{m.group(1)}host: {host}", txt, count=1)
    if n == 0:
        m = re.search(r"(?m)^(database:\s*)$", txt)
        txt2 = txt[:m.end()] + f"\n  host: {host}" + txt[m.end():]
    p.write_text(txt2, encoding="utf-8")
    return host


def run(snippet):
    """在隔离副本里跑一段代码，返回 (stdout, 耗时)"""
    t0 = time.time()
    r = subprocess.run([sys.executable, "-c", snippet], cwd=str(TESTROOT / "scripts"),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.stdout.strip(), time.time() - t0, r.returncode


SNIPPET_CALL = """
import sys, json, time
sys.path.insert(0, '.')
import db_sync
t0 = time.time()
try:
    ok = db_sync.record_router_audit_db({mark!r} + '-{n}', {{'task_tier':'T1','tier_reason':'r','primary_focus':'f','pipeline':[]}}, 'FAILOVER-PROBE')
    err = ''
except Exception as e:
    ok, err = False, type(e).__name__ + ': ' + str(e)[:80]
print(json.dumps({{'ok': bool(ok), 'call_seconds': round(time.time() - t0, 2), 'err': err}}))
"""

SNIPPET_TRACE = """
import sys, json, time
sys.path.insert(0, '.')
import db_sync
t0 = time.time()
ok = db_sync.record_tool_trace_db('auto-skills', 'FailoverProbe', action='execute',
                                  user_query={mark!r} + '-TRACE', project_root=str(SRC))
print(json.dumps({{'ok': bool(ok), 'call_seconds': round(time.time() - t0, 2)}}))
"""

SNIPPET_HEALTH = """
import sys, json
sys.path.insert(0, '.')
import db_sync
h = db_sync.health_state()
h['count'] = db_sync.spool_count()
print(json.dumps(h, ensure_ascii=False))
"""

SNIPPET_FLUSH = """
import sys, json
sys.path.insert(0, '.')
import db_sync
ok, bad = db_sync.spool_replay(limit=1000)
print(json.dumps({'ok': ok, 'bad': bad, 'left': db_sync.spool_count()}))
"""


def spool_items():
    p = TESTROOT / ".evolution" / "db_spool" / "pending.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def mysql(sql, fetch=False):
    import pymysql
    c = pymysql.connect(host=REAL_MYSQL["host"], port=REAL_MYSQL["port"],
                        user=REAL_MYSQL["user"], password=REAL_MYSQL["password"],
                        database=REAL_MYSQL["db"], charset="utf8mb4", autocommit=True,
                        connect_timeout=20)
    cur = c.cursor()
    cur.execute(sql)
    r = cur.fetchall() if fetch else cur.rowcount
    c.close()
    return r


def main():
    print("=" * 72)
    print("  容错层验收：模拟数据库不可用 → 熔断 → 恢复 → 自动补传")
    print("=" * 72)

    prep()

    # ---------------------------------------------------------- 阶段 1：库不可用
    print("\n【阶段 1】把 database.host 指向黑洞地址，模拟库不可用")
    set_host(DEAD_HOST)
    out, dt, rc = run(SNIPPET_CALL.format(mark=MARK, n="A"))
    r1 = json.loads(out)
    check("落库调用不抛异常（主流程不被炸）", r1.get("ok") is False,
          f"输出={out}")

    items = spool_items()
    check("失败记录已本地暂存", len(items) == 1, f"pending.jsonl 有 {len(items)} 条")
    if items:
        it = items[0]
        check("暂存内容可回放（含函数名与参数）",
              it.get("fn") == "record_router_audit_db" and it.get("args", [None])[0].startswith(MARK),
              f"fn={it.get('fn')} args[0]={str(it.get('args', [''])[0])[:40]}")

    # ---------------------------------------------------------- 阶段 2：熔断
    print("\n【阶段 2】累计 3 次失败触发熔断，第 4 次应快速失败")
    run(SNIPPET_CALL.format(mark=MARK, n="B"))
    out_c, _, _ = run(SNIPPET_CALL.format(mark=MARK, n="C"))
    rc_ = json.loads(out_c)
    out_h, _, _ = run(SNIPPET_HEALTH)
    h = json.loads(out_h)
    check("第 3 次失败后熔断器打开", bool(h.get("breaker_open")),
          f"consecutive_failures={h.get('consecutive_failures')} open={h.get('breaker_open')} "
          f"剩余={h.get('breaker_remaining_seconds')}s")

    out_d, _, _ = run(SNIPPET_CALL.format(mark=MARK, n="D"))
    r4 = json.loads(out_d)
    base = rc_.get("call_seconds", 8.0)
    check("熔断后快速失败（不再等连接超时）", r4.get("call_seconds", 99) < 1.0,
          f"熔断前单次 {base}s → 熔断后 {r4.get('call_seconds')}s"
          + (f"；错误={r4.get('err')}" if r4.get('err') else ""))

    out_h2, _, _ = run(SNIPPET_HEALTH)
    h2 = json.loads(out_h2)
    check("暂存累积不丢（4 次失败 → 4 条）", h2.get("count") == 4, f"pending={h2.get('count')}")

    # ---------------------------------------------------------- 阶段 3：恢复
    print("\n【阶段 3】恢复真实地址 + 清熔断，验证自动补传")
    set_host(REAL_MYSQL["host"])
    hp = TESTROOT / ".evolution" / "db_health.json"
    if hp.exists():
        hp.unlink()
    out_ok, dt_ok, _ = run(SNIPPET_CALL.format(mark=MARK, n="E"))
    r5 = json.loads(out_ok)
    check("库恢复后正常落库", r5.get("ok") is True, f"{out_ok}")

    out_h3, _, _ = run(SNIPPET_HEALTH)
    h3 = json.loads(out_h3)
    check("库恢复后自动回灌暂存（pending 归零）", h3.get("count") == 0,
          f"pending={h3.get('count')} 上次补传={h3.get('last_replay_result', '')}")

    # ---------------------------------------------------------- 阶段 4：落库确认
    print("\n【阶段 4】确认补传的记录真的进了 MySQL")
    n_router = mysql(f"SELECT COUNT(*) FROM router_audit_logs WHERE query_text LIKE '{MARK}%'", fetch=True)[0][0]
    check("router_audit 5 条全部入库（A/B/C/D/E）", n_router == 5, f"实际 {n_router} 条")
    n_trace = 0
    try:
        n_trace = mysql(f"SELECT COUNT(*) FROM tool_execution_traces WHERE user_query LIKE '{MARK}%'", fetch=True)[0][0]
    except Exception as e:
        check("tool_execution_traces 查询", False, str(e)[:80])

    # ---------------------------------------------------------- 阶段 5：复杂参数
    print("\n【阶段 5】带 kwargs 的落库函数（tool_trace）在库挂掉时也应暂存")
    set_host(DEAD_HOST)
    if hp.exists():
        hp.unlink()
    run(SNIPPET_TRACE.format(mark=MARK))
    items2 = spool_items()
    tr = [i for i in items2 if i.get("fn") == "record_tool_trace_db"]
    check("kwargs 形式的记录也能暂存", len(tr) == 1,
          f"kwargs keys={list(tr[0]['kwargs'].keys())[:5] if tr else '—'}")
    set_host(REAL_MYSQL["host"])
    if hp.exists():
        hp.unlink()
    out_fl, _, _ = run(SNIPPET_FLUSH)
    fl = json.loads(out_fl)
    check("手动补传 --flush-spool 生效", fl.get("ok", 0) >= 1 and fl.get("left") == 0, f"{fl}")
    n_trace2 = mysql(f"SELECT COUNT(*) FROM tool_execution_traces WHERE user_query LIKE '{MARK}%'", fetch=True)[0][0]
    check("tool_trace 记录入库", n_trace2 >= 1, f"实际 {n_trace2} 条")

    # ---------------------------------------------------------- 清理
    print("\n【清理】删除测试数据与隔离副本")
    d1 = mysql(f"DELETE FROM router_audit_logs WHERE query_text LIKE '{MARK}%'")
    d2 = mysql(f"DELETE FROM tool_execution_traces WHERE user_query LIKE '{MARK}%'")
    print(f"  已删 router_audit {d1} 条 / tool_trace {d2} 条")
    shutil.rmtree(TESTROOT, ignore_errors=True)
    print(f"  已删隔离副本 {TESTROOT}")

    print("\n" + "=" * 72)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"  验收：{passed}/{len(results)} 通过")
    for n, ok, d in results:
        if not ok:
            print(f"    ✗ {n} —— {d}")
    print("=" * 72)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
