# -*- coding: utf-8 -*-
"""XFeat 能力边界测定：什么条件下它真的可用。"""
import sys

# Windows CI（英文环境）stdout 是 cp1252，print 中文会 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        passimport time

sys.path.insert(0, r"F:\smartpy")

import cv2
import numpy as np
import torch
from kornia.feature import XFeat

xfeat = XFeat.from_pretrained()


def to_t(img):
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).unsqueeze(0)


def match_official(scene, tpl):
    t0 = time.perf_counter()
    with torch.inference_mode():
        out = xfeat.match_xfeat(to_t(scene), to_t(tpl), top_k=4096)
    dt = (time.perf_counter() - t0) * 1000
    ps, pt = out[0].cpu().numpy(), out[1].cpu().numpy()
    if len(ps) < 4:
        return None, 0, len(ps), dt
    Hm, mask = cv2.findHomography(pt, ps, cv2.RANSAC, 4.0)
    if Hm is None:
        return None, 0, len(ps), dt
    th, tw = tpl.shape[:2]
    c = np.float32([[[tw / 2, th / 2]]])
    dst = cv2.perspectiveTransform(c, Hm)[0][0]
    return (float(dst[0]), float(dst[1])), int(mask.sum()), len(ps), dt


def textured_scene(W=1280, H=720, seed=11):
    """高纹理 "照片级" 场景：多层纹理 + 渐变 + 随机色块 + 文字"""
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (21, 21), 0)
    # 叠加高频纹理
    tex = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
    tex = cv2.GaussianBlur(tex, (3, 3), 0)
    img = cv2.addWeighted(base, 0.55, tex, 0.45, 0)
    # 随机形状
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
    """典型 UI：纯色面板 + 按钮 + 文字（低纹理）"""
    rng = np.random.default_rng(seed)
    img = np.full((H, W, 3), 240, np.uint8)
    cv2.rectangle(img, (40, 40), (W - 40, H - 40), (225, 225, 225), -1)
    for i in range(8):
        x, y = 80 + (i % 4) * 280, 120 + (i // 4) * 200
        cv2.rectangle(img, (x, y), (x + 220, y + 60), (70, 130, 200), -1)
        cv2.rectangle(img, (x, y), (x + 220, y + 60), (30, 30, 30), 2)
        cv2.putText(img, "Button %d" % i, (x + 14, y + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def run_case(tag, scene, tpl_box, transform=None, truth_scale=1.0):
    x, y, w, h = tpl_box
    tpl = scene[y:y + h, x:x + w].copy()
    truth = (x + w / 2, y + h / 2)
    if transform is not None:
        tpl = transform(tpl)
    c, inl, npair, dt = match_official(scene, tpl)
    if c is None:
        print("  %-34s 失败 (配对 %d 内点 %d, %.0fms)" % (tag, npair, inl, dt))
        return
    err = np.hypot(c[0] - truth[0], c[1] - truth[1])
    print("  %-34s 误差 %6.1fpx 内点 %3d 配对 %3d %5.0fms %s"
          % (tag, err, inl, npair, dt, "OK" if err <= 8 else "✗"))


def main():
    print("=" * 78)
    print("场景 A：高纹理（照片级）")
    print("=" * 78)
    sa = textured_scene()
    box = (520, 300, 240, 160)
    run_case("原图同源", sa, box)
    run_case("放大 1.5x", sa, box, lambda t: cv2.resize(t, None, fx=1.5, fy=1.5))
    run_case("缩小 0.6x", sa, box, lambda t: cv2.resize(t, None, fx=0.6, fy=0.6))
    run_case("旋转 20 度", sa, box,
             lambda t: cv2.warpAffine(t, cv2.getRotationMatrix2D((t.shape[1] / 2, t.shape[0] / 2), 20, 1.0),
                                      (t.shape[1], t.shape[0])))
    run_case("亮度 -50", sa, box,
             lambda t: np.clip(t.astype(np.int16) - 50, 0, 255).astype(np.uint8))

    print()
    print("=" * 78)
    print("场景 B：典型 UI（纯色面板 + 按钮 + 文字）")
    print("=" * 78)
    sb = ui_scene()
    box2 = (80, 120, 220, 60)   # 一个按钮
    run_case("原图同源", sb, box2)
    run_case("放大 1.5x", sb, box2, lambda t: cv2.resize(t, None, fx=1.5, fy=1.5))
    run_case("旋转 20 度", sb, box2,
             lambda t: cv2.warpAffine(t, cv2.getRotationMatrix2D((t.shape[1] / 2, t.shape[0] / 2), 20, 1.0),
                                      (t.shape[1], t.shape[0])))

    print()
    print("对照：同样场景下 matchTemplate 的表现")
    import sys as _s
    _s.path.insert(0, r"F:\smartpy")
    import smartpy
    for tag, sc, bx, tr in [
        ("UI 原图", sb, box2, None),
        ("UI 放大1.5x", sb, box2, lambda t: cv2.resize(t, None, fx=1.5, fy=1.5)),
        ("UI 旋转20度", sb, box2,
         lambda t: cv2.warpAffine(t, cv2.getRotationMatrix2D((t.shape[1] / 2, t.shape[0] / 2), 20, 1.0),
                                  (t.shape[1], t.shape[0]))),
        ("纹理图 原图", sa, box, None),
        ("纹理图 放大1.5x", sa, box, lambda t: cv2.resize(t, None, fx=1.5, fy=1.5)),
    ]:
        x, y, w, h = bx
        tpl = sc[y:y + h, x:x + w].copy()
        if tr is not None:
            tpl = tr(tpl)
        truth = (x + w / 2, y + h / 2)
        t0 = time.perf_counter()
        pts = smartpy.matchTemplate(tpl, sc, threshold=0.9, onlyone=True, midpoint=True)
        dt = (time.perf_counter() - t0) * 1000
        if pts:
            err = np.hypot(pts[0][0] - truth[0], pts[0][1] - truth[1])
            print("  %-34s 误差 %6.1fpx %5.1fms %s" % (tag, err, dt, "OK" if err <= 8 else "✗"))
        else:
            print("  %-34s 未命中        %5.1fms ✗" % (tag, dt))


if __name__ == "__main__":
    main()
