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
            except Exception:
                pass
        else:
            save_config(get_default_config())

    base = get_default_config()
    if yaml and CONFIG_FILE.exists():
        try:
            content = CONFIG_FILE.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                base = deep_merge(base, data)
        except Exception as e:
            print(f"[WARN] 解析 config.yaml 失败: {e}，将采用默认空配置。")

    # 检查是否有 .evolution/ 私有层覆盖
    if yaml and EVOLUTION_OVERRIDE.exists():
        try:
            priv_content = EVOLUTION_OVERRIDE.read_text(encoding="utf-8")
            priv_data = yaml.safe_load(priv_content)
            if isinstance(priv_data, dict):
                base = deep_merge(base, priv_data)
        except Exception:
            pass

    return base


def save_config(cfg: Dict[str, Any]) -> bool:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if yaml:
        try:
            text = yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False)
            CONFIG_FILE.write_text(text, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[ERROR] 保存 config.yaml 失败: {e}")
            return False
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
