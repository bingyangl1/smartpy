# -*- coding: utf-8 -*-
"""smartpy.xfeat —— XFeat (CVPR 2024) 特征匹配适配器。

与 matchTemplate 的分工：
- matchTemplate：像素级同源（同分辨率/同缩放/同亮度）的 UI 图标，最快最准 —— 主力
- XFeat：模板被缩放 / 旋转 / 亮度变化 / 轻微透视变形时仍能定位 —— 兜底

XFeat 的能力边界（实测）：
- 模板纹理越丰富越准（std 高、唯一色数多）
- 纯色块 / 渐变面板这类弱纹理模板提不出特征，会自动拒绝并建议用 matchTemplate
- CPU 640x480 特征提取约 30ms；特征可缓存，模板侧只算一次

依赖：torch + kornia。首次调用会下载约 6MB 权重（缓存在
~/.cache/torch/hub/checkpoints/xfeat.pt）。
"""

import math
import os

import cv2
import numpy as np

__all__ = ["xfeat_match", "xfeat_available", "XFeatLocator"]

_MODEL = None
_DEVICE = None
_CACHE = {}          # key -> (keypoints, descriptors)
_CACHE_MAX = 64


def _try_import():
    try:
        import torch  # noqa: F401
        from kornia.feature import XFeat  # noqa: F401
        return True
    except Exception:
        return False


def xfeat_available():
    """XFeat 依赖是否就绪（torch + kornia 可导入）。"""
    return _try_import()


def _get_model():
    global _MODEL, _DEVICE
    if _MODEL is not None:
        return _MODEL
    from kornia.feature import XFeat

    _ensure_weights()
    model = XFeat.from_pretrained()
    # ROCm/GPU 首次初始化可能很慢或不可用，默认优先 CPU，可用环境变量开启 GPU
    import torch

    want_gpu = (
        os.environ.get("SMARTPY_XFEAT_GPU")
        or os.environ.get("AUTOPY_XFEAT_GPU")   # 旧名兼容
        or "0"
    ) == "1"
    if want_gpu and torch.cuda.is_available():
        try:
            model = model.to("cuda")
            _DEVICE = "cuda"
        except Exception:
            _DEVICE = "cpu"
    else:
        _DEVICE = "cpu"
    model.eval()
    _MODEL = model
    return _MODEL


_WEIGHTS_FILE = "xfeat.pt"
_WEIGHTS_URL = ("https://raw.githubusercontent.com/verlab/accelerated_features/"
                "main/weights/xfeat.pt")
_WEIGHTS_SIZE = 6247949


def _ckpt_dir():
    return os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints")


def weights_path():
    """权重缓存路径。"""
    return os.path.join(_ckpt_dir(), _WEIGHTS_FILE)


def _ensure_weights(proxy=None):
    """本地无权重时，走代理 + 重试下载（GitHub 直连实测要 6 分钟，代理 3.6 秒）。"""
    dest = weights_path()
    if os.path.isfile(dest) and os.path.getsize(dest) == _WEIGHTS_SIZE:
        return dest
    try:
        from .net import download_with_proxy, enable_proxy
    except Exception:
        return dest  # 交给 kornia 自己下载

    print("[xfeat] 本地权重缺失，尝试走代理下载…")
    enable_proxy()
    ok, info = download_with_proxy(_WEIGHTS_URL, dest, proxy=proxy,
                                   retries=5, expected_size=_WEIGHTS_SIZE)
    if ok:
        print("[xfeat] 权重下载完成: %d bytes (%d 次尝试)" % (info["size"], info["attempts"]))
    else:
        print("[xfeat] 代理下载失败（%s），回退给 kornia 自行下载" % info.get("error"))
    return dest


def _to_tensor(img):
    """BGR/BGRA/Gray ndarray -> (1,3,H,W) float tensor on device"""
    import torch

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float().div(255.0)
    t = t.unsqueeze(0)
    if _DEVICE == "cuda":
        t = t.to("cuda")
    return t


def _texture_score(img):
    """模板纹理丰富度：0~1，太低说明不适合特征匹配。"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    std = float(gray.std())
    uniq = len(np.unique(gray))
    # 经验阈值：std<8 或唯一色数<24 视为弱纹理
    s = min(std / 30.0, 1.0) * 0.6 + min(uniq / 120.0, 1.0) * 0.4
    return s


def _extract(img, top_k=2048, use_cache=True, cache_key=None):
    """提取关键点与描述子（可缓存，键为模板路径或内容 hash）。"""
    if use_cache and cache_key is not None and cache_key in _CACHE:
        return _CACHE[cache_key]

    import torch

    model = _get_model()
    with torch.inference_mode():
        out = model.detectAndCompute(_to_tensor(img), top_k=top_k)[0]
    kp = out["keypoints"].detach().cpu().numpy()
    desc = out["descriptors"].detach().cpu().numpy()

    if use_cache and cache_key is not None:
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[cache_key] = (kp, desc)
    return kp, desc


def _locate(tpl_kp, tpl_desc, src_kp, src_desc, ratio=0.95, min_sim=0.5,
            ransac=5.0, min_inliers=6):
    """双向互匹配 + RANSAC 单应性，返回 (H, 内点数)。"""
    if len(tpl_kp) < 4 or len(src_kp) < 4:
        return None, 0
    a = tpl_desc / (np.linalg.norm(tpl_desc, axis=1, keepdims=True) + 1e-8)
    b = src_desc / (np.linalg.norm(src_desc, axis=1, keepdims=True) + 1e-8)
    sim = a @ b.T
    nn_ts = sim.argmax(axis=1)
    nn_st = sim.argmax(axis=0)
    mutual = nn_st[nn_ts] == np.arange(len(nn_ts))
    best = sim[np.arange(len(sim)), nn_ts]
    sim2 = sim.copy()
    sim2[np.arange(len(sim2)), nn_ts] = -1.0
    second = sim2.max(axis=1)
    keep = mutual & (best > min_sim) & ((second / (best + 1e-8)) < ratio)
    if keep.sum() < 4:
        return None, int(keep.sum())
    H, mask = cv2.findHomography(tpl_kp[keep], src_kp[nn_ts[keep]], cv2.RANSAC, ransac)
    if H is None:
        return None, int(keep.sum())
    inliers = int(mask.sum())
    if inliers < min_inliers:
        return None, inliers
    return H, inliers


class XFeatLocator:
    """
    XFeat 定位器（可复用实例，模板特征缓存）。

    示例:
        loc = XFeatLocator()
        pts = loc.locate(template, screenshot)   # [(x, y)]
    """

    def __init__(self, top_k=2048, ratio=0.95, min_sim=0.5, min_inliers=6,
                 min_texture=0.25):
        self.top_k = top_k
        self.ratio = ratio
        self.min_sim = min_sim
        self.min_inliers = min_inliers
        self.min_texture = min_texture

    def locate(self, template, screenshot, midpoint=True, debug=False):
        """
        参数:
            template: 模板 ndarray
            screenshot: 大图 ndarray
            midpoint: True 返回中心点，False 返回左上角（由单应性反算）
            debug: 打印诊断
        返回: [(x, y), ...]（0 或 1 个点）；失败返回 []
        """
        if template is None or screenshot is None:
            return []
        th, tw = template.shape[:2]
        sh, sw = screenshot.shape[:2]
        if th > sh or tw > sw:
            return []
        if th < 12 or tw < 12:
            if debug:
                print("[xfeat] 模板过小（%dx%d），特征不足" % (tw, th))
            return []

        tex = _texture_score(template)
        if tex < self.min_texture:
            if debug:
                print("[xfeat] 模板弱纹理（score %.2f < %.2f），建议用 matchTemplate"
                      % (tex, self.min_texture))
            return []

        tpl_kp, tpl_desc = _extract(template, self.top_k)
        src_kp, src_desc = _extract(screenshot, self.top_k, use_cache=False)
        if debug:
            print("[xfeat] 模板点=%d 大图点=%d 纹理=%.2f"
                  % (len(tpl_kp), len(src_kp), tex))

        H, inliers = _locate(tpl_kp, tpl_desc, src_kp, src_desc,
                             self.ratio, self.min_sim, min_inliers=self.min_inliers)
        if H is None:
            if debug:
                print("[xfeat] 定位失败（内点 %d < %d）" % (inliers, self.min_inliers))
            return []

        if midpoint:
            probe = np.float32([[[tw / 2.0, th / 2.0]]])
        else:
            probe = np.float32([[[0.0, 0.0]]])
        dst = cv2.perspectiveTransform(probe, H)[0][0]
        x, y = float(dst[0]), float(dst[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            return []
        if not (0 <= x < sw and 0 <= y < sh):
            if debug:
                print("[xfeat] 定位越界 (%.1f, %.1f)" % (x, y))
            return []
        if debug:
            print("[xfeat] 命中 (%.1f, %.1f) 内点 %d" % (x, y, inliers))
        return [(int(round(x)), int(round(y)))]


_LOCATOR = None


def _get_locator():
    global _LOCATOR
    if _LOCATOR is None:
        _LOCATOR = XFeatLocator()
    return _LOCATOR


def xfeat_match(template, screenshot, midpoint=True, debug=False):
    """
    XFeat 特征匹配定位（与 matchTemplate 同风格：返回 [(x, y)]）。

    适合：模板被缩放 / 旋转 / 亮度变化时仍要定位
    不适合：纯色弱纹理模板（会自动返回 []，请用 matchTemplate）

    参数:
        template: 模板 ndarray
        screenshot: 大图 ndarray
        midpoint: 返回中心点 / 左上角
        debug: 输出诊断
    返回: [(x, y)] 或 []
    """
    if not _try_import():
        print("[xfeat] 缺少依赖，请先安装: pip install torch kornia")
        return []
    return _get_locator().locate(template, screenshot, midpoint=midpoint, debug=debug)
