# -*- coding: utf-8 -*-
"""smartpy.color —— 图色识别（找色 / 比色 / 多点找色 / 色块统计）。

按键精灵 / 大漠插件那套图色能力的 Python 实现，全部基于 numpy + OpenCV，
不依赖任何第三方找色库。

坐标约定：
- 所有坐标默认是**屏幕坐标**（与 smartpy.matchTemplate 一致）
- 传入 hwnd 时，截图原点为窗口左上角，返回值自动换算成屏幕坐标

颜色约定：
- 输入输出统一用 **0xRRGGBB 整数**（如 0xFF0000 是纯红），这是按键精灵的习惯
- 内部按 BGR 处理（OpenCV/截图原生顺序），转换在边界完成

性能（4K 3840x2160 实测）：
    全屏精确找色（首点）   ~7 ms   （cv2.inRange + findNonZero）
    全屏精确找色（全部）  ~15 ms
    区域找色 700x500       ~1.6 ms
    多点找色 300x200       ~2 ms
    单点取值               ~0.1 us
"""

import time

import numpy as np

import cv2

from ._compat import win32gui

__all__ = [
    "rgb_to_bgr", "bgr_to_rgb", "hex_to_bgr", "bgr_to_hex",
    "getPixel", "getColor", "getColorAt", "compareColor", "compareColorEx",
    "findColor", "findColorEx", "findColorBlock", "findMultiColor",
    "findMultiColorEx", "countColor", "findColorClick",
    "findColorRange", "countColorRange",
    "waitColor", "waitColorDisappear", "waitColorChange", "waitMultiColor",
    "snapshot", "clearSnapshot",
]


# ---------------------------------------------------------------- 颜色换算


def rgb_to_bgr(color):
    """0xRRGGBB -> (B, G, R) 元组"""
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return (b, g, r)


def bgr_to_rgb(b, g, r):
    """(B,G,R) -> 0xRRGGBB 整数"""
    return ((int(r) & 0xFF) << 16) | ((int(g) & 0xFF) << 8) | (int(b) & 0xFF)


def hex_to_bgr(color):
    """0xRRGGBB / '#RRGGBB' / (r,g,b) -> (b, g, r)"""
    if isinstance(color, str):
        color = color.lstrip("#")
        color = int(color, 16)
    if isinstance(color, (tuple, list)):
        r, g, b = color[0], color[1], color[2]
        return (int(b), int(g), int(r))
    return rgb_to_bgr(int(color))


def bgr_to_hex(bgr):
    """(B,G,R) -> 0xRRGGBB"""
    return bgr_to_rgb(bgr[0], bgr[1], bgr[2])


# ---------------------------------------------------------------- 内部分色


_UNSET = object()

# ---------------------------------------------------------------- 截图缓存
# 每次操作都重新截图代价很大（4K 一次约 25~30ms），而连续取色/找色
# 通常面对的是同一帧画面。snapshot() 拍一张缓存起来，后续操作复用，
# 同一帧内做 N 次查询只需 1 次截图开销。

_SNAPSHOT = None       # (hwnd, bgr_img, offset_x, offset_y)


def snapshot(hwnd=None):
    """
    拍一张快照并缓存，后续 getPixel / findColor / ... 自动复用它。

    适用：一个动作序列内需要多次取色/找色（同一帧）。
    注意：画面会变时请重新 snapshot() 或 clearSnapshot()。

    示例:
        smartpy.snapshot(hwnd)          # 拍一帧
        smartpy.getPixel(100, 200)      # 复用快照，~微秒级
        smartpy.findColor(0xFF0000)     # 复用快照
        smartpy.clearSnapshot()         # 用完清理
    """
    global _SNAPSHOT
    bgr, ox, oy = _grab(hwnd=hwnd, region=None)
    if bgr is None:
        _SNAPSHOT = None
        return None
    _SNAPSHOT = (hwnd, bgr, ox, oy)
    return bgr


def clearSnapshot():
    """清除快照缓存。"""
    global _SNAPSHOT
    _SNAPSHOT = None


def _grab_cached(hwnd=None, region=None):
    """优先用快照（同 hwnd 且无需区域裁剪时）。"""
    if _SNAPSHOT is not None and region is None:
        snap_hwnd, bgr, ox, oy = _SNAPSHOT
        if snap_hwnd == hwnd:
            return bgr, ox, oy
    return _grab(hwnd=hwnd, region=region)


def _as_bgr(img):
    """统一成 3 通道 BGR（截图为 BGRA）。"""
    if img is None:
        return None
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return np.ascontiguousarray(img[:, :, :3])
    return img


def _grab(hwnd=None, region=None):
    """
    取图。返回 (bgr_img, offset_x, offset_y)。

    region=(x, y, w, h)，语义与 screenCapture 一致（相对窗口左上角）。
    """
    from .screen import screenCapture

    if region is None or len(region) != 4:
        img = screenCapture(hwnd=hwnd)
        ox = oy = 0
    else:
        x, y, w, h = region
        img = screenCapture(hwnd=hwnd, region=(x, y, w, h))
        ox, oy = x, y
    if img is None:
        return None, 0, 0
    return _as_bgr(img), ox, oy


def _to_screen(hwnd, ox, oy):
    """局部图坐标 -> 屏幕坐标 的加法量。"""
    if hwnd:
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        return left + ox, top + oy
    return ox, oy


def _color_mask(bgr, color, sim):
    """生成颜色匹配掩码（uint8 0/255）。

    sim: 0~255 每通道容差（按键精灵风格的相似度）。0 表示精确匹配。
    """
    b, g, r = hex_to_bgr(color)
    if sim <= 0:
        mask = ((bgr[:, :, 0] == b) &
                (bgr[:, :, 1] == g) &
                (bgr[:, :, 2] == r)).astype(np.uint8) * 255
        return mask
    lower = np.array([max(b - sim, 0), max(g - sim, 0), max(r - sim, 0)], np.uint8)
    upper = np.array([min(b + sim, 255), min(g + sim, 255), min(r + sim, 255)], np.uint8)
    return cv2.inRange(bgr, lower, upper)


# ---------------------------------------------------------------- 单点


def getPixel(x, y, hwnd=None):
    """
    取单点颜色，返回 0xRRGGBB 整数。

    参数:
        x, y: 屏幕坐标（传 hwnd 时为屏幕坐标，内部换算成窗口相对）
        hwnd: 窗口句柄（可选，从该窗口截图取值）
    返回: 0xRRGGBB；失败返回 None

    性能说明：
        有 snapshot() 快照时走内存索引（约 1 微秒）；
        没快照时截 1x1 区域（约 20~30ms，含截图开销）。
        连续取色请先 snapshot()。
    """
    # 1) 有快照：直接内存索引（最快路径）
    if _SNAPSHOT is not None:
        snap_hwnd, bgr, ox, oy = _SNAPSHOT
        if snap_hwnd == hwnd:
            if hwnd:
                left, top, _, _ = win32gui.GetWindowRect(hwnd)
                lx, ly = int(x - left), int(y - top)
            else:
                lx, ly = int(x), int(y)
            h, w = bgr.shape[:2]
            if 0 <= lx < w and 0 <= ly < h:
                return bgr_to_hex(bgr[ly, lx])

    # 2) 无快照：截 1x1
    from .screen import screenCapture

    if hwnd:
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        lx, ly = int(x - left), int(y - top)
        if lx < 0 or ly < 0:
            return None
        img = screenCapture(hwnd=hwnd, region=(lx, ly, 1, 1))
    else:
        img = screenCapture(region=(int(x), int(y), 1, 1))
    if img is None or img.size == 0:
        return None
    bgr = _as_bgr(img)
    return bgr_to_hex(bgr[0, 0])


def getColor(x, y, hwnd=None):
    """getPixel 的别名（按键精灵习惯名）"""
    return getPixel(x, y, hwnd=hwnd)


def getColorAt(img, x, y):
    """从已给的图（ndarray）里取 (x, y) 的 0xRRGGBB 颜色。"""
    bgr = _as_bgr(img)
    if bgr is None:
        return None
    h, w = bgr.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return None
    return bgr_to_hex(bgr[int(y), int(x)])


# ---------------------------------------------------------------- 比色


def compareColor(x, y, color, sim=0, hwnd=None):
    """
    比色：判断指定点颜色是否等于给定色。

    参数:
        x, y: 坐标
        color: 0xRRGGBB 或 '#RRGGBB' 或 (r,g,b)
        sim: 每通道容差 0~255，0 为精确比色
        hwnd: 窗口句柄（可选）
    返回: True / False
    """
    actual = getPixel(x, y, hwnd=hwnd)
    if actual is None:
        return False
    return compareColorEx(actual, color, sim)


def compareColorEx(actual, expected, sim=0):
    """
    两个 0xRRGGBB 颜色的相似比较。

    参数:
        actual: 实际颜色 0xRRGGBB
        expected: 期望颜色 0xRRGGBB
        sim: 每通道容差
    返回: True / False
    """
    ab, ag, ar = rgb_to_bgr(actual)
    eb, eg, er = hex_to_bgr(expected)
    return (abs(ab - eb) <= sim and abs(ag - eg) <= sim and abs(ar - er) <= sim)


# ---------------------------------------------------------------- 找色


def findColor(color, region=None, sim=0, hwnd=None, img=_UNSET, all_points=False):
    """
    找色：在区域内找指定颜色的**第一个**坐标（优先屏幕坐标）。

    参数:
        color: 0xRRGGBB / '#RRGGBB' / (r,g,b)
        region: (x, y, w, h) 搜索区域；None 表示全屏/整窗
        sim: 每通道容差 0~255
        hwnd: 窗口句柄（可选）
        img: 直接给定图像（给了就不截图；显式传 None 会返回未命中）
        all_points: True 时返回全部命中坐标
    返回:
        (x, y) 或 None；all_points=True 时返回 [(x, y), ...]
    """
    if img is not _UNSET:
        bgr = _as_bgr(img)
        sx = sy = 0
        if bgr is None:
            return [] if all_points else None
    else:
        bgr, ox, oy = _grab_cached(hwnd=hwnd, region=region)
        sx, sy = _to_screen(hwnd, ox, oy)
        if bgr is None:
            return [] if all_points else None

    mask = _color_mask(bgr, color, sim)

    if not all_points:
        # 快速路径：只要首个点（findNonZero 比 np.where 快约 2 倍）
        pts = cv2.findNonZero(mask)
        if pts is None:
            return None
        x, y = int(pts[0][0][0]), int(pts[0][0][1])
        return (x + sx, y + sy)

    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return []
    return [(int(x) + sx, int(y) + sy) for x, y in zip(xs, ys)]


def findColorEx(color, region=None, sim=0, hwnd=None, img=_UNSET, limit=0):
    """
    找色（全部）：返回所有匹配坐标。

    参数:
        limit: 最多返回多少个（0 为不限）
    """
    pts = findColor(color, region=region, sim=sim, hwnd=hwnd, img=img,
                    all_points=True)
    if limit and limit > 0:
        return pts[:limit]
    return pts


def countColor(color, region=None, sim=0, hwnd=None, img=_UNSET):
    """统计区域内指定颜色的像素数。"""
    if img is not _UNSET:
        bgr = _as_bgr(img)
    else:
        bgr, _, _ = _grab_cached(hwnd=hwnd, region=region)
    if bgr is None:
        return 0
    mask = _color_mask(bgr, color, sim)
    return int(cv2.countNonZero(mask))


def findColorBlock(color, region=None, sim=0, hwnd=None, img=_UNSET, min_area=20):
    """
    找色块：找出指定颜色的连通区域（比单点找色更抗噪）。

    参数:
        min_area: 最小连通面积（像素），小于此值忽略
    返回: [{"x": 左, "y": 上, "w": 宽, "h": 高,
            "cx": 中心x, "cy": 中心y, "area": 面积}, ...]
    """
    if img is not _UNSET:
        bgr = _as_bgr(img)
        sx = sy = 0
    else:
        bgr, ox, oy = _grab_cached(hwnd=hwnd, region=region)
        sx, sy = _to_screen(hwnd, ox, oy)
        if bgr is None:
            return []

    if bgr is None:
        return []

    mask = _color_mask(bgr, color, sim)
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    blocks = []
    for i in range(1, num):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        cx, cy = centroids[i]
        blocks.append({
            "x": x + sx, "y": y + sy, "w": w, "h": h,
            "cx": int(cx) + sx, "cy": int(cy) + sy, "area": area,
        })
    blocks.sort(key=lambda b: b["area"], reverse=True)
    return blocks


# ---------------------------------------------------------------- 多点找色


def findMultiColor(first_color, offsets, region=None, sim=0, hwnd=None,
                   img=_UNSET, all_points=False):
    """
    多点找色：先找主色，再校验一组偏移点的颜色 —— 抗干扰最强的方式。

    参数:
        first_color: 主色 0xRRGGBB
        offsets: [((dx, dy), color), ...] 偏移点与对应颜色
                 也接受 [(dx, dy, color), ...] 写法
        region: 搜索区域
        sim: 每通道容差
        hwnd / img: 同 findColor
        all_points: True 返回全部命中，False 只返回第一个
    返回: (x, y) / None，或 [(x, y), ...]

    示例:
        # 找「左上角红 + 右侧 10px 绿 + 下方 5px 蓝」的图案
        findMultiColor(0xFF0000,
                       [((10, 0), 0x00FF00), ((0, 5), 0x0000FF)],
                       region=(0, 0, 800, 600), sim=10)
    """
    if img is not _UNSET:
        bgr = _as_bgr(img)
        sx = sy = 0
    else:
        bgr, ox, oy = _grab_cached(hwnd=hwnd, region=region)
        sx, sy = _to_screen(hwnd, ox, oy)
        if bgr is None:
            return [] if all_points else None
    if bgr is None:
        return [] if all_points else None

    # 统一 offsets 格式 -> [(dx, dy, (b,g,r))]
    norm = []
    for item in offsets:
        if len(item) == 2 and isinstance(item[0], (tuple, list)):
            # ((dx, dy), color)
            (dx, dy), col = item
        elif len(item) == 3:
            # (dx, dy, color)
            dx, dy, col = item
        else:
            raise ValueError(
                "offsets 元素应为 ((dx,dy), color) 或 (dx,dy,color)，收到: %r" % (item,))
        norm.append((int(dx), int(dy), hex_to_bgr(col)))

    h, w = bgr.shape[:2]

    # 1) 主色候选
    first = _color_mask(bgr, first_color, sim)
    ys, xs = np.where(first > 0)
    if len(xs) == 0:
        return [] if all_points else None

    # 2) 向量化校验所有偏移点（一次性取值，不做 Python 循环扫像素）
    ok = np.ones(len(xs), dtype=bool)
    for dx, dy, (cb, cg, cr) in norm:
        px = xs + dx
        py = ys + dy
        valid = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        ok &= valid
        if not ok.any():
            break
        px_c = np.clip(px, 0, w - 1)
        py_c = np.clip(py, 0, h - 1)
        vals = bgr[py_c, px_c]
        if sim <= 0:
            ok &= (vals[:, 0] == cb) & (vals[:, 1] == cg) & (vals[:, 2] == cr)
        else:
            ok &= (np.abs(vals[:, 0].astype(np.int16) - cb) <= sim)
            ok &= (np.abs(vals[:, 1].astype(np.int16) - cg) <= sim)
            ok &= (np.abs(vals[:, 2].astype(np.int16) - cr) <= sim)
        if not ok.any():
            break

    hits = np.where(ok)[0]
    if len(hits) == 0:
        return [] if all_points else None

    if not all_points:
        i = hits[0]
        return (int(xs[i]) + sx, int(ys[i]) + sy)
    return [(int(xs[i]) + sx, int(ys[i]) + sy) for i in hits]


def findMultiColorEx(first_color, offsets, region=None, sim=0, hwnd=None,
                     img=_UNSET, limit=0):
    """多点找色（全部）。"""
    pts = findMultiColor(first_color, offsets, region=region, sim=sim,
                         hwnd=hwnd, img=img, all_points=True)
    if limit and limit > 0:
        return pts[:limit]
    return pts


# ---------------------------------------------------------------- 找色点击


def findColorClick(color, offsets=None, region=None, sim=0, hwnd=None,
                   isclick=True, button="left", offset=3, all_points=False):
    """
    找色并点击（与 findClick 的用法对齐，但按颜色而非图片定位）。

    参数:
        color: 主色 0xRRGGBB
        offsets: 给了就走多点找色，否则单色找色
        region / sim / hwnd: 同 findColor
        isclick: 是否真的点击
        button: left / right / doubleleft / enter
        offset: 点击随机偏移
        all_points: 是否点击全部命中
    返回: 找到的坐标（全部时返回列表），未找到返回 None / []
    """
    from .mouse import click_it, click_point
    from ._compat import win32gui

    if offsets:
        pts = findMultiColor(color, offsets, region=region, sim=sim,
                             hwnd=hwnd, all_points=all_points)
    elif all_points:
        pts = findColorEx(color, region=region, sim=sim, hwnd=hwnd)
    else:
        pts = findColor(color, region=region, sim=sim, hwnd=hwnd)

    if not pts:
        return [] if all_points else None

    if not all_points:
        pts = [pts]

    for x, y in pts:
        if isclick:
            if hwnd:
                # 后台点击：坐标是屏幕坐标，click_point 内部转客户区
                click_point((x, y), hwnd=hwnd, offset=offset)
            else:
                click_it(x=x, y=y, button=button, offset=offset)
    return pts if all_points else pts[0]


# ---------------------------------------------------------------- 颜色范围


def _range_mask(bgr, lo_color, hi_color):
    """生成 [lo, hi] 颜色区间掩码（通道各自比较，适合"任意红"这类需求）。"""
    lb, lg, lr = hex_to_bgr(lo_color)
    hb, hg, hr = hex_to_bgr(hi_color)
    lower = np.array([min(lb, hb), min(lg, hg), min(lr, hr)], np.uint8)
    upper = np.array([max(lb, hb), max(lg, hg), max(lr, hr)], np.uint8)
    return cv2.inRange(bgr, lower, upper)


def findColorRange(low, high, region=None, hwnd=None, img=_UNSET,
                   all_points=False, limit=0):
    """
    颜色范围找色：在 [low, high] 颜色区间内找像素。

    适合「任意红」「深灰到浅灰」这类无法给出单一精确色的场景。
    区间按 RGB 三分量各自比较，low/high 顺序无所谓（内部会取 min/max）。

    参数:
        low:  颜色下界 0xRRGGBB（如 0x800000 深红）
        high: 颜色上界 0xRRGGBB（如 0xFF3333 浅红）
        region / hwnd / img: 同 findColor
        all_points: True 返回全部
        limit: 全部模式下最多返回多少个
    返回: (x, y) / None，或 [(x, y), ...]

    示例:
        # 找屏幕上任意偏红的像素
        findColorRange(0x800000, 0xFF4040)
        # 找深色按钮区域（深灰到中灰）
        findColorRange(0x303030, 0x707070, region=(0, 0, 1920, 1080))
    """
    if img is not _UNSET:
        bgr = _as_bgr(img)
        sx = sy = 0
        if bgr is None:
            return [] if all_points else None
    else:
        bgr, ox, oy = _grab_cached(hwnd=hwnd, region=region)
        sx, sy = _to_screen(hwnd, ox, oy)
        if bgr is None:
            return [] if all_points else None

    mask = _range_mask(bgr, low, high)

    if not all_points:
        pts = cv2.findNonZero(mask)
        if pts is None:
            return None
        return (int(pts[0][0][0]) + sx, int(pts[0][0][1]) + sy)

    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return []
    result = [(int(x) + sx, int(y) + sy) for x, y in zip(xs, ys)]
    return result[:limit] if limit and limit > 0 else result


def countColorRange(low, high, region=None, hwnd=None, img=_UNSET):
    """统计落在颜色区间内的像素数。"""
    if img is not _UNSET:
        bgr = _as_bgr(img)
    else:
        bgr, _, _ = _grab_cached(hwnd=hwnd, region=region)
    if bgr is None:
        return 0
    return int(cv2.countNonZero(_range_mask(bgr, low, high)))


# ---------------------------------------------------------------- 等待


def waitColor(color, timeout=10.0, interval=0.05, region=None, sim=0,
              hwnd=None, all_points=False):
    """
    等待颜色出现（带超时）——挂机脚本最常用的等待原语。

    每次轮询都会重新截图（画面在变，不能用旧快照）。

    参数:
        color: 目标色 0xRRGGBB
        timeout: 最长等待秒数；<=0 表示只检测一次
        interval: 轮询间隔秒数
        region / sim / hwnd: 同 findColor
        all_points: True 返回全部命中点
    返回:
        命中: (x, y) 或 [(x, y), ...]
        超时: None / []
    """
    deadline = time.monotonic() + max(timeout, 0)
    while True:
        # 每次都重新抓图（不能复用快照，否则画面不会更新）
        pts = findColor(color, region=region, sim=sim, hwnd=hwnd,
                        all_points=all_points)
        if pts:
            return pts
        remain = deadline - time.monotonic()
        if remain <= 0:
            return [] if all_points else None
        time.sleep(min(interval, remain))


def waitColorDisappear(color, timeout=10.0, interval=0.05, region=None,
                       sim=0, hwnd=None):
    """
    等待颜色消失（例如等 loading 转圈的某个色块消失）。

    返回: True 已消失 / False 超时仍存在
    """
    deadline = time.monotonic() + max(timeout, 0)
    while True:
        if findColor(color, region=region, sim=sim, hwnd=hwnd) is None:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.001)))


def waitColorChange(x, y, timeout=10.0, interval=0.05, hwnd=None):
    """
    等待某点颜色变化（点击后等界面响应）。

    参数:
        x, y: 屏幕坐标
        timeout: 最长等待秒数
    返回: 变化后的新颜色 0xRRGGBB；超时返回 None
    """
    base = getPixel(x, y, hwnd=hwnd)
    if base is None:
        return None
    deadline = time.monotonic() + max(timeout, 0)
    while True:
        cur = getPixel(x, y, hwnd=hwnd)
        if cur is not None and cur != base:
            return cur
        if time.monotonic() >= deadline:
            return None
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.001)))


def waitMultiColor(first_color, offsets, timeout=10.0, interval=0.05,
                   region=None, sim=0, hwnd=None):
    """
    等待多点找色命中（比单色等待更抗干扰）。
    返回: (x, y) 或 None
    """
    deadline = time.monotonic() + max(timeout, 0)
    while True:
        pt = findMultiColor(first_color, offsets, region=region, sim=sim,
                            hwnd=hwnd)
        if pt is not None:
            return pt
        if time.monotonic() >= deadline:
            return None
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.001)))
