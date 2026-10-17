# -*- coding: utf-8 -*-
"""回归测试：全部针对旧 Module.py 已实测确认的 Bug。

运行: cd <项目根目录> && python -m pytest tests -q
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

import smartpy
from conftest import requires_desktop
from smartpy.overlay import Window
from smartpy.mouse import CubicBezier, genLinePointList
from smartpy.vision import matchTemplate


# ---------------------------------------------------------------- 轨迹


def test_bezier_derivative_no_longer_zero():
    """旧版 _delta_bezier_func 恒为 0 -> get_x/get_y 除零。"""
    cb = CubicBezier(c1=(10, 10), c2=(20, 20), end=(100, 100))
    d = cb._delta_bezier_func(0, 0.5, 50)
    assert d != 0 and math.isfinite(d)


def test_bezier_get_y_works():
    cb = CubicBezier(c1=(0, 30), c2=(70, 70), end=(100, 100))
    y = cb.get_y(50)
    assert 0 <= y <= 100


def test_cubic_bezier_gen_endpoints():
    pts = list(smartpy.cubic_bezier_gen((0, 0), (100, 50), 11))
    assert pts[0] == (0, 0)
    assert pts[-1] == (100, 50)


def test_genLinePointList_forward():
    pts = genLinePointList((0, 0), (100, 0))
    assert pts[0] == (0, 0)
    assert pts[-1] == (100, 0)
    # 保持生成顺序（x 单调不减）
    xs = [p[0] for p in pts]
    assert xs == sorted(xs)
    assert len(pts) >= 12


def test_genLinePointList_backward():
    """旧版反向拖拽会飞出终点（实测生成到 (500,300)）。"""
    pts = genLinePointList((300, 300), (100, 300))
    assert pts[0] == (300, 300)
    assert pts[-1] == (100, 300)
    xs = [p[0] for p in pts]
    assert xs == sorted(xs, reverse=True)


def test_genLinePointList_vertical():
    pts = genLinePointList((50, 0), (50, 80))
    assert pts[0] == (50, 0)
    assert pts[-1] == (50, 80)
    for p in pts:
        assert p[0] == 50


# ---------------------------------------------------------------- 位运算优先级


@requires_desktop
def test_getTopWindowExist_precedence_fix():
    """旧版 `a & b == 8` 恒 False。新实现用 Z 序判断，验证返回 bool。"""
    import win32con
    from smartpy._compat import win32gui

    hwnd = win32gui.GetDesktopWindow()
    assert smartpy.getTopWindowExist(hwnd) in (True, False)


# ---------------------------------------------------------------- 屏幕


@requires_desktop
def test_screenCapture_full():
    img = smartpy.screenCapture()
    assert img is not None
    assert img.ndim == 3
    assert img.shape[2] == 4  # BGRA
    assert img.size > 0


@requires_desktop
def test_screenCapture_region_shape():
    img = smartpy.screenCapture(region=(0, 0, 64, 32))
    assert img.shape[0] == 32
    assert img.shape[1] == 64


@requires_desktop
def test_window_capture_no_unboundlocal():
    """旧版 del retA -> UnboundLocalError，必崩。"""
    img = smartpy.window_capture(None)  # 桌面
    assert img is not None
    assert img.ndim == 3


def test_readImage_missing_returns_none(tmp_path):
    assert smartpy.readImage(str(tmp_path / "not_exist.png")) is None


def test_imgReSize_uses_nsize():
    """旧版硬编码 1136/820，nSize 无效。"""
    img = np.zeros((100, 200, 3), np.uint8)   # 高 100 宽 200
    out = smartpy.imgReSize(img, (100, 100))   # 目标 100x100
    assert out.shape[0] == 100                # fy = 100/100 = 1，高不变
    assert out.shape[1] == 100                # fx = 100/200 = 0.5，宽减半


def test_imgReSize_gray():
    img = np.zeros((100, 200), np.uint8)
    out = smartpy.imgReSize(img, (100, 50))
    assert out.shape[0] == 50                 # fy = 50/100 = 0.5
    assert out.shape[1] == 100                # fx = 100/200 = 0.5


# ---------------------------------------------------------------- 识图


def test_matchTemplate_hit_center():
    # 注意：常量模板（无方差）会让 CCOEFF_NORMED 退化恒为 1，必须用有方差的图案
    rng = np.random.default_rng(42)
    tpl = rng.integers(0, 256, (20, 20, 3), dtype=np.uint8)
    src = rng.integers(0, 256, (100, 200, 3), dtype=np.uint8)
    src[50:70, 30:50] = tpl
    pts = matchTemplate(tpl, src, threshold=0.95, onlyone=True, midpoint=True)
    assert len(pts) == 1
    x, y = pts[0]
    assert abs(x - 40) <= 1
    assert abs(y - 60) <= 1


def test_matchTemplate_pyramid_equals_brute():
    """金字塔粗到精必须与全分辨率暴力法给出相同坐标。"""
    rng = np.random.default_rng(123)
    tpl = rng.integers(0, 256, (60, 60, 3), dtype=np.uint8)
    src = rng.integers(0, 256, (600, 1000, 3), dtype=np.uint8)
    src[320:380, 480:540] = tpl
    brute = matchTemplate(tpl, src, threshold=0.9, onlyone=True,
                          midpoint=True, pyramid=False)
    fast = matchTemplate(tpl, src, threshold=0.9, onlyone=True,
                         midpoint=True, pyramid=True)
    assert brute and fast
    assert abs(brute[0][0] - fast[0][0]) <= 2
    assert abs(brute[0][1] - fast[0][1]) <= 2


def test_matchTemplate_small_tpl_pyramid_fallback():
    """小模板（缩略后 <12px）金字塔应退化为全分辨率，不能漏检。"""
    rng = np.random.default_rng(7)
    tpl = rng.integers(0, 256, (20, 20, 3), dtype=np.uint8)
    src = rng.integers(0, 256, (100, 200, 3), dtype=np.uint8)
    src[50:70, 30:50] = tpl
    pts = matchTemplate(tpl, src, threshold=0.95, onlyone=True,
                        midpoint=True, pyramid=True)
    assert len(pts) == 1


def test_matchTemplate_multi_dedup():
    """多目标：NMS + 距离去重，两个分离目标各命中一次。"""
    rng = np.random.default_rng(9)
    tpl = rng.integers(0, 256, (30, 30, 3), dtype=np.uint8)
    src = rng.integers(0, 256, (200, 300, 3), dtype=np.uint8)
    src[40:70, 40:70] = tpl
    src[120:150, 200:230] = tpl
    pts = matchTemplate(tpl, src, threshold=0.9, midpoint=True,
                        duplicateRemoval=20)
    assert 2 <= len(pts) <= 4  # 目标周围像素也可能成峰，去重后应接近 2
    # 两个目标点都应在结果里
    found_a = any(abs(x - 55) <= 3 and abs(y - 55) <= 3 for x, y in pts)
    found_b = any(abs(x - 215) <= 3 and abs(y - 135) <= 3 for x, y in pts)
    assert found_a and found_b


def test_matchTemplate_sqdiff_direction():
    """旧版 SQDIFF 也用 >= threshold，永远不命中。"""
    rng = np.random.default_rng(7)
    tpl = rng.integers(0, 256, (20, 20, 3), dtype=np.uint8)
    src = rng.integers(0, 256, (80, 80, 3), dtype=np.uint8)
    src[20:40, 20:40] = tpl
    pts = matchTemplate(tpl, src, threshold=0.05, method=5, onlyone=True)
    assert len(pts) == 1


def test_matchTemplate_returns_list_not_tuple():
    # 模板大于大图 -> 返回空列表（不崩溃）
    big_tpl = np.full((20, 20, 3), 128, np.uint8)
    small_src = np.full((10, 10, 3), 128, np.uint8)
    assert matchTemplate(big_tpl, small_src) == []


def test_MatchTemplate_show_false_no_nameerror():
    """旧版 show=False 时 del vis -> UnboundLocalError。"""
    src = np.zeros((200, 200, 3), np.uint8)
    cv = __import__("cv2")
    src[40:80, 40:80] = 255
    tpl = np.full((40, 40, 3), 255, np.uint8)
    pts = smartpy.MatchTemplate(src, tpl, mode="sift", threshold=0.5, show=False)
    assert isinstance(pts, list)


# ---------------------------------------------------------------- 键鼠逻辑（不真实点击）


def test_click_it_requires_coords():
    with pytest.raises(TypeError):
        smartpy.click_it()


def test_click_it_unknown_button():
    with pytest.raises(ValueError):
        smartpy.click_it(x=10, y=10, button="middle")


def test_mouseDown_uses_pos():
    """旧版引用未定义 startPoint。验证函数签名与参数绑定即可（不真发消息）。"""
    import inspect
    sig = inspect.signature(smartpy.mouseDown)
    assert list(sig.parameters) == ["hwnd", "pos"]


def test_SendMessage_signature():
    import inspect
    sig = inspect.signature(smartpy.SendMessage)
    assert list(sig.parameters) == ["hwnd", "Param1", "Param2", "Param3"]


# ---------------------------------------------------------------- 窗口（只读操作）


@requires_desktop
def test_findWindow_desktop_default():
    from smartpy._compat import win32gui
    hwnd = smartpy.findWindow()
    assert hwnd == win32gui.GetDesktopWindow()


@requires_desktop
def test_enumWindows_returns_list():
    infos = smartpy.enumWindows()
    assert isinstance(infos, list)
    assert all(set(d) >= {"className", "windowTitle", "hwnd"} for d in infos)


@requires_desktop
def test_getWindowRect_desktop():
    rect = smartpy.getWindowRect(hwnd=smartpy.findWindow())
    assert len(rect) == 4
    assert rect[2] > rect[0] and rect[3] > rect[1]


def test_setWindowState_bad_state():
    with pytest.raises(ValueError):
        smartpy.setWindowState(hwnd=smartpy.findWindow(), state=9)


# ---------------------------------------------------------------- 工具 / 输出


def test_prints_emoji_no_unicodeerror(capsys):
    smartpy.prints("测试 😀 输出", width=30, fillchar="=")
    out = capsys.readouterr().out
    assert "测试 😀 输出" in out


def test_printf_cn_align(capsys):
    smartpy.printf("中文", width=20, pre="|", end="|", debug=True)
    assert capsys.readouterr().out


def test_getFile_returns_sorted_list(tmp_path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    files = smartpy.getFile(str(tmp_path))
    assert isinstance(files, list)
    assert [os.path.basename(f) for f in files] == ["a.txt", "b.txt"]


def test_matchFile_list():
    paths = ["x/a1.png", "y/b2.png", "z/a2.png"]
    assert smartpy.matchFile("b2", paths) == "y/b2.png"
    assert smartpy.matchFile(["a1", "a2"], paths) == ["x/a1.png", "z/a2.png"]


# ---------------------------------------------------------------- 遮罩窗（全生命周期）


@requires_desktop
def test_overlay_window_lifecycle():
    import time
    from smartpy._compat import win32con, win32gui

    win = Window(className="AutopyTestWnd", windowTitle="smartpy-test-overlay",
                 windowWidth=320, windowHeight=240, isDaemon=True)
    win.start()
    try:
        deadline = time.time() + 5
        while time.time() < deadline and win.hwnd is None:
            time.sleep(0.05)
        assert win.hwnd is not None
        assert win32gui.IsWindow(win.hwnd)
        # 扩展样式检查：分层 + 穿透 + 不进任务栏 + 置顶
        # （ShowWindow 之后再 SetWindowPos(HWND_TOPMOST) 会写入 WS_EX_TOPMOST 位）
        exstyle = win32gui.GetWindowLong(win.hwnd, win32con.GWL_EXSTYLE)
        assert exstyle & win32con.WS_EX_LAYERED
        assert exstyle & win32con.WS_EX_TRANSPARENT
        assert exstyle & win32con.WS_EX_TOOLWINDOW
        assert exstyle & win32con.WS_EX_TOPMOST
    finally:
        win.close()
        time.sleep(0.3)
