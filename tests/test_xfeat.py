# -*- coding: utf-8 -*-
"""XFeat 特征匹配适配器回归测试。

重要边界（实测，见 scripts/xfeat_boundary.py）：
- XFeat 只在高纹理画面有效（游戏画面 / 照片 / 复杂图标）
- 典型 Windows UI（纯色面板 + 文字）纹理不足，XFeat 会失败 —— 那是 matchTemplate 的领域
- 因此测试用高纹理场景，并验证「弱纹理自动拒绝」

实测数据（1280x720，纹理场景）：
  原图同源      误差 0.4px  184ms
  放大 1.5x     误差 1.0px  532ms   <- matchTemplate 此处漏检
  亮度 -50      误差 0.4px  151ms
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import pytest

import smartpy
from smartpy.xfeat import xfeat_available, xfeat_match, XFeatLocator

requires_xfeat = pytest.mark.skipif(
    not xfeat_available(), reason="需要 torch + kornia"
)


def textured_scene(W=1280, H=720, seed=11):
    """高纹理"照片级"场景（XFeat 的有效场景）。"""
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (21, 21), 0)
    tex = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
    tex = cv2.GaussianBlur(tex, (3, 3), 0)
    img = cv2.addWeighted(base, 0.55, tex, 0.45, 0)
    for _ in range(60):
        p1 = (int(rng.integers(0, W)), int(rng.integers(0, H)))
        p2 = (int(rng.integers(0, W)), int(rng.integers(0, H)))
        cv2.line(img, p1, p2, tuple(int(c) for c in rng.integers(0, 255, 3)),
                 int(rng.integers(1, 4)))
    for _ in range(25):
        p = (int(rng.integers(0, W)), int(rng.integers(0, H)))
        cv2.circle(img, p, int(rng.integers(5, 40)),
                   tuple(int(c) for c in rng.integers(0, 255, 3)),
                   int(rng.integers(1, 4)))
    return img


def ui_scene(W=1280, H=720, seed=5):
    """典型 UI 场景（低纹理，XFeat 的失败场景 / matchTemplate 的强项）。"""
    img = np.full((H, W, 3), 240, np.uint8)
    cv2.rectangle(img, (40, 40), (W - 40, H - 40), (225, 225, 225), -1)
    for i in range(8):
        x, y = 80 + (i % 4) * 280, 120 + (i // 4) * 200
        cv2.rectangle(img, (x, y), (x + 220, y + 60), (70, 130, 200), -1)
        cv2.rectangle(img, (x, y), (x + 220, y + 60), (30, 30, 30), 2)
        cv2.putText(img, "Button %d" % i, (x + 14, y + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return img


BOX = (520, 300, 240, 160)


def take(scene, box=BOX):
    x, y, w, h = box
    return scene[y:y + h, x:x + w].copy(), (x + w / 2, y + h / 2)


@requires_xfeat
def test_xfeat_textured_locate():
    """高纹理 + 同源：应精确命中。"""
    scene = textured_scene()
    tpl, truth = take(scene)
    pts = xfeat_match(tpl, scene, midpoint=True, debug=True)
    assert len(pts) == 1
    x, y = pts[0]
    assert np.hypot(x - truth[0], y - truth[1]) <= 5


@requires_xfeat
def test_xfeat_scaled_template():
    """高纹理 + 放大 1.5x：XFeat 的独有优势（matchTemplate 此处漏检）。"""
    scene = textured_scene()
    tpl, truth = take(scene)
    scaled = cv2.resize(tpl, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)

    # 对照组：matchTemplate 在缩放模板上漏检
    assert smartpy.matchTemplate(scaled, scene, threshold=0.9, onlyone=True) == []

    pts = xfeat_match(scaled, scene, midpoint=True)
    assert len(pts) == 1, "XFeat 应能处理缩放"
    x, y = pts[0]
    assert np.hypot(x - truth[0], y - truth[1]) <= 6


@requires_xfeat
def test_xfeat_brightness_change():
    """高纹理 + 亮度 -50：XFeat 应命中。"""
    scene = textured_scene()
    tpl, truth = take(scene)
    dim = np.clip(tpl.astype(np.int16) - 50, 0, 255).astype(np.uint8)
    pts = xfeat_match(dim, scene, midpoint=True)
    assert len(pts) == 1
    x, y = pts[0]
    assert np.hypot(x - truth[0], y - truth[1]) <= 6


@requires_xfeat
def test_xfeat_rejects_flat_template():
    """纯色模板必须被拒绝（特征匹配对它无效）。"""
    scene = textured_scene()
    flat = np.full((80, 120, 3), 128, np.uint8)
    assert xfeat_match(flat, scene, debug=True) == []


@requires_xfeat
def test_xfeat_ui_scene_is_not_its_job():
    """典型 UI 场景：XFeat 会失败，这正是 matchTemplate 存在的理由。"""
    scene = ui_scene()
    tpl, truth = take(scene, (80, 120, 220, 60))
    # matchTemplate 精确命中
    mt = smartpy.matchTemplate(tpl, scene, threshold=0.9, onlyone=True, midpoint=True)
    assert mt and np.hypot(mt[0][0] - truth[0], mt[0][1] - truth[1]) <= 3
    # XFeat 允许失败（不抛异常即可），若命中则要求足够准
    xf = xfeat_match(tpl, scene)
    if xf:
        assert np.hypot(xf[0][0] - truth[0], xf[0][1] - truth[1]) <= 15


@requires_xfeat
def test_xfeat_locator_reuse():
    """XFeatLocator 实例复用。"""
    scene = textured_scene()
    tpl, truth = take(scene)
    loc = XFeatLocator()
    p1 = loc.locate(tpl, scene)
    p2 = loc.locate(tpl, scene)
    assert p1 and p2
    assert p1[0] == p2[0]


@requires_xfeat
def test_matchTemplate_feature_fallback():
    """matchTemplate(feature_fallback=True) 在模板匹配失败后兜底成功。"""
    scene = textured_scene()
    tpl, truth = take(scene)
    scaled = cv2.resize(tpl, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)

    assert smartpy.matchTemplate(scaled, scene, threshold=0.9, onlyone=True,
                                feature_fallback=False) == []
    pts = smartpy.matchTemplate(scaled, scene, threshold=0.9, onlyone=True,
                               feature_fallback=True)
    assert len(pts) == 1
    x, y = pts[0]
    assert np.hypot(x - truth[0], y - truth[1]) <= 8


def test_xfeat_available_is_bool():
    assert isinstance(xfeat_available(), bool)


@requires_xfeat
def test_xfeat_graceful_on_bad_input():
    """空图 / 超大模板不应崩溃。"""
    scene = textured_scene(400, 300)
    assert xfeat_match(None, scene) == []
    assert xfeat_match(scene, None) == []
    big = np.zeros((600, 900, 3), np.uint8)
    assert xfeat_match(big, scene) == []
