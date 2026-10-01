#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""untrusted_text.py —— 不可信文本消毒（吸收 IronClaw 的 Prompt Injection Defense）。

为什么需要（2026-10-01 借鉴 nearai/ironclaw，12.6K star）
=========================================================
IronClaw 的安全四层里有「Prompt Injection Defense：模式检测 + 内容消毒 +
策略执行」。对照 auto-skills，**nm-skills 的多 Agent 场景正是注入高危面**：

  · `nm_register.py` 有 5 处 `json.loads(read_text())` 直接把台账内容当可信数据
  · Agent A 写的 `agent_word/工作日志.md` 会被 Agent B 读进上下文
  · 一个被污染的台账条目就是一条针对读它者的注入指令

全库此前只有 `auto_router.py:224` 的**关键词分类**（给任务分级用），
没有任何针对不可信输入的消毒——注入面完全暴露。

设计原则（克制的三层，不是 IronClaw 的完整方案）
------------------------------------------------
IronClaw 是 Rust + WASM 沙箱 + 能力权限的完整 Agent OS，auto-skills 不能也
不该照搬。这里只取**与现有架构兼容、低风险、可验证**的部分：

  1. **detect()** —— 模式检测：识别常见注入/外带形状，返回命中标签（不阻断）
  2. **sanitize()** —— 内容消毒：剥离可执行形状（控制字符、零宽、伪标记），
     保留可读正文；**不改写语义**，避免把正常内容改坏
  3. **wrap()** —— 边界标注：把文本包进「以下是不可信数据」的围栏，
     让读它的 Agent 在上下文里就看到边界

**刻意不做**：策略执行（阻断/拒绝读）——那会改变 nm-skills 的协同语义，
属于需要用户授权的架构变更；且 auto-skills 的 Agent 本就受 SKILL.md 纪律约束。

判据（可验证）
==============
  · detect 必须命中真实注入样本、且不误报正常中文技术文本
  · sanitize 必须剥掉控制字符/零宽字符，但保留中文与代码可读性
  · sanitize 必须是幂等的（sanitize(sanitize(x)) == sanitize(x)）
  · wrap 必须含边界标记与原始内容
"""
import re
from typing import List, Tuple

# ---- 注入/外带模式 ----
# 每条 = (编译后的正则, 标签)。判据是「形状」而非关键词，避免误伤正常技术文本。
_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # 直接指令覆盖
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", re.I),
     "指令覆盖"),
    (re.compile(r"忽略.{0,6}(之前|以上|上述).{0,4}(指令|提示|要求)", re.I),
     "指令覆盖"),
    # 角色/系统伪装
    (re.compile(r"\b(system|assistant|user)\s*:\s*", re.I), "角色伪装"),
    # 角色/系统伪装。注意 <|im_start|user> 这类：token 后还带角色名，
    # 不能只匹配到 token 本身就收尾（实测踩过：原模式漏了它）。
    (re.compile(r"<\|?(system|im_start|im_end|endoftext)\|?[a-z]*\|?>", re.I),
     "角色伪装"),
    (re.compile(r"\[?(SYSTEM|INST)\]", re.I), "角色伪装"),
    # 工具/命令诱导
    (re.compile(r"\b(execute|run|eval)\s+(this|the following|below)", re.I), "命令诱导"),
    (re.compile(r"^(curl|wget|nc|bash|sh|python)\s+-[a-z]", re.I | re.M), "命令诱导"),
    # 数据外带
    (re.compile(r"(send|post|upload|exfiltrate).{0,20}(to|http|webhook|url)", re.I),
     "数据外带"),
    (re.compile(r"\b(cat|type|read)\s+.{0,30}(\.env|password|token|secret|credential)", re.I),
     "凭据读取诱导"),
    # 文件/覆盖诱导
    (re.compile(r"(delete|rm\s+-rf|overwrite|truncate).{0,20}(file|ledger|台账|db|database)", re.I),
     "破坏诱导"),
    # 编码混淆（base64 大段、十六进制串）
    (re.compile(r"[A-Za-z0-9+/]{80,}={0,2}"), "编码混淆"),
    (re.compile(r"(\\x[0-9a-f]{2}){8,}", re.I), "编码混淆"),
]

# 零宽/双向控制字符（用于混淆与绕过检测）
_ZERO_WIDTH = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u00ad\ufeff]")

# 除 \t \n \r 外的 C0/C1 控制字符
_CTRL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def detect(text: str) -> List[str]:
    """返回命中的注入形状标签（去重、保序）。无命中返回空列表。

    只检测不改写：让调用方决定怎么处置（记日志 / 标注 / 上报）。
    """
    if not text:
        return []
    out: List[str] = []
    for rx, label in _PATTERNS:
        if rx.search(text) and label not in out:
            out.append(label)
    return out


def sanitize(text: str) -> str:
    """剥掉可执行形状，保留可读正文。

    ⚠️ 刻意保守：只删「不可能属于正常正文」的字符（零宽、控制字符），
    **不改写任何可见文字**——把正常内容改坏比留着注入形状更危险
    （调用方会以为已经安全了，其实语义被破坏）。
    """
    if not text:
        return text
    out = _ZERO_WIDTH.sub("", text)
    out = _CTRL.sub("", out)
    # 规范化行尾，防 CRLF 混淆
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    return out


def wrap(text: str, source: str = "") -> str:
    """把文本包进「不可信数据」围栏。

    让读它的 Agent 在上下文里就看到边界——这是三层里唯一直接作用到
    LLM 的一层，也是 IronClaw「策略执行」在 auto-skills 里的轻量对应物
    （不阻断读取，只让边界可见）。
    """
    body = sanitize(text)
    labels = detect(body)
    tag = (" ⚠ 检测到: " + "/".join(labels)) if labels else ""
    src = (" 来源: %s" % source) if source else ""
    return ("<<<UNTRUSTED{tag}{src}>>>\n"
            "{body}\n"
            "<<<END UNTRUSTED>>>").format(tag=tag, src=src, body=body)


def is_idempotent_sanitize(text: str) -> bool:
    """自检用：sanitize 必须幂等。"""
    once = sanitize(text)
    return sanitize(once) == once
