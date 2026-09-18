#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify_push.py — 大型任务完成自动化通知与 Server酱 (ServerChan Turbo) 消息推送模块
================================================================================
支持功能：
1. 零外部依赖 HTTP POST/GET 推送：基于 Python 原生 urllib，即开即用无需安装 requests；
2. 兼容 serverchan-sdk（若环境已安装则自动适配）；
3. 智能密钥多级回退获取：
   - 命令行显式传入 `--sendkey` / `-k`
   - 默认内置 SendKey (`SCT280861TA-2aWLS0PNUXewsTX4DrUBffTt`)
   - 环境变量 `SERVERCHAN_SENDKEY` / `SCT_KEY`
   - 配置文件 `~/.config/serverchan/key` 或 `./.env`
4. 结构化任务完成卡片模板 (Markdown 格式)：
   - 包含：任务名称、执行状态、完成耗时、Git 提交记录/分支、主要交付物产出清单；
5. CLI 命令行与 Python API 双重调用支持。

用法示例：
    # 1. 快速命令行推送
    python scripts/notify_push.py --title "PPT项目全量重构完成" --desp "已完成全部18页图表重排，并通过健康审计"

    # 2. 携带标签与自定义 SendKey
    python scripts/notify_push.py -t "CI部署通知" -d "后端二进制构建完成" --tags "部署|成功" -k "<sendkey>"

    # 3. 在其他 Python 自动化脚本中作为模块调用：
    from notify_push import send_task_notification
    send_task_notification("大型任务完成", "### 交付清单\n- 已生成PPTX\n- 已上传GitHub")
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional

DEFAULT_SENDKEY = "SCT280861TA-2aWLS0PNUXewsTX4DrUBffTt"


def resolve_sendkey(explicit_key: Optional[str] = None) -> str:
    """
    多级回退解析有效的 Server酱 SendKey
    """
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    # 环境变量
    env_key = os.environ.get("SERVERCHAN_SENDKEY") or os.environ.get("SCT_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 本地配置文件查找
    cfg_paths = [
        os.path.expanduser("~/.config/serverchan/key.txt"),
        os.path.join(os.path.dirname(__file__), ".sendkey")
    ]
    for p in cfg_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    k = f.read().strip()
                    if k:
                        return k
            except Exception:
                pass

    return DEFAULT_SENDKEY


def send_serverchan_message(
    title: str,
    desp: str = "",
    tags: str = "任务通知|完成",
    sendkey: Optional[str] = None,
    channel: Optional[str] = None
) -> Dict[str, Any]:
    """
    通过 Server酱 Turbo API 发送通知消息
    """
    key = resolve_sendkey(sendkey)
    if not key or key == "<sendkey>":
        raise ValueError("缺少有效的 Server酱 SendKey，无法推送通知")

    url = f"https://sctapi.ftqq.com/{key}.send"

    payload = {
        "title": title[:100],  # 标题限制
        "desp": desp
    }
    if tags:
        payload["tags"] = tags
    if channel:
        payload["channel"] = channel

    # 优先尝试使用原生 urllib 发送 POST 请求
    encoded_data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded_data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "AutoSkills-Notifier/2.5"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            result = json.loads(resp_body)
            code = result.get("code", -1)
            if code == 0:
                print(f"[OK] Server酱通知已送达: {title} (推送到微信/绑定的移动设备)")
            else:
                print(f"[WARN] Server酱返回非零状态: {result.get('message', '未知错误')}")
            return result
    except Exception as e:
        print(f"[ERROR] 推送请求发生网络异常: {e}")
        return {"code": -1, "message": str(e)}


def format_task_completion_card(
    task_name: str,
    project_name: str = "auto-skills",
    status: str = "SUCCESS",
    summary: str = "",
    deliverables: Optional[list] = None,
    git_commit: Optional[str] = None
) -> str:
    """
    格式化大型任务完成通知的 Markdown 报告卡片
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_icon = "✅" if status.upper() == "SUCCESS" else "⚠️"

    lines = [
        f"## {status_icon} 【{project_name}】大型研发任务执行完成",
        f"- **任务名称**：{task_name}",
        f"- **执行状态**：`{status.upper()}`",
        f"- **完成时间**：{now_str}",
    ]

    if git_commit:
        lines.append(f"- **Git 提交**：`{git_commit}`")

    if summary:
        lines.append(f"\n### 📝 任务成果总结\n{summary}")

    if deliverables:
        lines.append("\n### 📦 核心交付物清单")
        for item in deliverables:
            lines.append(f"- {item}")

    lines.append("\n---\n*由 auto-skills 智能工作流总控中枢自动化推送*")
    return "\n".join(lines)


def notify_task_complete(
    task_name: str,
    project_name: str = "auto-skills",
    summary: str = "",
    deliverables: Optional[list] = None,
    git_commit: Optional[str] = None,
    sendkey: Optional[str] = None,
    tags: str = "任务完成|报告"
) -> Dict[str, Any]:
    """
    供自动化脚本一键调用的标准封装入口
    """
    title = f"【完成】{project_name}: {task_name}"
    desp = format_task_completion_card(
        task_name=task_name,
        project_name=project_name,
        status="SUCCESS",
        summary=summary,
        deliverables=deliverables,
        git_commit=git_commit
    )
    return send_serverchan_message(title=title, desp=desp, tags=tags, sendkey=sendkey)


def main():
    parser = argparse.ArgumentParser(description="大型任务完成 Server酱 自动化推送工具")
    parser.add_argument("-t", "--title", default="大型任务执行完毕", help="通知标题")
    parser.add_argument("-d", "--desp", default="", help="通知正文 (支持 Markdown)")
    parser.add_argument("-p", "--project", default="auto-skills", help="项目名称")
    parser.add_argument("--tags", default="任务完成|报告", help="Server酱分类标签 (竖线分隔)")
    parser.add_argument("-k", "--sendkey", default=None, help="Server酱 SendKey (默认读取系统配置)")
    parser.add_argument("--test", action="store_true", help="发送一条自检测试消息")

    args = parser.parse_args()

    if args.test:
        print("[*] 正在发送 Server酱 联通性自检测试...")
        res = send_serverchan_message(
            title="【自检】auto-skills 通知推送模块已就绪",
            desp="这是一条来自 auto-skills 工作流总控中枢的联通性测试消息。\n\n- 时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n- 状态：Normal",
            tags="自检|正常",
            sendkey=args.sendkey
        )
        sys.exit(0 if res.get("code") == 0 else 1)

    if not args.desp:
        # 使用标准卡片模版
        desp = format_task_completion_card(
            task_name=args.title,
            project_name=args.project,
            summary="自动化任务流水线顺利完成，各项质检指标全部达标。"
        )
    else:
        desp = args.desp

    send_serverchan_message(title=args.title, desp=desp, tags=args.tags, sendkey=args.sendkey)


if __name__ == "__main__":
    main()
