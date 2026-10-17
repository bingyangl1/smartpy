# -*- coding: utf-8 -*-
"""优化前后对比基准（调用新版 matchTemplate 的 pyramid 参数）。"""
import os
import sys

# Windows CI（英文环境）stdout 是 cp1252，print 中文会 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        passimport time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from smartpy.vision import matchTemplate


def bench(name, func, repeat=5):
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        func()
        best = min(best, time.perf_counter() - t0)
    print("%-56s %8.2f ms" % (name, best * 1000))
    return best


rng = np.random.default_rng(0)
W, H = 1920, 1080
src = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
tpl40 = rng.integers(0, 256, (40, 40, 3), dtype=np.uint8)
src[540:580, 960:1000] = tpl40
tpl80 = rng.integers(0, 256, (80, 80, 3), dtype=np.uint8)
src[400:480, 600:680] = tpl80

# 4K
src4 = cv2.resize(src, (3840, 2160), interpolation=cv2.INTER_NEAREST)
tpl160 = cv2.resize(tpl80, (160, 160), interpolation=cv2.INTER_NEAREST)
src4[800:960, 1200:1360] = tpl160

print("== 1080p，40x40 模板 ==")
t1 = bench("rgb 暴力 (pyramid=False)", lambda: matchTemplate(tpl40, src, threshold=0.9, onlyone=True, pyramid=False))
t2 = bench("rgb 金字塔 (pyramid=True)", lambda: matchTemplate(tpl40, src, threshold=0.9, onlyone=True, pyramid=True))
t3 = bench("gray 金字塔 (pyramid=True)", lambda: matchTemplate(tpl40, src, threshold=0.9, mode="gray", onlyone=True, pyramid=True))
print("  加速比: %.1fx (rgb) / %.1fx (gray)" % (t1 / t2, t1 / t3))

print("\n== 1080p，80x80 模板 ==")
t4 = bench("rgb 暴力 (pyramid=False)", lambda: matchTemplate(tpl80, src, threshold=0.9, onlyone=True, pyramid=False))
t5 = bench("rgb 金字塔 (pyramid=True)", lambda: matchTemplate(tpl80, src, threshold=0.9, onlyone=True, pyramid=True))
t6 = bench("gray 金字塔 (pyramid=True)", lambda: matchTemplate(tpl80, src, threshold=0.9, mode="gray", onlyone=True, pyramid=True))
print("  加速比: %.1fx (rgb) / %.1fx (gray)" % (t4 / t5, t4 / t6))

print("\n== 4K，160x160 模板 ==")
t7 = bench("rgb 暴力 (pyramid=False)", lambda: matchTemplate(tpl160, src4, threshold=0.9, onlyone=True, pyramid=False))
t8 = bench("rgb 金字塔 (pyramid=True)", lambda: matchTemplate(tpl160, src4, threshold=0.9, onlyone=True, pyramid=True))
t9 = bench("gray 金字塔 (pyramid=True)", lambda: matchTemplate(tpl160, src4, threshold=0.9, mode="gray", onlyone=True, pyramid=True))
print("  加速比: %.1fx (rgb) / %.1fx (gray)" % (t7 / t8, t7 / t9))

print("\n== 正确性抽查 ==")
print("  40x40 应命中 (980, 560):",
      matchTemplate(tpl40, src, threshold=0.9, onlyone=True, midpoint=True, pyramid=True))
print("  160x160 应命中 (1280, 880):",
      matchTemplate(tpl160, src4, threshold=0.9, onlyone=True, midpoint=True, pyramid=True))
