#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""obsidian_bridge 从知识库导入技能这条路径的守卫。

为什么必须有
============
2026-10-02 实测发现 `import_skills_from_obsidian` **对每个笔记都失败**：
函数里用了 `re.sub`（两处），但整个模块**从未 import re**。于是：

  · 每个文件都抛 NameError，被逐文件 try 吞掉；
  · 最后仍打印「[OK] 导入完成！共计导入 0 个私有技能」；
  · 读起来像「你的知识库里没有技能笔记」，而不是「这个功能坏了」。

这正是本项目最在意的一类缺陷：**功能全坏却报成功**。修掉之后顺带发现
两个会随之显形的问题（撞名静默覆盖、frontmatter 引号注入），一并在本文件
立判据。

判据锚在**用户可见的输出与磁盘结果**上，不锚内部变量。
"""
import importlib.util
import json
import pathlib
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "obsidian_bridge.py"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if (detail and not ok) else ""))


def _load():
    spec = importlib.util.spec_from_file_location("obsidian_bridge", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _capture(fn):
    """执行并返回 (输出文本, 是否抛异常)。stdout+stderr 合并看。"""
    import contextlib
    import io
    buf = io.StringIO()
    raised = None
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            fn()
        except BaseException as e:      # noqa: BLE001 —— 就是要观察有没有炸
            raised = e
    return buf.getvalue(), raised


def _setup(ob, tmp, notes):
    vault = pathlib.Path(tmp) / "vault"
    vault.mkdir()
    custom = pathlib.Path(tmp) / "custom_skills"
    custom.mkdir()
    ob.CUSTOM_SKILLS_DIR = custom
    for name, body in notes.items():
        (vault / name).write_text(body, encoding="utf-8")
    return vault, custom


def main():
    if not SCRIPT.exists():
        print("  [SKIP] 找不到 %s" % SCRIPT)
        print("\nRESULT: SKIP (1/1)")
        return 0

    # ---- 1. 模块必须真的能跑（这条直接钉死「漏 import re」那类缺陷）----
    ob = _load()
    check("模块里有 re 可用（曾因漏 import 导致整条路径全废）",
          hasattr(ob, "re"), "模块看不到 re")

    with tempfile.TemporaryDirectory() as tmp:
        vault, custom = _setup(ob, tmp, {
            "one.md": "#skill\n一个正常的技能\n",
            "two.md": "#skill\n另一个技能\n",
        })
        out, raised = _capture(
            lambda: ob.import_skills_from_obsidian(str(vault)))
        check("正常笔记能被真的导入（不是 0 个）",
              len(list(custom.glob("*/SKILL.md"))) == 2,
              "磁盘上只有 %d 个 SKILL.md；输出=%r"
              % (len(list(custom.glob("*/SKILL.md"))), out[-120:]))
        check("导入不抛异常", raised is None, "抛了 %r" % raised)

    # ---- 2. 首行含引号时 frontmatter 必须仍是合法 YAML ----
    ob = _load()
    with tempfile.TemporaryDirectory() as tmp:
        vault, custom = _setup(ob, tmp, {
            "quote.md": '#skill\n他说"你好"，然后转身离开\n',
        })
        _capture(lambda: ob.import_skills_from_obsidian(str(vault)))
        f = custom / "quote" / "SKILL.md"
        ok = False
        if f.exists():
            raw = f.read_text(encoding="utf-8")
            try:
                import yaml
                yaml.safe_load(raw.split("---")[1])
                ok = True
            except Exception as e:
                ok = False
                detail = "%s: %s" % (type(e).__name__, e)
        else:
            detail = "文件没生成"
        check("首行含引号时 frontmatter 仍是合法 YAML", ok,
              detail if not ok else "")

    # ---- 3. 归一化撞名必须点名，不能静默覆盖 ----
    ob = _load()
    with tempfile.TemporaryDirectory() as tmp:
        vault, custom = _setup(ob, tmp, {
            "My Skill.md": "#skill\n第一个\n",
            "My-Skill.md": "#skill\n第二个\n",
        })
        out, _ = _capture(lambda: ob.import_skills_from_obsidian(str(vault)))
        check("撞名被点名（含两个来源文件名）",
              "撞名" in out and "My Skill.md" in out and "My-Skill.md" in out,
              out[-160:])
        # 报的数字必须与磁盘一致（曾按「导入动作次数」报，会多报一个）
        n_disk = len(list(custom.glob("*/SKILL.md")))
        check("汇总里的技能数与磁盘一致（不得多报）",
              f"现有 {n_disk} 个私有技能" in out,
              "磁盘 %d 个；输出=%r" % (n_disk, out[-160:]))

    # ---- 4. 全部候选都失败时必须报 FAIL，不能说「导入完成」 ----
    ob = _load()
    with tempfile.TemporaryDirectory() as tmp:
        vault, custom = _setup(ob, tmp, {"bad.md": "#skill\n内容\n"})

        class Boom:
            def sub(self, *a, **k):
                raise RuntimeError("forced failure")

        ob.re = Boom()
        out, _ = _capture(lambda: ob.import_skills_from_obsidian(str(vault)))
        check("全部失败时报 FAIL（不得报「导入完成」）",
              "FAIL" in out and "导入完成" not in out, out[-160:])
        check("全部失败时给出失败原因条数", "解析失败" in out, out[-160:])

    # ---- 5. 无候选笔记 vs 全部失败必须是两句不同的话 ----
    ob = _load()
    with tempfile.TemporaryDirectory() as tmp:
        vault, _ = _setup(ob, tmp, {"plain.md": "普通笔记，没有标记\n"})
        out, _ = _capture(lambda: ob.import_skills_from_obsidian(str(vault)))
        check("无候选笔记时给出「未发现标记」而非失败",
              "未发现" in out and "FAIL" not in out, out[-160:])

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())