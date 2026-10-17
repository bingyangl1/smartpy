# -*- coding: utf-8 -*-
"""示例：基本用法一览（不执行真实点击的部分）。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smartpy  # noqa: E402


def demo_enum():
    """枚举前 5 个窗口"""
    for info in smartpy.enumWindows()[:5]:
        print("[%s] %s | %s" % (info["hwnd"], info["className"], info["windowTitle"]))


def demo_capture():
    """截全屏并保存"""
    img = smartpy.screenCapture(save=os.path.join(os.path.dirname(__file__), "screen.jpg"))
    print("截图尺寸:", None if img is None else img.shape)


def demo_match():
    """把屏幕左上角 60x60 当模板，在全屏找"""
    img = smartpy.screenCapture()
    if img is not None:
        tpl = img[0:60, 0:60]
        pts = smartpy.matchTemplate(tpl, img, threshold=0.9, onlyone=True)
        print("匹配到:", pts[:3])


def demo_trajectory():
    print("直线轨迹:", smartpy.genLinePointList((0, 0), (120, 40))[:5], "...")
    print("贝塞尔轨迹:", list(smartpy.cubic_bezier_gen((0, 0), (120, 40), 8)))


if __name__ == "__main__":
    demo_enum()
    demo_capture()
    demo_match()
    demo_trajectory()
