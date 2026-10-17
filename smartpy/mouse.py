# -*- coding: utf-8 -*-
"""smartpy.mouse —— 键鼠操作、轨迹生成、识图点击。

相对旧 Module.py 的修复：
- CubicBezier._delta_bezier_func 用中心差分（旧版 f(t)-f(t) 恒为 0，get_x/get_y 必崩）。
- genLinePointList 按 start→end 方向生成（旧版只往正方向累加，反向拖拽会飞出终点），
  且不再 sorted() 打乱轨迹顺序。
- moveMouse1 的绝对坐标换算改用标准公式 x*65535/(screen-1)，带括号（不再有 << 优先级歧义）。
- click_it：enter 补上 KEYDOWN；左/右键拆成 DOWN、UP 两次事件；x/y 缺省时给出明确报错。
- mouseScroll：WM_MOUSEWHEEL 的 lParam 传屏幕坐标（旧版误传客户区坐标）。
- findClick：删除对未赋值变量 template 的 del（旧版命中即 UnboundLocalError）。
- 所有类型判断 isinstance 化。
"""

import math
import random
import time

import numpy as np

from ._compat import win32api, win32con, win32gui

__all__ = [
    "SetCursorPos",
    "click1",
    "click2",
    "click3",
    "click_it",
    "mouseScroll",
    "CubicBezier",
    "cubic_bezier_gen",
    "moveMouse1",
    "mouseMove",
    "mouseUp",
    "mouseDown",
    "SendMessage",
    "PostMessage",
    "moveMouse2",
    "moveMouse3",
    "moveMouse4",
    "genLinePointList",
    "findClick",
    "click_point",
    "click_pointForClient",
    "send_enter",
    "send_str",
    "set_clipboard_text",
    "clipboard_paste",
]


# ---------------------------------------------------------------- 基础封装


def SetCursorPos(pos):
    """设置鼠标位置 (x, y)"""
    win32api.SetCursorPos(pos)


def SendMessage(hwnd, Param1, Param2, Param3):
    """同步发送消息（旧版被同名坏实现覆盖，这里统一为正确的直通封装）"""
    return win32gui.SendMessage(hwnd, Param1, Param2, Param3)


def PostMessage(hwnd, Param1, Param2, Param3):
    """异步投递消息"""
    return win32gui.PostMessage(hwnd, Param1, Param2, Param3)


def getCurpos():
    """获取当前鼠标位置"""
    return win32gui.GetCursorPos()


def _jittermove(x, y, offset):
    if offset:
        x = x + random.randrange(-offset, offset + 1)
        y = y + random.randrange(-offset, offset + 1)
    return x, y


# ---------------------------------------------------------------- 点击


def click1(x, y, offset=0, reduction=True, debug=False):
    """
    功能: 前台点击（win32api.mouse_event 实现）
    参数:
        x, y 坐标
        offset 随机偏移范围 [-offset, offset]
        reduction 是否恢复原坐标
    返回: 实际点击坐标 (x, y)
    """
    old_point = win32api.GetCursorPos()
    x, y = _jittermove(x, y, offset)
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    if debug:
        print("click1:{(%d, %d)}" % (x, y))
    if reduction:
        win32api.SetCursorPos(old_point)
    return (x, y)


def click2(x, y, offset=0, reduction=True, debug=False):
    """
    功能: 前台点击（ctypes.windll.user32.mouse_event 实现）
    参数同 click1
    """
    import ctypes

    old_point = win32api.GetCursorPos()
    x, y = _jittermove(x, y, offset)
    ctypes.windll.user32.SetCursorPos(x, y)
    ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    if debug:
        print("click2:{(%d, %d)}" % (x, y))
    if reduction:
        ctypes.windll.user32.SetCursorPos(old_point[0], old_point[1])
    return (x, y)


def click3(x, y, offset=0, debug=False):
    """
    功能: 通过 SendMessage 向窗口发点击消息（不动物理鼠标）
    参数:
        x, y 屏幕坐标
        offset 随机偏移范围
    返回: 实际点击坐标 (x, y)
    """
    x, y = _jittermove(x, y, offset)
    pos = (x, y)
    hwnd = win32gui.WindowFromPoint(pos)
    client_pos = win32gui.ScreenToClient(hwnd, pos)
    tmp = win32api.MAKELONG(client_pos[0], client_pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, tmp)
    win32gui.SendMessage(
        hwnd, win32con.WM_SETFOCUS, hwnd,
        win32api.MAKELONG(win32con.HTCLIENT, win32con.WM_LBUTTONUP),
    )
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, tmp)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, tmp)
    if debug:
        print("click3:{(%d, %d)}" % (x, y))
    return pos


def click_it(x=None, y=None, button="left", offset=3, debug=False):
    """
    功能: 移动鼠标并点击，坐标带随机偏移
    参数:
        x, y 必填坐标
        button: left / right / doubleleft / enter
        offset: 偏移范围
    返回: 实际点击坐标 (x, y)
    """
    if x is None or y is None:
        raise TypeError("click_it 需要显式传入 x 与 y 坐标")
    x = random.randint(x - offset, x + offset)
    y = random.randint(y - offset, y + offset)
    if button in ("left", "right", "doubleleft"):
        win32api.SetCursorPos([x, y])
        if button == "left":
            down, up = win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP
        else:
            down, up = win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP
        win32api.mouse_event(down, 0, 0, 0, 0)
        win32api.mouse_event(up, 0, 0, 0, 0)
        if button == "doubleleft":
            time.sleep(0.001)
            win32api.mouse_event(down, 0, 0, 0, 0)
            win32api.mouse_event(up, 0, 0, 0, 0)
    elif button == "enter":
        win32api.keybd_event(13, 0, 0, 0)
        win32api.keybd_event(13, 0, win32con.KEYEVENTF_KEYUP, 0)
    else:
        raise ValueError("未知的 button: %r" % (button,))
    if debug:
        print("click_it:{(%d, %d)}" % (x, y))
    return (x, y)


def mouseScroll(pos=(0, 0), hwnd=None, scrollbutton=1, rotate=1, debug=False, isClient=False):
    """
    模拟鼠标滚动
    参数:
        hwnd：句柄；不给则按 pos 取窗口
        pos：坐标（屏幕坐标；isClient=True 时为客户区坐标）
        rotate：滚动行数 正数向上，负数向下
        scrollbutton：滚轮键位标志（0 无修饰键，1 MK_LBUTTON）
        isClient：pos 是否为客户区坐标
    """
    if not hwnd:
        hwnd = win32gui.WindowFromPoint(pos)
        if debug:
            print("from point %s get hwnd %s" % (pos, hwnd))
    screen_pos = pos if not isClient else win32gui.ClientToScreen(hwnd, pos)
    client_pos = pos if isClient else win32gui.ScreenToClient(hwnd, pos)
    tmp = win32api.MAKELONG(client_pos[0], client_pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, tmp)
    win32gui.SendMessage(
        hwnd, win32con.WM_SETFOCUS, hwnd,
        win32api.MAKELONG(win32con.HTCLIENT, win32con.WM_LBUTTONUP),
    )
    # WM_MOUSEWHEEL: wParam 高字=delta，低字=键状态；lParam 必须是屏幕坐标
    wparam = win32api.MAKELONG(scrollbutton & 0xFFFF, win32con.WHEEL_DELTA * rotate)
    lparam = win32api.MAKELONG(screen_pos[0], screen_pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, tmp)
    win32gui.SendMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, tmp)
    if debug:
        print(
            "mouseScroll: %s pos=%s %s" % (
                win32gui.GetWindowText(hwnd),
                pos,
                "up" if rotate > 0 else "down",
            )
        )
    return pos


# ---------------------------------------------------------------- 轨迹


class CubicBezier:
    """三次贝塞尔曲线"""

    def __init__(self, c1=(0, 0), c2=(1, 1), begin=(0, 0), end=(1, 1)):
        self.c1 = c1
        self.c2 = c2
        self.begin = begin
        self.end = end

    def _bezier_func(self, p, t, targ):
        return (
            self.begin[p] * math.pow(1 - t, 3)
            + self.c1[p] * 3 * t * math.pow(1 - t, 2)
            + self.c2[p] * 3 * (1 - t) * math.pow(t, 2)
            + self.end[p] * math.pow(t, 3)
            - targ
        )

    def _delta_bezier_func(self, p, t, targ):
        # 中心差分（旧版是 f(t)-f(t)，恒为 0，除零必崩）
        dt = 1e-6
        return (
            self._bezier_func(p, t + dt, targ) - self._bezier_func(p, t - dt, targ)
        ) / (2 * dt)

    def get_x(self, y):
        """给定 y 求 x（牛顿迭代）"""
        t = 0.5
        for _ in range(200):
            f = self._bezier_func(1, t, y)
            d = self._delta_bezier_func(1, t, y)
            if abs(f) < 1e-9:
                break
            if abs(d) < 1e-12:
                break
            t -= f / d
            t = min(max(t, 0.0), 1.0)
        return self._bezier_func(0, t, 0)

    def get_y(self, x):
        """给定 x 求 y（牛顿迭代）"""
        t = 0.5
        for _ in range(200):
            f = self._bezier_func(0, t, x)
            d = self._delta_bezier_func(0, t, x)
            if abs(f) < 1e-9:
                break
            if abs(d) < 1e-12:
                break
            t -= f / d
            t = min(max(t, 0.0), 1.0)
        return self._bezier_func(1, t, 0)

    def get(self, t):
        """t∈[0,1] 求曲线上点 (x, y)"""
        return self._bezier_func(0, t, 0), self._bezier_func(1, t, 0)


def cubic_bezier_gen(start, end, dv=10):
    """
    贝塞尔曲线轨迹生成器
    参数:
        start: 起点 (x, y)
        end: 终点 (x, y)
        dv: 轨迹点数
    生成: 从 start 到 end 的 (x, y) 序列
    """
    arg = (0.17, 0.67, 0.83, 0.67)
    del_x = abs(end[0] - start[0])
    del_y = abs(end[1] - start[1])
    cb_x = CubicBezier(
        c1=(del_x * arg[0], del_x * arg[1]),
        c2=(del_x * arg[2], del_x * arg[3]),
        end=(del_x, del_y),
    )
    fg_x = 1 if start[0] < end[0] else -1
    fg_y = 1 if start[1] < end[1] else -1
    for t in np.linspace(0, 1, dv):
        x = cb_x.get(t)[0]
        y = cb_x.get(t)[1]
        yield (int(x * fg_x + start[0]), int(y * fg_y + start[1]))


def genLinePointList(start, end, offset=0):
    """
    根据指定点生成直线轨迹点集合（保持顺序）
    参数:
        start: 起点 (x, y)
        end: 终点 (x, y)
        offset: 每点随机偏移
    返回: 轨迹列表 [(x1,y1),...,(xn,yn)]，首点=start，末点=end
    """
    x1, y1 = start
    x2, y2 = end
    # 沿线段生成采样点：步长 1~9 随机，覆盖整个线段
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist <= 0:
        return [start]
    dx = (x2 - x1) / dist
    dy = (y2 - y1) / dist
    points = [start]
    covered = 0.0
    while covered < dist:
        step = min(random.randint(1, 9), dist - covered)
        covered += step
        x = x1 + dx * covered
        y = y1 + dy * covered
        if offset:
            x += random.randrange(-offset, offset + 1)
            y += random.randrange(-offset, offset + 1)
        points.append((int(round(x)), int(round(y))))
    # 保证终点精确
    points[-1] = end
    # 去重但保持顺序
    seen, result = set(), []
    for p in points:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------- 拖拽


def moveMouse1(start, end, reduction=True, debug=False, offset=0):
    """
    功能: 拖拽鼠标从 start 到 end（win32api.mouse_event，绝对坐标）
    参数:
        start / end: (x, y)
        reduction: 是否恢复原坐标
        offset: 随机偏移
    """
    if offset:
        start = _jittermove(start[0], start[1], offset)
        end = _jittermove(end[0], end[1], offset)
    old_point = win32api.GetCursorPos()
    sw = max(win32api.GetSystemMetrics(win32con.SM_CXSCREEN) - 1, 1)
    sh = max(win32api.GetSystemMetrics(win32con.SM_CYSCREEN) - 1, 1)
    mx = int((end[0] * 65535) / sw)
    my = int((end[1] * 65535) / sh)
    win32api.SetCursorPos(start)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE,
                         mx, my, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    if debug:
        print("move: %s ==> %s" % (start, end))
    if reduction:
        win32api.SetCursorPos(old_point)


def mouseMove(hwnd, pos):
    p = win32api.MAKELONG(pos[0], pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, p)


def mouseUp(hwnd, pos):
    p = win32api.MAKELONG(pos[0], pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, p)


def mouseDown(hwnd, pos):
    # 旧版这里误用未定义的 startPoint，修复为按入参构造
    p = win32api.MAKELONG(pos[0], pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, p)


def _to_client(hwnd, point, isClient):
    return point if isClient else win32gui.ScreenToClient(hwnd, point)


def moveMouse2(start, end, hwnd=None, debug=False, offset=1, isClient=False):
    """拖拽（SendMessage 一步到位）"""
    if not hwnd:
        hwnd = win32gui.WindowFromPoint(start)
    if offset:
        start = _jittermove(start[0], start[1], offset)
        end = _jittermove(end[0], end[1], offset)
    cs = _to_client(hwnd, start, isClient)
    ce = _to_client(hwnd, end, isClient)
    startPoint = win32api.MAKELONG(cs[0], cs[1])
    endPoint = win32api.MAKELONG(ce[0], ce[1])
    win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, startPoint)
    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, endPoint)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, endPoint)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, startPoint)
    if debug:
        print("%s move: %s ==> %s" % (win32gui.GetWindowText(hwnd), start, end))


def moveMouse3(start, end, movePointList=None, hwnd=None, debug=False, offset=1,
               isClient=False):
    """拖拽（SendMessage 沿轨迹逐点发送）"""
    if not hwnd:
        hwnd = win32gui.WindowFromPoint(start)
    if not movePointList:
        movePointList = genLinePointList(start, end)
    if offset:
        start = _jittermove(start[0], start[1], offset)
        end = _jittermove(end[0], end[1], offset)
    cs = _to_client(hwnd, start, isClient)
    ce = _to_client(hwnd, end, isClient)
    startPoint = win32api.MAKELONG(cs[0], cs[1])
    endPoint = win32api.MAKELONG(ce[0], ce[1])
    win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, startPoint)
    time.sleep(0.001)
    for i in movePointList:
        pt = i if isClient else win32gui.ScreenToClient(hwnd, i)
        if offset:
            pt = _jittermove(pt[0], pt[1], offset)
        tempPoint = win32api.MAKELONG(pt[0], pt[1])
        win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, tempPoint)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, endPoint)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, startPoint)
    if debug:
        print("%s move: %s ==> %s" % (win32gui.GetWindowText(hwnd), start, end))


def moveMouse4(start, end, movePointList=None, hwnd=None, debug=False, offset=1,
               cost=1, isClient=False):
    """拖拽（贝塞尔轨迹）"""
    if not hwnd:
        hwnd = win32gui.WindowFromPoint(start)
    if not movePointList:
        movePointList = list(cubic_bezier_gen(start, end, max(int(cost * 10), 2)))
    if offset:
        start = _jittermove(start[0], start[1], offset)
        end = _jittermove(end[0], end[1], offset)
    cs = _to_client(hwnd, start, isClient)
    ce = _to_client(hwnd, end, isClient)
    startPoint = win32api.MAKELONG(cs[0], cs[1])
    endPoint = win32api.MAKELONG(ce[0], ce[1])
    win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, startPoint)
    time.sleep(0.001)
    for i in movePointList:
        pt = i if isClient else win32gui.ScreenToClient(hwnd, i)
        tempPoint = win32api.MAKELONG(pt[0], pt[1])
        win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, tempPoint)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, endPoint)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, startPoint)
    if debug:
        print("%s move: %s ==> %s" % (win32gui.GetWindowText(hwnd), start, end))


# ---------------------------------------------------------------- 按键与剪贴板


def _resolve_hwnd(hwnd, ClassName=None, WindowTitle=None):
    if hwnd:
        return hwnd
    if ClassName or WindowTitle:
        return win32gui.FindWindow(ClassName, WindowTitle)
    return None


def send_enter(hwnd=None, ClassName=None, WindowTitle=None):
    """发送 Enter 键"""
    hwnd = _resolve_hwnd(hwnd, ClassName, WindowTitle)
    if not hwnd:
        print("窗口句柄为空 hwnd:%s" % (hwnd,))
        return
    win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
    win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    win32gui.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)


def send_str(text, hwnd=None, ClassName=None, WindowTitle=None):
    """向指定窗口发送字符串（WM_CHAR）"""
    if not hwnd and not ClassName and not WindowTitle:
        print("未指定 句柄hwnd 、 类名ClassName 、窗口标题 WindowTitle")
        return
    if isinstance(hwnd, (list, tuple)):
        for h in hwnd:
            send_str(text, hwnd=h, ClassName=ClassName, WindowTitle=WindowTitle)
        return
    hwnd = _resolve_hwnd(hwnd, ClassName, WindowTitle)
    if not hwnd:
        return
    print("向窗口%s %s 发送文本%s" % (hwnd, win32gui.GetWindowText(hwnd), text))
    for ch in text:
        win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)


def set_clipboard_text(text):
    """将字符串复制到剪贴板"""
    win32clipboard = __import__("win32clipboard", fromlist=["x"])
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def clipboard_paste(hwnd=None, ClassName=None, WindowTitle=None):
    """从剪贴板粘贴到指定窗口"""
    hwnd = _resolve_hwnd(hwnd, ClassName, WindowTitle)
    if not hwnd:
        print("窗口句柄为空 hwnd:%s" % (hwnd,))
        return
    win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
    win32gui.SendMessage(hwnd, win32con.WM_CLEAR, 0, 0)
    win32gui.SendMessage(hwnd, win32con.WM_PASTE, 0, 0)


# ---------------------------------------------------------------- 识图点击


def findClick(findName, filePathList, endswith=".png", mode="rgb", isclick=True,
              clickAll=False, hwnd=None, retHwnd=False, threshold=0.95,
              pyramid=True, preload=True, onlyone=False, feature_fallback=False):
    """
    介绍: 在文件夹中找到包含 findName 且以 endswith 结尾的文件，作为模板
          在屏幕上寻找并点击
    参数:
        findName: 文件名关键词 str
        filePathList: 图片目录或文件路径列表
        endswith: 扩展名 默认 '.png'
        mode: 'gray' 或 'rgb'
        isclick: 是否点击
        clickAll: 是否点击全部匹配
        hwnd: 指定窗口范围（句柄或句柄列表）
        retHwnd: 返回 {(x, y): hwnd}
        threshold: 匹配阈值（透传给 matchTemplate）
        pyramid: 金字塔粗到精加速（透传给 matchTemplate）
        preload: 只截屏一次、缓存模板（N 个模板共享一张大图）
        onlyone: 只找一个模板命中点
        feature_fallback: 模板匹配失败时用 XFeat 特征匹配兜底
                          （抗缩放/旋转/亮度变化）
    返回: 坐标 (x, y) / [(x, y)] / {(x,y): hwnd} / [] 或 {}
    """
    # 延迟导入避免包内循环依赖
    from .vision import matchTemplate, readImage
    from .screen import screenCapture
    from .util import getFile

    if isinstance(hwnd, (list, tuple)):
        pointList, pointDict = [], {}
        for h in hwnd:
            res = findClick(
                findName=findName, filePathList=filePathList, endswith=endswith,
                mode=mode, isclick=isclick, clickAll=clickAll, hwnd=h,
                retHwnd=retHwnd, threshold=threshold, pyramid=pyramid,
                preload=preload, onlyone=onlyone,
                feature_fallback=feature_fallback,
            )
            if isinstance(res, dict):
                pointDict.update(res)
            elif isinstance(res, (list, tuple)):
                pointList += list(res)
            else:
                print("未知的返回类型: %r" % (res,))
        return pointDict if retHwnd else pointList

    if os_is_dir_or_list(filePathList):
        imagePathList = getFile(filePathList)
    else:
        imagePathList = list(filePathList)

    # 预筛候选模板文件
    candidates = [p for p in imagePathList
                  if findName in p and p.endswith(endswith)]
    if not candidates:
        return {} if retHwnd else []

    # 优化：只截一次屏，所有模板共享同一张大图
    src = screenCapture(hwnd=hwnd) if preload else None

    # 优化：模板只读一次（旧版每个模板重读一遍 + 每个模板重截一遍屏）
    templates = [readImage(p) for p in candidates] if preload else None

    pointList, pointDict = [], {}
    for idx, filePath in enumerate(candidates):
        template = templates[idx] if preload else readImage(filePath)
        if template is None:
            continue
        src_now = src if preload else screenCapture(hwnd=hwnd)
        for point in matchTemplate(
            template=template,
            src_rgb=src_now,
            hwnd=hwnd,
            mode=mode,
            threshold=threshold,
            pyramid=pyramid,
            onlyone=onlyone or not clickAll,
            feature_fallback=feature_fallback,
        ):
            if isclick:
                click_point(pos=point, hwnd=hwnd)
            if retHwnd:
                pointDict[point] = hwnd
            else:
                pointList.append(point)
            print("[hwnd:%s] 找到 %s 对应的点 %s" % (hwnd, findName, point))
            if not clickAll:
                # 返回类型与旧版保持一致：单个坐标
                if retHwnd:
                    return {point: hwnd}
                return point
    if retHwnd:
        return pointDict
    return pointList


def os_is_dir_or_list(path):
    import os

    if isinstance(path, (list, tuple)):
        return False
    return os.path.isdir(path)


def click_point(pos, hwnd=None, offset=0, debug=False, isClient=False):
    """
    功能: 点击指定的坐标（默认屏幕坐标；传 hwnd 后台点击）
    参数:
        pos: (x, y)
        hwnd: 窗口句柄
        offset: 随机偏移
        isClient: pos 是否为客户区坐标
    返回: 实际点击坐标
    """
    if not hwnd:
        hwnd = win32gui.WindowFromPoint(pos)
    if offset:
        pos = _jittermove(pos[0], pos[1], offset)
    client_pos = pos if isClient else win32gui.ScreenToClient(hwnd, pos)
    tmp = win32api.MAKELONG(client_pos[0], client_pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, tmp)
    win32gui.SendMessage(
        hwnd, win32con.WM_SETFOCUS, hwnd,
        win32api.MAKELONG(win32con.HTCLIENT, win32con.WM_LBUTTONUP),
    )
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, tmp)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, tmp)
    if debug:
        print("%s click_point: %s" % (win32gui.GetWindowText(hwnd), pos))
    return pos


def click_pointForClient(pos, hwnd=None, offset=0, debug=False):
    """
    功能: 以客户区坐标点击（不动物理鼠标；未传 hwnd 时按屏幕坐标反查窗口）
    参数:
        pos: 客户区坐标 (x, y)（hwnd=None 时视为屏幕坐标）
        hwnd: 窗口句柄
        offset: 随机偏移
    """
    if hwnd is None:
        hwnd = win32gui.WindowFromPoint(pos)
    if offset:
        pos = _jittermove(pos[0], pos[1], offset)
    tmp = win32api.MAKELONG(pos[0], pos[1])
    win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
    win32gui.SendMessage(hwnd, win32con.WM_NCHITTEST, 0, tmp)
    win32gui.SendMessage(
        hwnd, win32con.WM_SETFOCUS, hwnd,
        win32api.MAKELONG(win32con.HTCLIENT, win32con.WM_LBUTTONUP),
    )
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, tmp)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, tmp)
    if debug:
        print("click_point: hwnd:%s title:%s --> pos:%s" %
              (hwnd, win32gui.GetWindowText(hwnd), pos))
    return pos
