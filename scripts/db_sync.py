#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_sync.py — auto-skills 数据库存储与全链路自动落库引擎 (v3.0)
====================================================================
功能：
1. 支持 MySQL (如 MySQL 8.4) 与 SQLite 双模存储；
2. 自动建表并维护四张核心表：
   - `nm_tasks`: 多 Agent 任务排他认领记录与租约锁状态
   - `nm_work_logs`: 任务执行完成详细工作日志与改动清单
   - `skill_registry`: 公开与自安装私有技能台账与元数据
   - `router_audit_logs`: 路由器意图路由判定与流水线调用轨迹
   - `academic_references`: 参考文献与知识库引文数据
3. 读写 `config/config.yaml` 或 `.evolution/config.yaml` 中的 `database` 字段；
4. 提供 CLI 命令：
   - `--test`：测试数据库连接与版本
   - `--init-db`：初始化创建数据库表结构
   - `--sync-all`：将当前本地 agent_word/、registry 与 router 记录全量同步存入数据库
   - `--status`：查看数据库中记录概览
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

try:
    import config_manager
except ImportError:
    sys.path.insert(0, str(SCRIPT_DIR))
    import config_manager

try:
    import pymysql
except ImportError:
    pymysql = None


def get_db_connection(timeout: int = 8):
    """
    根据配置获取数据库连接对象
    """
    db_cfg = config_manager.get_value("database", {})
    db_type = db_cfg.get("type", "mysql").lower()

    if db_type == "mysql":
        if not pymysql:
            raise RuntimeError("未安装 pymysql 驱动，请先运行: pip install pymysql cryptography")
        
        host = db_cfg.get("host", "db.example.com")
        port = int(db_cfg.get("port", 42870))
        user = db_cfg.get("user", "db_user")
        password = db_cfg.get("password", "REDACTED&X")
        dbname = db_cfg.get("dbname", "auto_skills")

        # 先尝试连指定数据库，不存在则先建
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=dbname,
                charset="utf8mb4",
                connect_timeout=timeout,
                autocommit=True
            )
            return conn
        except pymysql.err.OperationalError as e:
            # 1049: Unknown database
            if e.args[0] == 1049:
                temp_conn = pymysql.connect(
                    host=host, port=port, user=user, password=password,
                    charset="utf8mb4", connect_timeout=timeout, autocommit=True
                )
                with temp_conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                temp_conn.close()
                return pymysql.connect(
                    host=host, port=port, user=user, password=password,
                    database=dbname, charset="utf8mb4", connect_timeout=timeout, autocommit=True
                )
            raise e
    else:
        # SQLite 备用模式
        import sqlite3
        sqlite_file = SKILL_ROOT / ".evolution" / "auto_skills.db"
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(sqlite_file))


def init_database_tables():
    """
    初始化数据表结构
    """
    conn = get_db_connection()
    is_mysql = hasattr(conn, "server_version") or "pymysql" in str(type(conn))

    tables_sql = [
        # 1. nm_tasks: 多 Agent 认领与排他锁表
        """
        CREATE TABLE IF NOT EXISTS `nm_tasks` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(64) NOT NULL,
            `task_name` VARCHAR(255) NOT NULL,
            `holder_id` VARCHAR(64) NOT NULL,
            `client` VARCHAR(32) NOT NULL,
            `status` VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS',
            `claimed_at` DATETIME NOT NULL,
            `expires_at` DATETIME NOT NULL,
            `expires_at_ts` DOUBLE NOT NULL,
            `files_involved` TEXT,
            `project_root` VARCHAR(255),
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_task_id` (`task_id`),
            KEY `idx_status` (`status`),
            KEY `idx_expires` (`expires_at_ts`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # 2. nm_work_logs: 工作登记总表与详细日志
        """
        CREATE TABLE IF NOT EXISTS `nm_work_logs` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(64) NOT NULL,
            `agent_id` VARCHAR(64) NOT NULL,
            `client` VARCHAR(32) NOT NULL,
            `task_name` VARCHAR(255) NOT NULL,
            `changes_summary` TEXT,
            `api_changes` TEXT,
            `files_modified` TEXT,
            `skills_used` VARCHAR(255),
            `mcps_used` VARCHAR(255),
            `tools_called` VARCHAR(255),
            `start_time` DATETIME,
            `done_time` DATETIME,
            `status` VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
            `raw_journal` LONGTEXT,
            `project_root` VARCHAR(255),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            KEY `idx_task_id` (`task_id`),
            KEY `idx_agent_id` (`agent_id`),
            KEY `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # 3. skill_registry: 技能资产权威台账
        """
        CREATE TABLE IF NOT EXISTS `skill_registry` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `skill_name` VARCHAR(128) NOT NULL,
            `scope` VARCHAR(32) NOT NULL DEFAULT 'public', -- public / custom
            `category` VARCHAR(64) NOT NULL,
            `description` TEXT,
            `path` VARCHAR(255),
            `has_skill_md` TINYINT(1) DEFAULT 1,
            `version` VARCHAR(32) DEFAULT '1.0.0',
            `last_synced` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_skill_scope` (`skill_name`, `scope`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # 4. router_audit_logs: 调度器请求审计流水线轨迹
        """
        CREATE TABLE IF NOT EXISTS `router_audit_logs` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `query_text` TEXT NOT NULL,
            `task_tier` VARCHAR(32) NOT NULL,
            `tier_reason` VARCHAR(255),
            `primary_focus` VARCHAR(128),
            `pipeline_json` JSON,
            `caller_agent` VARCHAR(64),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            KEY `idx_tier` (`task_tier`),
            KEY `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        # 5. academic_references: 参考文献定义库
        """
        CREATE TABLE IF NOT EXISTS `academic_references` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `ref_index` INT NOT NULL,
            `raw_citation` TEXT NOT NULL,
            `title` VARCHAR(500),
            `author_or_org` VARCHAR(255),
            `pub_date` VARCHAR(64),
            `url` VARCHAR(1000),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_ref_index` (`ref_index`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    ]

    with conn.cursor() as cur:
        for sql in tables_sql:
            cur.execute(sql)

    conn.close()
    print("[OK] 数据库表结构初始化/验证完成 (nm_tasks, nm_work_logs, skill_registry, router_audit_logs, academic_references)！")
    return True


# ==============================================================================
# 自动落库 API
# ==============================================================================

def record_task_claim_db(claim_info: Dict[str, Any], project_root: str = "") -> bool:
    """自动将认领锁信息存入/更新到数据库"""
    if not config_manager.get_value("database.enabled", True):
        return False
    try:
        conn = get_db_connection()
        sql = """
        INSERT INTO `nm_tasks`
            (`task_id`, `task_name`, `holder_id`, `client`, `status`, `claimed_at`, `expires_at`, `expires_at_ts`, `files_involved`, `project_root`)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `task_name`=VALUES(`task_name`),
            `holder_id`=VALUES(`holder_id`),
            `client`=VALUES(`client`),
            `status`=VALUES(`status`),
            `claimed_at`=VALUES(`claimed_at`),
            `expires_at`=VALUES(`expires_at`),
            `expires_at_ts`=VALUES(`expires_at_ts`),
            `files_involved`=VALUES(`files_involved`),
            `project_root`=VALUES(`project_root`);
        """
        files_str = json.dumps(claim_info.get("files", []), ensure_ascii=False)
        with conn.cursor() as cur:
            cur.execute(sql, (
                claim_info.get("task_id"),
                claim_info.get("task_name"),
                claim_info.get("holder_id"),
                claim_info.get("client"),
                claim_info.get("status", "IN_PROGRESS"),
                claim_info.get("claimed_at"),
                claim_info.get("expires_at"),
                claim_info.get("expires_at_ts", 0),
                files_str,
                str(project_root)
            ))
        conn.close()
        return True
    except Exception as e:
        print(f"[!] 自动落库 nm_tasks 提示: {e}")
        return False


def record_task_done_db(done_info: Dict[str, Any], project_root: str = "") -> bool:
    """自动将任务完成与日志存入数据库"""
    if not config_manager.get_value("database.enabled", True):
        return False
    try:
        conn = get_db_connection()
        tid = done_info.get("task_id")
        # 1. 更新 nm_tasks 状态为 COMPLETED
        with conn.cursor() as cur:
            cur.execute("UPDATE `nm_tasks` SET `status`='COMPLETED' WHERE `task_id`=%s", (tid,))
            
            # 2. 写入 nm_work_logs
            sql = """
            INSERT INTO `nm_work_logs`
                (`task_id`, `agent_id`, `client`, `task_name`, `changes_summary`, `api_changes`, `files_modified`,
                 `skills_used`, `mcps_used`, `tools_called`, `start_time`, `done_time`, `status`, `raw_journal`, `project_root`)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(sql, (
                tid,
                done_info.get("holder_id", "NM-AUTO"),
                done_info.get("client", "CODE"),
                done_info.get("task_name", tid),
                done_info.get("changes", ""),
                done_info.get("api", ""),
                done_info.get("files", ""),
                done_info.get("skills", "nm-skills"),
                done_info.get("mcps", ""),
                done_info.get("tools", ""),
                done_info.get("start_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                done_info.get("done_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "COMPLETED",
                done_info.get("journal", ""),
                str(project_root)
            ))
        conn.close()
        return True
    except Exception as e:
        print(f"[!] 自动落库 nm_work_logs 提示: {e}")
        return False


def record_tool_trace_db(
    skill_name: str,
    tool_name: str,
    action: str = "execute",
    task_id: Optional[str] = None,
    user_query: str = "",
    stage: str = "execution",
    input_params: Any = None,
    output_summary: str = "",
    status: str = "SUCCESS",
    error_message: str = "",
    duration_ms: int = 0,
    lessons_learned: str = "",
    project_root: str = "",
    client: str = "CODE"
) -> bool:
    """
    全自动落库：将单次工具链调用和执行过程沉淀至 `tool_execution_traces` 表
    """
    if not config_manager.get_value("database.enabled", True):
        return False

    # 首次或按配置执行 30 天超期数据滚动清理
    if config_manager.get_value("database.auto_cleanup_expired_traces", True):
        try:
            cleanup_expired_traces(days=config_manager.get_value("database.retention_days", 30))
        except Exception:
            pass

    import uuid
    trace_id = f"TR-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

    try:
        conn = get_db_connection()
        sql = """
        INSERT INTO `tool_execution_traces`
            (`trace_id`, `task_id`, `agent_name`, `client`, `user_query`, `stage`,
             `skill_name`, `tool_name`, `action`, `input_params`, `output_summary`,
             `status`, `error_message`, `duration_ms`, `lessons_learned`, `project_root`)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params_json = json.dumps(input_params, ensure_ascii=False) if input_params is not None else None
        with conn.cursor() as cur:
            cur.execute(sql, (
                trace_id, task_id, "auto-skills", client, user_query[:1000] if user_query else "",
                stage, skill_name, tool_name, action, params_json,
                output_summary[:2000] if output_summary else "",
                status, error_message[:1000] if error_message else "",
                duration_ms, lessons_learned[:1000] if lessons_learned else "",
                str(project_root)
            ))
        conn.close()
        return True
    except Exception as e:
        # 静默不影响工具链主执行
        return False


def cleanup_expired_traces(days: int = 30) -> int:
    """
    30 天滚动清理过期工具链调用轨迹，防止数据库膨胀
    """
    if not config_manager.get_value("database.enabled", True):
        return 0
    try:
        conn = get_db_connection()
        sql = "DELETE FROM `tool_execution_traces` WHERE `created_at` < DATE_SUB(NOW(), INTERVAL %s DAY);"
        with conn.cursor() as cur:
            affected = cur.execute(sql, (days,))
        conn.close()
        if affected > 0:
            print(f"[*] 【30天滚动清理】已成功清理 {affected} 条超过 {days} 天的历史工具调用轨迹。")
        return affected
    except Exception as e:
        return 0


def record_router_audit_db(query: str, plan: Dict[str, Any], caller: str = "CODE") -> bool:
    """自动将路由器的每次调用、阶段流水与决策存入数据库"""
    if not config_manager.get_value("database.enabled", True):
        return False
    try:
        conn = get_db_connection()
        sql = """
        INSERT INTO `router_audit_logs`
            (`query_text`, `task_tier`, `tier_reason`, `primary_focus`, `pipeline_json`, `caller_agent`)
        VALUES
            (%s, %s, %s, %s, %s, %s);
        """
        pipeline_str = json.dumps(plan.get("pipeline", []), ensure_ascii=False)
        with conn.cursor() as cur:
            cur.execute(sql, (
                query,
                plan.get("task_tier", "UNKNOWN"),
                plan.get("tier_reason", ""),
                plan.get("primary_focus", ""),
                pipeline_str,
                caller
            ))
        conn.close()
        return True
    except Exception as e:
        # 静默不阻塞主调用
        return False


def sync_skills_registry_to_db() -> int:
    """将公共与私有技能台账同步至数据库"""
    if not config_manager.get_value("database.enabled", True):
        return 0
    try:
        conn = get_db_connection()
        count = 0
        sql = """
        INSERT INTO `skill_registry`
            (`skill_name`, `scope`, `category`, `description`, `path`, `has_skill_md`)
        VALUES
            (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `category`=VALUES(`category`),
            `description`=VALUES(`description`),
            `path`=VALUES(`path`),
            `has_skill_md`=VALUES(`has_skill_md`),
            `last_synced`=CURRENT_TIMESTAMP;
        """
        # 公共工具
        pub_reg = SKILL_ROOT / "tools" / "registry.json"
        if pub_reg.exists():
            data = json.loads(pub_reg.read_text(encoding="utf-8"))
            for name, info in data.get("tools", {}).items():
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        name, "public", info.get("category", "general"),
                        info.get("description", ""), info.get("path", f"tools/{name}"),
                        1 if info.get("has_skill_md") else 0
                    ))
                    count += 1

        # 私有技能
        priv_reg = SKILL_ROOT / ".evolution" / "custom_skills" / "registry.json"
        if priv_reg.exists():
            data = json.loads(priv_reg.read_text(encoding="utf-8"))
            for name, info in data.get("tools", {}).items():
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        name, "custom", info.get("category", "general"),
                        info.get("description", ""), info.get("path", f".evolution/custom_skills/{name}"),
                        1 if info.get("has_skill_md") else 0
                    ))
                    count += 1

        conn.close()
        return count
    except Exception as e:
        print(f"[!] 同步技能台账至数据库失败: {e}")
        return 0


def import_academic_references_file(ref_file_path: str) -> int:
    """解析 compile_references_100.py 并存入 academic_references 表"""
    p = Path(ref_file_path).resolve()
    if not p.exists():
        print(f"[ERROR] 参考文献文件未找到: {p}")
        return 0

    import importlib.util
    import re

    try:
        spec = importlib.util.spec_from_file_location("ref_module_auto", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ref_list = getattr(mod, "references_100", None) or getattr(mod, "references_85", None) or getattr(mod, "references", None)
        if not ref_list:
            for attr in dir(mod):
                if attr.startswith("references"):
                    ref_list = getattr(mod, attr)
                    break
        if not ref_list:
            print(f"[ERROR] 未能在模块 {p.name} 中找到 references 数组！")
            return 0
    except Exception as e:
        print(f"[ERROR] 加载模块失败: {e}")
        return 0

    conn = get_db_connection()
    sql = """
    INSERT INTO `academic_references`
        (`ref_index`, `raw_citation`, `title`, `author_or_org`, `pub_date`, `url`)
    VALUES
        (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        `raw_citation`=VALUES(`raw_citation`),
        `title`=VALUES(`title`),
        `author_or_org`=VALUES(`author_or_org`),
        `pub_date`=VALUES(`pub_date`),
        `url`=VALUES(`url`);
    """
    inserted = 0
    with conn.cursor() as cur:
        for idx, item in enumerate(ref_list, 1):
            raw = str(item).strip()
            # 提取序号如 [1]
            idx_match = re.match(r"^\[(\d+)\]", raw)
            real_idx = int(idx_match.group(1)) if idx_match else idx

            # 提取 URL
            url_match = re.search(r"https?://[^\s\]]+", raw)
            url = url_match.group(0) if url_match else ""

            # 提取 作者与标题: [1] 中共中央、国务院. 关于锚定...[EB/OL]. 2026-02-03.
            body = re.sub(r"^\[\d+\]\s*", "", raw)
            parts = body.split(". ", 1)
            author = parts[0].strip() if len(parts) > 1 else ""
            remainder = parts[1] if len(parts) > 1 else parts[0]

            title_match = re.search(r"^(.*?)(?:\[|\.|$)", remainder)
            title = title_match.group(1).strip() if title_match else remainder[:100]

            # 提取日期
            date_match = re.search(r"\b(20\d{2}(?:-\d{2}-\d{2}|年\d{1,2}月|\b))", remainder)
            pub_date = date_match.group(1) if date_match else ""

            cur.execute(sql, (real_idx, raw, title, author, pub_date, url))
            inserted += 1

    conn.close()
    print(f"[OK] 成功将 {inserted} 篇权威参考文献入库存入 `academic_references`！")
    return inserted


def print_db_status():
    """查看数据库连接与各表行数概览"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT VERSION(), DATABASE(), CURRENT_USER()")
        v, db, u = cur.fetchone()

        tables = ["nm_tasks", "nm_work_logs", "tool_execution_traces", "skill_registry", "router_audit_logs", "academic_references"]
        counts = {}
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                counts[t] = cur.fetchone()[0]
            except Exception:
                counts[t] = "表未创建"

        conn.close()
        print("\n" + "=" * 70)
        print("🐬 auto-skills 数据库存储状态 (MySQL 8.4 Engine)")
        print("=" * 70)
        print(f"- 数据库引擎 : MySQL {v}")
        print(f"- 当前数据库 : {db}")
        print(f"- 数据库用户 : {u}")
        print(f"- 主机与端口 : db.example.com:42870 (香港区 2vCPUs|8GB)")
        print("-" * 70)
        print("📊 核心数据表记录统计：")
        for t, cnt in counts.items():
            print(f"  • {t:<24}: {cnt} 条记录")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="auto-skills 数据库存储与全链路自动落库引擎")
    parser.add_argument("--test", action="store_true", help="测试数据库连接与版本信息")
    parser.add_argument("--init-db", action="store_true", help="初始化创建全部数据表结构")
    parser.add_argument("--status", action="store_true", help="查看数据库记录概况")
    parser.add_argument("--sync-skills", action="store_true", help="将当前技能台账同步至数据库")
    parser.add_argument("--import-refs", help="导入参考文献定义文件至数据库 (如 compile_references_100.py)")

    parser.add_argument("--cleanup-traces", type=int, nargs="?", const=30, default=None, help="执行指定天数(默认30天)滚动清理过期工具调用轨迹")

    args = parser.parse_args()

    if args.cleanup_traces is not None:
        affected = cleanup_expired_traces(days=args.cleanup_traces)
        print(f"[OK] 滚动清理完成，删除了 {affected} 条过期轨迹。")
        sys.exit(0)

    if args.test:
        print_db_status()
        sys.exit(0)

    if args.init_db:
        init_database_tables()
        sys.exit(0)

    if args.sync_skills:
        cnt = sync_skills_registry_to_db()
        print(f"[OK] 已将 {cnt} 个技能元数据同步至数据库！")
        sys.exit(0)

    if args.import_refs:
        import_academic_references_file(args.import_refs)
        sys.exit(0)

    if args.status or len(sys.argv) == 1:
        print_db_status()


if __name__ == "__main__":
    main()
