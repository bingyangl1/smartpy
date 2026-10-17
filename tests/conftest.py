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


def pytest_configure(config):
    # 把「无桌面」状态打到测试头，便于排查
    if not desktop_ok():
        config._smartpy_no_desktop = True
        print("\n[conftest] 未检测到可交互桌面，截图/窗口相关用例将跳过")
