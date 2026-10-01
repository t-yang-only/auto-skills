#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态守卫：函数里用了、但模块内从未定义或导入的名字。

为什么必须有
============
2026-10-02 实测发现 `obsidian_bridge.py` 用了两处 `re.sub` 却**从未 import re**
—— 于是「从知识库导入技能」整条功能 100% 失败，而最后仍打印
「[OK] 导入完成！共计导入 0 个私有技能」，把「功能坏了」说成了
「你的知识库里没有技能笔记」。

这类缺陷的可怕之处：
  · 语法检查（compileall）**完全看不见** —— 它只在运行时炸；
  · 单元测试看不见 —— 除非恰好覆盖到那条路径；
  · 使用者的第一反应是「我这边数据不对」，而不是「功能坏了」。

所以值得专门用一条静态判据守着。本文件把那次排查用的检查器固定下来，
并**自带变异检查**证明它不是空转（一个永远报「没问题」的检查器，
和没有检查器一样危险）。

判据只报「模块内也找不到定义」的名字，因此不会误伤：
  · 内置名（len / print / open …）
  · 闭包引用外层函数的局部变量
  · 函数内 import / for 目标 / with-as / except-as / 参数
"""
import ast
import builtins
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__builtins__"}
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if (detail and not ok) else ""))


def _module_names(tree):
    """模块层可见的名字。"""
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.add(n.id)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            names.update(n.names)
    return names


def _fn_locals(fn):
    """函数自身作用域内可见的名字。"""
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
    return out


def find_undefined(src):
    """返回 [(行号, 名字)] —— 函数里加载、但模块与所有外层作用域都没有的名字。"""
    tree = ast.parse(src)
    mod = _module_names(tree) | BUILTINS
    problems = []

    def walk(fn, outer):
        loc = _fn_locals(fn)
        visible = mod | outer | loc
        for n in ast.walk(fn):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) \
                    and n.id not in visible:
                problems.append((n.lineno, n.id))
        for stmt in fn.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    walk(sub, outer | loc)

    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            walk(n, set())
    return problems


def main():
    # ---- 1. 变异检查：先证明检查器真的能抓到那类缺陷 ----
    # 没有这一步，「全仓库 0 处」这个结论毫无意义 —— 检查器坏掉时也报 0。
    must_catch = [
        ("漏 import re", "import os\ndef f(x):\n    return re.sub('a','b',x)\n", "re"),
        ("引用未定义变量", "def f(x):\n    return x + undefined_thing\n", "undefined_thing"),
    ]
    for label, src, expect in must_catch:
        got = [nm for _, nm in find_undefined(src)]
        check("变异：能抓到「%s」" % label, expect in got, "只报出 %s" % got)

    must_pass = [
        ("有 import re", "import re\ndef f(x):\n    return re.sub('a','b',x)\n"),
        ("内置名", "def f(x):\n    return len(x)\n"),
        ("正常循环", "import os\ndef f(x):\n    for i in x:\n        print(i)\n"),
        ("闭包引用外层", "def outer():\n    v = 1\n    def inner():\n        return v\n    return inner\n"),
        ("函数内 import", "def f():\n    import json\n    return json.dumps({})\n"),
    ]
    for label, src in must_pass:
        got = find_undefined(src)
        check("变异：不误报「%s」" % label, not got, got)

    # ---- 2. 真判据：全部脚本里不得有未定义名 ----
    bad = []
    n_files = 0
    for p in sorted(SCRIPTS.glob("*.py")):
        n_files += 1
        try:
            src = p.read_text(encoding="utf-8")
        except Exception as e:
            bad.append("%s: 读不到 (%s)" % (p.name, e))
            continue
        try:
            for line, nm in find_undefined(src):
                bad.append("%s:%s 用了未定义名 '%s'" % (p.name, line, nm))
        except SyntaxError as e:
            bad.append("%s: 语法错误 %s" % (p.name, e))

    check("扫描到了脚本（否则本条不具判别力）", n_files > 0, "扫到 %d 个" % n_files)
    check("全部脚本无未定义名（这类缺陷会让整条功能静默全废）",
          not bad, "; ".join(bad[:3]))

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())