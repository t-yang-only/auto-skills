#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aoci_cognition.py — AOCI-CODE 全局认知地图调度器、索引治理与生命周期中枢
=============================================================================
功能：
1. 项目认知状态探查 (probe / status)：
   - 自动度量项目规模，判定是否达到建立 AOCI 认知索引的门槛 (eligible / below_threshold / unknown)；
   - 检查目标项目是否已存在 Volume-first 认知资产 (aoci.txt, aoci.meta.txt, aoci.code.txt)；
2. AOCI 骨架初始化 (init)：
   - 为达标项目一键生成规范的 Volume-first 认知索引骨架与 Meta 标签字典约束；
3. FRAS 认知草稿生成 (generate-draft)：
   - 提取受管源码列表，生成标准 FRAS (Function | Relations | API | Non-obvious constraints) 初始候选模板；
4. 认知索引校验 (verify)：
   - 验证 Root/Meta/Code 卷完整性、语法规范性与对象对齐状态；
5. auto_router 联动感知：
   - 为路由规划阶段提供非阻塞的认知感知与待办建议。
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

SELF_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SELF_DIR.parent

# 导入本地库存与度量引擎
try:
    import aoci_inventory as inv
except ImportError:
    sys.path.insert(0, str(SELF_DIR))
    import aoci_inventory as inv


def _get_cognition_config() -> Dict[str, Any]:
    """读取 cognition 配置段，失败平滑降级。"""
    try:
        import config_manager
        return config_manager.get_value("cognition", {}) or {}
    except Exception:
        return {}


def is_aoci_initialized(project_root: Path) -> bool:
    """检查项目是否已存在有效的 AOCI 认知根与代码卷。"""
    root_txt = project_root / "aoci.txt"
    code_txt = project_root / "aoci.code.txt"
    return root_txt.is_file() and code_txt.is_file()


def read_project_cognition_status(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """只读查询项目的 AOCI 认知状态。"""
    root = inv.resolve_project_root(str(project_root) if project_root else None)
    initialized = is_aoci_initialized(root)

    cfg = _get_cognition_config()
    thresholds = cfg.get("thresholds", {})
    extra_ext = (cfg.get("scope") or {}).get("extra_source_extensions", [])

    files, auth = inv.scan_source_files(root, extra_extensions=extra_ext)
    metrics = inv.calculate_metrics(files, root)
    scale_status, reasons = inv.evaluate_thresholds(metrics, thresholds)

    code_entries_count = 0
    if initialized:
        try:
            code_lines = (root / "aoci.code.txt").read_text(encoding="utf-8", errors="replace").splitlines()
            code_entries_count = sum(1 for l in code_lines if l.strip() and not l.startswith("#") and not l.startswith("==="))
        except Exception:
            pass

    return {
        "project_root": str(root),
        "initialized": initialized,
        "scale_status": scale_status,
        "reasons": reasons,
        "metrics": metrics,
        "scan_authority": auth,
        "code_entries_count": code_entries_count,
        "volumes": {
            "root": (root / "aoci.txt").is_file(),
            "meta": (root / "aoci.meta.txt").is_file(),
            "code": (root / "aoci.code.txt").is_file(),
            "database": (root / "aoci.database.txt").is_file(),
        }
    }


def init_aoci_volumes(project_root: Path, project_name: Optional[str] = None, locale: str = "zh-CN") -> Dict[str, Any]:
    """
    为目标项目创建 Volume-first AOCI 规范骨架。
    幂等安全：已有正式资产时不强制覆盖。
    """
    root = inv.resolve_project_root(str(project_root))
    proj_name = project_name or root.name

    root_file = root / "aoci.txt"
    meta_file = root / "aoci.meta.txt"
    code_file = root / "aoci.code.txt"

    created = []

    # 1. 创建 aoci.txt (Root)
    if not root_file.exists():
        root_content = (
            "#AOCI-ROOT-MANIFEST: 1\n"
            "#Format-Version: cognition-volumes/v1\n"
            f"#Locale: {locale}\n"
            f"#Project: {proj_name}\n"
            "#Global-Invariants: -\n"
            "#Volume: id=meta kind=meta path=aoci.meta.txt format=meta-v1 depends=- state=enabled\n"
            "#Volume: id=code kind=code path=aoci.code.txt format=object-fras-v2 depends=meta state=enabled\n"
        )
        root_file.write_text(root_content, encoding="utf-8")
        created.append("aoci.txt")

    # 2. 创建 aoci.meta.txt (Meta)
    if not meta_file.exists():
        meta_content = (
            "#AOCI-META-VOLUME: 1\n"
            "#Object-Protocol: repository-cognition-object/v2\n"
            "#FRAS-Discipline: 2\n"
            "#FRAS-v2-Limits-Authority: machine-contract\n"
            "#S-Admission: non-inferable-and-error-preventing\n"
            "#S配额: C9-8<=600 C7-4<=200 C3-1<=50\n"
            "#Object-Kinds: code=file database=table\n"
            "#Canonical-Tag-Authoring: compact A+B+C+[D]+E\n"
            "#[Tag dictionary: code]\n"
            "#A Layer: C-共享基础 E-入口边界 A-应用编排 D-领域逻辑 K-算法计算 M-中间件 P-持久化 I-集成适配 R-运行基础 L-库与SDK F-声明配置 O-运维交付 T-测试验证 S-文档规范 X-开发工具 Z-其他\n"
            "#B Module: G-跨域通用 U-用户交互 B-核心业务 D-数据状态 I-身份权限 N-网络协议 M-消息事件 S-安全隐私 C-配置策略 O-可观测性 R-可靠性恢复 P-性能资源 W-流程调度 A-分析智能 H-硬件设备 L-本地化 V-构建发布 Q-质量保障 E-扩展插件 Z-其他\n"
            "#C Importance: 9-最高 8-很高 7-高 6-较高 5-中等 4-较低 3-低 2-很低 1-最低\n"
            "#E Scale: L-大>400 M-中200-400 S-小100-200 T-微<100\n"
        )
        meta_file.write_text(meta_content, encoding="utf-8")
        created.append("aoci.meta.txt")

    # 3. 创建 aoci.code.txt (Code)
    if not code_file.exists():
        code_content = "#AOCI-CODE-VOLUME: 1\n\n"
        code_file.write_text(code_content, encoding="utf-8")
        created.append("aoci.code.txt")

    return {
        "project_root": str(root),
        "created": created,
        "status": "ready"
    }


def generate_draft_fras(project_root: Path) -> Dict[str, Any]:
    """生成受管源码对象的初始 FRAS 候选草稿行，辅助 Agent 快速展开认知。"""
    root = inv.resolve_project_root(str(project_root))
    cfg = _get_cognition_config()
    extra_ext = (cfg.get("scope") or {}).get("extra_source_extensions", [])
    files, _ = inv.scan_source_files(root, extra_extensions=extra_ext)

    dir_groups: Dict[str, List[Path]] = {}
    for f in files:
        rel_dir = os.path.relpath(f.parent, str(root)).replace("\\", "/")
        dir_groups.setdefault(rel_dir, []).append(f)

    draft_lines: List[str] = []
    draft_lines.append("#AOCI-CODE-VOLUME: 1\n")

    for dir_path in sorted(dir_groups.keys()):
        heading = f"==={dir_path}===" if dir_path != "." else "===.==="
        draft_lines.append(f"\n{heading}")
        for fp in sorted(dir_groups[dir_path], key=lambda x: x.name):
            # 基础标签推断：默认 C(共享基础) G(跨域通用) 5(中等) S(小规模)
            fn = fp.name
            draft_lines.append(f"{fn}[CG5S]: F:实现 {fn} 核心逻辑 | R:- | A:- | S:-")

    draft_content = "\n".join(draft_lines) + "\n"
    return {
        "project_root": str(root),
        "total_files": len(files),
        "draft_content": draft_content
    }


def verify_cognition_assets(project_root: Path) -> Tuple[bool, List[str]]:
    """验证目标项目的 AOCI 认知资产一致性。"""
    root = inv.resolve_project_root(str(project_root))
    issues = []

    root_txt = root / "aoci.txt"
    meta_txt = root / "aoci.meta.txt"
    code_txt = root / "aoci.code.txt"

    if not root_txt.is_file():
        issues.append("缺少 Root 资产文件: aoci.txt")
    else:
        content = root_txt.read_text(encoding="utf-8", errors="replace")
        if "#AOCI-ROOT-MANIFEST: 1" not in content:
            issues.append("aoci.txt 缺少有效 manifest 标识 (#AOCI-ROOT-MANIFEST: 1)")

    if not meta_txt.is_file():
        issues.append("缺少 Meta 资产文件: aoci.meta.txt")
    if not code_txt.is_file():
        issues.append("缺少 Code 资产文件: aoci.code.txt")
    else:
        lines = code_txt.read_text(encoding="utf-8", errors="replace").splitlines()
        entries = [l for l in lines if l.strip() and not l.startswith("#") and not l.startswith("===")]
        for i, ent in enumerate(entries[:50]):  # 采样验证前 50 行格式
            if not re.search(r"^[^\[]+\[[A-Za-z0-9]+\]:\s*F:", ent):
                issues.append(f"条目格式不符合 FRAS 标准: {ent[:60]}")
                break

    return (len(issues) == 0), issues


def check_project_cognition_need(project_root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    供 auto_router 等核心调度器调用的轻量级感知接口。
    若达到规模阈值且缺少 AOCI 认知，返回引导建档信息；否则返回 None。
    """
    cfg = _get_cognition_config()
    mode = cfg.get("mode", "advisory")
    if mode == "off":
        return None

    try:
        status = read_project_cognition_status(project_root)
        # 如果已经初始化并对齐，则无需触发报警
        if status.get("initialized"):
            return {
                "has_cognition": True,
                "project_root": status["project_root"],
                "code_entries_count": status["code_entries_count"]
            }

        # 规模达标但未建立索引
        if status.get("scale_status") == "eligible":
            return {
                "has_cognition": False,
                "scale_status": "eligible",
                "project_root": status["project_root"],
                "reasons": status["reasons"],
                "metrics": status["metrics"],
                "recommendation": "项目规模已达中大型标准，建议建立 AOCI 认知索引 (python scripts/aoci_cognition.py init) 以建立全局认知地图。"
            }
    except Exception:
        pass

    return None


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口，严格支持 --help 零副作用。"""
    parser = argparse.ArgumentParser(
        description="AOCI-CODE 项目认知索引管理中枢与规模探测器",
        epilog=(
            "示例：\n"
            "  python scripts/aoci_cognition.py probe               # 探测当前项目规模与建索阈值\n"
            "  python scripts/aoci_cognition.py status              # 查看项目 AOCI 认知资产状态\n"
            "  python scripts/aoci_cognition.py init                # 为达标项目初始化 AOCI 骨架文件\n"
            "  python scripts/aoci_cognition.py draft               # 预览受管源码的初始 FRAS 草稿\n"
            "  python scripts/aoci_cognition.py verify              # 校验 AOCI 认知资产结构规范\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="subcmd", help="子命令")

    p_probe = subparsers.add_parser("probe", help="度量项目规模并评估 AOCI 认知建立需求")
    p_probe.add_argument("--root", help="目标项目根目录（缺省当前工作目录）")
    p_probe.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    p_status = subparsers.add_parser("status", help="查看项目 AOCI 认知资产现状")
    p_status.add_argument("--root", help="目标项目根目录")
    p_status.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    p_init = subparsers.add_parser("init", help="初始化 Volume-first AOCI 认知骨架")
    p_init.add_argument("--root", help="目标项目根目录")
    p_init.add_argument("--name", help="项目标识名")
    p_init.add_argument("--locale", default="zh-CN", help="语种标识 (默认 zh-CN)")
    p_init.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    p_draft = subparsers.add_parser("draft", help="生成受管源码的初始 FRAS 候选草稿行")
    p_draft.add_argument("--root", help="目标项目根目录")
    p_draft.add_argument("--output", help="写入文件路径（留空直接输出到 stdout）")
    p_draft.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    p_verify = subparsers.add_parser("verify", help="校验 AOCI 认知资产与 FRAS 规范")
    p_verify.add_argument("--root", help="目标项目根目录")
    p_verify.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    args = parser.parse_args(argv)

    if not args.subcmd:
        parser.print_help()
        return 0

    target_root = Path(args.root).resolve() if getattr(args, "root", None) else None

    if args.subcmd == "probe":
        status = read_project_cognition_status(target_root)
        if args.json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print("=" * 64)
            print(f"🔍 AOCI 项目规模探测报告: {status['project_root']}")
            print("=" * 64)
            m = status["metrics"]
            print(f"- 扫描方式     : {status['scan_authority']}")
            print(f"- 有效源码文件 : {m['source_files']} 个")
            print(f"- 物理代码行数 : {m['code_lines']} 行")
            print(f"- 源码总字节量 : {m['source_bytes']} 字节 ({m['source_bytes'] // 1024} KB)")
            print(f"- 认知建立判定 : [{'NEED' if status['scale_status'] == 'eligible' else 'OPTIONAL'}] {status['scale_status']}")
            for r in status["reasons"]:
                print(f"  · {r}")
            print(f"- 已有AOCI索引 : {'已就绪' if status['initialized'] else '未初始化'}")
            print("=" * 64)
        return 0

    if args.subcmd == "status":
        status = read_project_cognition_status(target_root)
        if args.json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(f"AOCI 项目状态: {status['project_root']}")
            print(f"  初始化: {'是' if status['initialized'] else '否'}")
            print(f"  已有词条数: {status['code_entries_count']}")
            print(f"  Volumes: {status['volumes']}")
        return 0

    if args.subcmd == "init":
        res = init_aoci_volumes(target_root or Path.cwd(), args.name, args.locale)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[OK] AOCI 认知卷初始化完成 ({res['project_root']})")
            if res["created"]:
                print(f"  新建文件: {', '.join(res['created'])}")
            else:
                print("  正式认知资产已存在，无需重复创建。")
        return 0

    if args.subcmd == "draft":
        res = generate_draft_fras(target_root or Path.cwd())
        if args.output:
            Path(args.output).write_text(res["draft_content"], encoding="utf-8")
            print(f"[OK] 已导出 {res['total_files']} 个文件的 FRAS 草稿至: {args.output}")
        elif args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            sys.stdout.write(res["draft_content"])
        return 0

    if args.subcmd == "verify":
        ok, issues = verify_cognition_assets(target_root or Path.cwd())
        if args.json:
            print(json.dumps({"ok": ok, "issues": issues}, ensure_ascii=False, indent=2))
        else:
            if ok:
                print("[OK] AOCI 认知资产校验通过，格式符合规范！")
            else:
                print(f"[FAIL] 发现 {len(issues)} 处认知一致性问题:")
                for iss in issues:
                    print(f"  - {iss}")
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
