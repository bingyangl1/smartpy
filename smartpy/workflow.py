# -*- coding: utf-8 -*-
"""smartpy.workflow —— 配置驱动的任务执行 + 定时内存回收线程。

相对旧 Module.py 的修复：
- runWork / runWorkN 旧版 num>1 时把 workList 整个替换成 workList[0] 的
  重复列表（语义错误），现在 num 表示「把整个任务列表重复 num 遍」。
- ThreadPoolExecutor.map 的惰性生成器在 with 退出后遍历会抛
  RuntimeError（can't schedule new futures after shutdown），
  现在在 with 内物化成 list 再返回。
- repeat() 旧版调用不存在的 createTimer，现在实现为循环定时器。
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import wrapt

__all__ = ["runWork", "runWorkN", "runWorkConfig", "runTimer", "repeat"]


def runWork(func, workList, num=1, max_workers=4):
    """
    功能: 用线程池执行任务列表
    参数:
        func: 待执行函数
        workList: 参数列表 [{kw: v}, ...]
        num: 整个列表重复执行次数
        max_workers: 线程数
    返回: 结果 list
    """
    tasks = workList * max(num, 1)
    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix=getattr(func, "__name__", "worker"),
    ) as pool:
        results = list(pool.map(lambda args: func(**args), tasks))
    return results


def runWorkN(func, workList, num=1, max_workers=4):
    """同 runWork（保留旧名）"""
    return runWork(func, workList, num=num, max_workers=max_workers)


def runWorkConfig(func):
    """装饰器：把被装饰配置函数返回的 [{kw: v}] 列表用线程池执行"""
    @wrapt.decorator
    def wrapper(config, instance, args, kwargs):
        workList = config(*args, **kwargs)
        with ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix=getattr(func, "__name__", "worker"),
        ) as pool:
            results = list(pool.map(lambda work: func(**work), workList))
        return results

    return wrapper


def runTimer(sleep=60, func=None):
    """
    启动一个一次性定时器，sleep 秒后执行 func
    """
    def _run():
        if func is not None:
            func()

    t = threading.Timer(sleep, _run)
    t.setDaemon(True)
    t.start()
    return t


def repeat(sleep=60, func=None, forever=True):
    """
    循环定时执行 func
    参数:
        sleep: 间隔秒数
        func: 回调
        forever: True 无限循环；False 执行一次
    返回: 停止函数 stop()
    """
    stopped = threading.Event()

    def _loop():
        while not stopped.is_set():
            if func is not None:
                func()
            if not forever or stopped.wait(sleep):
                break

    t = threading.Thread(target=_loop, daemon=True)
    t.start()

    def stop():
        stopped.set()

    return stop
