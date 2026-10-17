# -*- coding: utf-8 -*-
"""把旧 Module.py 的公开名字与新包比对，确认没有丢 API。"""

import os
import sys

OLD = r"D:\smartpy\Module.py"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def main():
    import ast

    src = open(OLD, "rb").read().decode("utf-8")
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
    print("旧版公开名:", len(old_names), " 新版 __all__:", len(new_names))
    if missing:
        print("新包缺失的旧名字:")
        for n in missing:
            print("  -", n)
    else:
        print("全部旧名字都已在新包导出")


if __name__ == "__main__":
    main()
