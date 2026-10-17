# -*- coding: utf-8 -*-
"""图色识别（smartpy.color）回归测试。

全部用内存构造图验证，不依赖屏幕内容，可重复。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

import smartpy


def make_img(w=200, h=100):
    """黑底 + 红色块(40,30)-(80,50) + 绿色点(150,80)"""
    img = np.zeros((h, w, 3), np.uint8)
    img[30:50, 40:80] = (0, 0, 255)      # BGR 纯红
    img[80, 150] = (0, 255, 0)           # BGR 纯绿
    return img


# ---------------------------------------------------------------- 颜色换算


def test_rgb_bgr_roundtrip():
    assert smartpy.rgb_to_bgr(0xFF0000) == (0, 0, 255)
    assert smartpy.bgr_to_rgb(0, 0, 255) == 0xFF0000
    assert smartpy.bgr_to_rgb(*smartpy.rgb_to_bgr(0x123456)) == 0x123456


def test_hex_to_bgr_formats():
    assert smartpy.hex_to_bgr(0xFF0000) == (0, 0, 255)
    assert smartpy.hex_to_bgr("#FF0000") == (0, 0, 255)
    assert smartpy.hex_to_bgr("FF0000") == (0, 0, 255)
    assert smartpy.hex_to_bgr((255, 0, 0)) == (0, 0, 255)


def test_bgr_to_hex():
    assert smartpy.bgr_to_hex((0, 0, 255)) == 0xFF0000
    assert smartpy.bgr_to_hex((255, 0, 0)) == 0x0000FF


# ---------------------------------------------------------------- 取色 / 比色


def test_getColorAt():
    img = make_img()
    assert smartpy.getColorAt(img, 60, 40) == 0xFF0000
    assert smartpy.getColorAt(img, 150, 80) == 0x00FF00
    assert smartpy.getColorAt(img, 0, 0) == 0x000000


def test_getColorAt_out_of_range():
    img = make_img()
    assert smartpy.getColorAt(img, -1, 0) is None
    assert smartpy.getColorAt(img, 999, 0) is None
    assert smartpy.getColorAt(None, 0, 0) is None


def test_compareColorEx_exact():
    assert smartpy.compareColorEx(0xFF0000, 0xFF0000, 0) is True
    assert smartpy.compareColorEx(0xFE0000, 0xFF0000, 0) is False


def test_compareColorEx_tolerance():
    assert smartpy.compareColorEx(0xFE0100, 0xFF0000, 0) is False
    assert smartpy.compareColorEx(0xFE0100, 0xFF0000, 3) is True
    assert smartpy.compareColorEx(0xF00000, 0xFF0000, 10) is False


# ---------------------------------------------------------------- 找色


def test_findColor_returns_first_point():
    img = make_img()
    pt = smartpy.findColor(0xFF0000, img=img)
    assert pt is not None
    assert pt == (40, 30)


def test_findColor_not_found():
    img = make_img()
    assert smartpy.findColor(0x123456, img=img) is None


def test_findColor_with_tolerance():
    img = make_img()
    noisy = img.copy()
    noisy[30:50, 40:80] = (5, 5, 250)
    assert smartpy.findColor(0xFF0000, img=noisy, sim=10) is not None


def test_findColorEx_all_points():
    img = make_img()
    pts = smartpy.findColorEx(0xFF0000, img=img)
    assert len(pts) == 40 * 20      # 红色块 800 像素
    assert (40, 30) in pts
    assert (79, 49) in pts


def test_findColorEx_limit():
    img = make_img()
    pts = smartpy.findColorEx(0xFF0000, img=img, limit=5)
    assert len(pts) == 5


def test_countColor():
    img = make_img()
    assert smartpy.countColor(0xFF0000, img=img) == 800
    assert smartpy.countColor(0x00FF00, img=img) == 1
    assert smartpy.countColor(0x123456, img=img) == 0


# ---------------------------------------------------------------- 色块


def test_findColorBlock():
    img = make_img()
    blocks = smartpy.findColorBlock(0xFF0000, img=img, min_area=10)
    assert len(blocks) == 1
    b = blocks[0]
    assert b["x"] == 40 and b["y"] == 30
    assert b["w"] == 40 and b["h"] == 20
    assert b["area"] == 800
    assert abs(b["cx"] - 59) <= 1 and abs(b["cy"] - 39) <= 1


def test_findColorBlock_min_area_filter():
    img = make_img()
    blocks = smartpy.findColorBlock(0x00FF00, img=img, min_area=10)
    assert blocks == []
    blocks2 = smartpy.findColorBlock(0x00FF00, img=img, min_area=1)
    assert len(blocks2) == 1


def test_findColorBlock_sorted_by_area():
    img = make_img()
    img[60:80, 100:140] = (0, 0, 255)
    img[5:8, 5:10] = (0, 0, 255)
    blocks = smartpy.findColorBlock(0xFF0000, img=img, min_area=1)
    areas = [b["area"] for b in blocks]
    assert areas == sorted(areas, reverse=True)


# ---------------------------------------------------------------- 多点找色


def test_findMultiColor_hit():
    img = make_img()
    offsets = [((10, 0), 0xFF0000), ((0, 5), 0xFF0000)]
    pt = smartpy.findMultiColor(0xFF0000, offsets, img=img)
    assert pt is not None
    assert pt[0] == 40


def test_findMultiColor_anchor_offset():
    """带偏移锚点：只有满足「主色+偏移色」的位置才算命中。"""
    img = np.zeros((60, 60, 3), np.uint8)
    img[10, 10] = (0, 0, 255)
    img[10, 20] = (0, 255, 0)
    img[40, 40] = (0, 0, 255)

    pt = smartpy.findMultiColor(0xFF0000, [((10, 0), 0x00FF00)], img=img)
    assert pt == (10, 10), "应命中 L 形锚点，而不是孤立红点"


def test_findMultiColor_no_match():
    img = make_img()
    offsets = [((10, 0), 0x0000FF)]
    assert smartpy.findMultiColor(0xFF0000, offsets, img=img) is None


def test_findMultiColor_offset_formats():
    img = make_img()
    a = smartpy.findMultiColor(0xFF0000, [((10, 0), 0xFF0000)], img=img)
    b = smartpy.findMultiColor(0xFF0000, [(10, 0, 0xFF0000)], img=img)
    assert a == b


def test_findMultiColorEx_all():
    img = make_img()
    img[70:80, 100:140] = (0, 0, 255)
    pts = smartpy.findMultiColorEx(0xFF0000, [((5, 0), 0xFF0000)], img=img)
    assert len(pts) > 0
    assert all(isinstance(p, tuple) and len(p) == 2 for p in pts)


def test_findMultiColor_tolerance():
    img = make_img()
    img[30:50, 40:80] = (6, 4, 251)
    assert smartpy.findMultiColor(0xFF0000, [((10, 0), 0xFF0000)], img=img, sim=0) is None
    assert smartpy.findMultiColor(0xFF0000, [((10, 0), 0xFF0000)], img=img, sim=10) is not None


# ---------------------------------------------------------------- 边界


def test_empty_and_invalid_inputs():
    assert smartpy.findColor(0xFF0000, img=None) is None
    assert smartpy.findColorEx(0xFF0000, img=None) == []
    assert smartpy.findColorBlock(0xFF0000, img=None) == []
    assert smartpy.countColor(0xFF0000, img=None) == 0
    assert smartpy.getColorAt(np.zeros((0, 0, 3), np.uint8), 0, 0) is None


def test_bgra_input_supported():
    img = make_img()
    bgra = np.dstack([img, np.full((100, 200, 1), 255, np.uint8)])
    assert smartpy.getColorAt(bgra, 60, 40) == 0xFF0000
    assert smartpy.findColor(0xFF0000, img=bgra) == (40, 30)


def test_gray_input_supported():
    gray = np.zeros((50, 50), np.uint8)
    gray[10:20, 10:20] = 255
    pt = smartpy.findColor(0xFFFFFF, img=gray)
    assert pt == (10, 10)


def test_region_semantics():
    """坐标原点语义：img 模式下返回图内坐标。"""
    img = np.zeros((200, 400, 3), np.uint8)
    img[100:120, 300:340] = (0, 0, 255)
    assert smartpy.findColor(0xFF0000, img=img) == (300, 100)


# ---------------------------------------------------------------- 快照


def test_snapshot_cache_basic():
    """snapshot 后 getPixel / findColor 应复用同一帧。"""
    try:
        img = smartpy.snapshot()
        if img is None:
            pytest.skip("截图不可用")
        c1 = smartpy.getPixel(100, 100)
        c2 = smartpy.getPixel(100, 100)
        assert c1 is not None and c1 == c2
        # findColor 也应能走快照（不抛异常）
        smartpy.findColor(c1)
        smartpy.countColor(c1)
    finally:
        smartpy.clearSnapshot()


def test_snapshot_is_fast():
    """快照后取色应远快于每次截图。"""
    import time

    try:
        if smartpy.snapshot() is None:
            pytest.skip("截图不可用")
        t0 = time.perf_counter()
        for _ in range(2000):
            smartpy.getPixel(100, 100)
        dt = time.perf_counter() - t0
        assert dt < 0.5, "快照取色 2000 次应 < 0.5s，实际 %.3fs" % dt
    finally:
        smartpy.clearSnapshot()


def test_clear_snapshot():
    smartpy.snapshot()
    smartpy.clearSnapshot()
    # 清理后仍能正常工作（会重新截图）
    v = smartpy.getPixel(100, 100)
    assert v is None or isinstance(v, int)


# ---------------------------------------------------------------- 颜色范围


def test_findColorRange_hit():
    """深红到浅红区间，应命中纯红块。"""
    img = make_img()
    pt = smartpy.findColorRange(0x800000, 0xFF4040, img=img)
    assert pt == (40, 30)


def test_findColorRange_order_agnostic():
    """low/high 顺序颠倒也应正常（内部取 min/max）。"""
    img = make_img()
    a = smartpy.findColorRange(0x800000, 0xFF4040, img=img)
    b = smartpy.findColorRange(0xFF4040, 0x800000, img=img)
    assert a == b == (40, 30)


def test_findColorRange_miss():
    """蓝色区间不应命中红块。"""
    img = make_img()
    assert smartpy.findColorRange(0x000080, 0x0000FF, img=img) is None


def test_findColorRange_all_points():
    img = make_img()
    pts = smartpy.findColorRange(0x800000, 0xFF4040, img=img, all_points=True)
    assert len(pts) == 800
    assert (40, 30) in pts


def test_findColorRange_limit():
    img = make_img()
    pts = smartpy.findColorRange(0x800000, 0xFF4040, img=img,
                                all_points=True, limit=10)
    assert len(pts) == 10


def test_countColorRange():
    img = make_img()
    assert smartpy.countColorRange(0x800000, 0xFF4040, img=img) == 800
    assert smartpy.countColorRange(0x000080, 0x0000FF, img=img) == 0


def test_findColorRange_covers_gradient():
    """渐变场景：范围找色应能覆盖出精确找色找不到的像素。"""
    img = np.zeros((40, 100, 3), np.uint8)
    for i in range(100):
        # 红色从 0x80 渐变到 0xFF
        v = 0x80 + int(0x7F * i / 99)
        img[:, i] = (0, 0, v)
    # 精确找纯红只在最后一列
    exact = smartpy.findColor(0xFF0000, img=img)
    assert exact is not None and exact[0] == 99
    # 范围找色第一列就命中
    rng = smartpy.findColorRange(0x800000, 0xFF0000, img=img)
    assert rng is not None and rng[0] == 0


# ---------------------------------------------------------------- 等待


def test_waitColor_timeout_zero_hit(monkeypatch):
    """timeout=0 时若已存在应立即返回。"""
    img = make_img()
    target = smartpy.getColorAt(img, 60, 40)
    # 用 img 模式模拟：把 findColor 打桩成直接命中
    monkeypatch.setattr(smartpy.color, "findColor",
                        lambda *a, **k: (60, 40))
    assert smartpy.waitColor(target, timeout=0) == (60, 40)


def test_waitColor_timeout_returns_none(monkeypatch):
    """一直不命中时，超时应返回 None 且耗时接近 timeout。"""
    import time

    monkeypatch.setattr(smartpy.color, "findColor", lambda *a, **k: None)
    t0 = time.monotonic()
    r = smartpy.waitColor(0xFF0000, timeout=0.3, interval=0.05)
    elapsed = time.monotonic() - t0
    assert r is None
    assert 0.25 <= elapsed <= 1.0, "耗时 %.2fs 不符合 timeout=0.3" % elapsed


def test_waitColor_eventually_hits(monkeypatch):
    """前几次不命中，之后命中，应返回坐标。"""
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return (7, 8) if calls["n"] >= 3 else None

    monkeypatch.setattr(smartpy.color, "findColor", fake)
    assert smartpy.waitColor(0xFF0000, timeout=2.0, interval=0.01) == (7, 8)
    assert calls["n"] >= 3


def test_waitColorDisappear(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return None if calls["n"] >= 2 else (1, 1)

    monkeypatch.setattr(smartpy.color, "findColor", fake)
    assert smartpy.waitColorDisappear(0xFF0000, timeout=2.0, interval=0.01) is True


def test_waitColorDisappear_timeout(monkeypatch):
    monkeypatch.setattr(smartpy.color, "findColor", lambda *a, **k: (1, 1))
    assert smartpy.waitColorDisappear(0xFF0000, timeout=0.2, interval=0.02) is False


def test_waitColorChange(monkeypatch):
    vals = iter([0xFF0000, 0xFF0000, 0x00FF00])

    def fake_pixel(*a, **k):
        try:
            return next(vals)
        except StopIteration:
            return 0x00FF00

    monkeypatch.setattr(smartpy.color, "getPixel", fake_pixel)
    assert smartpy.waitColorChange(10, 10, timeout=2.0, interval=0.01) == 0x00FF00


def test_waitColorChange_timeout(monkeypatch):
    monkeypatch.setattr(smartpy.color, "getPixel", lambda *a, **k: 0xFF0000)
    assert smartpy.waitColorChange(10, 10, timeout=0.2, interval=0.02) is None


def test_waitMultiColor(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return (3, 4) if calls["n"] >= 2 else None

    monkeypatch.setattr(smartpy.color, "findMultiColor", fake)
    assert smartpy.waitMultiColor(0xFF0000, [((1, 0), 0x00FF00)],
                                 timeout=2.0, interval=0.01) == (3, 4)
