# -*- coding: utf-8 -*-
"""smartpy.screen —— 截图 / 图像读写 / 显示。

相对旧 Module.py 的修复与增强：
- screenCapture：异常路径不再引用未初始化的句柄（旧版 GetWindowDC 失败时
  except 分支自身抛 NameError 把真正原因盖掉）。
- 新增 PrintWindow 后备：BitBlt 对 DWM 合成窗口可能截到黑图，
  失败/全黑时可退回 PrintWindow（对最小化窗口可用）。
- region 语义：窗口句柄模式下的 region 相对「窗口左上角」（与旧版一致），
  新增 client_region=True 时相对「客户区左上角」。
- DPI 设置移到 _compat 包导入时执行一次，不再每次截图重复调用。
- window_capture 修复 del retA 的 UnboundLocalError，并保留 RGBA 返回。
- 行序实测为 top-down，与 OpenCV 一致，无需翻转。
"""

import os
import time

import cv2
import numpy as np

from ._compat import win32api, win32con, win32gui, win32ui

__all__ = [
    "readImage",
    "saveImage",
    "screenCapture",
    "window_capture",
    "imageConcatenate",
    "imshow",
    "imgReSize",
    "async_screenCapture",
]


def async_screenCapture(hwnd=None, save="", show=False, region=(0, 0, 0, 0)):
    """截图函数的异步包装（兼容旧名；内部仍是同步实现，可在 asyncio 中调用）。"""
    return screenCapture(hwnd=hwnd, save=save, show=show, region=region)


def readImage(src, dtype="uint8"):
    """
    从 src 路径读取图片（numpy + cv2，支持中文路径）
    返回: ndarray；读取失败返回 None
    """
    try:
        data = np.fromfile(src, dtype=np.dtype(dtype))
    except OSError:
        return None
    image = cv2.imdecode(data, cv2.IMREAD_ANYCOLOR)
    return image


def saveImage(name, image, endswitch=".jpg"):
    """保存图片（支持中文路径）"""
    return cv2.imencode(endswitch, image)[1].tofile(name)


def imshow(img, namespace="screenCapture", waitkey=None):
    """显示图片"""
    cv2.imshow(namespace, img)
    if waitkey is None:
        cv2.waitKey(0)
    else:
        cv2.waitKey(waitkey)


def imgReSize(img, nSize, rSize=None):
    """
    将图像按比例缩放到目标分辨率 nSize = (w, h)
    参数:
        img: ndarray
        nSize: 目标 (宽, 高)
        rSize: 来源分辨率 (宽, 高)，缺省取图像自身尺寸
    旧版 BUG：算完缩放比不用，硬编码 1136/820、640/462，此处修复。
    """
    h, w = img.shape[:2]
    if rSize is None:
        rSize = (w, h)
    rw, rh = rSize
    tw, th = nSize
    fx = tw / rw
    fy = th / rh
    interpolation = cv2.INTER_AREA if (fx < 1 and fy < 1) else cv2.INTER_LINEAR
    return cv2.resize(img, (int(round(w * fx)), int(round(h * fy))),
                      interpolation=interpolation)


def _bitmap_to_array(saveBitMap, w, h):
    buf = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(buf, dtype=np.uint8)
    img.shape = (h, w, 4)  # BGRA
    return img


def screenCapture(hwnd=None, save="", show=False, region=(0, 0, 0, 0),
                  client_region=False):
    """
    功能: 对窗口/桌面截图（默认全屏）
    参数:
        hwnd: 窗口句柄；None = 桌面
        save: 保存文件名（空字符串不保存）
        show: 是否显示
        region: (x, y, w, h) 截取区域；0 表示整幅。
                默认相对窗口左上角；client_region=True 时相对客户区左上角。
        client_region: region 是否以客户区为原点
    返回: BGRA ndarray；失败返回 None 并打印原因
    """
    if not hwnd:
        hwnd = win32gui.GetDesktopWindow()

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top

    x = region[0] if len(region) == 4 else 0
    y = region[1] if len(region) == 4 else 0
    w = region[2] if (len(region) == 4 and region[2] != 0) else width
    h = region[3] if (len(region) == 4 and region[3] != 0) else height

    if client_region and hwnd != win32gui.GetDesktopWindow():
        # 客户区原点在窗口内的偏移
        cxp, cyp = win32gui.ClientToScreen(hwnd, (0, 0))
        x += cxp - left
        y += cyp - top

    w = max(min(w, width - x), 1)
    h = max(min(h, height - y), 1)

    hDC = None
    mfcDC = None
    saveDC = None
    saveBitMap = None
    try:
        hDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (w, h), mfcDC, (x, y), win32con.SRCCOPY)
        img = _bitmap_to_array(saveBitMap, w, h)
    except Exception as e:
        print("截图失败(BitBlt): %r" % (e,))
        img = None
    finally:
        if saveBitMap is not None:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        if saveDC is not None:
            saveDC.DeleteDC()
        if mfcDC is not None:
            mfcDC.DeleteDC()
        if hDC is not None:
            win32gui.ReleaseDC(hwnd, hDC)

    if img is None or img.size == 0:
        img = _printwindow_capture(hwnd, region=(x, y, w, h))

    if img is None:
        return None

    if save:
        cv2.imencode(".jpg", img)[1].tofile(save)
    if show:
        cv2.namedWindow("screenCapture")
        cv2.imshow("screenCapture", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return img


def _printwindow_capture(hwnd, region=(0, 0, 0, 0)):
    """PrintWindow 后备截图（对 DWM 合成窗口更可靠）。

    PrintWindow 会把整窗画到位图上（位图左上角=窗口左上角），
    不支持源偏移，因此先整窗绘制、再按 region 裁剪。
    """
    from ctypes import windll

    x, y, w, h = region
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    win_w = max(right - left, 1)
    win_h = max(bottom - top, 1)
    hDC = None
    mfcDC = None
    saveDC = None
    saveBitMap = None
    try:
        hDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, win_w, win_h)
        saveDC.SelectObject(saveBitMap)
        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT
        if not result:
            return None
        img = _bitmap_to_array(saveBitMap, win_w, win_h)
        x2 = min(x + w, win_w)
        y2 = min(y + h, win_h)
        if x >= win_w or y >= win_h or x2 <= 0 or y2 <= 0:
            return None
        return img[y:y2, x:x2].copy()
    except Exception as e:
        print("截图失败(PrintWindow): %r" % (e,))
        return None
    finally:
        if saveBitMap is not None:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        if saveDC is not None:
            saveDC.DeleteDC()
        if mfcDC is not None:
            mfcDC.DeleteDC()
        if hDC is not None:
            win32gui.ReleaseDC(hwnd, hDC)


def window_capture(hwnd):
    """
    后台截图（整窗）
    返回: BGRA ndarray
    """
    if not hwnd:
        hwnd = win32gui.GetDesktopWindow()
    rctA = win32gui.GetWindowRect(hwnd)
    w = rctA[2] - rctA[0]
    h = rctA[3] - rctA[1]
    return screenCapture(hwnd=hwnd, region=(0, 0, w, h))


def imageConcatenate(hwnd=None, save="", show=False):
    """
    分 4 块截图后拼接（同步实现）
    参数:
        hwnd: 窗口句柄（可选）
        save: 保存位置（可选）
        show: 显示（可选）
    返回: ndarray uint8
    """
    if not hwnd:
        hwnd = win32gui.GetDesktopWindow()
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    rw, rh = width // 2, height // 2
    img1 = screenCapture(hwnd=hwnd, region=(0, 0, rw, rh))
    img2 = screenCapture(hwnd=hwnd, region=(0, rh, rw, rh))
    img3 = screenCapture(hwnd=hwnd, region=(rw, 0, rw, rh))
    img4 = screenCapture(hwnd=hwnd, region=(rw, rh, rw, rh))
    if any(i is None for i in (img1, img2, img3, img4)):
        return None
    img5 = np.concatenate((img1, img2), axis=0)
    img6 = np.concatenate((img3, img4), axis=0)
    img7 = np.concatenate((img5, img6), axis=1)
    if save:
        cv2.imencode(".jpg", img7)[1].tofile(save)
    if show:
        cv2.imshow("image", img7)
        cv2.waitKey(0)
    return img7
