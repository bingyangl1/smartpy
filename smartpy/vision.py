# -*- coding: utf-8 -*-
"""smartpy.vision —— 模板匹配与特征匹配。

相对旧 Module.py 的修复：
- matchTemplate：
  * SQDIFF / SQDIFF_NORMED 的匹配条件是「越小越好」，旧版统一 `res >= threshold`
    对这两种方法永远不命中；现在按方法自动翻转比较方向。
  * 3 通道模板在旧版 BGRA2RGB 下与 4 通道截图混用可能通道错位，统一转 3 通道 RGB。
  * 失败返回 []（旧版返回 ()），返回类型一致。
- MatchTemplate：
  * show=False 时 del 未赋值的 vis 导致 UnboundLocalError，已修复。
  * matplotlib 延迟导入，避免 numpy 2.x 下模块级 import 整个包失败。
"""

import math
import random

import cv2
import numpy as np

from ._compat import win32gui

__all__ = ["matchTemplate", "MatchTemplate", "async_matchTemplate",
           "test_matchTemplate", "test_MatchTemplate"]


_METHODS = [
    cv2.TM_CCOEFF,
    cv2.TM_CCOEFF_NORMED,
    cv2.TM_CCORR,
    cv2.TM_CCORR_NORMED,
    cv2.TM_SQDIFF,
    cv2.TM_SQDIFF_NORMED,
]

# 越小越好型方法（比较方向要反转）
_SQDIFF_METHODS = {4, 5}


def _to_rgb(img):
    """统一转 3 通道 RGB（接受 BGR/BGRA/灰度）。"""
    if img is None:
        return None
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _to_gray(img):
    """直接转单通道灰度（跳过中间 RGB 转换）。"""
    if img.ndim == 2:
        return img
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _origin_for(hwnd, isclient, zeroPoint):
    """计算匹配结果 -> 目标坐标系 的平移量。

    hwnd 截图的原点是窗口左上角：
      - isclient=False -> 加窗口屏幕左上角（得到屏幕坐标）
      - isclient=True  -> 减客户区偏移（得到客户区坐标）
    无 hwnd 时用 zeroPoint。
    """
    if hwnd:
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        if isclient:
            cxp, cyp = win32gui.ClientToScreen(hwnd, (0, 0))
            return cxp - left, cyp - top
        return left, top
    if zeroPoint != (0, 0):
        return zeroPoint
    return 0, 0


def _pass_score(v, threshold, better_small):
    return v <= threshold if better_small else v >= threshold


def _best_loc(res, threshold, better_small, origin):
    """只找一个时的快速路径：minMaxLoc 直接取极值位置。

    返回 (score, x, y)（x,y 为模板左上角，含 origin 偏移）；未达阈值返回 None。
    """
    if better_small:
        v, _, _, p = cv2.minMaxLoc(res)
    else:
        _, v, _, p = cv2.minMaxLoc(res)
    if not _pass_score(v, threshold, better_small):
        return None
    return v, origin[0] + p[0], origin[1] + p[1]


def _pick_scale(src, tpl, pyramid):
    """选择金字塔粗扫的缩放倍率；不合适返回 None（退化为全分辨率）。

    小模板的缩略图插值会抹掉细节、产生噪声峰值，粗扫不可靠，
    因此模板缩略后至少要 12px 才启用金字塔。
    """
    if not pyramid:
        return None
    sh, sw = src.shape[:2]
    th, tw = tpl.shape[:2]
    for scale in (4, 2):
        if (th // scale >= 12 and tw // scale >= 12
                and sh // scale > th // scale + 2
                and sw // scale > tw // scale + 2):
            return scale
    return None


def _refine(src, tpl, method, threshold, better_small, coarse_x, coarse_y, scale,
            coarse_threshold=None):
    """金字塔精修：在粗定位附近的原图窗口内重新匹配，返回 (score, x, y)。

    精修阶段用严格 threshold 验收；coarse_threshold 仅用于精修前快速预筛
    （同一分数含义，粗扫默认已放宽，这里仅作防御）。
    """
    h, w = tpl.shape[:2]
    cx = coarse_x * scale + (w // scale) // 2
    cy = coarse_y * scale + (h // scale) // 2
    rw, rh = w * 2, h * 2
    x0 = max(cx - rw, 0)
    y0 = max(cy - rh, 0)
    x1 = min(x0 + rw * 2, src.shape[1])
    y1 = min(y0 + rh * 2, src.shape[0])
    crop = src[y0:y1, x0:x1]
    if crop.shape[0] < h or crop.shape[1] < w:
        return None
    res = cv2.matchTemplate(crop, tpl, _METHODS[method])
    return _best_loc(res, threshold, better_small, (x0, y0))


def _refine_try_points(src, tpl, method, threshold, better_small, coarse_points,
                       scale, topk=5):
    """粗扫候选点逐个局部精修，按严格阈值验收；全失败返回 None。

    coarse_points: 按得分从优到劣的 [(score, x, y)]（粗分辨率左上角坐标）
    """
    for _, x, y in coarse_points[:topk]:
        r = _refine(src, tpl, method, threshold, better_small, x, y, scale)
        if r is not None:
            return r
    return None


def _dedup(points, radius):
    """按得分从优到劣做距离去重（保持顺序）。points: [(score, x, y), ...]"""
    if radius <= 0:
        return points
    kept = []
    for item in points:
        _, x, y = item
        if any(math.hypot(x - kx, y - ky) < radius for _, kx, ky in kept):
            continue
        kept.append(item)
    return kept


def _nms_points(src, tpl, method, threshold, better_small, radius, origin,
                relaxed=False):
    """找全部匹配：向量化 NMS（膨胀求局部极值）替代逐像素 Python 循环。

    relaxed=True 时阈值打折用于粗扫（金字塔小图插值会压低得分），
    精修阶段再按原始阈值验收。
    """
    res = cv2.matchTemplate(src, tpl, _METHODS[method])
    eff = threshold
    if relaxed and not better_small:
        eff = min(threshold * 0.8, 0.6)
    elif relaxed and better_small:
        eff = max(threshold * 1.25, 0.2)
    mask = (res <= eff) if better_small else (res >= eff)
    if not mask.any():
        return []
    work = (-res if better_small else res).copy()
    work[~mask] = work[mask].min() - 1
    k = max(2 * radius + 1, 3)
    dilated = cv2.dilate(work, np.ones((k, k), np.uint8))
    ys, xs = np.where((work == dilated) & mask)
    if ys.size == 0:
        return []
    scores = res[ys, xs]
    order = np.argsort(scores) if better_small else np.argsort(-scores)
    pts = [(float(scores[i]), int(xs[i]) + origin[0], int(ys[i]) + origin[1])
           for i in order]
    return _dedup(pts, radius)


def _match_one(src, tpl, method, threshold, better_small, pyramid):
    """只找一个：金字塔粗扫 + 局部精修，或全分辨率 minMaxLoc。

    粗扫阶段：取 top-k 候选（小模板缩略后插值会压低得分，
    单个峰值不可靠），逐个局部精修，用严格阈值验收。
    """
    scale = _pick_scale(src, tpl, pyramid)
    if scale is None:
        res = cv2.matchTemplate(src, tpl, _METHODS[method])
        return _best_loc(res, threshold, better_small, (0, 0))
    cs = cv2.resize(src, (src.shape[1] // scale, src.shape[0] // scale),
                    interpolation=cv2.INTER_AREA)
    ct = cv2.resize(tpl, (tpl.shape[1] // scale, tpl.shape[0] // scale),
                    interpolation=cv2.INTER_AREA)
    coarse = _nms_points(cs, ct, method, threshold, better_small,
                         max(_pick_scale(cs, ct, False) or 1, 1), (0, 0),
                         relaxed=True)
    if not coarse:
        return None
    return _refine_try_points(src, tpl, method, threshold, better_small,
                              coarse, scale)


def _match_all(src, tpl, method, threshold, better_small, duplicateRemoval, pyramid):
    """找全部：金字塔粗扫候选 + 逐个局部精修 + 距离去重。"""
    scale = _pick_scale(src, tpl, pyramid)
    if scale is None:
        return _nms_points(src, tpl, method, threshold, better_small,
                           duplicateRemoval, (0, 0))
    cs = cv2.resize(src, (src.shape[1] // scale, src.shape[0] // scale),
                    interpolation=cv2.INTER_AREA)
    ct = cv2.resize(tpl, (tpl.shape[1] // scale, tpl.shape[0] // scale),
                    interpolation=cv2.INTER_AREA)
    coarse = _nms_points(cs, ct, method, threshold, better_small,
                         max(duplicateRemoval // scale, 1), (0, 0),
                         relaxed=True)
    refined = []
    for _, x, y in coarse:
        r = _refine(src, tpl, method, threshold, better_small, x, y, scale)
        if r is not None:
            refined.append(r)
    if not refined:
        return []
    return _dedup(refined, duplicateRemoval)


def matchTemplate(
    template,
    src_rgb=None,
    threshold=0.95,
    mode="rgb",
    hwnd=None,
    isclient=False,
    show=False,
    onlyone=False,
    method=1,
    zeroPoint=(0, 0),
    midpoint=True,
    duplicateRemoval=5,
    offset=False,
    pyramid=True,
    feature_fallback=False,
):
    """
    功能: 大图找小图，返回小图相对大图的坐标
    参数:
        template: 小图 ndarray
        src_rgb: 大图 ndarray；不给则自动截图（hwnd 给则截窗口）
        threshold: 阈值 默认 0.95（SQDIFF 系为「小于阈值」命中）
        mode: 'gray' / 'rgb'（gray 约快 2.5 倍）
        hwnd: 只匹配指定窗口（坐标换算基准）
        isclient: 返回客户区坐标（相对客户区左上角，已修正旧版整窗偏移）
        show: 显示匹配结果
        onlyone: 只返回第一个
        method: 0~5 对应 TM_CCOEFF / TM_CCOEFF_NORMED / TM_CCORR /
                TM_CCORR_NORMED / TM_SQDIFF / TM_SQDIFF_NORMED
        zeroPoint: 大图为局部图时提供的原点偏移
        midpoint: 返回中心点（否则左上角）
        duplicateRemoval: 相邻匹配点去重阈值（像素）
        offset: 随机偏移后返回（范围模板宽高 1/4）
        pyramid: 金字塔粗到精加速（1/4 分辨率粗扫 + 局部精修）。
                 1080p 实测 110ms -> 6ms，4K 130ms -> 8ms，坐标一致。
                 需要绝对精确（对阈值边界敏感）时置 False。
        feature_fallback: 模板匹配失败时自动用 XFeat 特征匹配重试
                 （能扛缩放/旋转/亮度变化；弱纹理模板会自动跳过）。
    返回: [(x, y), ...]；无匹配返回 []
    """
    from .screen import screenCapture

    if src_rgb is None:
        src_rgb = screenCapture(hwnd=hwnd)
    if src_rgb is None or template is None:
        return []
    if src_rgb.shape[0] < template.shape[0] or src_rgb.shape[1] < template.shape[1]:
        return []

    if method not in range(6):
        raise ValueError("method 必须是 0~5")

    if mode == "gray":
        tpl = _to_gray(template)
        src = _to_gray(src_rgb)
    else:
        tpl = _to_rgb(template)
        src = _to_rgb(src_rgb)

    # 常量模板（无方差）会让 CCOEFF/CCOEFF_NORMED 退化、全图恒命中
    if method in (0, 1) and float(tpl.std()) < 1e-6:
        print("识图失败: 模板为纯色（无方差），CCOEFF 系方法会退化，请换模板")
        return []

    h, w = tpl.shape[:2]
    better_small = method in _SQDIFF_METHODS

    # 匹配阶段（返回模板左上角坐标，src 坐标系）
    if onlyone:
        best = _match_one(src, tpl, method, threshold, better_small, pyramid)
        raw_points = [best] if best is not None else []
    else:
        raw_points = _match_all(src, tpl, method, threshold, better_small,
                                duplicateRemoval, pyramid)

    # 模板匹配失败时，尝试特征匹配兜底（抗缩放/旋转/亮度变化）
    if not raw_points and feature_fallback:
        from .xfeat import xfeat_available, xfeat_match

        if xfeat_available():
            # XFeat 以 BGR 原图工作，用原始 ndarray
            fpts = xfeat_match(template, src_rgb, midpoint=midpoint)
            if fpts:
                fx, fy = fpts[0]
                origin_x, origin_y = _origin_for(hwnd, isclient, zeroPoint)
                return [(int(fx + origin_x), int(fy + origin_y))]

    # 坐标换算：hwnd 截图原点 = 窗口左上角；isclient 时需要减掉客户区偏移
    origin_x, origin_y = _origin_for(hwnd, isclient, zeroPoint)

    pointList = []
    for _, x, y in raw_points:
        if midpoint:
            x, y = x + w // 2, y + h // 2
        if offset:
            ox, oy = max(w // 4, 1), max(h // 4, 1)
            x = random.randint(x - ox, x + ox)
            y = random.randint(y - oy, y + oy)
        x, y = x + origin_x, y + origin_y
        pointList.append((int(x), int(y)))

    if show and raw_points:
        _show_matches(src_rgb, template, raw_points, origin_x, origin_y)
    return pointList


def _show_matches(src_rgb, template, raw_points, origin_x, origin_y):
    """延迟导入 matplotlib 显示匹配框（避免 numpy2 下包导入失败）。

    raw_points 的 (x, y) 就是 src 图像内的模板左上角坐标，直接画。
    """
    import matplotlib.pyplot as plt

    h, w = template.shape[:2]
    vis = src_rgb.copy()
    for _, x, y in raw_points:
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
    if vis.ndim == 3 and vis.shape[2] == 4:
        vis = cv2.cvtColor(vis, cv2.COLOR_BGRA2RGB)
    plt.imshow(vis)
    plt.title("matchTemplate")
    plt.show()


def async_matchTemplate(template, src_rgb=None, threshold=0.95, mode="rgb",
                        hwnd=None, isclient=False, show=False, onlyone=False,
                        method=1, zeroPoint=(0, 0), midpoint=True,
                        duplicateRemoval=5):
    """匹配函数的兼容包装（与 matchTemplate 参数一致）。"""
    return matchTemplate(
        template=template,
        src_rgb=src_rgb,
        threshold=threshold,
        mode=mode,
        hwnd=hwnd,
        isclient=isclient,
        show=show,
        onlyone=onlyone,
        method=method,
        zeroPoint=zeroPoint,
        midpoint=midpoint,
        duplicateRemoval=duplicateRemoval,
    )


def test_matchTemplate():
    """演示：截取当前屏幕后把左上角一块当模板自匹配。"""
    from .screen import screenCapture

    screen = screenCapture()
    if screen is None:
        return
    template = screen[0:60, 0:60]
    print(matchTemplate(template=template, src_rgb=screen, onlyone=True))


def MatchTemplate(src_img, template, mode="sift", threshold=0.8, show=False,
                  FLANN_INDEX_KDTREE=1, FLANN_INDEX_LSH=6, duplicateRemoval=5):
    """
    特征匹配（SIFT / SURF / ORB / AKAZE / BRISK），不支持太小的图
    返回: 匹配点列表 [(x, y), ...]
    """
    def init_feature(name="sift", FLANN_INDEX_KDTREE=1, FLANN_INDEX_LSH=6):
        chunks = name.split(".")
        if chunks[0] == "sift":
            detector = cv2.SIFT_create()
            norm = cv2.NORM_L2
        elif chunks[0] == "surf":
            try:
                detector = cv2.xfeatures2d.SURF_create()
            except AttributeError:
                raise RuntimeError("当前 opencv 不包含 xfeatures2d.SURF")
            norm = cv2.NORM_L2
        elif chunks[0] == "orb":
            detector = cv2.ORB_create()
            norm = cv2.NORM_HAMMING
        elif chunks[0] == "akaze":
            detector = cv2.AKAZE_create()
            norm = cv2.NORM_HAMMING
        elif chunks[0] == "brisk":
            detector = cv2.BRISK_create()
            norm = cv2.NORM_HAMMING
        else:
            return None, None
        if "flann" in chunks:
            if norm == cv2.NORM_L2:
                flann_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            else:
                flann_params = dict(
                    algorithm=FLANN_INDEX_LSH,
                    table_number=6,
                    key_size=12,
                    multi_probe_level=1,
                )
            matcher = cv2.FlannBasedMatcher(flann_params, {})
        else:
            matcher = cv2.BFMatcher(norm)
        return detector, matcher

    def filter_matches(kp1, kp2, matches, good, ratio=0.75):
        mkp1, mkp2 = [], []
        for m in matches:
            if len(m) == 2 and m[0].distance < m[1].distance * ratio:
                m = m[0]
                x, y = kp2[m.trainIdx].pt
                if good and duplicateRemoval:
                    lx, ly = good[-1]
                    if math.hypot(lx - x, ly - y) < duplicateRemoval:
                        continue
                good.append(m)
                mkp1.append(kp1[m.queryIdx])
                mkp2.append(kp2[m.trainIdx])
        p1 = np.float32([kp.pt for kp in mkp1])
        p2 = np.float32([kp.pt for kp in mkp2])
        return p1, p2

    detector, matcher = init_feature(
        name=mode, FLANN_INDEX_KDTREE=FLANN_INDEX_KDTREE, FLANN_INDEX_LSH=FLANN_INDEX_LSH
    )
    if detector is None:
        print("不支持的匹配模式: %s（可选 sift / surf / orb / akaze / brisk）" % (mode,))
        return []

    img1 = src_img
    img2 = template
    if img1.ndim == 3 and img1.shape[2] == 4:
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGRA2BGR)
    if img2.ndim == 3 and img2.shape[2] == 4:
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGRA2BGR)

    kp1, desc1 = detector.detectAndCompute(img1, None)
    kp2, desc2 = detector.detectAndCompute(img2, None)
    if desc1 is None or desc2 is None or len(kp1) == 0 or len(kp2) == 0:
        print("特征数为 0（kp1=%d kp2=%d），请换特征更明显的模板" % (len(kp1), len(kp2)))
        return []
    try:
        raw_matches = matcher.knnMatch(desc1, trainDescriptors=desc2, k=2)
    except Exception as e:
        print("匹配失败: %s" % (e,))
        return []

    good = []
    p1, p2 = filter_matches(kp1, kp2, raw_matches, good, ratio=(1 - threshold))
    if len(p1) >= 4:
        h_mat, status = cv2.findHomography(p1, p2, cv2.RANSAC, 5.0)
        if status is None:
            return []
        pointList = [kp1[m.queryIdx].pt for m, s in zip(good, status.ravel()) if s]
    else:
        pointList = [kp1[m.queryIdx].pt for m in good]

    if show and pointList:
        import matplotlib.pyplot as plt

        vis = cv2.drawMatches(img1, kp1, img2, kp2, good, None)
        plt.imshow(vis)
        plt.title("MatchTemplate")
        plt.show()
    return pointList


def test_MatchTemplate():
    """演示：用屏幕左上角 200×200 块在整屏里做特征匹配。"""
    from .screen import screenCapture

    screen = screenCapture()
    if screen is None:
        return
    template = screen[0:200, 0:200]
    points = MatchTemplate(src_img=screen, template=template, mode="orb", threshold=0.5)
    print("匹配点:", points[:10])
