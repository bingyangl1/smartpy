# -*- coding: utf-8 -*-
"""smartpy._compat —— pywin32 / OpenCV 导入与 DPI 兼容层。

集中处理所有 Windows 相关依赖的导入与进程级设置：
- SetProcessDPIAware 只调用一次（每次截图都调会导致窗口尺度前后不一致）
- 统一导出 win32api / win32con / win32gui / win32process / win32ui / win32clipboard
"""

import ctypes as _ctypes
import sys as _sys

# 进程级 DPI 感知：只设置一次。
# 放在导入包时就完成，保证 GetWindowRect / GetCursorPos / 截图像素三者用同一套坐标。
if _sys.platform == "win32":
    try:
        _ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32ui
    import win32clipboard
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "smartpy 需要 pywin32，请先安装：pip install pywin32"
    ) from _e

__all__ = [
    "win32api",
    "win32con",
    "win32gui",
    "win32process",
    "win32ui",
    "win32clipboard",
]
