#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_manager.py — auto-skills 统一配置读写与状态管理模块 (v3.0)
==================================================================
管理 `config/config.yaml` 的加载、保存、迁移与首次配置检测。
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
EXAMPLE_CONFIG = CONFIG_DIR / "config.example.yaml"
EVOLUTION_OVERRIDE = SKILL_ROOT / ".evolution" / "config.yaml"


def deep_merge(base: dict, override: dict) -> dict:
    res = dict(base)
    for k, v in override.items():
        if k in res and isinstance(res[k], dict) and isinstance(v, dict):
            res[k] = deep_merge(res[k], v)
        else:
            res[k] = v
    return res


def get_default_config() -> Dict[str, Any]:
    return {
        "version": "3.0.0",
        "is_configured": False,
        "auto_update": {
            "auto_download_public_update": None,
            "check_interval_hours": 24,
            "remote_git_url": "https://github.com/t-yang-only/auto-skills.git"
        },
        "notifications": {
            "enabled": None,
            "serverchan_sendkey": "",
            "wecom_webhook": "",
            "feishu_webhook": "",
            "dingtalk_webhook": "",
            "dingtalk_secret": "",
            "pushplus_token": "",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "bark_url": ""
        },
        "nm_skills": {
            "always_enable_project_ledger": None,
            "default_client_id": "CODE",
            "default_lease_minutes": 45,
            "auto_claim_before_edit": True,
            "auto_check_file_conflicts": True,
            "auto_clean_stale_locks": True,
            "ledger_dir_name": "agent_word"
        },
        "persona": {
            "talk_like_girlfriend": {
                "default_enabled": None,
                "kb_sync_traits": None,
                "kb_source_url_or_path": "",
                "kb_api_token": "",
                "traits_cache_file": ".evolution/profile/persona_girlfriend.json"
            }
        },
        "evolution_vault": {
            "private_git_remote": "",
            "auto_sync_on_install": True,
            "custom_skills_dir": ".evolution/custom_skills"
        },
        "agent_connections": {
            "auto_scan_on_startup": True,
            "connected_agents": []
        }
    }


def load_config() -> Dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        if EXAMPLE_CONFIG.exists():
            try:
                CONFIG_FILE.write_text(EXAMPLE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception as e:
                # 首次初始化失败必须报出来：不然后续所有读取都走默认值，
                # 使用者会以为「配置好了」而实际什么都没落盘。
                print(f"[WARN] 初始化 {CONFIG_FILE} 失败: {e}（将使用内置默认配置）")
        else:
            save_config(get_default_config(), target="base")  # 首次初始化才写基础层

    base = get_default_config()
    if not yaml:
        # 缺 pyyaml 时必须显式报出来，不能静默降级。
        # 实测后果：load_config 会跳过基础层与覆盖层的读取，返回**默认空配置**
        # —— database.enabled / type / host 全变成 None，而 is_db_enabled()
        # 会因此把落库判定为「已禁用」。使用者看到的是「功能没生效」，
        # 而不是「少了依赖」，排查方向会被完全带偏。
        print("[WARN] 缺少 pyyaml 依赖：配置文件无法解析，"
              "数据库与私有覆盖层的设置都不会生效。")
        print("       请安装：pip install pyyaml pymysql")
        return base
    if CONFIG_FILE.exists():
        try:
            content = CONFIG_FILE.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                base = deep_merge(base, data)
        except Exception as e:
            print(f"[WARN] 解析 config.yaml 失败: {e}，将采用默认空配置。")

    # 检查是否有 .evolution/ 私有层覆盖
    if EVOLUTION_OVERRIDE.exists():
        try:
            priv_content = EVOLUTION_OVERRIDE.read_text(encoding="utf-8")
            priv_data = yaml.safe_load(priv_content)
            if isinstance(priv_data, dict):
                base = deep_merge(base, priv_data)
        except Exception as e:
            # 覆盖层解析失败**必须报出来**：它承载着真实数据库地址、凭据路径与
            # 各项开关，静默跳过会让程序用基础层的占位符继续跑，表现为
            # 「配置改了但没生效」——和缺 pyyaml 那类静默降级同一性质。
            print(f"[WARN] 解析私有覆盖层 {EVOLUTION_OVERRIDE} 失败: {e}")
            print("       将只用基础层配置；改动不会生效。")

    return base


def save_config(cfg: Dict[str, Any], target: str = "override") -> bool:
    """保存配置。

    target 决定写到哪一层，默认 "override"（覆盖层）：

      "override" -> .evolution/config.yaml   （已 gitignore，本地私有状态）
      "base"     -> config/config.yaml       （被 git 跟踪，必须永远是可公开的占位符）

    为什么默认写覆盖层：load_config() 返回的是 base 与 override 的 deep_merge 结果，
    里面含用户真实值（数据库 IP、私有仓库地址、本地路径、密码文件路径等）。
    早期实现把合并结果整体写回基础层，于是「调用一次 mark_configured()」就会
    把真实 IP 落进被 git 跟踪的 config/config.yaml —— 2026-09-22 实测发生过一次，
    提交前被隐私闸门拦下。基础层只在首次初始化时写（见 load_config 的 else 分支）。

    这条约束是硬性的：新增任何写配置的路径都必须走本函数，不要直接 write CONFIG_FILE。
    """
    if not yaml:
        return False
    try:
        text = yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False)
        if target == "base":
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(text, encoding="utf-8")
        else:
            EVOLUTION_OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
            EVOLUTION_OVERRIDE.write_text(text, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERROR] 保存配置失败 (target={target}): {e}")
        return False


def is_configured() -> bool:
    cfg = load_config()
    return bool(cfg.get("is_configured", False))


def get_value(key_path: str, default: Any = None) -> Any:
    """例如 get_value('nm_skills.always_enable_project_ledger')"""
    cfg = load_config()
    parts = key_path.split(".")
    curr = cfg
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return default
    return curr if curr is not None else default


def set_value(key_path: str, value: Any) -> bool:
    """例如 set_value('nm_skills.always_enable_project_ledger', True)"""
    cfg = load_config()
    parts = key_path.split(".")
    curr = cfg
    for p in parts[:-1]:
        if p not in curr or not isinstance(curr[p], dict):
            curr[p] = {}
        curr = curr[p]
    curr[parts[-1]] = value
    return save_config(cfg)


def mark_configured(status: bool = True) -> bool:
    return set_value("is_configured", status)
