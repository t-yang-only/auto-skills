#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wizard_setup.py — auto-skills 首次启动引导与全自动配置向导 (v3.0)
==================================================================
核心功能：
1. 【配置门禁检查】：在任意 Agent 首次调用时，检查 `config/config.yaml` 的 `is_configured` 状态；
2. 【引导配置细节】：
   - 是否自动下载公开 auto-skills 更新；
   - 是否永远默认启用 nm-skills 项目目录执行登记与原子任务认领 (agent_word/)；
   - 多渠道推送凭据（Server酱、企微、飞书等，可留空）；
   - 女朋友人格层是否默认开启及是否从知识库拉取特性；
   - 用户个人私有 Git 进化仓库绑定；
3. 【跨 Agent 智能扫描与连接建立】：
   - 自动探测本机所有 AI Agent 环境 (Codex, Agents, DSH, WorkBuddy, Claude Code, Cursor 等)；
   - 提供选择是否一键建立连接与同步映射。

用法：
    # 交互式完整引导向导
    python scripts/wizard_setup.py --interactive

    # 快捷自动推荐配置 (静默/自适应模式)
    python scripts/wizard_setup.py --auto

    # 查看当前配置状态
    python scripts/wizard_setup.py --status

    # 仅执行跨 Agent 扫描与连接
    python scripts/wizard_setup.py --connect-agents
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

import config_manager
import pull_persona_traits

KNOWN_AGENT_PATHS = [
    ("Codex CLI / Extension", Path.home() / ".codex" / "skills"),
    ("Claude Code / ~/.agents", Path.home() / ".agents" / "skills"),
    ("DeepSeek Harness (DSH)", Path.home() / ".dsh" / "skills"),
    ("WorkBuddy AI", Path.home() / ".workbuddy-ai" / "skills"),
    ("Claude Code Dedicated", Path.home() / ".claude" / "skills"),
    ("Cursor IDE", Path.home() / ".cursor" / "skills"),
]


def scan_local_agents() -> List[Dict[str, Any]]:
    results = []
    for name, p in KNOWN_AGENT_PATHS:
        exists = p.exists()
        has_autoskills = (p / "auto-skills").exists() or (p / "auto-skills.lnk").exists()
        results.append({
            "name": name,
            "path": str(p),
            "exists": exists,
            "connected": has_autoskills
        })
    return results


# 本地凭据：绝不允许出现在任何分发副本里。
# 实测踩过两次：第一次是 robocopy 未排除 config/ 导致 4 个根各 3 个副本；
# 第二次是 .claude 与 .cursor 两个根因副本更早（早于首次修复）而清理循环
# 只覆盖"本轮连接成功"的根，所以那两处一直带着真实凭据留在磁盘上。
# 因此清理必须独立成全量巡检，不依赖本轮连了哪些根。
SECRET_FILES = ("config/db.password", "config/gateway.token", "config/gateway.url")


def purge_deployed_secrets(verbose: bool = True) -> List[str]:
    """全量巡检所有已知 harness 根，清除分发副本里的本地凭据。

    与 connect_agents 解耦：即使某根本轮不参与同步（例如路径不存在、
    被 agent_names 过滤、或同步失败），只要它下面已有旧副本就必须清理。
    """
    removed = []
    for name, p in KNOWN_AGENT_PATHS:
        target = p / "auto-skills"
        if not target.exists():
            continue
        for rel in SECRET_FILES:
            f = target / rel
            if not f.exists():
                continue
            try:
                f.unlink()
                removed.append(f"{name}:{rel}")
                if verbose:
                    print(f"  [i] 已清除历史残留凭据: {p.name}/auto-skills/{rel}")
            except Exception as e:
                if verbose:
                    print(f"  [!] 清除失败 {f}: {e}")
    return removed


def _file_map(d: Path) -> Dict[str, str]:
    """目录内容映射 {相对路径: sha256}，排除 .git/.evolution/__pycache__ 与凭据文件。"""
    import hashlib
    out: Dict[str, str] = {}
    root = d.resolve()
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        if any(x in f.parts for x in (".git", ".evolution", "__pycache__")):
            continue
        if rel in SECRET_FILES:
            continue  # 凭据本就不该分发，不参与比对
        try:
            out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            out[rel] = "<unreadable>"
    return out


def _dir_signature(d: Path) -> str:
    """目录内容指纹（路径 + 内容哈希），用于快速判断部署副本是否陈旧。

    两条必须遵守的口径：
    ① **绝不能把 mtime 算进指纹**——源与副本的修改时间天然不同（robocopy 会
       重写时间戳），用它比较会让每个根永远显示"陈旧"，校验器等于坏掉；
    ② **必须排除凭据文件**——副本里没有 config/db.password 是**正确状态**
       （部署时被 /XF 与巡检主动排除），拿"源有副本没有"当陈旧是误判。
    """
    import hashlib
    h = hashlib.sha256()
    for rel, digest in _file_map(d).items():
        h.update(f"{rel}|{digest}\n".encode("utf-8", "replace"))
    return h.hexdigest()[:16]


def check_deployment(verbose: bool = True) -> List[Dict[str, Any]]:
    """检查各 harness 根下的 auto-skills 副本是否与源同步。

    存在的理由：connect_agents 只在首次向导时跑一次，仓库之后每次提交
    都不会再分发——实测 6 个副本全部落后一个功能（缺 discover_skill_roots
    动态根发现），而没有任何机制会报出来。
    """
    src_files = _file_map(SKILL_ROOT)
    src_sig = _dir_signature(SKILL_ROOT)
    rows = []
    for name, p in KNOWN_AGENT_PATHS:
        target = p / "auto-skills"
        # 用 lexists 判「路径本身在不在」：失效链接的 exists() 返回 False，
        # 会让整根被判成「未部署」而跳过——实测后果是快照丢失后
        # `--deploy` 无法自愈（既不重建快照也不修链接，只报"无需同步"）。
        if not os.path.lexists(str(target)):
            rows.append({"name": name, "path": str(target), "status": "missing"})
            continue
        # 链接形态：一份内容多个入口。失效链接单列 broken，因为它需要修
        # 但不能当作"没部署"（那会漏掉重建快照这一步）。
        if target.is_symlink() or _is_junction(target):
            if not target.exists() or not (target / "SKILL.md").exists():
                rows.append({"name": name, "path": str(target), "status": "broken"})
            else:
                rows.append({"name": name, "path": str(target), "status": "linked"})
            continue
        leaked = [rel for rel in SECRET_FILES if (target / rel).exists()]
        tgt_files = _file_map(target)
        missing = sorted(set(src_files) - set(tgt_files))
        extra = sorted(set(tgt_files) - set(src_files))
        changed = sorted(k for k in set(src_files) & set(tgt_files) if src_files[k] != tgt_files[k])
        # 凭据残留优先级最高：内容再同步，留了真实凭据也是故障
        status = "leaked" if leaked else ("ok" if not (missing or extra or changed) else "stale")
        rows.append({"name": name, "path": str(target), "status": status,
                     "src_sig": src_sig, "tgt_sig": _dir_signature(target),
                     "leaked": leaked, "missing": missing, "extra": extra, "changed": changed})
    if verbose:
        icon = {"ok": "🟢 同步", "stale": "🟡 陈旧", "leaked": "🔴 含凭据",
                "missing": "⚪ 未部署", "linked": "🔗 链接快照",
                "broken": "💔 链接失效"}
        print(f"\n{'目标':<26} 状态")
        print("-" * 62)
        for r in rows:
            detail = ""
            if r["status"] == "stale":
                parts = []
                if r.get("missing"):
                    parts.append(f"缺 {len(r['missing'])}")
                if r.get("extra"):
                    parts.append(f"多 {len(r['extra'])}")
                if r.get("changed"):
                    parts.append(f"异 {len(r['changed'])}")
                detail = "  " + " / ".join(parts)
                sample = (r.get("changed") or r.get("missing") or [])[:2]
                if sample:
                    detail += f"  如 {', '.join(sample)}"
            elif r["status"] == "linked":
                detail = "  与快照同一份内容，六根共用"
            elif r["status"] == "broken":
                detail = "  链接目标不存在（快照丢失或被删）"
            elif r.get("leaked"):
                detail = f"  泄漏={r['leaked']}"
            print(f"  {r['name']:<24} {icon[r['status']]}{detail}")
        bad = [r for r in rows if r["status"] in ("stale", "leaked", "broken")]
        if bad:
            print(f"\n[i] 有 {len(bad)} 个根需要修复：跑 `python scripts/wizard_setup.py --deploy`")
        else:
            n_link = sum(1 for r in rows if r["status"] == "linked")
            tail = f"（其中 {n_link} 个为链接形态，共用一份快照）" if n_link else ""
            print(f"\n[OK] 全部根内容一致、无凭据残留{tail}")
    return rows


def deploy_agents(agent_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """把仓库当前内容重新分发到各 harness 技能目录（**仅副本形态**）。

    链接形态的根由 build_dist() + link_agents() 负责，不要在这里处理：
    链接的目标就是快照目录，对它跑 robocopy 会把真源内容（含 agent_word/
    等被排除的运行时产物）镜像回快照。
    """
    result = connect_agents(agent_names=agent_names)
    # 部署之后再全量巡检一次凭据：robocopy 的 /XF 万一失效也不会留下真实凭据
    purged = purge_deployed_secrets()
    return {"connected": result, "purged": purged}


def build_dist() -> Path:
    """构建分发快照：真源的完整副本，但**不含本地凭据**。

    为什么需要这一层：直接把 harness 目录链接到真源有个副作用——
    真源里的 config/db.password 等凭据会从每个链接路径变得可达
    （实测确认：链接后 `~/.cursor/skills/auto-skills/config/db.password`
    能读到内容）。分发快照把「要分发的」与「只属于本机的」切开，
    链接指向快照，凭据仍只留在真源一处。

    重要语义（实测确认）：链接路径与快照是**同一份文件**（inode 相同），
    而不是与真源同一份。所以"改了真源立刻从各 harness 生效"是不成立的
    ——必须重建快照。`--deploy` 的职责因此是「重建快照 + 确保链接存在」，
    而不是往每个根拷一份。好处是重建只有一次写入（而不是六次），
    且不存在"某些根同步了、某些没同步"的中间态。
    """
    # 快照必须放在真源 .evolution **之外**：它内部会有一个指回
    # `<真源>/.evolution` 的链接，若快照本身就在 .evolution 下，就会形成
    # `dist/.evolution/dist/.evolution/...` 的无限自引用（实测症状：
    # copytree 报 WinError 1921，路径长到几百层）。
    dist = SKILL_ROOT / ".dist" / "snapshot"
    dist.parent.mkdir(parents=True, exist_ok=True)
    if dist.exists():
        # 先删内部的链接，避免 rmtree 跟着链接钻进真源
        _inner_evo = dist / ".evolution"
        if os.path.lexists(str(_inner_evo)):
            try:
                if _is_junction(_inner_evo):
                    subprocess.run(["cmd", "/c", "rmdir", str(_inner_evo)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    _inner_evo.unlink()
            except Exception:
                pass
        shutil.rmtree(dist, ignore_errors=True)
    shutil.copytree(
        SKILL_ROOT, dist,
        ignore=shutil.ignore_patterns(
            ".git", ".evolution", "__pycache__", "*.pyc",
            "db.password", "gateway.token", "gateway.url",
            # agent_word/ 是**本地运行时台账**（多 Agent 任务认领与工作日志，
            # 已被 .gitignore 排除、不属仓库内容）。把它分发出去会把本机的
            # 任务记录与文件清单暴露给所有 harness，且各 harness 会看到
            # 同一份"别人的台账"而误判任务归属。实测发现它被一起拷进了快照。
            "agent_word",
            # .dist/ 是快照自己的家（SKILL_ROOT/.dist/snapshot）。不排除会
            # 让 copytree 把"正在写入的目标"当作源来读，直接 RecursionError
            # （实测踩过）。凡是在 SKILL_ROOT 之下放产物，都必须在这里排除。
            ".dist",
        ),
    )
    # 关键：在快照里把 .evolution 指回真源。
    #
    # 所有脚本都用 `SKILL_ROOT / ".evolution"` 解析运行时状态（配置覆盖层、
    # 数据库凭据、暂存/熔断状态、私有技能区）。从链接根运行时 SKILL_ROOT
    # 就是快照目录，于是状态被解析到 `<快照>/.evolution` —— 实测后果有两条：
    #   ① 数据库凭据找不到（快照排除了凭据）→ 落库整条链路失效；
    #   ② 暂存/熔断状态分裂成两份（真源一份、快照一份），多 Agent 会看到
    #      互不一致的健康状态。
    # 用 Junction 把快照里的 .evolution 指回真源，既保留"凭据不从链接路径
    # 通过 config/ 读到"，又让运行时状态六根共用同一份。
    _dist_evo = dist / ".evolution"
    try:
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(_dist_evo),
                            str(SKILL_ROOT / ".evolution")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            os.symlink(SKILL_ROOT / ".evolution", _dist_evo, target_is_directory=True)
    except Exception as e:
        print(f"  [!] 警告：未能把快照的 .evolution 指回真源（{e}）；"
              f"从链接根运行代码时落库与私有技能区会失效")

    # 凭据文件在快照里改成**硬链接**（同一份数据，不是拷贝）。
    #
    # 为什么必须有：db_sync.py 用 `SKILL_ROOT / config/db.password` 解析密码，
    # 而从链接根运行时 SKILL_ROOT 就是快照。快照若完全没有凭据，落库整条
    # 链路失效（实测报 "password_file 指向的 ... 不存在"，熔断器随即打开）。
    #
    # 为什么用硬链接而不是拷贝：拷贝会在七个位置散布同一份密码，改了真源
    # 后副本仍是旧值——这正是之前实测踩到的故障（.claude / .cursor 两处
    # 带着旧凭据长期留在磁盘上）。硬链接只有一份数据，改真源即刻全生效，
    # 删除也只需删真源。
    #
    # 安全边界说明：能读 harness 目录的人，在副本方案下本来也能读到拷贝，
    # 所以这没有降低门槛；真正的边界是文件权限（0600）而不是「藏起来」。
    # 唯一变化是「不再有 6 份可能过期的拷贝」。
    for _rel in SECRET_FILES:
        _src = SKILL_ROOT / _rel
        if not _src.exists():
            continue
        _dst = dist / _rel
        _dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/H", str(_dst), str(_src)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            else:
                os.link(_src, _dst)
        except Exception as e:
            print(f"  [!] 警告：未能为 {_rel} 建立硬链接（{e}）；从链接根运行时会落库失败")
    return dist


def link_agents(agent_names: Optional[List[str]] = None, mode: str = "auto") -> Dict[str, Any]:
    """用目录链接把各 harness 的技能目录指向分发快照，从结构上消除漂移。

    为什么不继续用副本：副本要求「每次改仓库都记得重新分发」，实测漏过
    一次（六个根全部落后一个功能，每个 agent 都在跑旧代码）。

    链接方案的收益：内容是**一份**（快照）而不是六份，重建只写一次，
    因此不可能出现"某些根同步了、某些没同步"的中间态；凭据也只有一个
    地方需要守（快照本身排除了它们）。`--deploy` 之后所有根同时生效。

    代价（必须知道）：真源改动不会自动出现在 harness 里，仍要跑
    `--deploy` 重建快照。这与副本方案的纪律要求相同，但失败模式更轻——
    要么全好要么全旧，不会出现参差不齐。

    为什么链接快照而不链接真源：直链真源会让凭据从每个 harness 路径
    可达（实测确认）。快照排除了凭据，链接路径下读不到。

    模式（实测结论）：
    - Windows 上目录符号链接需管理员（开发者模式已开也会报
      "Administrator privilege required"）；**Junction 免管理员可用**，
      且本机已有先例（`.dsh/skills/ppt-skills`）。
    - `mode="copy"` 保留副本方案，作为不跟随链接的工具的降级路径。
    """
    results = {"linked": [], "copied": [], "skipped": [], "errors": []}
    is_win = os.name == "nt"
    dist = build_dist()
    for name, p in KNOWN_AGENT_PATHS:
        if not p.exists():
            results["skipped"].append(name)
            continue
        # 过滤要认三种写法：展示名 / 目录名(skills) / 宿主目录(.cursor)。
        # 只比 p.name 是无效的——六个根的 p.name 全是 'skills'，
        # 传什么都不可能只选中一个根（实测踩过）。
        if agent_names and not (
            name in agent_names
            or p.name in agent_names
            or p.parent.name in agent_names
        ):
            continue
        target = p / "auto-skills"
        if target.exists() and (target.is_symlink() or _is_junction(target)):
            results["linked"].append(name)  # 幂等
            continue
        if mode == "copy":
            results["skipped"].append(name)
            continue
        print(f"[*] 正在为 【{name}】 建立到分发快照的链接...")
        # 旧副本先挪走（不直接删，便于失败时恢复）
        stash = None
        if target.exists():
            stash = p / f".auto-skills.bak-{int(time.time())}"
            try:
                target.rename(stash)
            except Exception as e:
                results["errors"].append(f"{name}: 无法移开旧副本 {e}")
                continue
        try:
            if is_win:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(target), str(dist)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
                )
            else:
                os.symlink(dist, target, target_is_directory=True)
            if not (target / "SKILL.md").exists():
                raise RuntimeError("链接建立后读不到 SKILL.md")
            # 注意：这里**不能**判"链接路径下存在凭据即失败"。
            # 快照里的三个凭据是有意放的**硬链接**（同一份数据），因为
            # db_sync.py 用 SKILL_ROOT/config/db.password 解析密码，缺了
            # 落库整条链路失效。判据应是「是否与真源同一份」而不是「是否存在」
            # ——旧版按"存在即失败"会导致每次建链接都误判失败并回退到
            # robocopy，而 robocopy 的目标正是快照目录，于是把 agent_word/
            # 等运行时产物又倒回快照（实测踩过：快照 4028 文件、含 agent_word）。
            _split = []
            for _rel in SECRET_FILES:
                _f = target / _rel
                if not _f.exists():
                    continue
                _o = SKILL_ROOT / _rel
                try:
                    if not _o.exists() or _f.stat().st_ino != _o.stat().st_ino:
                        _split.append(_rel)
                except OSError:
                    _split.append(_rel)
            if _split:
                raise RuntimeError(f"链接路径下的凭据是独立拷贝而非同一份: {_split}")
            results["linked"].append(name)
            print(f"  [+] 已链接至分发快照: {p}")
            if stash:
                shutil.rmtree(stash, ignore_errors=True)
        except Exception as e:
            # 回退：恢复旧副本或改用复制
            if stash and not target.exists():
                try:
                    stash.rename(target)
                except Exception:
                    pass
            print(f"  [!] 链接失败（{e}），回退到复制模式")
            try:
                copied = connect_agents(agent_names=[name])
                if copied:
                    results["copied"].append(name)
                else:
                    results["errors"].append(f"{name}: 复制回退也失败")
            except Exception as e2:
                results["errors"].append(f"{name}: {e2}")
    return results


def unlink_agents(agent_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """把链接形态改回独立副本（给不跟随 Junction 的工具做降级）。

    删除 Junction 只删链接本身、不动目标内容（这是 Junction 的语义，
    已实测确认真源不受影响），所以这里先 rmdir 链接再拷副本。
    """
    results = {"copied": [], "skipped": [], "errors": []}
    for name, p in KNOWN_AGENT_PATHS:
        if not p.exists():
            results["skipped"].append(name)
            continue
        if agent_names and not (
            name in agent_names or p.name in agent_names or p.parent.name in agent_names
        ):
            continue
        target = p / "auto-skills"
        if not (target.is_symlink() or _is_junction(target)):
            results["skipped"].append(name)
            continue
        try:
            if _is_junction(target):
                subprocess.run(["cmd", "/c", "rmdir", str(target)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            else:
                target.unlink()
            if connect_agents(agent_names=[name]):
                results["copied"].append(name)
            else:
                results["errors"].append(f"{name}: 副本重建失败")
        except Exception as e:
            results["errors"].append(f"{name}: {e}")
    return results


def _is_junction(p: Path) -> bool:
    """判断路径是否为 Windows Junction。

    不能用 Path.is_symlink()：它对 Junction 返回 False（Junction 是
    reparse point 的一个子类型，不是 symlink）。这里直接读 Windows
    属性位 FILE_ATTRIBUTE_REPARSE_POINT(0x400)，并且要求 Path.is_symlink()
    为假，避免把普通符号链接也算进来。
    """
    try:
        if os.name != "nt":
            return False
        if Path(str(p)).is_symlink():
            return False
        st = os.lstat(str(p))
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)
    except Exception:
        return False


def connect_agents(agent_names: Optional[List[str]] = None) -> List[str]:
    """建立到扫描到的 Agent 目录的连接与同步"""
    connected = []
    auto_src = str(SKILL_ROOT)
    for name, p in KNOWN_AGENT_PATHS:
        if not p.exists():
            continue
        # 过滤要认三种写法：展示名 / 目录名(skills) / 宿主目录(.cursor)。
        # 只比 p.name 是无效的——六个根的 p.name 全是 'skills'，
        # 传什么都不可能只选中一个根（实测踩过）。
        if agent_names and not (
            name in agent_names
            or p.name in agent_names
            or p.parent.name in agent_names
        ):
            continue

        target_link = p / "auto-skills"
        # 兜底守卫：若这个路径已是链接（指向快照），绝不对它跑 robocopy
        # ——那会把真源内容（含 agent_word/ 等运行时产物）镜像进快照目录，
        # 而快照正是链接的目标，等于把刚排除的东西倒回去（实测踩过）。
        if os.path.lexists(str(target_link)) and (
            target_link.is_symlink() or _is_junction(target_link)
        ):
            print(f"  [i] 【{name}】已是链接形态，跳过副本同步")
            connected.append(name)
            continue
        print(f"[*] 正在为 【{name}】 建立 auto-skills 连接...")
        try:
            # 在 Windows 上优先使用 robocopy 同步以规避特权问题并保持原生稳定。
            # 关键：必须排除本地凭据，否则数据库密码与网关令牌会被复制进
            # 各个 AI 工具的技能目录（实测踩过：config/db.password 与
            # config/gateway.token 被同步到了 ~/.dsh/skills/auto-skills）。
            cmd = (
                f'robocopy "{auto_src}" "{target_link}" /MIR '
                f'/XD .git .evolution /XF db.password gateway.token gateway.url '
                f'/R:1 /W:1 /NP /NFL /NDL'
            )
            subprocess.run(["powershell", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            connected.append(name)
            print(f"  [+] 成功连接至: {p}")
        except Exception as e:
            print(f"  [-] 连接失败: {e}")

    # 更新配置
    config_manager.set_value("agent_connections.connected_agents", connected)
    return connected


def run_auto_setup(
    always_nm: bool = True,
    auto_update: bool = True,
    girlfriend_mode: bool = False,
    kb_sync_gf: bool = False,
    private_git: str = "",
    connect_all_agents: bool = True
) -> bool:
    """自动完成基础配置并标记 is_configured: true"""
    print("\n" + "=" * 72)
    print("🚀 正在执行 auto-skills 基础配置自动化引导 (v3.0 旗舰版)...")
    print("=" * 72)

    cfg = config_manager.load_config()

    # 1. 自动更新
    cfg["auto_update"]["auto_download_public_update"] = auto_update
    print(f"[*] 公开库自动更新: {'启用' if auto_update else '禁用'}")

    # 2. nm-skills 协同台账
    cfg["nm_skills"]["always_enable_project_ledger"] = always_nm
    cfg["nm_skills"]["auto_claim_before_edit"] = True
    cfg["nm_skills"]["auto_check_file_conflicts"] = True
    cfg["nm_skills"]["auto_clean_stale_locks"] = True
    print(f"[*] nm-skills 协同防撞与项目台账 (agent_word/): {'永远默认启用' if always_nm else '按需手动启用'}")

    # 3. 人格层
    cfg["persona"]["talk_like_girlfriend"]["default_enabled"] = girlfriend_mode
    cfg["persona"]["talk_like_girlfriend"]["kb_sync_traits"] = kb_sync_gf
    if girlfriend_mode and kb_sync_gf:
        print("[*] 正在从知识库拉取女友人格特性...")
        pull_persona_traits.pull_and_sync_traits()  # 路径由 pull_persona_traits 按已保存配置解析
    print(f"[*] 女友人格模式: {'默认启用' if girlfriend_mode else '默认关闭 (可通过 /gf 显式触发)'}")

    # 4. 私有 Git 仓库
    if private_git:
        cfg["evolution_vault"]["private_git_remote"] = private_git
        print(f"[*] 个人私有 Git 进化仓库: {private_git}")
        # 联动同步脚本
        try:
            from sync_evolution import set_private_remote_url
            set_private_remote_url(private_git)
        except Exception:
            pass

    # 5. Agent 扫描与连接
    scanned = scan_local_agents()
    detected_existing = [a for a in scanned if a["exists"]]
    print(f"[*] 本机扫描到 {len(detected_existing)} 个活跃 Agent 环境:")
    for a in detected_existing:
        print(f"    - {a['name']} ({a['path']})")

    if connect_all_agents:
        conn_list = connect_agents()
        cfg["agent_connections"]["connected_agents"] = conn_list
        print(f"[OK] 已成功为 {len(conn_list)} 个 Agent 建立 auto-skills 连接！")

    # 标记配置完成
    cfg["is_configured"] = True
    config_manager.save_config(cfg)
    print("=" * 72)
    print("🎉 auto-skills 首次基础配置已圆满完成！后续调用将畅通无阻。")
    print("=" * 72 + "\n")
    return True


def print_status():
    cfg = config_manager.load_config()
    is_conf = cfg.get("is_configured", False)
    scanned = scan_local_agents()

    print("\n" + "=" * 72)
    print("📋 auto-skills 配置与环境集成总览")
    print("=" * 72)
    print(f"- 首次引导配置状态 : {'✅ 已配置 (Configured)' if is_conf else '⚠️ 待首次配置 (Unconfigured)'}")
    print(f"- 配置文件绝对路径 : {CONFIG_FILE}")
    print(f"- 公开库自动更新   : {cfg.get('auto_update', {}).get('auto_download_public_update')}")
    print(f"- nm-skills 默认启用: {cfg.get('nm_skills', {}).get('always_enable_project_ledger')}")
    print(f"- 女友人格默认启用 : {cfg.get('persona', {}).get('talk_like_girlfriend', {}).get('default_enabled')}")
    print(f"- 私有 Git 远端    : {cfg.get('evolution_vault', {}).get('private_git_remote') or '<未绑定>'}")
    print("-" * 72)
    print("🤖 本机 Agent 环境连接状态：")
    for a in scanned:
        stat = "🟢 已连接" if a["connected"] else ("🟡 已就绪未连接" if a["exists"] else "⚪ 未安装")
        print(f"  - {a['name']:<24}: {stat} ({a['path']})")
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="auto-skills 首次启动引导与配置向导")
    parser.add_argument("--status", action="store_true", help="查看当前配置与 Agent 连接状态")
    parser.add_argument("--auto", action="store_true", help="自动以推荐安全标准完成首次配置")
    parser.add_argument("--connect-agents", action="store_true", help="立即扫描并建立到所有 Agent 环境的连接")
    parser.add_argument("--deploy", action="store_true",
                        help="重新分发到所有 Agent 技能目录（仓库更新后跑这个；链接形态下=重建快照）")
    parser.add_argument("--link", action="store_true",
                        help="改用目录链接指向分发快照（六个根共用一份内容；凭据不可从链接路径读到）")
    parser.add_argument("--unlink", action="store_true",
                        help="把链接形态改回独立副本（某些工具不跟随 Junction 时用）")
    parser.add_argument("--mode", choices=["auto", "link", "copy"], default="auto",
                        help="部署形态：auto=优先链接失败回退复制（默认）、link=只链接、copy=只复制")
    parser.add_argument("--check-deploy", action="store_true",
                        help="检查各 Agent 技能目录是否与仓库同步（含凭据残留巡检）")
    parser.add_argument("--always-nm", choices=["true", "false"], help="设置是否永远默认启用 nm-skills 台账")
    parser.add_argument("--gf-mode", choices=["true", "false"], help="设置是否默认开启女友人格")
    parser.add_argument("--set-private-remote", help="设置个人私有 Git 仓库 URL")

    args = parser.parse_args()

    if args.status:
        print_status()
        sys.exit(0)

    if args.connect_agents:
        connect_agents()
        # 连接之后必须全量巡检凭据：清理不能只覆盖本轮连接的根，
        # 否则更早版本留下的副本会一直带着真实凭据留在磁盘上。
        purge_deployed_secrets()
        sys.exit(0)

    if args.check_deploy:
        rows = check_deployment()
        bad = [r for r in rows if r["status"] in ("stale", "leaked")]
        sys.exit(1 if bad else 0)

    if args.link:
        res = link_agents(mode=args.mode)
        print(f"\n[OK] 链接 {len(res['linked'])} 个；复制回退 {len(res['copied'])} 个；"
              f"跳过 {len(res['skipped'])} 个")
        if res["errors"]:
            print("[!] 错误:")
            for e in res["errors"]:
                print(f"    {e}")
        rows = check_deployment()
        bad = [r for r in rows if r["status"] in ("stale", "leaked")]
        sys.exit(1 if bad or res["errors"] else 0)

    if args.unlink:
        res = unlink_agents()
        print(f"\n[OK] 已改回独立副本: {len(res['copied'])} 个；跳过 {len(res['skipped'])} 个")
        if res["errors"]:
            print("[!] 错误:")
            for e in res["errors"]:
                print(f"    {e}")
        sys.exit(1 if res["errors"] else 0)

    if args.deploy:
        # 双形态：链接形态的根走"重建快照"，副本形态的根走"重新拷贝"。
        # 注意：**两种不能同时跑**——链接指向的就是快照目录，若再对它执行
        # robocopy /MIR，会把真源内容（含 .gitignore 掉的 agent_word/ 等
        # 运行时产物）镜像进快照，等于把刚排除的东西又倒回去（实测踩过：
        # 快照里出现了 agent_word/，正是这一步造成的）。
        rows0 = check_deployment(verbose=False)
        linked_roots = [r for r in rows0 if r["status"] == "linked"]
        broken_roots = [r for r in rows0 if r["status"] == "broken"]
        copy_roots = [r for r in rows0 if r["status"] in ("stale", "ok", "leaked")]
        # 有链接根或失效链接根都要重建快照：失效链接的唯一成因就是快照丢了，
        # 重建后还需把链接重新指过去（link_agents 会在 --link 路径做）。
        if (linked_roots or broken_roots) and args.mode != "copy":
            dist = build_dist()
            n = len(linked_roots) + len(broken_roots)
            print(f"[*] 已重建分发快照（{n} 个根通过链接共用这一份）")
            print(f"    {dist}")
        if broken_roots:
            # 失效链接：先删掉再按链接形态重建（rmdir 只删链接不动目标）
            print(f"[*] 检测到 {len(broken_roots)} 个失效链接，正在修复...")
            for _r in broken_roots:
                _t = Path(_r["path"])
                try:
                    if _is_junction(_t):
                        subprocess.run(["cmd", "/c", "rmdir", str(_t)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        _t.unlink()
                except Exception as e:
                    print(f"  [!] 无法移除失效链接 {_t}: {e}")
            res = link_agents(mode="link")
            print(f"  [+] 已重建 {len(res['linked'])} 个链接；回退 {len(res['copied'])} 个")
            for e in res["errors"]:
                print(f"  [!] {e}")
        if copy_roots and args.mode != "link":
            out = deploy_agents()
            print(f"\n[OK] 已重新分发到 {len(out['connected'])} 个副本根；清除凭据 {len(out['purged'])} 个")
        elif not copy_roots and not broken_roots:
            print("[i] 全部根都是链接形态，无需副本同步")
        rows = check_deployment()
        bad = [r for r in rows if r["status"] in ("stale", "leaked", "broken")]
        sys.exit(1 if bad else 0)

    # 快捷配置单个字段
    if args.always_nm:
        config_manager.set_value("nm_skills.always_enable_project_ledger", args.always_nm == "true")
        print(f"[OK] nm_skills.always_enable_project_ledger 已更新为: {args.always_nm}")

    if args.gf_mode:
        config_manager.set_value("persona.talk_like_girlfriend.default_enabled", args.gf_mode == "true")
        print(f"[OK] persona.talk_like_girlfriend.default_enabled 已更新为: {args.gf_mode}")

    if args.set_private_remote:
        config_manager.set_value("evolution_vault.private_git_remote", args.set_private_remote)
        print(f"[OK] evolution_vault.private_git_remote 已更新为: {args.set_private_remote}")

    # 默认或 --auto 执行
    if args.auto or not config_manager.is_configured():
        run_auto_setup(
            always_nm=True,
            auto_update=True,
            girlfriend_mode=False,
            kb_sync_gf=True,
            private_git="",
            connect_all_agents=True
        )


if __name__ == "__main__":
    main()
