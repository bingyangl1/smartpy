# -*- coding: utf-8 -*-
"""
smartpy —— 从旧 Module.py 重构的 Windows 自动化工具包。

结构:
    smartpy.util     计时装饰器 / 格式化输出 / 文件操作
    smartpy.mouse    键鼠操作 / 轨迹 / 识图点击 / 剪贴板
    smartpy.screen   截图 / 图像读写
    smartpy.vision   模板匹配 / 特征匹配
    smartpy.window   窗口查找 / 样式 / 关闭
    smartpy.overlay  置顶透明穿透遮罩窗
    smartpy.workflow 配置驱动任务 / 定时线程

兼容性:
    旧 `import Module` 的所有顶层名字继续可用:
        from smartpy import findClick, screenCapture, ...
    或直接在 <项目根目录> 下 import Module（shim 模块）。
"""

from .util import (
    Timer,
    timer,
    prints,
    printf,
    printc,
    printa,
    copyFile,
    getFile,
    moveFiles,
    moveFile,
    getDir,
    TraverseDir,
    matchFile,
)
from .mouse import (
    SetCursorPos,
    click1,
    click2,
    click3,
    click_it,
    mouseScroll,
    CubicBezier,
    cubic_bezier_gen,
    moveMouse1,
    mouseMove,
    mouseUp,
    mouseDown,
    SendMessage,
    PostMessage,
    moveMouse2,
    moveMouse3,
    moveMouse4,
    genLinePointList,
    findClick,
    click_point,
    click_pointForClient,
    send_enter,
    send_str,
    set_clipboard_text,
    clipboard_paste,
)
from .screen import (
    readImage,
    saveImage,
    screenCapture,
    window_capture,
    imageConcatenate,
    imshow,
    imgReSize,
    async_screenCapture,
)
from .vision import (
    matchTemplate,
    MatchTemplate,
    async_matchTemplate,
    test_matchTemplate,
    test_MatchTemplate,
)
from .xfeat import (
    xfeat_match,
    xfeat_available,
    XFeatLocator,
)
from .color import (
    rgb_to_bgr,
    bgr_to_rgb,
    hex_to_bgr,
    bgr_to_hex,
    getPixel,
    getColor,
    getColorAt,
    compareColor,
    compareColorEx,
    findColor,
    findColorEx,
    findColorBlock,
    findMultiColor,
    findMultiColorEx,
    countColor,
    findColorClick,
    findColorRange,
    countColorRange,
    waitColor,
    waitColorDisappear,
    waitColorChange,
    waitMultiColor,
    snapshot,
    clearSnapshot,
)
from . import net
from .window import (
    findWindow,
    ScreenToClient,
    ClientToScreen,
    WindowFromPoint,
    MAKELONG,
    get_focus,
    getWindowRect,
    setWindowRect,
    setWindowState,
    getCurpos,
    gePosWindowHandle,
    closeWindows,
    Rename,
    printWindowTitle,
    getChildWindows,
    getWindowTitle,
    setWindowTitle,
    getClassName,
    getChildWindow,
    enumWindow,
    enumWindows,
    showWindow,
    sortWindow,
    kill,
    setTopWindow,
    getTopWindowExist,
    setWindowTrans,
    showTaskBar,
    setMousePenetration,
    HideTitleAndBorder,
)
from .overlay import Window, mydraw
from .workflow import (
    runWork,
    runWorkN,
    runWorkConfig,
    runTimer,
    repeat,
)
from ._compat import win32con, win32gui

# 兼容旧版里散落的别名
from .mouse import getCurpos as _getCurpos  # noqa: F401  (getCurpos 已从 window 导入)


def config():
    """兼容旧版的配置示例入口。

    旧版用 @runWorkConfig(findClick) 装饰、并把示例路径写死为 e:/t。
    此处提供等价的可配置版本：返回任务列表，配合 runWork(findClick, config()) 使用。
    """
    defaultArgsDict = {
        "findName": None,
        "filePathList": r"e:/t",
        "endswith": ".png",
        "mode": "rgb",
        "isclick": True,
        "clickAll": False,
        "hwnd": None,
        "retHwnd": False,
    }

    def update(a, b):
        c = a.copy()
        c.update(b)
        return c

    return [
        update(defaultArgsDict, {"findName": "测试", "isclick": False}),
        update(defaultArgsDict, {"findName": "测试", "isclick": False}),
        update(defaultArgsDict, {"findName": "测试", "isclick": False}),
    ]


def main():
    """兼容旧版入口"""
    print("Load Module Success")


def test_setMousePenetration():
    """兼容旧版测试入口（不修改真实窗口，仅打印当前穿透状态）。"""
    hwnd = findWindow(windowTitle=None)
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    print("WS_EX_TRANSPARENT:", bool(style & win32con.WS_EX_TRANSPARENT))

__version__ = "2.1.0"

__all__ = [
    # util
    "Timer", "timer", "prints", "printf", "printc", "printa",
    "copyFile", "getFile", "moveFiles", "moveFile", "getDir",
    "TraverseDir", "matchFile",
    # mouse
    "SetCursorPos", "click1", "click2", "click3", "click_it", "mouseScroll",
    "CubicBezier", "cubic_bezier_gen", "moveMouse1", "mouseMove", "mouseUp",
    "mouseDown", "SendMessage", "PostMessage", "moveMouse2", "moveMouse3",
    "moveMouse4", "genLinePointList", "findClick", "click_point",
    "click_pointForClient", "send_enter", "send_str", "set_clipboard_text",
    "clipboard_paste",
    # screen
    "readImage", "saveImage", "screenCapture", "window_capture",
    "imageConcatenate", "imshow", "imgReSize", "async_screenCapture",
    # vision
    "matchTemplate", "MatchTemplate", "async_matchTemplate",
    "test_matchTemplate", "test_MatchTemplate",
    # xfeat
    "xfeat_match", "xfeat_available", "XFeatLocator",
    # color
    "rgb_to_bgr", "bgr_to_rgb", "hex_to_bgr", "bgr_to_hex",
    "getPixel", "getColor", "getColorAt", "compareColor", "compareColorEx",
    "findColor", "findColorEx", "findColorBlock", "findMultiColor",
    "findMultiColorEx", "countColor", "findColorClick",
    "findColorRange", "countColorRange",
    "waitColor", "waitColorDisappear", "waitColorChange", "waitMultiColor",
    "snapshot", "clearSnapshot",
    # window
    "findWindow", "ScreenToClient", "ClientToScreen", "WindowFromPoint",
    "MAKELONG", "get_focus", "getWindowRect", "setWindowRect",
    "setWindowState", "getCurpos", "gePosWindowHandle", "closeWindows",
    "Rename", "printWindowTitle", "getChildWindows", "getWindowTitle",
    "setWindowTitle", "getClassName", "getChildWindow", "enumWindow",
    "enumWindows", "showWindow", "sortWindow", "kill", "setTopWindow",
    "getTopWindowExist", "setWindowTrans", "showTaskBar",
    "setMousePenetration", "HideTitleAndBorder",
    # overlay
    "Window", "mydraw",
    # workflow
    "runWork", "runWorkN", "runWorkConfig", "runTimer", "repeat",
    # compat
    "config", "main", "test_setMousePenetration",
]
