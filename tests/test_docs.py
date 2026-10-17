# -*- coding: utf-8 -*-
"""文档一致性测试：确保接口文档与代码同步、用例文档引用的 API 真实存在。

这是防止「文档写完了但代码改了没同步」的护栏。
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
API = os.path.join(DOCS, "API.md")
COOKBOOK = os.path.join(DOCS, "COOKBOOK.md")
CHANGELOG = os.path.join(DOCS, "CHANGELOG.md")
DOC_INDEX = os.path.join(DOCS, "README.md")


def test_docs_exist():
    for p in (API, COOKBOOK, CHANGELOG, DOC_INDEX):
        assert os.path.isfile(p), "文档缺失: %s" % p
        assert os.path.getsize(p) > 100, "文档为空: %s" % p


def test_api_doc_up_to_date():
    """API.md 必须与当前 docstring 一致（运行 gen_api_docs.py --check）。"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "gen_api_docs.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT, timeout=120,
        encoding="utf-8", errors="replace", env=env,
    )
    assert r.returncode == 0, (
        "接口文档已过期，请运行 python scripts/gen_api_docs.py\n"
        + (r.stdout or "") + (r.stderr or "")
    )


def test_api_doc_covers_all_modules():
    """接口文档应覆盖全部核心模块。"""
    text = open(API, encoding="utf-8").read()
    for mod in ("color", "vision", "screen", "mouse", "window", "overlay",
                "util", "workflow"):
        assert "smartpy.%s" % mod in text, "接口文档缺少模块 smartpy.%s" % mod


def test_api_doc_has_no_memory_address():
    """签名里不能出现内存地址（说明哨兵值没格式化好）。"""
    text = open(API, encoding="utf-8").read()
    assert "object at 0x" not in text, "接口文档里出现了对象内存地址"


def test_cookbook_api_references_exist():
    """用例文档里 smartpy.xxx 形式的调用，必须在 smartpy 里真实存在。"""
    import smartpy

    text = open(COOKBOOK, encoding="utf-8").read()
    names = set(re.findall(r"smartpy\.([A-Za-z_]\w*)", text))
    modules = {"color", "vision", "screen", "mouse", "window", "overlay",
               "util", "workflow", "xfeat", "net", "win32api", "win32con",
               "win32gui"}
    missing = []
    for n in sorted(names - modules):
        if not hasattr(smartpy, n):
            missing.append(n)
    assert not missing, "用例文档引用了不存在的 API: %s" % missing


def test_changelog_mentions_new_apis():
    """变更记录应提到本次新增的关键接口。"""
    text = open(CHANGELOG, encoding="utf-8").read()
    for name in ("findColorRange", "waitColor", "findMultiColor", "snapshot",
                 "findColorBlock"):
        assert name in text, "CHANGELOG 未提及新接口 %s" % name


def test_docstring_sections_parseable():
    """抽查若干函数的 docstring 能被文档生成器正确解析。

    注意：无参函数（如 snapshot）不要求「参数:」段。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_api_docs", os.path.join(ROOT, "scripts", "gen_api_docs.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    import smartpy

    cases = [
        (smartpy.findColor, True),
        (smartpy.findMultiColor, True),
        (smartpy.waitColor, True),
        (smartpy.getPixel, True),
        (smartpy.snapshot, False),   # 无参
    ]
    for func, need_params in cases:
        brief, params, returns, example, note = gen.parse_doc(func.__doc__)
        assert brief, "%s 缺少简述" % func.__name__
        if need_params:
            assert params, "%s 的「参数:」段解析不到参数" % func.__name__


def test_readme_docs_link():
    """主 README 应链接到文档目录。"""
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert "docs/" in text or "docs\\" in text, "README 未链接到 docs 目录"
