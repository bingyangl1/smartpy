# -*- coding: utf-8 -*-
"""smartpy.window —— 窗口查找 / 样式 / 位置 / 关闭 / 标题。

相对旧 Module.py 的修复：
- WindiwTitle 拼写（3 处）→ NameError，已统一为 WindowTitle。
- getTopWindowExist：`a & b == 8` 优先级错误导致永远返回 False，已加括号。
- closeWindows：`return flag` 在循环体内导致只关第一个窗口，已移出循环。
- setWindowTrans(isTrans=False)：旧版最后把 GWL_EXSTYLE 清 0 导致
  TOOLWINDOW/TOPMOST 等样式全丢，现在只清除 WS_EX_LAYERED 位。
- setTopWindow：SWP 标志里误写 WS_ACTIVECAPTION(0x1)，实际与 SWP_NOSIZE 撞值
  才没炸，已改为 SWP_SHOWWINDOW。
- 所有 FindWindow 调用前显式处理 None，避免 str(None) 参与匹配。
"""

from ._compat import win32api, win32con, win32gui, win32process

__all__ = [
    "findWindow",
    "ScreenToClient",
    "ClientToScreen",
    "WindowFromPoint",
    "MAKELONG",
    "get_focus",
    "getWindowRect",
    "setWindowRect",
    "setWindowState",
    "getCurpos",
    "gePosWindowHandle",
    "closeWindows",
    "Rename",
    "printWindowTitle",
    "getChildWindows",
    "getWindowTitle",
    "setWindowTitle",
    "getClassName",
    "getChildWindow",
    "enumWindow",
    "enumWindows",
    "showWindow",
    "sortWindow",
    "kill",
    "setTopWindow",
    "getTopWindowExist",
    "setWindowTrans",
    "showTaskBar",
    "setMousePenetration",
    "HideTitleAndBorder",
]


# ---------------------------------------------------------------- 基础


def findWindow(className=None, windowTitle=None):
    """
    获取指定的窗口句柄
    参数: className 类名 / windowTitle 标题（均可不传）
    返回: hwnd；两个都不传时返回桌面句柄
    """
    if not className and not windowTitle:
        return win32gui.GetDesktopWindow()
    return win32gui.FindWindow(className, windowTitle)


def ScreenToClient(hwnd, pos):
    return win32gui.ScreenToClient(hwnd, pos)


def ClientToScreen(hwnd, pos):
    return win32gui.ClientToScreen(hwnd, pos)


def WindowFromPoint(pos):
    return win32gui.WindowFromPoint(pos)


def MAKELONG(x, y):
    return win32api.MAKELONG(x, y)


def get_focus(hwnd=None):
    """获取窗口焦点"""
    if not hwnd:
        hwnd = win32gui.GetDesktopWindow()
    win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)


def getCurpos():
    """获取当前鼠标位置"""
    return win32gui.GetCursorPos()


def gePosWindowHandle(pos):
    """获取指定坐标位置的窗口句柄"""
    return win32gui.WindowFromPoint(pos)


def getWindowTitle(hwnd):
    return win32gui.GetWindowText(hwnd)


def setWindowTitle(hwnd, title):
    return win32gui.SetWindowText(hwnd, title)


def getClassName(hwnd):
    return win32gui.GetClassName(hwnd)


def _resolve(hwnd, ClassName=None, WindowTitle=None):
    if hwnd:
        return hwnd
    if ClassName or WindowTitle:
        return win32gui.FindWindow(ClassName, WindowTitle)
    return None


# ---------------------------------------------------------------- 位置 / 状态


def getWindowRect(hwnd=None, ClassName=None, WindowTitle=None, mode=0):
    """
    获取窗口位置。参数优先级: hwnd > ClassName/WindowTitle
    mode: 0 -> (left, top, right, bottom)；1 -> (left, top, w, h)
    """
    hwnd = _resolve(hwnd, ClassName, WindowTitle)
    if not hwnd:
        print("窗口句柄不存在 hwnd:%s" % (hwnd,))
        return None
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    if mode == 1:
        return (left, top, right - left, bottom - top)
    return (left, top, right, bottom)


def setWindowRect(hwnd=None, ClassName=None, WindowTitle=None,
                  Rect=(None, None, None, None)):
    """
    设置窗口位置 (x, y, w, h)，None 项保持不变
    """
    hwnd = _resolve(hwnd, ClassName, WindowTitle)
    if not hwnd:
        print("窗口句柄不存在 hwnd:%s" % (hwnd,))
        return
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    x = Rect[0] if Rect[0] is not None else left
    y = Rect[1] if Rect[1] is not None else top
    w = Rect[2] if Rect[2] is not None else right - left
    h = Rect[3] if Rect[3] is not None else bottom - top
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h,
                          win32con.SWP_SHOWWINDOW)


def setWindowState(hwnd=None, state=0, ClassName=None, WindowTitle=None):
    """
    设置窗口状态：0 还原 / 1 最小化 / 2 最大化
    """
    if state not in (0, 1, 2):
        raise ValueError("state 只能是 0(还原)/1(最小化)/2(最大化)")
    hwnd = _resolve(hwnd, ClassName, WindowTitle)
    if not hwnd:
        print("窗口句柄不存在 hwnd:%s" % (hwnd,))
        return
    choice = [win32con.SC_RESTORE, win32con.SC_MINIMIZE, win32con.SC_MAXIMIZE]
    win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, choice[state], 0)
    win32gui.SetForegroundWindow(hwnd)


def showWindow(hwnd):
    """前台显示窗口"""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)


# ---------------------------------------------------------------- 样式


def setTopWindow(hwnd, setTop=True):
    """置顶 / 取消置顶窗口"""
    flag = win32con.SWP_SHOWWINDOW | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
    if setTop:
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, flag)
    else:
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, flag)


def getTopWindowExist(hwnd):
    """
    查看指定窗口是否置顶。

    判断依据：WS_EX_TOPMOST 位。注意该位只有 ShowWindow 之后调用
    SetWindowPos(HWND_TOPMOST) 才会写入 GWL_EXSTYLE；Z 序 GW_HWNDPREV
    不区分置顶层，不能作为判断依据。
    """
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    return bool(style & win32con.WS_EX_TOPMOST)


def setWindowTrans(hwnd, transColor=win32api.RGB(255, 255, 255), Alpha=220,
                   isTrans=True):
    """
    设置窗口透明度
    isTrans=False 时恢复不透明（只清除 LAYERED 位，保留其它扩展样式）
    """
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if isTrans:
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(
            hwnd, transColor, Alpha, win32con.LWA_ALPHA | win32con.LWA_COLORKEY
        )
    else:
        win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style & ~win32con.WS_EX_LAYERED)


def showTaskBar(hwnd, show=True):
    """
    设置任务栏图标显示 / 隐藏
    """
    if isinstance(hwnd, (list, tuple)):
        for h in hwnd:
            showTaskBar(h, show=show)
        return
    exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if not show:
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               exstyle | win32con.WS_EX_TOOLWINDOW)
    else:
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               exstyle & ~win32con.WS_EX_TOOLWINDOW)
        # 需要重挂 caption 样式让任务栏重新识别
        style |= win32con.WS_CAPTION
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    # 让样式生效
    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                          win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)


def setMousePenetration(hwnd, Penetration=True):
    """设置 / 取消鼠标穿透"""
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if Penetration:
        style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
    else:
        style &= ~win32con.WS_EX_TRANSPARENT
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)


def HideTitleAndBorder(hwnd, hide=True):
    """隐藏 / 恢复标题栏和边框"""
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if hide:
        style &= ~(win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.WS_SIZEBOX |
                   win32con.WS_MAXIMIZEBOX | win32con.WS_MINIMIZEBOX)
    else:
        style |= (win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.WS_SIZEBOX |
                  win32con.WS_MAXIMIZEBOX | win32con.WS_MINIMIZEBOX)
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                          win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)


# ---------------------------------------------------------------- 枚举 / 关闭


def enumWindows(debug=False):
    """
    枚举所有窗口
    返回: [{"className": ..., "windowTitle": ..., "hwnd": ...}, ...]
    """
    hWndList = []
    win32gui.EnumWindows(lambda hWnd, param: param.append(hWnd), hWndList)
    result = []
    for hwnd in hWndList:
        windowTitle = win32gui.GetWindowText(hwnd)
        className = win32gui.GetClassName(hwnd)
        if debug:
            print(className, windowTitle)
        result.append({"className": className, "windowTitle": windowTitle, "hwnd": hwnd})
    return result


def enumWindow(ClassName=None, WindowTitle=None, debug=False):
    """
    按类名 / 标题（子串，模糊）查找窗口
    返回: 句柄列表
    """
    if not ClassName and not WindowTitle:
        return []
    findList = []
    for info in enumWindows(debug=debug):
        ok = True
        if ClassName:
            ok = ok and (ClassName in info["className"])
        if WindowTitle:
            ok = ok and (WindowTitle in info["windowTitle"])
        if ok:
            findList.append(info["hwnd"])
    return sorted(findList)


def getChildWindows(parent):
    """获得 parent 的所有子窗口句柄"""
    if not parent:
        return []
    hwndChildList = []
    win32gui.EnumChildWindows(
        parent, lambda hwnd, param: param.append(hwnd), hwndChildList
    )
    return hwndChildList


def getChildWindow(parent, ClassName=None, WindowTitle=None, strict=False):
    """
    获得父窗口下符合类名 / 标题的子窗口
    strict: True 用 == 精确匹配；False 用 in 包含匹配
    """
    if not parent:
        return []
    findList = []
    for hwnd in getChildWindows(parent):
        title = win32gui.GetWindowText(hwnd)
        className = win32gui.GetClassName(hwnd)
        if ClassName or WindowTitle:
            if strict:
                if ClassName and className == ClassName:
                    findList.append(hwnd)
                elif WindowTitle and title == WindowTitle:
                    findList.append(hwnd)
            else:
                if ClassName and ClassName in className:
                    findList.append(hwnd)
                elif WindowTitle and WindowTitle in title:
                    findList.append(hwnd)
    return findList


def closeWindows(hwndList):
    """
    关闭窗口列表（先发 WM_CLOSE，收不到再终止进程）
    返回: 0 全部处理完，-1 有失败
    """
    flag = 0
    for hwnd in hwndList:
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            threadId, processId = win32process.GetWindowThreadProcessId(hwnd)
            hProcess = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, 0, processId)
            win32api.TerminateProcess(hProcess, 0)
        except Exception as e:
            print("报错:\n\t", e)
            print("程序关闭失败,请自行关闭!")
            flag = -1
    return flag


def kill(ClassName=None, WindowTitle=None):
    """按类名 / 标题关闭程序（多开场景重写）"""
    return closeWindows(enumWindow(ClassName=ClassName, WindowTitle=WindowTitle))


def Rename(ClassName=None, WindowTitle=None, rename=None, hwndList=None):
    """修改窗口标题"""
    if hwndList:
        for i in range(len(hwndList)):
            win32gui.SetWindowText(hwndList[i], rename)
        return
    if ClassName or WindowTitle:
        hwndList = enumWindow(ClassName=ClassName, WindowTitle=WindowTitle)
        for i in range(len(hwndList)):
            win32gui.SetWindowText(hwndList[i], rename)
        return


def printWindowTitle(hwndList):
    """打印 hwndList 中每个窗口的类名 / 标题 / 句柄"""
    if isinstance(hwndList, (list, tuple)):
        for i, hwnd in enumerate(hwndList):
            print("编号:%d 类名:%s 标题:%s 句柄：%s" % (
                i, win32gui.GetClassName(hwnd),
                win32gui.GetWindowText(hwnd), hwnd))


def sortWindow(ClassName=None, WindowTitle=None, hwndList=None, x=0, y=0, w=836, h=501):
    """前台显示并网格化排列窗口"""
    cx, cy = 0, 0
    W = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    H = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    if hwndList:
        findList = list(hwndList)
    else:
        findList = enumWindow(ClassName=ClassName, WindowTitle=WindowTitle)
    cols = max(W // w, 1)
    rows = max(H // h, 1)
    for hwnd in findList:
        if cx >= cols:
            cx = 0
            cy += 1
        if cy >= rows:
            cy = 0
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP,
                              x + cx * w, y + cy * h, w, h,
                              win32con.SWP_SHOWWINDOW)
        cx += 1
