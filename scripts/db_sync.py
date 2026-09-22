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
import contextlib
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


# ==============================================================================
# 配置解析：连接方式 / 凭据来源 / 分项开关
# ==============================================================================

#: 分项开关名 -> 落库目标表（配置项 database.streams.<名>）
STREAM_TABLES = {
    "task_claim": "nm_tasks",
    "task_done": "nm_work_logs",
    "tool_trace": "tool_execution_traces",
    "router_audit": "router_audit_logs",
    "skill_registry": "skill_registry",
    "academic_references": "academic_references",
}


def db_config() -> Dict[str, Any]:
    """当前 database 配置段（永远返回 dict）"""
    cfg = config_manager.get_value("database", {}) or {}
    return cfg if isinstance(cfg, dict) else {}


def is_db_enabled() -> bool:
    """总开关：database.enabled=false 或 database.type=disabled 时，任何表都不写。"""
    cfg = db_config()
    val = cfg.get("enabled", True)
    if val is None:
        val = True
    if not val:
        return False
    return str(cfg.get("type", "mysql")).strip().lower() != "disabled"


def is_stream_enabled(stream: str) -> bool:
    """分项开关：database.streams.<name>=false 可单独关掉一类落库。

    未配置的项一律按开启处理（保证旧配置文件行为不变）。
    """
    if not is_db_enabled():
        return False
    streams = db_config().get("streams") or {}
    if not isinstance(streams, dict):
        return True
    val = streams.get(stream, True)
    return True if val is None else bool(val)


def _resolve_password(cfg: Dict[str, Any]) -> str:
    """按 password_env -> password_file -> password 的顺序解析密码。

    刻意不内置任何默认凭据：配置缺失时报错停下，而不是悄悄用某个账号连上。
    password_file 可写相对技能根目录的相对路径（如 config/db.password）。
    """
    env_name = str(cfg.get("password_env") or "").strip()
    if env_name:
        val = os.environ.get(env_name)
        if not val:
            raise RuntimeError(
                "database.password_env 指向环境变量 %s，但它为空或未设置" % env_name
            )
        return val.strip()

    rel = str(cfg.get("password_file") or "").strip()
    if rel:
        p = Path(rel)
        if not p.is_absolute():
            p = SKILL_ROOT / rel
        if not p.is_file():
            raise RuntimeError("database.password_file 指向的 %s 不存在" % p)
        return p.read_text(encoding="utf-8").strip()

    val = str(cfg.get("password") or "").strip()
    if val:
        return val

    raise RuntimeError(
        "数据库密码未配置。请在 config/config.yaml 的 database 段设置 password_file"
        "（推荐，该文件必须加进 .gitignore），或 password_env，或 password。"
    )



def _get_db_connection_raw(timeout: int = 8):
    """
    根据配置获取数据库连接对象。

    注意：调用方应先用 is_stream_enabled() 判断该不该落库，再连。这里再兜一层，
    是为了防止「关掉数据库后仍有代码直接连库」——那会静默落到 SQLite 分支上去。
    """
    if not is_db_enabled():
        raise RuntimeError(
            "数据库已关闭（database.enabled=false 或 database.type=disabled）。"
            "调用方应先判断 is_stream_enabled()，不要直接连库。"
        )
    db_cfg = config_manager.get_value("database", {})
    db_type = db_cfg.get("type", "mysql").lower()

    if db_type == "mysql":
        if not pymysql:
            raise RuntimeError("未安装 pymysql 驱动，请先运行: pip install pymysql cryptography")
        
        # 刻意不写默认值：配置缺失就报错，绝不静默连到某个账号上。
        host = str(db_cfg.get("host") or "").strip()
        port = int(db_cfg.get("port") or 3306)
        user = str(db_cfg.get("user") or "").strip()
        dbname = str(db_cfg.get("dbname") or "auto_skills").strip()
        password = _resolve_password(db_cfg)
        if not host or not user:
            raise RuntimeError(
                "数据库未配置完整：config/config.yaml 的 database 段需要 host 与 user"
            )

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
        # SQLite 备用模式（database.type: sqlite）
        import sqlite3
        custom = str(db_cfg.get("sqlite_path") or "").strip()
        sqlite_file = Path(custom) if custom else (SKILL_ROOT / ".evolution" / "auto_skills.db")
        if not sqlite_file.is_absolute():
            sqlite_file = SKILL_ROOT / sqlite_file
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
    if not is_stream_enabled("task_claim"):
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
        _spool_on_failure("task_claim", "record_task_claim_db",
                          (claim_info, project_root), {}, e)
        return False


def record_task_done_db(done_info: Dict[str, Any], project_root: str = "") -> bool:
    """自动将任务完成与日志存入数据库"""
    if not is_stream_enabled("task_done"):
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
        _spool_on_failure("task_done", "record_task_done_db",
                          (done_info, project_root), {}, e)
        return False


def _log_db_error(where: str, exc: BaseException) -> None:
    """
    落库失败必须留痕。

    此前所有调用点都写成 `try: ... except Exception: pass`，于是「没报错」被
    当成「在写」——2026-09 就是因此让 record_tool_trace_db 长期无人调用而无人
    发现。这里统一写到 .evolution/db_sync_errors.log：stdout 保持干净（agent 在
    读 stdout），但失败可追溯。
    """
    try:
        log_dir = Path(__file__).resolve().parent.parent / ".evolution"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "db_sync_errors.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} [{where}] "
                    f"{type(exc).__name__}: {exc}\n")
    except Exception:
        pass


@contextlib.contextmanager
def trace_tool(skill_name: str, tool_name: str, action: str = "execute",
               user_query: str = "", stage: str = "execution",
               input_params: Any = None, project_root: str = "",
               client: str = "CODE", summary: str = ""):
    """
    把一次工具链调用记进 `tool_execution_traces`（自动测耗时、自动判成败）。

        with db_sync.trace_tool("nm-skills", "nm_register", "claim",
                                user_query=q, stage="coordination") as t:
            ...
            t["summary"] = "任务 T-1 已锁定"

    函数体抛异常也会落库（status=FAILED 且带错误原文），然后原样抛出。
    """
    t0 = time.time()
    box = {"summary": summary, "status": "SUCCESS", "error": ""}
    try:
        yield box
    except Exception as ex:
        box["status"] = "FAILED"
        box["error"] = f"{type(ex).__name__}: {ex}"
        raise
    finally:
        try:
            record_tool_trace_db(
                skill_name, tool_name, action=action, user_query=user_query,
                stage=stage, input_params=input_params,
                output_summary=box["summary"], status=box["status"],
                error_message=box["error"],
                duration_ms=int((time.time() - t0) * 1000),
                project_root=project_root, client=client)
        except Exception as ex:
            _log_db_error(f"trace_tool:{tool_name}.{action}", ex)


def trace_call(skill_name: str, tool_name: str, action: str = "execute",
               **kw) -> bool:
    """一次性记录（无需测耗时的场景）。落库失败只留痕，不打断调用方。"""
    try:
        return record_tool_trace_db(skill_name, tool_name, action=action, **kw)
    except Exception as ex:
        _log_db_error(f"trace_call:{tool_name}.{action}", ex)
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
    if not is_stream_enabled("tool_trace"):
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
        # 不打断工具链主执行，但必须留痕（见 _log_db_error）
        _log_db_error("record_tool_trace_db", e)
        _spool_on_failure("tool_trace", "record_tool_trace_db", (), {
            "skill_name": skill_name, "tool_name": tool_name, "action": action,
            "task_id": task_id, "user_query": user_query, "stage": stage,
            "input_params": input_params, "output_summary": output_summary,
            "status": status, "error_message": error_message, "duration_ms": duration_ms,
            "lessons_learned": lessons_learned, "project_root": project_root, "client": client,
        }, e)
        return False


def cleanup_expired_traces(days: int = 30, force: bool = False) -> int:
    """30 天滚动清理过期工具链调用轨迹，防止数据库膨胀。

    按时间节流：默认**每小时最多跑一次**（force=True 可强制）。
    为什么要节流：本函数原先每次 record_tool_trace_db 都无条件调用一次，
    而它自己会建立一条数据库连接并执行 DELETE。于是一次 route 调用要建
    三条连接（清理 + 审计 + 轨迹），实测单次连接约 300ms，白白多花
    ~300ms；而"清理过期行"是维护动作，按小时做一次完全够用。
    节流状态写在 .evolution/db_cleanup.json（每次调用都是新进程，内存态无效）。
    """
    if not config_manager.get_value("database.enabled", True):
        return 0

    _now = time.time()
    if not force:
        try:
            _st = SKILL_ROOT / ".evolution" / "db_cleanup.json"
            if _st.exists():
                _last = float(json.loads(_st.read_text(encoding="utf-8")).get("last_run", 0))
                if _now - _last < 3600:
                    return 0
        except Exception:
            pass  # 状态文件坏了就照常清理，不影响主流程

    try:
        conn = get_db_connection()
        sql = "DELETE FROM `tool_execution_traces` WHERE `created_at` < DATE_SUB(NOW(), INTERVAL %s DAY);"
        with conn.cursor() as cur:
            affected = cur.execute(sql, (days,))
        conn.close()
        # 清理成功才写节流时间戳
        try:
            _st = SKILL_ROOT / ".evolution" / "db_cleanup.json"
            _st.parent.mkdir(parents=True, exist_ok=True)
            _st.write_text(json.dumps({"last_run": _now, "last_affected": affected}),
                           encoding="utf-8")
        except Exception:
            pass
        if affected > 0:
            print(f"[*] 【30天滚动清理】已成功清理 {affected} 条超过 {days} 天的历史工具调用轨迹。")
        return affected
    except Exception as e:
        return 0


def record_router_audit_db(query: str, plan: Dict[str, Any], caller: str = "CODE") -> bool:
    """自动将路由器的每次调用、阶段流水与决策存入数据库"""
    if not is_stream_enabled("router_audit"):
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
        # 静默不阻塞主调用，但失败要留底并可补传
        _spool_on_failure("router_audit", "record_router_audit_db",
                          (query, plan, caller), {}, e)
        return False


def sync_skills_registry_to_db() -> int:
    """将公共与私有技能台账同步至数据库"""
    if not is_stream_enabled("skill_registry"):
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
        _spool_on_failure("skill_registry", "sync_skills_registry_to_db", (), {}, e)
        return 0


def _import_refs_raw(ref_file_path: str) -> int:
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


# ---- academic_references：原实现没有 try/except 包住落库段，
#      一次数据库故障会直接把异常抛给调用方。这里补上外层包装。----
def import_academic_references_file(ref_file_path: str) -> int:
    try:
        return _import_refs_raw(ref_file_path)
    except Exception as e:
        _spool_on_failure("academic_references", "_import_refs_raw",
                          (str(ref_file_path),), {}, e)
        return 0


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
        print(f"- 主机与端口 : (见 config.yaml / 环境变量)")
        print("-" * 70)
        print("📊 核心数据表记录统计：")
        for t, cnt in counts.items():
            print(f"  • {t:<24}: {cnt} 条记录")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")


# ==============================================================================
# 容错层：熔断器 + 本地暂存(outbox) + 自动补传
# ------------------------------------------------------------------------------
# 落库是【旁路】。数据库不可用时，既不能丢数据，也不能拖慢 agent。三条不变量：
#   1. 落库失败绝不抛到调用方——主流程永远不受数据库影响；
#   2. 失败的记录本地留底，库恢复后自动补传（不丢数据）；
#   3. 库不可用时不得反复等待连接超时——连续失败即熔断，冷却期内快速失败。
# 状态一律落盘（.evolution/）：auto-skills 每次调用都是新进程，内存态无效。
# 开关全部在 database.failover 段，可整体关闭。
# ==============================================================================

import time as _time

_FAILOVER_MARK = "failover-v1"
_REPLAY_GUARD = {"running": False}


class DatabaseUnavailable(RuntimeError):
    """数据库当前不可用（已关闭 / 连接失败 / 熔断器打开）。"""


def _failover_cfg() -> Dict[str, Any]:
    """database.failover 段配置（永远返回 dict）"""
    fo = db_config().get("failover", {}) or {}
    return fo if isinstance(fo, dict) else {}


def _fo_get(key: str, default):
    return _failover_cfg().get(key, default)


def _evolution_dir() -> Path:
    d = SKILL_ROOT / ".evolution"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _health_file() -> Path:
    return _evolution_dir() / "db_health.json"


def _spool_file() -> Path:
    return _evolution_dir() / "db_spool" / "pending.jsonl"


def _dead_file() -> Path:
    return _evolution_dir() / "db_spool" / "dead.jsonl"


def _load_health() -> Dict[str, Any]:
    try:
        return json.loads(_health_file().read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _save_health(h: Dict[str, Any]) -> None:
    p = _health_file()
    tmp = p.parent / (p.name + ".tmp")
    try:
        tmp.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(_health_file())
    except Exception:
        pass


# ---------------------------------------------------------------- 通知（可选）

def _notify(title: str, body: str) -> None:
    """熔断打开时的告警。best-effort：任何失败都不得影响主流程。"""
    try:
        if not _fo_get("notify_on_breaker", False):
            return
        cfg = config_manager.get_value("notifications", {}) or {}
        if not isinstance(cfg, dict):
            return
        key = (cfg.get("serverchan_sendkey") or "").strip()
        if not key:
            return
        import urllib.parse
        import urllib.request
        data = urllib.parse.urlencode({"title": title, "desp": body}).encode("utf-8")
        req = urllib.request.Request(
            f"https://sctapi.ftqq.com/{key}.send", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        urllib.request.urlopen(req, timeout=8).read()
    except Exception:
        pass


# ---------------------------------------------------------------- 健康状态

def health_state() -> Dict[str, Any]:
    """给 --doctor / --status 用的健康快照"""
    h = _load_health()
    now = _time.time()
    until = float(h.get("breaker_open_until") or 0)
    h["breaker_open"] = until > now
    h["breaker_remaining_seconds"] = max(0, int(until - now))
    h.setdefault("consecutive_failures", 0)
    h["spool_pending"] = spool_count()
    h["spool_dead"] = _count_lines(_dead_file())
    h["failover_enabled"] = bool(_fo_get("enabled", True))
    return h


def _health_record_success() -> None:
    h = _load_health()
    h["consecutive_failures"] = 0
    h["breaker_open_until"] = 0
    h["last_ok_at"] = datetime.now().isoformat(timespec="seconds")
    _save_health(h)


def _health_record_failure(exc: BaseException) -> None:
    h = _load_health()
    n = int(h.get("consecutive_failures") or 0) + 1
    h["consecutive_failures"] = n
    h["last_error"] = f"{type(exc).__name__}: {exc}"[:500]
    h["last_error_at"] = datetime.now().isoformat(timespec="seconds")
    threshold = int(_fo_get("breaker_threshold", 3))
    opened_now = False
    if n >= threshold and float(h.get("breaker_open_until") or 0) <= _time.time():
        cooldown = int(_fo_get("breaker_cooldown_seconds", 120))
        h["breaker_open_until"] = _time.time() + cooldown
        h["breaker_opened_at"] = datetime.now().isoformat(timespec="seconds")
        opened_now = True
    _save_health(h)
    if opened_now:
        _notify("auto-skills 落库熔断",
                f"连续 {n} 次无法使用数据库，已熔断 {_fo_get('breaker_cooldown_seconds', 120)} 秒。\\n"
                f"最后一次错误：{h['last_error']}\\n"
                f"期间失败的记录已本地暂存，库恢复后会自动补传。\\n"
                f"待补传：{spool_count()} 条")


# ---------------------------------------------------------------- 本地暂存

def _count_lines(p: Path) -> int:
    try:
        with open(p, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def spool_count() -> int:
    return _count_lines(_spool_file())


def _append_jsonl(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def spool_add(stream: str, fn_name: str, args, kwargs, error: BaseException) -> bool:
    """把一次失败落库的调用参数暂存到本地，等库恢复后补传。"""
    if not _fo_get("enabled", True) or not _fo_get("spool_enabled", True):
        return False
    limit = int(_fo_get("spool_max_records", 2000))
    if spool_count() >= limit:
        _log_db_error("spool_add", RuntimeError(f"暂存已满（{limit} 条），本次丢弃以保护磁盘"))
        return False
    rec = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "stream": stream,
        "fn": fn_name,
        "args": list(args or []),
        "kwargs": dict(kwargs or {}),
        "attempts": 0,
        "error": f"{type(error).__name__}: {error}"[:300],
    }
    try:
        json.dumps(rec, ensure_ascii=False)   # 不可序列化就别存（避免补传时炸）
    except Exception as e:
        _log_db_error("spool_add", RuntimeError(f"参数不可序列化，无法暂存：{e}"))
        return False
    try:
        _append_jsonl(_spool_file(), rec)
        return True
    except Exception as e:
        _log_db_error("spool_add", e)
        return False


def _spool_on_failure(stream: str, fn_name: str, args, kwargs, exc: BaseException) -> None:
    """落库失败的统一收口：记日志 + 本地暂存，绝不抛给调用方。"""
    _log_db_error(fn_name, exc)
    spool_add(stream, fn_name, args, kwargs, exc)


def _read_spool() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with open(_spool_file(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
    except FileNotFoundError:
        pass
    except Exception as e:
        _log_db_error("_read_spool", e)
    return out


def _write_spool(items: List[Dict[str, Any]]) -> None:
    p = _spool_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.parent / (p.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        tmp.replace(p)
    except Exception as e:
        _log_db_error("_write_spool", e)


def spool_purge_expired() -> int:
    """丢弃超过 spool_max_age_days 的暂存记录，防止无限积压。"""
    days = float(_fo_get("spool_max_age_days", 7))
    if days <= 0:
        return 0
    items = _read_spool()
    if not items:
        return 0
    cutoff = datetime.now().timestamp() - days * 86400
    keep, dropped = [], []
    for it in items:
        try:
            ts = datetime.fromisoformat(it.get("at", "")).timestamp()
        except Exception:
            ts = _time.time()
        (keep if ts >= cutoff else dropped).append(it)
    if dropped:
        for it in dropped:
            _append_jsonl(_dead_file(), dict(it, dead_reason="expired"))
        _write_spool(keep)
        _log_db_error("spool_purge_expired",
                      RuntimeError(f"{len(dropped)} 条暂存超过 {days} 天，已移入 dead.jsonl"))
    return len(dropped)


def spool_replay(limit: int = 50) -> tuple:
    """把暂存记录按原参数重新调用对应落库函数。返回 (成功数, 仍失败数)。"""
    items = _read_spool()
    if not items:
        return (0, 0)
    max_attempts = int(_fo_get("max_attempts", 5))
    g = globals()
    replayed = failed = 0
    keep: List[Dict[str, Any]] = []

    for it in items[:limit]:
        fn = g.get(it.get("fn") or "")
        if fn is None:
            _append_jsonl(_dead_file(), dict(it, dead_reason="unknown_fn"))
            failed += 1
            continue
        ok = False
        try:
            ok = bool(fn(*(it.get("args") or []), **(it.get("kwargs") or {})))
        except Exception as e:
            _log_db_error(f"replay:{it.get('fn')}", e)
        if ok:
            replayed += 1
        else:
            it["attempts"] = int(it.get("attempts") or 0) + 1
            if it["attempts"] >= max_attempts:
                _append_jsonl(_dead_file(), dict(it, dead_reason="max_attempts"))
            else:
                keep.append(it)
            failed += 1

    keep.extend(items[limit:])          # 本次没轮到的原样保留
    _write_spool(keep)
    return (replayed, failed)


def _maybe_replay() -> None:
    """库刚连上时顺手补传。节流 + 防重入（补传本身会再进 get_db_connection）。"""
    if not _fo_get("enabled", True) or _REPLAY_GUARD["running"]:
        return
    if spool_count() == 0:
        return
    h = _load_health()
    interval = float(_fo_get("replay_interval_seconds", 60))
    if _time.time() - float(h.get("last_replay_at") or 0) < interval:
        return
    _REPLAY_GUARD["running"] = True
    try:
        spool_purge_expired()
        ok, bad = spool_replay(limit=int(_fo_get("replay_batch", 50)))
        h = _load_health()
        h["last_replay_at"] = _time.time()
        h["last_replay_at_human"] = datetime.now().isoformat(timespec="seconds")
        h["last_replay_result"] = f"补传成功 {ok} 条，仍待补 {spool_count()} 条"
        _save_health(h)
    except Exception as e:
        _log_db_error("_maybe_replay", e)
    finally:
        _REPLAY_GUARD["running"] = False


# ---------------------------------------------------------------- 连接包装

def get_db_connection(timeout: int = 8):
    """带熔断的数据库连接。

    与原始实现的唯一差别：熔断打开时立即抛 DatabaseUnavailable，不再发起 TCP 连接。
    这是「库挂了不能拖慢 agent」的关键——没有它，每次落库都要干等 8 秒超时。
    """
    if not is_db_enabled():
        raise DatabaseUnavailable("数据库已关闭（database.enabled=false 或 type=disabled）")

    if _fo_get("enabled", True):
        until = float(_load_health().get("breaker_open_until") or 0)
        now = _time.time()
        if until > now:
            raise DatabaseUnavailable(
                f"熔断器打开中（剩余 {int(until - now)}s）—— 上次错误："
                f"{_load_health().get('last_error', '')[:150]}")

    try:
        conn = _get_db_connection_raw(timeout=timeout)
    except Exception as e:
        _health_record_failure(e)
        raise

    _health_record_success()
    _maybe_replay()          # 库刚恢复，顺手把暂存回灌
    return conn


def print_db_doctor() -> None:
    """落库健康自检：开关 / 连通性 / 熔断 / 暂存积压。"""
    print("=" * 70)
    print("  auto-skills 落库健康自检")
    print("=" * 70)
    cfg = db_config()
    print(f"  enabled            : {cfg.get('enabled')}")
    print(f"  type               : {cfg.get('type')}")
    print(f"  分项开关           : ", end="")
    print(", ".join(f"{s}={'on' if is_stream_enabled(s) else 'off'}" for s in STREAM_TABLES))
    print(f"  failover.enabled   : {_fo_get('enabled', True)}")
    print(f"  breaker_threshold  : {_fo_get('breaker_threshold', 3)} 次"
          f"  cooldown={_fo_get('breaker_cooldown_seconds', 120)}s")

    h = health_state()
    print("-" * 70)
    print(f"  熔断器             : {'【打开】剩余 ' + str(h['breaker_remaining_seconds']) + 's' if h['breaker_open'] else '正常（闭合）'}")
    print(f"  连续失败次数       : {h.get('consecutive_failures', 0)}")
    print(f"  上次成功           : {h.get('last_ok_at', '—')}")
    print(f"  上次失败           : {h.get('last_error_at', '—')}  {h.get('last_error', '')[:90]}")
    print(f"  上次补传           : {h.get('last_replay_at_human', '—')}  {h.get('last_replay_result', '')}")
    print(f"  暂存待补传         : {h['spool_pending']} 条   （{_spool_file()}）")
    print(f"  暂存已放弃         : {h['spool_dead']} 条   （{_dead_file()}）")

    print("-" * 70)
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            ver = cur.fetchone()[0]
        conn.close()
        print(f"  实时连通性         : OK（服务端 {ver}）")
    except Exception as e:
        print(f"  实时连通性         : 失败 —— {type(e).__name__}: {e}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="auto-skills 数据库存储与全链路自动落库引擎")
    parser.add_argument("--test", action="store_true", help="测试数据库连接与版本信息")
    parser.add_argument("--init-db", action="store_true", help="初始化创建全部数据表结构")
    parser.add_argument("--status", action="store_true", help="查看数据库记录概况")
    parser.add_argument("--sync-skills", action="store_true", help="将当前技能台账同步至数据库")
    parser.add_argument("--import-refs", help="导入参考文献定义文件至数据库 (如 compile_references_100.py)")

    parser.add_argument("--doctor", action="store_true", help="落库健康自检：开关/连通性/熔断/暂存积压")
    parser.add_argument("--flush-spool", action="store_true", help="手动补传本地暂存的失败记录")
    parser.add_argument("--cleanup-traces", type=int, nargs="?", const=30, default=None, help="执行指定天数(默认30天)滚动清理过期工具调用轨迹")

    args = parser.parse_args()

    if args.doctor:
        print_db_doctor()
        sys.exit(0)

    if args.flush_spool:
        ok, bad = spool_replay(limit=100000)
        print(f"[OK] 补传完成：成功 {ok} 条，仍待补 {spool_count()} 条，放弃 {_count_lines(_dead_file())} 条。")
        sys.exit(0 if bad == 0 else 1)

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
