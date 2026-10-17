# -*- coding: utf-8 -*-
"""从源码 docstring 自动生成接口文档，保证文档与代码不脱节。

用法:
    python scripts/gen_api_docs.py            # 生成 docs/API.md
    python scripts/gen_api_docs.py --check    # 仅校验，文档过期则退出码 1
"""

import argparse
import inspect
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DOCS_DIR = os.path.join(ROOT, "docs")
API_PATH = os.path.join(DOCS_DIR, "API.md")

# 模块 -> 中文标题
MODULES = [
    ("color", "图色识别"),
    ("vision", "识图匹配"),
    ("screen", "截图与图像"),
    ("mouse", "键鼠操作"),
    ("window", "窗口操作"),
    ("overlay", "遮罩窗口"),
    ("util", "工具与输出"),
    ("workflow", "任务与定时"),
    ("xfeat", "特征匹配（XFeat）"),
    ("net", "代理与网络"),
]

# 不写进文档的内部/演示函数
SKIP = {
    "test_matchTemplate", "test_MatchTemplate", "test_setMousePenetration",
    "main", "config", "mydraw",
}


def parse_doc(doc):
    """把 docstring 拆成 (简述, 参数列表, 返回值, 示例, 注意)。"""
    if not doc:
        return "", [], "", "", ""
    doc = inspect.cleandoc(doc)
    lines = doc.splitlines()

    sections = {}
    cur = "_brief"
    sections[cur] = []
    for line in lines:
        m = re.match(r"^\s*(参数|返回值|返回|示例|注|注意|性能说明|说明|用法)\s*[:：]?\s*$", line)
        if m:
            cur = m.group(1)
            sections.setdefault(cur, [])
            continue
        sections.setdefault(cur, []).append(line)

    brief = "\n".join(sections.pop("_brief", [])).strip()

    def get(*names):
        for n in names:
            if n in sections:
                return "\n".join(sections[n]).strip()
        return ""

    params_raw = get("参数")
    params = []
    for line in params_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*[:：]\s*(.*)$", line)
        if m:
            params.append((m.group(1), m.group(2).strip()))
        elif params:
            name, desc = params[-1]
            params[-1] = (name, (desc + " " + line).strip())
    return brief, params, get("返回值", "返回"), get("示例"), get("注意", "注", "性能说明")


def fmt_signature(func):
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return "()"
    parts = []
    for name, p in sig.parameters.items():
        if p.kind == p.VAR_POSITIONAL:
            parts.append("*" + name)
        elif p.kind == p.VAR_KEYWORD:
            parts.append("**" + name)
        elif p.default is inspect.Parameter.empty:
            parts.append(name)
        else:
            d = p.default
            if isinstance(d, str):
                # 转义控制字符，否则写文件时 \r 会被换行处理吞掉，
                # 导致 --check 每次都认为文档过期
                parts.append('%s="%s"' % (name, d.encode("unicode_escape").decode("ascii")))
            elif d is None:
                parts.append("%s=None" % name)
            elif isinstance(d, object) and type(d).__name__ == "object":
                # 内部哨兵值（如 _UNSET），显示成 _UNSET 而非内存地址
                parts.append("%s=_UNSET" % name)
            else:
                try:
                    repr_d = repr(d)
                except Exception:
                    repr_d = "..."
                if "0x" in repr_d and "object at" in repr_d:
                    repr_d = "_UNSET"
                parts.append("%s=%s" % (name, repr_d))
    return "(" + ", ".join(parts) + ")"


def render_function(mod_name, func):
    brief, params, returns, example, note = parse_doc(func.__doc__)
    out = []
    out.append("### `%s%s`" % (func.__name__, fmt_signature(func)))
    out.append("")
    if brief:
        first = brief.split("\n\n")[0].strip()
        out.append(first)
        out.append("")
    if params:
        out.append("**参数**")
        out.append("")
        out.append("| 参数 | 说明 |")
        out.append("|---|---|")
        for name, desc in params:
            out.append("| `%s` | %s |" % (name, desc.replace("|", "\\|")))
        out.append("")
    if returns:
        out.append("**返回值**: %s" % returns.replace("\n", " "))
        out.append("")
    if note:
        out.append("> **注意**: %s" % note.replace("\n", " "))
        out.append("")
    if example:
        out.append("**示例**")
        out.append("")
        out.append("```python")
        for line in example.splitlines():
            out.append(line.strip())
        out.append("```")
        out.append("")
    return "\n".join(out)


def build(verbose=False):
    import smartpy

    header = [
        "# smartpy 接口文档",
        "",
        "> 本文件由 `scripts/gen_api_docs.py` 从源码 docstring **自动生成**，请勿手工编辑。",
        "> 重新生成: `python scripts/gen_api_docs.py`",
        "",
        "版本: `%s`" % getattr(smartpy, "__version__", "unknown"),
        "",
        "## 目录",
        "",
    ]

    sections = []
    toc = []
    for mod_name, title in MODULES:
        try:
            mod = __import__("smartpy.%s" % mod_name, fromlist=["x"])
        except Exception as e:
            if verbose:
                print("跳过模块 %s: %s" % (mod_name, e))
            continue
        names = getattr(mod, "__all__", [])
        funcs = []
        for n in names:
            if n in SKIP:
                continue
            obj = getattr(mod, n, None)
            if obj is None:
                continue
            if inspect.isfunction(obj) or inspect.isclass(obj):
                if getattr(obj, "__module__", "").startswith("smartpy"):
                    funcs.append(obj)
        if not funcs:
            continue
        anchor = "mod-%s" % mod_name
        toc.append("- [%s](#%s) — `smartpy.%s` · %d 个接口"
                   % (title, anchor, mod_name, len(funcs)))
        parts = ['<a id="%s"></a>' % anchor, "",
                 "## %s `smartpy.%s`" % (title, mod_name), ""]
        doc = (mod.__doc__ or "").strip()
        if doc:
            parts.append(doc.split("\n\n")[0])
            parts.append("")
        for f in funcs:
            parts.append(render_function(mod_name, f))
        sections.append("\n".join(parts))

    text = "\n".join(header) + "\n".join(toc) + "\n\n" + "\n---\n\n".join(sections)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验文档是否最新")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    text = build(args.verbose)
    os.makedirs(DOCS_DIR, exist_ok=True)

    if args.check:
        if not os.path.isfile(API_PATH):
            print("文档不存在: %s" % API_PATH)
            return 1
        old = open(API_PATH, encoding="utf-8").read()
        if old.strip() != text.strip():
            print("接口文档已过期，请运行: python scripts/gen_api_docs.py")
            return 1
        print("接口文档是最新的")
        return 0

    with open(API_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("已生成 %s (%d 字节)" % (API_PATH, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
