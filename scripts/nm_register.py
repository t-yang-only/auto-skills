#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nm_register.py — NM-Skills 多 Agent 原子任务认领、互斥排他锁与台账协调引擎 (v2.0)
================================================================================
核心问题解决：
1. 【杜绝多 Agent 同时进行同一任务 (Atomic Task Claim & Mutual Exclusion)】：
   - 引入原子任务认领机制 (`claim`)：任何 Agent 在动手前必须显式抢占任务锁；
   - 排他租约锁 (Lease with TTL，默认 45 分钟)：若任务已被认领且未过期，其他 Agent 强行认领会被绝对拦截并报告持有者详情；
   - 跨进程/跨会话原子文件锁 (Atomic Mutex)：利用底层排他锁，杜绝并发竞争 (Race Condition)；
2. 【彻底根除同号序号冲突 (Race-Free Monotonic ID Reservation)】：
   - 分配 Agent 编号时加锁保护，保证绝对严格递增，永不再出现 015x3、016x2 等同号冲突；
3. 【工作区文件改动冲突防撞 (File Collision Guard)】：
   - 登记即将修改的文件列表；若发现其他活跃 Agent 正在编辑相同文件，立即报警；
4. 【任务生命周期看板与自动过期回收 (Task Kanban & Stale GC)】：
   - 维护 `agent_word/任务认领表.md` (TODO / CLAIMED / IN_PROGRESS / DONE / BLOCKED)；
   - 超时僵尸任务自动回收 (`gc`)，防止死锁。

CLI 命令：
    # 1. 原子认领任务 (未被抢占则获胜并加锁，已被抢占则返回拦截详情)
    python scripts/nm_register.py claim --task-id "TASK-001" --task "重构API层" --client CODE

    # 2. 检查当前看板与谁在做什么
    python scripts/nm_register.py board

    # 3. 完成任务并释放锁，追加日志
    python scripts/nm_register.py done --task-id "TASK-001" --changes "完成重构" --files "api.py"

    # 4. 释放/放弃任务认领 (遇错回滚)
    python scripts/nm_register.py release --task-id "TASK-001" --reason "遇到阻断"

    # 5. 清理过期超时僵尸锁
    python scripts/nm_register.py gc
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import string
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AGENT_DIR_NAME = "agent_word"
LOCKS_DIR_NAME = ".locks"

REGISTER_HEADER = (
    "| 编号 | 任务ID | Agent/客户端 | 任务目标 | 修改内容 | API 变更 | 获取/新增文件 | "
    "使用 Skill | 使用 MCP | 调用工具 | 开始时间 | 完成时间 | 状态 |"
)
REGISTER_SEP = (
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
)

BOARD_HEADER = (
    "| 任务ID | 任务名称 | 当前持有者 | 认领时间 | 租约截止 (TTL) | 状态 | 涉及文件 |"
)
BOARD_SEP = (
    "| --- | --- | --- | --- | --- | --- | --- |"
)


def _n_items(v) -> int:
    """changes/files 传进来是逗号分隔的字符串，len() 数出来的是字符数不是条数
    —— 实测记成「改动 25 项 / 涉及 25 个文件」，而实际分别是 1 条和 2 个。"""
    if not v:
        return 0
    if isinstance(v, (list, tuple, set)):
        return len(v)
    return len([x for x in str(v).split(",") if x.strip()])


def _db_note(where: str, exc: BaseException) -> None:
    """落库失败留痕，替代原来的 `except Exception: pass`。"""
    try:
        log_dir = Path(__file__).resolve().parent.parent / ".evolution"
        log_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime as _dt
        with open(log_dir / "db_sync_errors.log", "a", encoding="utf-8") as f:
            f.write(f"{_dt.now().isoformat(timespec='seconds')} [nm_register:{where}] "
                    f"{type(exc).__name__}: {exc}\n")
    except Exception:
        pass


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def escape_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ").strip()


class FileMutex:
    """
    跨进程/跨客户端安全的原子排他文件锁 (基于独占创建机制)
    """
    def __init__(self, lock_path: Path, timeout: float = 10.0, poll_interval: float = 0.1):
        self.lock_path = lock_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.acquired = False

    def __enter__(self):
        start = time.time()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                # O_CREAT | O_EXCL 在操作系统内核层保证原子性
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"pid:{os.getpid()};time:{time.time()}".encode("utf-8"))
                os.close(fd)
                self.acquired = True
                return self
            except FileExistsError:
                # 检查是否为超过 30 秒的死锁孤儿锁
                try:
                    mtime = self.lock_path.stat().st_mtime
                    if time.time() - mtime > 30.0:
                        try:
                            self.lock_path.unlink()
                            continue
                        except Exception:
                            pass
                except Exception:
                    pass

                if time.time() - start > self.timeout:
                    raise TimeoutError(f"获取排他协调锁超时: {self.lock_path}")
                time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            try:
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except Exception:
                pass


def get_agent_paths(root: Path) -> Tuple[Path, Path]:
    agent_dir = root / AGENT_DIR_NAME
    locks_dir = agent_dir / LOCKS_DIR_NAME
    agent_dir.mkdir(parents=True, exist_ok=True)
    locks_dir.mkdir(parents=True, exist_ok=True)
    return agent_dir, locks_dir


def init_workspace_files(agent_dir: Path):
    """初始化 agent_word 目录下的规范文件"""
    readme = agent_dir / "README.md"
    if not readme.exists():
        readme.write_text("""# Agent Word 台账与多 Agent 协同中枢

本目录由 NM-Skills 自动维护，内置排他任务认领 (Claim)、文件防冲突锁 (File Lock) 与无冲突单调序号分配器。

## 核心台账文件：
- `任务认领表.md`：任务级互斥认领总看板 (TODO -> CLAIMED -> IN_PROGRESS -> DONE)；
- `工作登记表.md`：所有 Agent 的历史工作流水账（严格递增编号）；
- `工作日志.md`：按时间顺序追加的详细工作汇报与复盘；
- `技能建议.md`：本项目已验证的优质 Skill / MCP / 工具沉淀；
- `API变更.md`：接口协议变更审计；
- `文件清单.md`：文件创建与修改追溯清单。
""", encoding="utf-8")

    reg_file = agent_dir / "工作登记表.md"
    if not reg_file.exists():
        reg_file.write_text(f"# 工作登记表\n\n{REGISTER_HEADER}\n{REGISTER_SEP}\n", encoding="utf-8")

    board_file = agent_dir / "任务认领表.md"
    if not board_file.exists():
        board_file.write_text(f"# 任务认领与互斥看板\n\n{BOARD_HEADER}\n{BOARD_SEP}\n", encoding="utf-8")

    for f in ["工作日志.md", "API变更.md", "文件清单.md"]:
        p = agent_dir / f
        if not p.exists():
            p.write_text(f"# {p.stem}\n\n", encoding="utf-8")

    rec_file = agent_dir / "技能建议.md"
    if not rec_file.exists():
        rec_file.write_text("# 技能建议\n\n## 推荐 Skill\n\n## 推荐 MCP\n\n## 推荐工具\n\n", encoding="utf-8")


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


# ==============================================================================
# 编号防撞单调分配器
# ==============================================================================

def allocate_id_atomic(client: str, agent_dir: Path, locks_dir: Path) -> str:
    """
    在全局互斥锁保护下读取并分配唯一的 Agent 编号，彻底杜绝同号冲突！
    """
    lock = FileMutex(locks_dir / "id_allocator.lock")
    with lock:
        reg_file = agent_dir / "工作登记表.md"
        text = read_file(reg_file)

        # 扫描该客户端所有已分配的三位序号
        pattern = re.compile(r"\|\s*NM-" + re.escape(client) + r"-(\d{3})(?:-([a-z0-9]+))?\s*\|", re.I)
        matched_seqs = []
        for m in pattern.finditer(text):
            try:
                matched_seqs.append(int(m.group(1)))
            except Exception:
                pass

        next_seq = max(matched_seqs) + 1 if matched_seqs else 1
        candidate = f"NM-{client}-{next_seq:03d}"

        # 极端防重检查：若依然有字面冲突，追加微秒短后缀
        if f"| {candidate} |" in text:
            suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
            candidate = f"{candidate}-{suffix}"

        return candidate


# ==============================================================================
# 任务原子认领与排他锁 (Task Claim & Mutex)
# ==============================================================================

def normalize_task_id(task_id: Optional[str], task_name: str) -> str:
    if task_id and task_id.strip():
        return task_id.strip().upper()
    # 自动从任务名哈希推导稳定的 task_id
    clean_name = re.sub(r"[^\w\-_]", "", task_name)[:12]
    h = hashlib_short(task_name)
    return f"TASK-{clean_name}-{h}".upper()


def hashlib_short(text: str) -> str:
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:6]


def get_task_claims(locks_dir: Path) -> Dict[str, Dict[str, Any]]:
    """读取所有活跃的任务锁"""
    claims = {}
    for lock_file in locks_dir.glob("task_*.json"):
        try:
            data = json.loads(lock_file.read_text(encoding="utf-8"))
            tid = data.get("task_id")
            if tid:
                claims[tid] = data
        except Exception:
            pass
    return claims


def claim_task_atomic(
    root: Path,
    task_name: str,
    client: str,
    task_id: Optional[str] = None,
    files: str = "",
    ttl_minutes: int = 45,
    force: bool = False
) -> Dict[str, Any]:
    """
    原子认领任务。若该任务已被其他活跃 Agent 抢占且未超时，直接拒绝！
    """
    agent_dir, locks_dir = get_agent_paths(root)
    init_workspace_files(agent_dir)

    tid = normalize_task_id(task_id, task_name)
    coordination_lock = FileMutex(locks_dir / "task_coordination.lock")

    with coordination_lock:
        task_lock_file = locks_dir / f"task_{tid}.json"
        now_ts = time.time()

        # 检查是否已存在认领
        if task_lock_file.exists():
            try:
                curr = json.loads(task_lock_file.read_text(encoding="utf-8"))
                expires_at = curr.get("expires_at_ts", 0)
                holder = curr.get("holder_id", "未知Agent")
                holder_task = curr.get("task_name", "")

                # 如果未过期且非强制接管
                if now_ts < expires_at and not force:
                    rem_min = int((expires_at - now_ts) / 60)
                    msg = (
                        f"❌ 【认领被拒绝】任务 [{tid}] 当前正被 【{holder}】 进行中！\n"
                        f"   任务描述: {holder_task}\n"
                        f"   认领时间: {curr.get('claimed_at')}\n"
                        f"   租约有效: 剩余约 {rem_min} 分钟 (截止 {curr.get('expires_at')})\n"
                        f"   💡 防撞策略: 严禁多个 Agent 同时进行同一任务！请选择其他任务，或待其完成后再协作。"
                    )
                    return {
                        "success": False,
                        "task_id": tid,
                        "status": "BLOCKED_BY_OTHER_AGENT",
                        "holder": holder,
                        "remaining_minutes": rem_min,
                        "message": msg
                    }
                else:
                    if now_ts >= expires_at:
                        print(f"[*] 任务 [{tid}] 原持有者【{holder}】的租约已超时，执行自动回收并重新认领...")
                    elif force:
                        print(f"[!] 正在强制接管任务 [{tid}] (原持有者: {holder})...")
            except Exception:
                pass

        # 检查涉及的文件是否有其他 Agent 正在修改
        file_list = [f.strip() for f in files.split(",") if f.strip()]
        if file_list:
            all_claims = get_task_claims(locks_dir)
            for other_tid, other_c in all_claims.items():
                if other_tid == tid:
                    continue
                if now_ts < other_c.get("expires_at_ts", 0):
                    other_files = other_c.get("files", [])
                    conflict_files = set(file_list).intersection(set(other_files))
                    if conflict_files and not force:
                        msg = (
                            f"⚠️ 【文件冲突拦截】任务 [{tid}] 涉及的文件 {list(conflict_files)} "
                            f"正由任务 [{other_tid}] ({other_c.get('holder_id')}) 编辑中！请稍后再试。"
                        )
                        return {
                            "success": False,
                            "task_id": tid,
                            "status": "FILE_CONFLICT",
                            "conflict_files": list(conflict_files),
                            "message": msg
                        }

        # 成功获得认领权：分配严格单调 Agent ID
        agent_id = allocate_id_atomic(client, agent_dir, locks_dir)
        expire_time = datetime.now() + timedelta(minutes=ttl_minutes)

        claim_info = {
            "task_id": tid,
            "task_name": task_name,
            "holder_id": agent_id,
            "client": client,
            "claimed_at": now_str(),
            "expires_at": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at_ts": now_ts + (ttl_minutes * 60),
            "status": "IN_PROGRESS",
            "files": file_list
        }

        # 写入任务锁
        task_lock_file.write_text(json.dumps(claim_info, ensure_ascii=False, indent=2), encoding="utf-8")

        # 登记到 工作登记表.md (状态为 进行中)
        reg_file = agent_dir / "工作登记表.md"
        reg_text = read_file(reg_file)
        start_t = now_str()
        cells = [
            agent_id, tid, client, task_name, "待实施", "无", files or "无",
            "nm-skills", "无", "nm_register", start_t, "", "进行中"
        ]
        new_row = "| " + " | ".join(escape_cell(c) for c in cells) + " |"
        write_file(reg_file, reg_text.rstrip() + "\n" + new_row + "\n")

        # 刷新 任务认领表.md
        refresh_board_markdown(agent_dir, locks_dir)

        # 5. 全链路自动持久化入库 (MySQL 8.4)：认领记录 + 工具链调用轨迹
        try:
            import db_sync
            db_sync.record_task_claim_db(claim_info, project_root=str(root))
            db_sync.record_tool_trace_db(
                "nm-skills", "nm_register", action="claim", stage="coordination",
                input_params={"task_id": tid, "ttl_minutes": ttl_minutes},
                output_summary=f"{agent_id} 独占锁定 {tid}（租约 {ttl_minutes} 分钟）",
                project_root=str(root), client=os.environ.get("NM_CLIENT_ID", "CODE"))
        except Exception as _e:
            _db_note("claim_trace", _e)

        msg = f"🎉 【认领成功】任务 [{tid}] 已成功由 【{agent_id}】 独占锁定，租约有效期 {ttl_minutes} 分钟。"
        print(msg)
        return {
            "success": True,
            "agent_id": agent_id,
            "task_id": tid,
            "status": "IN_PROGRESS",
            "expires_at": claim_info["expires_at"],
            "message": msg
        }


def release_task_atomic(root: Path, task_id: str, reason: str = "主动放弃") -> bool:
    """
    放弃或释放任务锁
    """
    agent_dir, locks_dir = get_agent_paths(root)
    tid = task_id.strip().upper()
    coordination_lock = FileMutex(locks_dir / "task_coordination.lock")

    with coordination_lock:
        lock_file = locks_dir / f"task_{tid}.json"
        if lock_file.exists():
            try:
                curr = json.loads(lock_file.read_text(encoding="utf-8"))
                holder = curr.get("holder_id", "")
                lock_file.unlink()
                print(f"[OK] 任务 [{tid}] 的排他锁已释放 (原持有者: {holder}, 原因: {reason})")

                # 更新登记表状态为已释放/取消
                reg_file = agent_dir / "工作登记表.md"
                reg_text = read_file(reg_file)
                lines = reg_text.splitlines()
                for i, l in enumerate(lines):
                    if f"| {holder} |" in l or f"| {tid} |" in l:
                        if "进行中" in l:
                            lines[i] = l.replace("进行中", f"已释放({escape_cell(reason)[:10]})")
                write_file(reg_file, "\n".join(lines) + "\n")

                refresh_board_markdown(agent_dir, locks_dir)
                return True
            except Exception as e:
                print(f"[ERROR] 释放任务锁失败: {e}")
                return False
        else:
            print(f"[!] 任务 [{tid}] 当前并无活跃锁")
            return True


def complete_task_atomic(
    root: Path,
    task_id: str,
    changes: str,
    api: str = "",
    files: str = "",
    skills: str = "nm-skills",
    mcps: str = "",
    tools: str = ""
) -> bool:
    """
    完成任务：更新工作登记表为已完成、追加详细工作日志、更新推荐列表，并安全解除任务锁！
    """
    agent_dir, locks_dir = get_agent_paths(root)
    tid = task_id.strip().upper()
    coordination_lock = FileMutex(locks_dir / "task_coordination.lock")

    with coordination_lock:
        lock_file = locks_dir / f"task_{tid}.json"
        holder_id = ""
        task_name = ""
        client = "CODE"
        if lock_file.exists():
            try:
                curr = json.loads(lock_file.read_text(encoding="utf-8"))
                holder_id = curr.get("holder_id", "")
                task_name = curr.get("task_name", "")
                client = curr.get("client", "CODE")
                lock_file.unlink()  # 任务完成，解除互斥排他锁
            except Exception:
                pass

        if not holder_id:
            holder_id = f"NM-{client}-DONE"

        done_t = now_str()

        # 1. 更新 工作登记表.md
        reg_file = agent_dir / "工作登记表.md"
        reg_text = read_file(reg_file)
        lines = reg_text.splitlines()
        found = False
        for i, l in enumerate(lines):
            if f"| {holder_id} |" in l or f"| {tid} |" in l:
                # 补全完成时间和状态
                parts = [p.strip() for p in l.split("|")[1:-1]]
                if len(parts) >= 12:
                    parts[4] = escape_cell(changes)  # 修改内容
                    parts[5] = escape_cell(api or "无")   # API变更
                    parts[6] = escape_cell(files or "无") # 文件
                    parts[7] = escape_cell(skills or "nm-skills")
                    parts[8] = escape_cell(mcps or "无")
                    parts[9] = escape_cell(tools or "无")
                    parts[11] = done_t               # 完成时间
                    parts[12] = "已完成"             # 状态
                    lines[i] = "| " + " | ".join(parts) + " |"
                    found = True
                    break

        if not found:
            # 独立补一行
            cells = [
                holder_id, tid, client, task_name or tid, changes, api or "无", files or "无",
                skills, mcps or "无", tools or "无", done_t, done_t, "已完成"
            ]
            lines.append("| " + " | ".join(escape_cell(c) for c in cells) + " |")

        write_file(reg_file, "\n".join(lines) + "\n")

        # 2. 追加 工作日志.md
        log_file = agent_dir / "工作日志.md"
        log_text = read_file(log_file)
        block = (
            f"\n## [{done_t}] {holder_id} (任务: {tid})\n\n"
            f"- 客户端：{escape_cell(client)}\n"
            f"- 任务目标：{escape_cell(task_name or tid)}\n"
            f"- 修改内容：{escape_cell(changes)}\n"
            f"- API 变更：{escape_cell(api or '无')}\n"
            f"- 获取/新增文件：{escape_cell(files or '无')}\n"
            f"- 使用 Skill：{escape_cell(skills or '无')}\n"
            f"- 使用 MCP：{escape_cell(mcps or '无')}\n"
            f"- 调用工具：{escape_cell(tools or '无')}\n"
            f"- 结果状态：已完成 (排他任务锁已正常释放)\n"
        )
        write_file(log_file, log_text.rstrip() + "\n" + block)

        # 3. 技能建议
        update_skills_recommendation(agent_dir, skills, mcps, tools)

        # 4. 刷新看板
        refresh_board_markdown(agent_dir, locks_dir)

        # 5. 全链路自动持久化入库 (MySQL 8.4)
        try:
            import db_sync
            done_info = {
                "task_id": tid,
                "holder_id": holder_id,
                "client": client,
                "task_name": task_name or tid,
                "changes": changes,
                "api": api,
                "files": files,
                "skills": skills,
                "mcps": mcps,
                "tools": tools,
                "done_time": done_t,
                "journal": block
            }
            db_sync.record_task_done_db(done_info, project_root=str(root))
            db_sync.record_tool_trace_db(
                "nm-skills", "nm_register", action="done", stage="coordination",
                input_params={"task_id": tid, "changes": _n_items(changes), "files": _n_items(files)},
                output_summary=f"任务 {tid} 完成；改动 {_n_items(changes)} 项、涉及 {_n_items(files)} 个文件",
                project_root=str(root), client=os.environ.get("NM_CLIENT_ID", "CODE"))
        except Exception as _e:
            _db_note("done_trace", _e)

        print(f"[OK] 任务 [{tid}] 已圆满完成！工作台账已更新，排他锁已安全释放。")
        return True


def update_skills_recommendation(agent_dir: Path, skills: str, mcps: str, tools: str):
    rec_file = agent_dir / "技能建议.md"
    text = read_file(rec_file)
    if not text.strip():
        text = "# 技能建议\n\n## 推荐 Skill\n\n## 推荐 MCP\n\n## 推荐工具\n\n"

    # 分割各项
    def parse_items(s):
        return [x.strip() for x in s.split(",") if x.strip() and x.strip() != "无"]

    new_skills = parse_items(skills)
    new_mcps = parse_items(mcps)
    new_tools = parse_items(tools)

    lines = text.splitlines()
    # 简单追加去重
    def append_under(header, items):
        nonlocal lines
        for item in items:
            tag = f"- {item}（最近使用："
            if not any(tag in l for l in lines):
                try:
                    idx = lines.index(header)
                    lines.insert(idx + 1, f"- {item}（最近使用：{now_str()}）")
                except ValueError:
                    lines.extend([header, f"- {item}（最近使用：{now_str()}）"])

    append_under("## 推荐 Skill", new_skills)
    append_under("## 推荐 MCP", new_mcps)
    append_under("## 推荐工具", new_tools)
    write_file(rec_file, "\n".join(lines) + "\n")


def renew_task_atomic(root: Path, task_id: str, extend_minutes: int = 30) -> bool:
    """
    为正在执行的任务续期（延长租约有效截止时间）
    """
    agent_dir, locks_dir = get_agent_paths(root)
    tid = task_id.strip().upper()
    coordination_lock = FileMutex(locks_dir / "task_coordination.lock")

    with coordination_lock:
        lock_file = locks_dir / f"task_{tid}.json"
        if not lock_file.exists():
            print(f"[ERROR] 无法续期：未找到任务 [{tid}] 的活跃锁！")
            return False

        try:
            curr = json.loads(lock_file.read_text(encoding="utf-8"))
            now_ts = time.time()
            old_exp = curr.get("expires_at_ts", now_ts)
            base_ts = max(now_ts, old_exp)
            new_ts = base_ts + (extend_minutes * 60)
            new_exp_str = (datetime.now() + timedelta(minutes=int((new_ts - now_ts)/60))).strftime("%Y-%m-%d %H:%M:%S")

            curr["expires_at_ts"] = new_ts
            curr["expires_at"] = new_exp_str
            lock_file.write_text(json.dumps(curr, ensure_ascii=False, indent=2), encoding="utf-8")

            refresh_board_markdown(agent_dir, locks_dir)
            print(f"[OK] 任务 [{tid}] 租约已成功续期 {extend_minutes} 分钟！新截止时间: {new_exp_str}")
            return True
        except Exception as e:
            print(f"[ERROR] 任务续期失败: {e}")
            return False


def check_file_conflicts_atomic(root: Path, files: str) -> Dict[str, Any]:
    """
    检查指定文件列表是否与其他 Agent 正在进行中的任务或文件锁冲突
    """
    _, locks_dir = get_agent_paths(root)
    file_list = [f.strip() for f in files.split(",") if f.strip()]
    if not file_list:
        return {"has_conflict": False, "conflicts": []}

    claims = get_task_claims(locks_dir)
    now_ts = time.time()
    conflicts = []

    for tid, c in claims.items():
        if now_ts < c.get("expires_at_ts", 0):
            target_files = c.get("files", [])
            overlap = set(file_list).intersection(set(target_files))
            if overlap:
                conflicts.append({
                    "task_id": tid,
                    "holder": c.get("holder_id"),
                    "task_name": c.get("task_name"),
                    "overlapping_files": list(overlap),
                    "expires_at": c.get("expires_at")
                })

    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts
    }


def cmd_whoami(root: Path):
    agent_dir, locks_dir = get_agent_paths(root)
    claims = get_task_claims(locks_dir)
    now_ts = time.time()

    active_locks = []
    for tid, c in claims.items():
        if now_ts < c.get("expires_at_ts", 0):
            active_locks.append(c)

    print("\n" + "=" * 70)
    print("🐂 NM-Skills 多 Agent 协同身份与活跃锁感知 (v2.5 Flagship)")
    print("=" * 70)
    print(f"- 当前工程目录 : {root}")
    print(f"- 协同台账目录 : {agent_dir}")
    print(f"- 活跃独占任务 : {len(active_locks)} 个正在进行")
    if active_locks:
        print("\n[当前进行中独占任务清单]:")
        for lk in active_locks:
            rem = int((lk.get("expires_at_ts", now_ts) - now_ts) / 60)
            print(f"  • 任务ID: [{lk.get('task_id')}] (持有者: {lk.get('holder_id')})")
            print(f"    描述: {lk.get('task_name')}")
            print(f"    文件: {lk.get('files', [])}")
            print(f"    租约剩余: 约 {rem} 分钟 (截止: {lk.get('expires_at')})")
    else:
        print("- 锁状态       : ⚪ 暂无正在独占执行的任务，所有文件均可安全认领！")
    print("=" * 70 + "\n")


def cmd_log(root: Path, limit: int = 15):
    agent_dir, _ = get_agent_paths(root)
    log_file = agent_dir / "工作日志.md"
    reg_file = agent_dir / "工作登记表.md"

    print("\n" + "=" * 70)
    print("📜 NM-Skills 最近工程工作登记与日志")
    print("=" * 70)
    if reg_file.exists():
        content = reg_file.read_text(encoding="utf-8", errors="ignore")
        lines = [l for l in content.splitlines() if l.strip()]
        tail_lines = lines[-limit:] if len(lines) > limit else lines
        print("\n".join(tail_lines))
    else:
        print("暂无登记记录。")
    print("=" * 70 + "\n")


def refresh_board_markdown(agent_dir: Path, locks_dir: Path):
    """根据 live locks 刷新 任务认领表.md"""
    board_file = agent_dir / "任务认领表.md"
    claims = get_task_claims(locks_dir)
    now_ts = time.time()

    rows = []
    for tid, c in claims.items():
        is_active = now_ts < c.get("expires_at_ts", 0)
        status = "🟢 执行中" if is_active else "⌛ 租约已超时"
        files_str = "、".join(c.get("files", [])) or "全局/未限定"
        cells = [
            tid,
            c.get("task_name", ""),
            c.get("holder_id", ""),
            c.get("claimed_at", ""),
            c.get("expires_at", ""),
            status,
            files_str
        ]
        rows.append("| " + " | ".join(escape_cell(x) for x in cells) + " |")

    content = f"# 任务认领与互斥看板\n\n> 实时反映各 Agent 正在独占执行的任务。同一任务在同一时刻只允许一个 Agent 认领。\n\n{BOARD_HEADER}\n{BOARD_SEP}\n"
    if rows:
        content += "\n".join(rows) + "\n"
    else:
        content += "| - | 当前无进行中任务 (所有任务锁已释放) | - | - | - | ⚪ 空闲 | - |\n"

    write_file(board_file, content)


def clean_stale_locks(root: Path) -> int:
    """清理超时超期的僵尸锁"""
    _, locks_dir = get_agent_paths(root)
    coordination_lock = FileMutex(locks_dir / "task_coordination.lock")
    cleaned = 0
    now_ts = time.time()

    with coordination_lock:
        for f in locks_dir.glob("task_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if now_ts >= data.get("expires_at_ts", 0):
                    tid = data.get("task_id")
                    holder = data.get("holder_id")
                    f.unlink()
                    cleaned += 1
                    print(f"[*] 已清理过期僵尸任务锁: [{tid}] (持有者: {holder})")
            except Exception:
                pass
    return cleaned


# ==============================================================================
# CLI 入口
# ==============================================================================

def main():
    root_parser = argparse.ArgumentParser(add_help=False)
    root_parser.add_argument("--root", default=None, help="工程根目录，默认当前目录")

    parser = argparse.ArgumentParser(
        description="NM-Skills 多 Agent 原子任务认领与互斥台账中枢 (v2.0)",
        parents=[root_parser]
    )

    subparsers = parser.add_subparsers(dest="action", help="选择动作")

    # 1. claim 任务认领
    p_claim = subparsers.add_parser("claim", parents=[root_parser], help="原子认领任务并加排他锁")
    p_claim.add_argument("--task", required=True, help="任务目标描述")
    p_claim.add_argument("--task-id", default=None, help="指定任务唯一标识 (如 TASK-001，缺省自动生成)")
    p_claim.add_argument("--client", default="CODE", help="客户端标识 (CODE/CUR/DB/DS)")
    p_claim.add_argument("--files", default="", help="预估修改的文件列表 (逗号分隔)")
    p_claim.add_argument("--ttl", type=int, default=45, help="租约有效时长分钟 (默认 45)")
    p_claim.add_argument("--force", action="store_true", help="强制抢占接管任务")

    # 2. done 任务完成
    p_done = subparsers.add_parser("done", parents=[root_parser], help="完成任务并释放排他锁")
    p_done.add_argument("--task-id", required=True, help="任务唯一标识")
    p_done.add_argument("--changes", required=True, help="具体修改内容")
    p_done.add_argument("--api", default="", help="API 变更")
    p_done.add_argument("--files", default="", help="修改/新增的文件")
    p_done.add_argument("--skills", default="nm-skills", help="使用的 Skill")
    p_done.add_argument("--mcps", default="", help="使用的 MCP")
    p_done.add_argument("--tools", default="", help="调用的工具")

    # 3. release 释放任务
    p_release = subparsers.add_parser("release", parents=[root_parser], help="放弃或提前释放任务锁")
    p_release.add_argument("--task-id", required=True, help="任务唯一标识")
    p_release.add_argument("--reason", default="手动放弃", help="释放原因")

    # 4. board 查看看板
    subparsers.add_parser("board", parents=[root_parser], help="查看实时任务认领看板")

    # 5. gc 清理僵尸锁
    subparsers.add_parser("gc", parents=[root_parser], help="清理超时过期僵尸任务锁")

    # 6. renew 租约续期
    p_renew = subparsers.add_parser("renew", parents=[root_parser], help="为进行中的任务延长租约有效时间")
    p_renew.add_argument("--task-id", required=True, help="任务唯一标识")
    p_renew.add_argument("--extend", type=int, default=30, help="延长时长分钟数 (默认 30)")

    # 7. check-file 文件冲突前置检测
    p_check = subparsers.add_parser("check-file", parents=[root_parser], help="预先检测即将修改的文件是否已被他人锁定")
    p_check.add_argument("--files", required=True, help="待检测的文件列表 (逗号分隔)")

    # 8. whoami 查看当前活跃锁
    subparsers.add_parser("whoami", parents=[root_parser], help="查看当前工程目录的排他锁状态与活跃任务")

    # 9. log 查看工作登记日志
    p_log = subparsers.add_parser("log", parents=[root_parser], help="查看最近的工作登记与流水日志")
    p_log.add_argument("--limit", type=int, default=15, help="显示行数 (默认 15)")

    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path.cwd()

    if args.action == "claim":
        res = claim_task_atomic(
            root=root,
            task_name=args.task,
            client=args.client,
            task_id=args.task_id,
            files=args.files,
            ttl_minutes=args.ttl,
            force=args.force
        )
        if not res.get("success"):
            print(res.get("message"))
            sys.exit(1)
        sys.exit(0)

    elif args.action == "done":
        ok = complete_task_atomic(
            root=root,
            task_id=args.task_id,
            changes=args.changes,
            api=args.api,
            files=args.files,
            skills=args.skills,
            mcps=args.mcps,
            tools=args.tools
        )
        sys.exit(0 if ok else 1)

    elif args.action == "release":
        ok = release_task_atomic(root=root, task_id=args.task_id, reason=args.reason)
        sys.exit(0 if ok else 1)

    elif args.action == "board":
        agent_dir, locks_dir = get_agent_paths(root)
        init_workspace_files(agent_dir)
        refresh_board_markdown(agent_dir, locks_dir)
        print(read_file(agent_dir / "任务认领表.md"))
        sys.exit(0)

    elif args.action == "gc":
        cnt = clean_stale_locks(root)
        print(f"[OK] 僵尸锁回收完毕，共清理 {cnt} 个过期锁。")
        sys.exit(0)

    elif args.action == "renew":
        ok = renew_task_atomic(root=root, task_id=args.task_id, extend_minutes=args.extend)
        sys.exit(0 if ok else 1)

    elif args.action == "check-file":
        res = check_file_conflicts_atomic(root=root, files=args.files)
        if res.get("has_conflict"):
            print(f"⚠️ 检测到 {len(res['conflicts'])} 处文件占用冲突：")
            for c in res["conflicts"]:
                print(f"  - 任务: [{c['task_id']}] (持有者: {c['holder']}, 任务名: {c['task_name']})")
                print(f"    冲突文件: {c['overlapping_files']} | 截止时间: {c['expires_at']}")
            sys.exit(1)
        else:
            print("✅ 检查通过：所选文件当前无任何 Agent 占用冲突，可安全编辑！")
            sys.exit(0)

    elif args.action == "whoami":
        cmd_whoami(root=root)
        sys.exit(0)

    elif args.action == "log":
        cmd_log(root=root, limit=args.limit)
        sys.exit(0)

    else:
        # 兼容旧版参数: 如果直接传 --client --task 等
        parser.print_help()


if __name__ == "__main__":
    main()
