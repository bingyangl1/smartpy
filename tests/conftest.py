# -*- coding: utf-8 -*-
"""pytest 全局配置：环境探测与跳过规则。

CI（GitHub Actions 的 windows-latest）是无桌面会话的 Session 0，
以下能力不可用，相关用例必须跳过而不是失败：
- 真实截图（BitBlt / PrintWindow 拿不到 DWM 合成画面）
- 创建遮罩窗口后读它的扩展样式

本机开发时这些用例正常执行。
"""

import os
import sys

import pytest

# Windows CI（英文环境）stdout 是 cp1252，print 中文会 UnicodeEncodeError。
# 不处理的话 pytest 会 INTERNALERROR 直接崩，不是用例失败而是框架崩。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _has_desktop():
    """能否拿到真实桌面截图（判断是否存在可交互桌面会话）。"""
    try:
        import smartpy

        img = smartpy.screenCapture()
        if img is None or img.size == 0:
            return False
        # 全黑 / 全透明通常也是无桌面
        import numpy as np

        return bool(np.asarray(img).std() > 1.0)
    except Exception:
        return False


def _ci_env():
    """CI 环境标记（显式声明时直接判定为无桌面）。"""
    return os.environ.get("SMARTPY_CI") == "1"


_DESKTOP_OK = None


def desktop_ok():
    """缓存探测结果，避免每个用例都截图。"""
    global _DESKTOP_OK
    if _DESKTOP_OK is None:
        _DESKTOP_OK = (not _ci_env()) and _has_desktop()
    return _DESKTOP_OK


requires_desktop = pytest.mark.skipif(
    not desktop_ok(),
    reason="需要可交互桌面会话（CI 的 Session 0 无桌面，跳过截图/窗口用例）",
)


def _safe_print(msg):
    """pytest 会替换 sys.stdout（capture），直接 print 中文在 cp1252 环境会崩。

    这里用 ascii 转义兜底：能编码就正常显示，编码不了就降级为 \\uXXXX。
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "backslashreplace").decode("ascii"))


def pytest_configure(config):
    # pytest 已替换 stdout，这里再切一次编码
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if not desktop_ok():
        config._smartpy_no_desktop = True
        _safe_print("[conftest] 未检测到可交互桌面，截图/窗口相关用例将跳过")
