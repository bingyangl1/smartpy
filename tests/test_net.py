# -*- coding: utf-8 -*-
"""代理环境助手回归测试。

这些测试验证「配置逻辑」而非网络可达性（网络会变，不该进 CI 断言）。
需要真实网络的用例默认跳过，设 SMARTPY_NET_TEST=1 开启。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from smartpy import net


def test_proxy_url_default():
    assert net.PROXY_URL.startswith("http://")
    # 默认端口可被 SMARTPY_PROXY 覆盖，这里只校验格式
    assert ":" in net.PROXY_URL.split("//")[1]


def test_proxy_env_enable():
    env = net.proxy_env(True)
    assert env["HTTP_PROXY"] == net.PROXY_URL
    assert env["HTTPS_PROXY"] == net.PROXY_URL
    # arxiv 走代理反而慢，应在 NO_PROXY 里
    assert "arxiv.org" in env["NO_PROXY"]


def test_proxy_env_disable():
    env = net.proxy_env(False)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        assert k not in env


def test_proxy_env_custom():
    env = net.proxy_env(True, "http://127.0.0.1:7890")
    assert env["HTTPS_PROXY"] == "http://127.0.0.1:7890"


def test_enable_disable_roundtrip():
    saved = {k: os.environ.get(k) for k in
             ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY")}
    try:
        net.enable_proxy()
        assert os.environ.get("HTTPS_PROXY") == net.PROXY_URL
        net.disable_proxy()
        assert "HTTPS_PROXY" not in os.environ
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_install_hint_keys():
    hints = net.install_hint()
    assert set(hints) >= {"pip_proxy", "torch_hub", "git_proxy", "hf_mirror"}
    assert "hf-mirror.com" in hints["hf_mirror"]


@pytest.mark.skipif(os.environ.get("SMARTPY_NET_TEST") != "1",
                    reason="需要真实网络（SMARTPY_NET_TEST=1 开启）")
def test_probe_sources_live():
    results = net.probe_sources()
    assert len(results) == len(net.PROBE_TARGETS)
    for r in results:
        assert set(r) >= {"host", "direct_code", "proxy_code", "advice"}


@pytest.mark.skipif(os.environ.get("SMARTPY_NET_TEST") != "1",
                    reason="需要真实网络（SMARTPY_NET_TEST=1 开启）")
def test_probe_stability_live():
    st = net.probe_stability(times=3)
    assert st["times"] == 3
    assert 0.0 <= st["success_rate"] <= 1.0
