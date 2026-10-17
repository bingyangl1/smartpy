# -*- coding: utf-8 -*-
"""smartpy.util —— 计时装饰器、格式化输出、文件操作。

重构要点（相对旧 Module.py）：
- 显示宽度改用 unicodedata.east_asian_width 计算，彻底去掉 gbk 字节长度，
  emoji / 生僻字 / 非 GBK 字符不再 UnicodeEncodeError。
- getFile / getDir 返回确定顺序的 list（旧版返回 set，顺序每次都不一样）。
- copyFile / moveFile 同时支持「目标目录」与「目标文件路径」两种写法。
"""

import os
import shutil
import subprocess
import sys
import time
import unicodedata
from functools import wraps

import wrapt

__all__ = [
    "Timer",
    "timer",
    "prints",
    "printf",
    "printc",
    "printa",
    "copyFile",
    "getFile",
    "moveFiles",
    "moveFile",
    "getDir",
    "TraverseDir",
    "matchFile",
]


# ---------------------------------------------------------------- 计时装饰器


class Timer:
    """
    功能:
        装饰器，用于计算函数运行的时间
    参数:
        show 是否输出 True/False
    示例:
        @Timer()
        def func():
            print(f'func name:{func.__name__}')
    """

    def __init__(self, show=True):
        self.show = show

    def __call__(self, func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            start = time.perf_counter() if self.show else 0.0
            ret = func(*args, **kwargs)
            if self.show:
                print(
                    "执行 %s 方法 用时 %.3fS"
                    % (func.__name__, time.perf_counter() - start)
                )
            return ret

        return wrapped_function


def timer():
    """
    功能:
        装饰器，用于计算函数运行的时间（wrapt 实现，保留原签名/文档）
    """
    @wrapt.decorator
    def wrapper(func, instance, args, kwargs):
        start = time.perf_counter()
        ret = func(*args, **kwargs)
        print("执行%s耗时 %.3fS" % (func.__name__, time.perf_counter() - start))
        return ret

    return wrapper


# ---------------------------------------------------------------- 格式化输出


def _display_width(text):
    """按显示宽度计算：东亚全角记 2，其余记 1（替代旧版 gbk 字节长度）。"""
    width = 0
    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _wrap(text, width):
    """按显示宽度把字符串切成多行，不拆字符。"""
    lines, cur, curw = [], "", 0
    for ch in str(text):
        cw = _display_width(ch)
        if cur and curw + cw > width:
            lines.append(cur)
            cur, curw = ch, cw
        else:
            cur += ch
            curw += cw
    if cur:
        lines.append(cur)
    return lines or [""]


def _center(text, width, fillchar):
    text = str(text)
    w = _display_width(text)
    if w >= width:
        return text
    left = (width - w) // 2
    return fillchar * left + text + fillchar * (width - w - left)


def _cls():
    if os.name == "nt":
        os.system("cls")
    else:
        subprocess.call("clear", shell=True)


def prints(strs="", width=60, fillchar="", pre="|", end="|", isPrint=True, cls=False):
    """
    介绍: 格式化输出字符串（居中填充）
    参数:
        strs: 要输出的字符串
        width: 填充宽度 默认60
        fillchar: 填充字符 默认 ''
        pre: 前缀 默认 '|'
        end: 后缀 默认 '|'
        isPrint: 是否输出 默认 True
        cls: 是否清屏
    """
    if cls:
        _cls()
    if not isPrint:
        return
    pre_end_len = _display_width(pre) + _display_width(end)
    body = _center(strs, max(width - pre_end_len, 1), fillchar)
    print("{0}{1}{2}".format(pre, body, end))


def printf(strs="", width=60, fillchar="", pre="|", end="|", isPrint=True, cls=False, debug=False):
    """
    介绍: 格式化输出字符串（居中填充，中文按全角宽度对齐）
    参数同 prints，另有 debug 输出宽度信息
    """
    if cls:
        _cls()
    if not isPrint:
        return
    pre_end_len = _display_width(pre) + _display_width(end)
    body = _center(strs, max(width - pre_end_len, 1), fillchar)
    if debug:
        print(
            "str width:", _display_width(strs),
            "fill width:", max(width - pre_end_len, 1),
        )
    print("{0}{1}{2}".format(pre, body, end))


def printc(message, color, end='\n', defaultColor=0x0A):
    """
    彩色输出（仅 Windows cmd）
    颜色属性由两个十六进制数字指定 -- 第一个对应背景，第二个对应前景：
        0 = 黑色       8 = 灰色
        1 = 蓝色       9 = 淡蓝色
        2 = 绿色       A = 淡绿色
        3 = 浅绿色     B = 淡浅绿色
        4 = 红色       C = 淡红色
        5 = 紫色       D = 淡紫色
        6 = 黄色       E = 淡黄色
        7 = 白色       F = 亮白色
    """
    if sys.platform != "win32":
        print(message, end=end)
        return
    import ctypes

    std_out_handle = ctypes.windll.kernel32.GetStdHandle(-11)
    ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, color)
    sys.stdout.write(message + end)
    sys.stdout.flush()
    ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, defaultColor)


def printa(strs="", width=60, fillchar=" ", pre="|", end="|", cls=False, debug=False,
           EOL='\r', showTime=0, printEOF=''):
    """
    介绍: 按宽度自动换行 + 居中填充输出
    参数:
        strs: 要输出的字符串
        width: 每行宽度（不含前缀后缀） 默认60
        fillchar: 填充字符 默认 ' '
        pre / end: 前缀 / 后缀
        cls: 是否清屏
        EOL: 行首控制符（'\\r' 回到行首，'\\n' 换行，'\\t' 制表）
        showTime: 每行输出间隔秒数
        printEOF: print 的 end 参数
    """
    if cls:
        _cls()
    body_width = max(width - _display_width(pre) - _display_width(end), 1)
    for line in _wrap(strs, body_width):
        if fillchar in ("", " ") and any(
            unicodedata.east_asian_width(ch) in ("W", "F") for ch in line
        ):
            fill = "\u3000"
        else:
            fill = fillchar
        body = _center(line, body_width, fill)
        if debug:
            print("width check:", _display_width(body))
        print(EOL + "{0}{1}{2}".format(pre, body, end), end=printEOF)
        if showTime > 0:
            time.sleep(showTime)


# ---------------------------------------------------------------- 文件操作


def copyFile(srcFile, dstDir):
    """
    功能: 复制 srcFile 到 dstDir
    参数:
        srcFile: 源文件 str
        dstDir: 目标目录（D:/）或目标文件路径（D:/test.txt） str
    """
    if not os.path.isfile(srcFile):
        print("%s 不存在" % (srcFile,))
        return
    if os.path.isdir(dstDir):
        dst = os.path.join(dstDir, os.path.basename(srcFile))
    else:
        dst = dstDir
        parent = os.path.dirname(dst)
        if parent and not os.path.exists(parent):
            os.makedirs(parent)
    shutil.copy2(srcFile, dst)
    print("复制文件 %s -> %s" % (srcFile, dst))


def getFile(path, show=False):
    """
    功能: 获取 path 路径下的所有文件
    返回值: 确定顺序（按名称排序）的文件路径 list
    """
    start = time.perf_counter()
    alllist = TraverseDir(path)
    filelist = sorted(i for i in alllist if os.path.isfile(i))
    if show:
        print("\n".join(filelist))
        print(
            "Function :[ %s ] 耗时%.2fS "
            % (sys._getframe().f_code.co_name, time.perf_counter() - start)
        )
    return filelist


def moveFiles(srcDir, dstDir):
    """功能: 将 srcDir 文件夹下的所有文件移动到 dstDir"""
    for file in getFile(srcDir):
        moveFile(file, dstDir)


def moveFile(srcFile, dstDir):
    """
    功能: 将 srcFile 移动至 dstDir
    参数:
        srcFile: 源文件
        dstDir: 目标目录（D:/）或目标文件路径（D:/test.txt）
    """
    if not os.path.isfile(srcFile):
        print("%s 不存在" % (srcFile,))
        return
    if os.path.isdir(dstDir):
        dst = os.path.join(dstDir, os.path.basename(srcFile))
    else:
        dst = dstDir
        parent = os.path.dirname(dst)
        if parent and not os.path.exists(parent):
            os.makedirs(parent)
    shutil.move(srcFile, dst)
    print("移动文件 %s -> %s" % (srcFile, dst))


def getDir(path, show=False):
    """
    功能: 获取 path 下的所有文件夹
    返回值: 确定顺序（按名称排序）的目录路径 list
    """
    start = time.perf_counter()
    alllist = TraverseDir(path)
    dirlist = sorted(i for i in alllist if os.path.isdir(i))
    if show:
        print("\n".join(dirlist))
        print(
            "Function :[ %s ] 耗时%.2fS "
            % (sys._getframe().f_code.co_name, time.perf_counter() - start)
        )
    return dirlist


def TraverseDir(rootDir, level=1, show=False):
    """
    功能: 遍历 rootDir 路径
    参数:
        rootDir 需要遍历的目录 str
    返回值: 所有文件与子目录的路径 list
    """
    alllist = []
    if level == 1 and show:
        print(rootDir)
    for name in os.listdir(rootDir):
        path = os.path.join(rootDir, name)
        if show:
            print("│  " * (level - 1) + "│--" + name)
        alllist.append(path)
        if os.path.isdir(path):
            try:
                alllist += TraverseDir(path, level + 1, show=show)
            except OSError:
                # 无权限 / 已删除的目录直接跳过
                continue
    return alllist


def matchFile(key, pathList):
    """
    功能: 从指定的 pathList 中匹配包含 key 的条目
    参数:
        key: str 返回第一个匹配；list 返回全部匹配
    """
    if isinstance(key, str):
        for path in pathList:
            if key in path:
                return path
        return None
    if isinstance(key, (list, tuple)):
        result = []
        for k in key:
            for path in pathList:
                if k in path:
                    result.append(path)
        return result
    print("传入的key参数类型错误")
    return None
