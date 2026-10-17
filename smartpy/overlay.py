# -*- coding: utf-8 -*-
"""smartpy.overlay —— 置顶透明鼠标穿透遮罩窗（Window 类重构版）。

相对旧 Module.py 的修复：
- 旧版 `self._setBGColor(hwnd, hdc, ps)` 少传 bgColor、`self.__draw(hwnd, hdc)`
  调用签名不匹配 → WM_PAINT 一进就 TypeError，窗口画不出来。
  现统一为 `__draw(hdc)`，wndProc 只负责 BeginPaint/EndPaint。
- 旧版把 GWL_STYLE 与 GWL_EXSTYLE 设置成同一个混合值，样式位错乱；
  现在 style（WS_*）与 exstyle（WS_EX_*）分开设置。
- 透明色默认值 rgb(255,255,251) 只是「接近白」——底色先统一填满
  TransparentColor 再绘制，保证 colorkey 透明生效。
- 增加 start() / close() / is_alive 生命周期 API；线程默认非守护，
  由 close() 发 WM_CLOSE 让消息循环退出。
- 绘制函数族 _drawText/_drawRectangle/_drawEllipse/_drawLine 为类方法，
  不再有游离在类外引用 self.debug 的副本。
"""

import threading

from ._compat import win32api, win32con, win32gui

__all__ = ["Window", "mydraw"]


def mydraw(hwnd, hdc):
    """
    绘画函数（兼容旧版模块级 mydraw）：所有绘画操作都写在这里。
    旧版直接调用类外的 _drawText/_drawRectangle（它们内部引用 self.debug 必崩），
    这里改为调用 _drawText / _drawRectangle 的模块级纯函数版本。
    """
    bgColor = win32api.RGB(0, 251, 0)
    textColor = win32api.RGB(255, 0, 0)
    windowHeight = 1080
    x, y, w, h = 0, int(windowHeight / 2) - 100, 100, 100
    rect = (x, y, x + w, y + h)
    _drawRectangle(hdc, rect, textColor, bgColor, rType=0)
    _drawText(hdc, "实心矩形", rect, textColor, bgColor)
    x += 200
    rect = (x, y, x + w, y + h)
    _drawRectangle(hdc, rect, textColor, bgColor, rType=1)
    _drawText(hdc, "空心矩形", rect, textColor, bgColor)
    x += 200
    rect = (x, y, x + w, y + h)
    _drawRectangle(hdc, rect, textColor, bgColor, rType=2)
    _drawText(hdc, "自定义矩形", rect, textColor, bgColor)
    x += 200
    rect = (x, y, x + w, y + h)
    _drawEllipse(hdc, rect, textColor, bgColor, rType=0)
    _drawText(hdc, "实心圆", rect, textColor, bgColor)
    x += 200
    rect = (x, y, x + w, y + h)
    _drawEllipse(hdc, rect, textColor, bgColor, rType=1)
    _drawText(hdc, "空心椭圆", rect, textColor, bgColor)
    x += 200
    rect = (x, y, x + w, y + h)
    _drawText(hdc, "测试文本", rect, textColor, bgColor)


def _drawText(hdc, text, rect=(0, 0, 20, 20),
              textColor=win32api.RGB(0, 0, 255),
              bgColor=win32api.RGB(255, 255, 255)):
    """模块级绘制文本（旧版此处引用 self.debug 必崩，已修复为纯函数）。"""
    win32gui.SetTextColor(hdc, textColor)
    win32gui.SetBkColor(hdc, bgColor)
    win32gui.DrawText(
        hdc, text, len(text), rect,
        win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER,
    )


def _drawRectangle(hdc, rect, penColor=win32api.RGB(0, 0, 255),
                   bgColor=win32api.RGB(0, 255, 0), rType=0):
    """模块级绘制矩形（旧版结尾引用 self.debug 必崩，已修复为纯函数）。"""
    hPen = win32gui.CreatePen(win32con.PS_SOLID, 2, penColor)
    prePen = win32gui.SelectObject(hdc, hPen)
    try:
        if rType == 0:
            hbrush = win32gui.CreateSolidBrush(bgColor)
        else:
            hbrush = win32gui.GetStockObject(win32con.NULL_BRUSH)
        prebrush = win32gui.SelectObject(hdc, hbrush)
        try:
            if rType == 2:
                x, y, x2, y2 = rect
                w, h = x2 - x, y2 - y
                win32gui.MoveToEx(hdc, x, y)
                win32gui.LineTo(hdc, x + round(w / 3), y)
                win32gui.MoveToEx(hdc, x, y)
                win32gui.LineTo(hdc, x, y + round(h / 3))
                win32gui.MoveToEx(hdc, x + w, y)
                win32gui.LineTo(hdc, x + w - round(w / 3), y)
                win32gui.MoveToEx(hdc, x + w, y)
                win32gui.LineTo(hdc, x + w, y + round(h / 3))
                win32gui.MoveToEx(hdc, x, y + h)
                win32gui.LineTo(hdc, x + round(w / 3), y + h)
                win32gui.MoveToEx(hdc, x, y + h)
                win32gui.LineTo(hdc, x, y + h - round(h / 3))
                win32gui.MoveToEx(hdc, x + w, y + h)
                win32gui.LineTo(hdc, x + w - round(w / 3), y + h)
                win32gui.MoveToEx(hdc, x + w, y + h)
                win32gui.LineTo(hdc, x + w, y + h - round(h / 3))
            else:
                win32gui.Rectangle(hdc, rect[0], rect[1], rect[2], rect[3])
        finally:
            win32gui.SelectObject(hdc, prebrush)
            win32gui.DeleteObject(hbrush)
    finally:
        win32gui.SelectObject(hdc, prePen)
        win32gui.DeleteObject(hPen)


def _drawEllipse(hdc, rect, penColor=win32api.RGB(0, 0, 255),
                 bgColor=win32api.RGB(0, 255, 0), rType=0):
    """模块级绘制椭圆（旧版结尾引用 self.debug 必崩，已修复为纯函数）。"""
    hPen = win32gui.CreatePen(win32con.PS_SOLID, 2, penColor)
    prePen = win32gui.SelectObject(hdc, hPen)
    try:
        if rType == 0:
            hbrush = win32gui.CreateSolidBrush(bgColor)
        else:
            hbrush = win32gui.GetStockObject(win32con.NULL_BRUSH)
        prebrush = win32gui.SelectObject(hdc, hbrush)
        try:
            win32gui.Ellipse(hdc, rect[0], rect[1], rect[2], rect[3])
        finally:
            win32gui.SelectObject(hdc, prebrush)
            win32gui.DeleteObject(hbrush)
    finally:
        win32gui.SelectObject(hdc, prePen)
        win32gui.DeleteObject(hPen)


class Window:
    """
    置顶、无标题栏、透明、鼠标穿透的遮罩窗口。

    参数：
        className / windowTitle: 类名与标题
        windowX / windowY / windowWidth / windowHeight: 位置尺寸
        bgColor: 背景色
        TransparentColor: 透明色（colorkey）
        Alpha: 整体透明度 [0, 255]
        isDaemon: 线程是否守护
        debug: 调试输出
    用法：
        win = Window(...)
        win.start()          # 启动消息循环线程
        win.close()          # 关闭窗口
    """

    def __init__(
        self,
        className="TranPy",
        windowTitle="TranPy",
        windowX=0,
        windowY=0,
        windowWidth=None,
        windowHeight=None,
        cxClient=None,
        cyClient=None,
        bgColor=win32api.RGB(255, 255, 251),
        TransparentColor=win32api.RGB(255, 255, 251),
        Alpha=220,
        isDaemon=False,
        debug=False,
    ):
        self.className = className
        self.windowTitle = windowTitle
        self.windowX = windowX
        self.windowY = windowY
        self.windowWidth = windowWidth or win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.windowHeight = windowHeight or win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        self.cxClient = cxClient or self.windowWidth
        self.cyClient = cyClient or self.windowHeight
        self.bgColor = bgColor
        self.TransparentColor = TransparentColor
        self.Alpha = Alpha
        self.isDaemon = isDaemon
        self.debug = debug
        self.hwnd = None
        self._win = threading.Thread(
            target=self._winMain, name="%s_Thread" % self.className
        )
        self._win.daemon = self.isDaemon

    # ------------------------------------------------------------ 生命周期

    def start(self):
        """启动窗口线程"""
        if not self._win.is_alive():
            self._win.start()
        return self

    def close(self):
        """关闭窗口"""
        if self.hwnd:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass

    @property
    def is_alive(self):
        return self._win.is_alive()

    # ------------------------------------------------------------ 窗口过程

    def _wndProc(self, hwnd, uMsg, wParam, lParam):
        if uMsg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            try:
                # 1) 整窗填 TransparentColor（colorkey 透明的关键）
                self._setBGColor(hwnd, hdc, self.TransparentColor)
                # 2) 用户绘制回调
                self._draw(hdc)
            finally:
                win32gui.EndPaint(hwnd, ps)
            return 0
        if uMsg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, uMsg, wParam, lParam)

    def _winMain(self):
        wc = win32gui.WNDCLASS()
        wc.hbrBackground = win32con.COLOR_BTNFACE + 1
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.lpszClassName = self.className
        wc.lpfnWndProc = self._wndProc
        reg = win32gui.RegisterClass(wc)

        style = win32con.WS_POPUP
        hwnd = win32gui.CreateWindow(
            reg, self.windowTitle, style,
            self.windowX, self.windowY,
            self.windowWidth, self.windowHeight,
            0, 0, 0, None,
        )
        self.hwnd = hwnd

        # 扩展样式：分层 + 鼠标穿透 + 不进任务栏
        # （WS_EX_TOPMOST 不能靠 SetWindowLong 写入，系统会清掉 0x8 位，
        #   必须用 SetWindowPos(HWND_TOPMOST) 设置）
        exstyle = (
            win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOOLWINDOW
        )
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)

        # 分层窗口属性：TransparentColor 全透明，其余按 Alpha
        win32gui.SetLayeredWindowAttributes(
            hwnd, self.TransparentColor, self.Alpha,
            win32con.LWA_ALPHA | win32con.LWA_COLORKEY,
        )

        # 置顶：必须 ShowWindow 之后再 SetWindowPos 才会写入 WS_EX_TOPMOST
        # （窗口未显示时调用不生效，GWL_EXSTYLE 的 0x8 位也不会置上）
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
        win32gui.UpdateWindow(hwnd)
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )
        win32gui.PumpMessages()
        self.hwnd = None

    # ------------------------------------------------------------ 绘制基础

    def _draw(self, hdc):
        """子类重写此方法执行绘制（默认不画任何东西）"""

    def _setBGColor(self, hwnd, hdc, bgColor, rect=(None, None, None, None)):
        """在 rect（默认全窗）填充 bgColor"""
        x = rect[0] if rect[0] is not None else 0
        y = rect[1] if rect[1] is not None else 0
        w = rect[2] if rect[2] is not None else self.cxClient
        h = rect[3] if rect[3] is not None else self.cyClient
        hb = win32gui.CreateSolidBrush(bgColor)
        pre = win32gui.SelectObject(hdc, hb)
        try:
            win32gui.PatBlt(hdc, x, y, w, h, win32con.PATCOPY)
        finally:
            win32gui.SelectObject(hdc, pre)
            win32gui.DeleteObject(hb)

    def _getRGB(self, r, g, b):
        return win32api.RGB(r, g, b)

    def _setTrans(self, hwnd=None, TransparentColor=None, Alpha=None):
        if not self.hwnd:
            self.hwnd = win32gui.FindWindow(self.className, self.windowTitle)
        if hwnd is None:
            hwnd = self.hwnd
        color = TransparentColor if TransparentColor is not None else self.TransparentColor
        alpha = Alpha if Alpha is not None else self.Alpha
        win32gui.SetLayeredWindowAttributes(
            hwnd, color, alpha, win32con.LWA_ALPHA | win32con.LWA_COLORKEY
        )

    def _getHDC(self, hwnd=None):
        if hwnd is None and not self.hwnd:
            hwnd = win32gui.FindWindow(self.className, self.windowTitle)
        elif hwnd is None:
            hwnd = self.hwnd
        self.hdc = win32gui.GetDC(hwnd)
        return self.hdc

    def _releaseHDC(self, hwnd, hdc):
        win32gui.ReleaseDC(hwnd, hdc)

    # ------------------------------------------------------------ 绘制 API

    def _drawText(self, hdc, text, rect=(0, 0, 20, 20),
                  textColor=win32api.RGB(0, 0, 255),
                  bgColor=win32api.RGB(255, 255, 255), debug=False):
        win32gui.SetTextColor(hdc, textColor)
        win32gui.SetBkColor(hdc, bgColor)
        flags = win32gui.DrawText(
            hdc, text, len(text), rect,
            win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER,
        )
        if debug:
            print("绘制文本成功", flags, rect)

    def _moveTo(self, hdc, x, y):
        win32gui.MoveToEx(hdc, x, y)

    def _drawLine(self, hdc, start, end,
                  textColor=win32api.RGB(0, 0, 255),
                  bgColor=win32api.RGB(255, 255, 255), debug=False):
        win32gui.SetTextColor(hdc, textColor)
        win32gui.SetBkColor(hdc, bgColor)
        win32gui.MoveToEx(hdc, start[0], start[1])
        flags = win32gui.LineTo(hdc, end[0], end[1])
        if debug:
            print("绘制线段成功", flags, start, end)

    def _drawRectangle(self, hdc, rect, penColor=win32api.RGB(0, 0, 255),
                       bgColor=win32api.RGB(0, 255, 0), rType=0, debug=False):
        """
        rect = (left, top, right, bottom)
        rType: 0 实心 / 1 空心 / 2 圆角自定义
        """
        hPen = win32gui.CreatePen(win32con.PS_SOLID, 2, penColor)
        prePen = win32gui.SelectObject(hdc, hPen)
        try:
            if rType == 0:
                hbrush = win32gui.CreateSolidBrush(bgColor)
                prebrush = win32gui.SelectObject(hdc, hbrush)
                try:
                    win32gui.Rectangle(hdc, rect[0], rect[1], rect[2], rect[3])
                finally:
                    win32gui.SelectObject(hdc, prebrush)
                    win32gui.DeleteObject(hbrush)
            elif rType == 1:
                hbrush = win32gui.GetStockObject(win32con.NULL_BRUSH)
                prebrush = win32gui.SelectObject(hdc, hbrush)
                try:
                    win32gui.Rectangle(hdc, rect[0], rect[1], rect[2], rect[3])
                finally:
                    win32gui.SelectObject(hdc, prebrush)
            else:
                self._drawRoundedCorners(hdc, rect)
        finally:
            win32gui.SelectObject(hdc, prePen)
            win32gui.DeleteObject(hPen)
        if debug:
            print("绘制矩形成功", rect)

    def _drawRoundedCorners(self, hdc, rect):
        x, y, x2, y2 = rect
        w, h = x2 - x, y2 - y
        win32gui.MoveToEx(hdc, x, y)
        win32gui.LineTo(hdc, x + round(w / 3), y)
        win32gui.MoveToEx(hdc, x, y)
        win32gui.LineTo(hdc, x, y + round(h / 3))
        win32gui.MoveToEx(hdc, x + w, y)
        win32gui.LineTo(hdc, x + w - round(w / 3), y)
        win32gui.MoveToEx(hdc, x + w, y)
        win32gui.LineTo(hdc, x + w, y + round(h / 3))
        win32gui.MoveToEx(hdc, x, y + h)
        win32gui.LineTo(hdc, x + round(w / 3), y + h)
        win32gui.MoveToEx(hdc, x, y + h)
        win32gui.LineTo(hdc, x, y + h - round(h / 3))
        win32gui.MoveToEx(hdc, x + w, y + h)
        win32gui.LineTo(hdc, x + w - round(w / 3), y + h)
        win32gui.MoveToEx(hdc, x + w, y + h)
        win32gui.LineTo(hdc, x + w, y + h - round(h / 3))

    def _drawEllipse(self, hdc, rect, penColor=win32api.RGB(0, 0, 255),
                     bgColor=win32api.RGB(0, 255, 0), rType=0, debug=False):
        hPen = win32gui.CreatePen(win32con.PS_SOLID, 2, penColor)
        prePen = win32gui.SelectObject(hdc, hPen)
        try:
            if rType == 0:
                hbrush = win32gui.CreateSolidBrush(bgColor)
                prebrush = win32gui.SelectObject(hdc, hbrush)
                try:
                    win32gui.Ellipse(hdc, rect[0], rect[1], rect[2], rect[3])
                finally:
                    win32gui.SelectObject(hdc, prebrush)
                    win32gui.DeleteObject(hbrush)
            else:
                hbrush = win32gui.GetStockObject(win32con.NULL_BRUSH)
                prebrush = win32gui.SelectObject(hdc, hbrush)
                try:
                    win32gui.Ellipse(hdc, rect[0], rect[1], rect[2], rect[3])
                finally:
                    win32gui.SelectObject(hdc, prebrush)
        finally:
            win32gui.SelectObject(hdc, prePen)
            win32gui.DeleteObject(hPen)
        if debug:
            print("绘制椭圆成功", rect)
