#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experience_mining.py — auto-skills 数据库历史工具链调用与经验挖掘沉淀引擎 (v3.0)
================================================================================
核心功能：
1. 【历史轨迹聚类与经验挖掘 (Experience Mining)】：
   - 针对用户当前提出的任务描述或报错信息，自动检索 `tool_execution_traces` 历史数据库；
   - 查找曾经调用过的相似工具链、执行时长、避坑要点与 `lessons_learned` 经验沉淀；
   - 辅助后续 Agent 在遇到类似问题时直接站在过往经验肩膀上，杜绝重复试错。
2. 【高频工具与成功率统计】：
   - 统计过去 30 天内各类工具调用频次、平均耗时与失败率。

用法示例：
    # 针对具体问题检索过往工具链经验
    python scripts/experience_mining.py "多 Agent 任务冲突文件被锁"

    # 查看最近 30 天工具调用排行榜与成功率
    python scripts/experience_mining.py --top-tools
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent

try:
    import db_sync
except ImportError:
    sys.path.insert(0, str(SCRIPT_DIR))
    import db_sync


def search_experience_by_query(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """根据任务或问题关键词从 tool_execution_traces 检索历史经验"""
    try:
        conn = db_sync.get_db_connection()
        cur = conn.cursor()
        # 匹配 query 或 lessons_learned
        kw = f"%{query.strip()}%"
        sql = """
        SELECT `trace_id`, `task_id`, `user_query`, `stage`, `skill_name`, `tool_name`,
               `output_summary`, `status`, `lessons_learned`, `created_at`
        FROM `tool_execution_traces`
        WHERE `user_query` LIKE %s OR `lessons_learned` LIKE %s OR `output_summary` LIKE %s
        ORDER BY `id` DESC
        LIMIT %s;
        """
        cur.execute(sql, (kw, kw, kw, limit))
        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append({
                "trace_id": r[0],
                "task_id": r[1],
                "user_query": r[2],
                "stage": r[3],
                "skill_name": r[4],
                "tool_name": r[5],
                "output_summary": r[6],
                "status": r[7],
                "lessons_learned": r[8],
                "created_at": str(r[9])
            })
        return results
    except Exception as e:
        print(f"[!] 经验检索提示: {e}")
        return []


def print_top_tools_stats(days: int = 30):
    try:
        conn = db_sync.get_db_connection()
        cur = conn.cursor()
        sql = """
        SELECT `skill_name`, `tool_name`, COUNT(*) as total_calls,
               SUM(CASE WHEN `status`='SUCCESS' THEN 1 ELSE 0 END) as success_calls,
               AVG(`duration_ms`) as avg_ms
        FROM `tool_execution_traces`
        WHERE `created_at` >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY `skill_name`, `tool_name`
        ORDER BY total_calls DESC
        LIMIT 15;
        """
        cur.execute(sql, (days,))
        rows = cur.fetchall()
        conn.close()

        print("\n" + "=" * 75)
        print(f"📈 过去 {days} 天工具链调用频次与成功率统计看板")
        print("=" * 75)
        print(f"{'所属技能':<20} | {'调用工具':<18} | {'总调用':<8} | {'成功率':<8} | {'平均耗时(ms)'}")
        print("-" * 75)
        if not rows:
            print("暂无调用记录。")
        for r in rows:
            rate = f"{(r[3]/r[2]*100):.1f}%" if r[2] > 0 else "N/A"
            avg_t = f"{float(r[4]):.1f}" if r[4] is not None else "0"
            print(f"{r[0]:<20} | {r[1]:<18} | {r[2]:<8} | {rate:<8} | {avg_t}")
        print("=" * 75 + "\n")
    except Exception as e:
        print(f"[!] 获取统计失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="auto-skills 历史工具链经验检索与挖掘引擎")
    parser.add_argument("query", nargs="*", help="检索关键词（如问题现象、模块名或技术特征）")
    parser.add_argument("--top-tools", action="store_true", help="查看最近30天高频工具与成功率统计")
    parser.add_argument("--limit", type=int, default=5, help="最多返回条数 (默认 5)")

    args = parser.parse_args()

    if args.top_tools:
        print_top_tools_stats()
        sys.exit(0)

    if not args.query:
        parser.print_help()
        sys.exit(0)

    q = " ".join(args.query)
    print(f"\n[*] 正在云端经验数据库中检索类似问题: '{q}' ...")
    exp_list = search_experience_by_query(q, limit=args.limit)

    if not exp_list:
        print("⚪ 未检索到相关的历史工具调用经验。")
    else:
        print(f"\n🎯 检索到 {len(exp_list)} 条高价值历史经验沉淀：")
        for i, item in enumerate(exp_list, 1):
            print(f"\n--- [经验 #{i}] Trace: {item['trace_id']} ({item['created_at']}) ---")
            print(f"  • 适用技能 : {item['skill_name']} -> {item['tool_name']} ({item['stage']})")
            print(f"  • 历史任务 : {item['user_query']}")
            print(f"  • 执行结果 : {item['status']} | 摘要: {item['output_summary']}")
            if item['lessons_learned']:
                print(f"  💡 【经验避坑】: {item['lessons_learned']}")


if __name__ == "__main__":
    main()
