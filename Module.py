# -*- coding: utf-8 -*-
"""
Module.py —— 旧代码兼容 shim。

用法:
    import sys
    sys.path.insert(0, r'<项目根目录>')
    import Module
    Module.findClick(...)

实现: 直接转发到重构后的 smartpy 包。
"""

from smartpy import *  # noqa: F401,F403
from smartpy import __version__  # noqa: F401
