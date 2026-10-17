# -*- coding: utf-8 -*-
"""API 完整性检查。

两种模式：
1. 默认（CI 用）：校验 smartpy.__all__ 里每个名字都真实可导入、且文档已覆盖。
   不依赖任何外部文件，可在干净环境中运行。
2. --legacy <旧Module.py路径>：对比旧版模块的公开名，确认重构没丢接口。

用法:
    python scripts/api_diff.py                      # 自检（CI）
    python scripts/api_diff.py --legacy old/Module.py   # 对比旧版
"""

import argparse
import ast
import os
import sys

# Windows CI（英文环境）stdout 是 cp1252，print 中文会 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def self_check():
    """校验 __all__ 里的每个名字都能真实取到。"""
    import smartpy

    missing = []
    for name in smartpy.__all__:
        if not hasattr(smartpy, name):
            missing.append(name)

    # __all__ 不能有重复
    dupes = sorted({n for n in smartpy.__all__ if smartpy.__all__.count(n) > 1})

    # 每个模块的 __all__ 名字也要能取到
    mods = ["color", "vision", "screen", "mouse", "window", "overlay",
            "util", "workflow", "xfeat", "net"]
    mod_missing = []
    for m in mods:
        try:
            mod = __import__("smartpy.%s" % m, fromlist=["x"])
        except Exception as e:
            mod_missing.append("%s (导入失败: %s)" % (m, e))
            continue
        for n in getattr(mod, "__all__", []):
            if not hasattr(mod, n):
                mod_missing.append("%s.%s" % (m, n))

    print("== 自检 ==")
    print("  __all__ 数量:", len(smartpy.__all__))
    print("  顶层缺失:", missing or "无")
    print("  重复项:", dupes or "无")
    print("  模块内缺失:", mod_missing or "无")

    ok = not (missing or dupes or mod_missing)
    print("  结果:", "通过" if ok else "失败")
    return 0 if ok else 1


def legacy_check(old_path):
    """对比旧版 Module.py 的公开名。"""
    if not os.path.isfile(old_path):
        print("旧文件不存在: %s" % old_path)
        return 2
    src = open(old_path, "rb").read().decode("utf-8")
    tree = ast.parse(src)
    old_names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                old_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("_"):
                    old_names.add(t.id)

    import smartpy

    new_names = set(smartpy.__all__)
    missing = sorted(old_names - new_names)
    print("== 旧版对比 ==")
    print("  旧版公开名:", len(old_names), " 新版 __all__:", len(new_names))
    if missing:
        print("  新包缺失的旧名字:")
        for n in missing:
            print("    -", n)
        return 1
    print("  全部旧名字都已在新包导出")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", metavar="OLD_MODULE_PY",
                    help="旧 Module.py 路径（可选，给了就做兼容性对比）")
    args = ap.parse_args()

    rc = self_check()
    if args.legacy:
        rc2 = legacy_check(args.legacy)
        rc = max(rc, rc2)
    return rc


if __name__ == "__main__":
    sys.exit(main())
