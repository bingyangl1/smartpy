# -*- coding: utf-8 -*-
"""端到端冒烟：真实截图 → 真实匹配 → shim 兼容验证（不做真实点击）。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402


def main():
    import smartpy

    print("== 1. 真实截图 ==")
    img = smartpy.screenCapture()
    assert img is not None and img.ndim == 3
    print("  全屏 BGRA:", img.shape)

    print("== 2. 截屏自匹配（用屏幕左上角一块当模板） ==")
    tpl = img[0:60, 0:60]
    pts = smartpy.matchTemplate(tpl, img, threshold=0.95, onlyone=True)
    print("  命中:", pts[:3])

    print("== 3. PrintWindow 后备（桌面句柄路径） ==")
    img2 = smartpy.window_capture(smartpy.findWindow())
    print("  BGRA:", None if img2 is None else img2.shape)

    print("== 4. 旧 shim 兼容 ==")
    import Module

    assert Module.screenCapture is smartpy.screenCapture
    assert Module.findClick is smartpy.findClick
    print("  Module.findClick is smartpy.findClick ->", Module.findClick is smartpy.findClick)

    print("== 5. 轨迹 ==")
    print("  直线:", smartpy.genLinePointList((0, 0), (60, 30))[:4])
    print("  贝塞尔:", list(smartpy.cubic_bezier_gen((0, 0), (60, 30), 7)))

    print("== 6. 遮罩窗 2 秒展示 ==")
    import time
    from smartpy.overlay import Window

    win = Window(className="SmokeOverlay", windowTitle="smartpy-smoke",
                 windowWidth=400, windowHeight=300, Alpha=180, isDaemon=True)
    win.start()
    deadline = time.time() + 5
    while time.time() < deadline and win.hwnd is None:
        time.sleep(0.05)
    assert win.hwnd is not None, "遮罩窗未创建"
    print("  hwnd:", win.hwnd)
    time.sleep(2)
    win.close()
    time.sleep(0.3)
    print("  已关闭")

    print("\nSMOKE OK")


if __name__ == "__main__":
    main()
