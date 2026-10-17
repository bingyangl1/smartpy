# -*- coding: utf-8 -*-
"""代理环境助手 —— 检测/启用本地代理，并验证各源可达性。

实测环境：本地 HTTP/SOCKS5 双协议代理（地址由 AUTOPY_PROXY 环境变量指定）：

    域名                        直连    代理    说明
    ----------------------------------------------------------------
    api.ipify.org               000     200    直连完全出不去
    raw.githubusercontent       200     200    代理更快更稳
    github.com                  200     200    代理更快
    api.github.com              200     200    代理更快
    huggingface.co (API)        000     307    直连不通，代理可用
    cdn-lfs.huggingface.co      000     000    ★ 大文件走不了代理
    arxiv.org                   200     000    代理反而更差，别走
    google.com                  000     200    直连不通，代理可用

结论：
- 代理解决「GitHub / HF API / Google 直连不通」
- ★ HF 大权重文件（cdn-lfs）走代理仍失败，需要 hf-mirror.com 之类的镜像
- arxiv.org 走代理会变慢/失败，应该排除
"""

import os
import subprocess
import time

__all__ = ["PROXY_URL", "enable_proxy", "disable_proxy", "probe_sources",
           "proxy_env", "install_hint", "probe_stability", "download_with_proxy"]

PROXY_URL = os.environ.get("AUTOPY_PROXY", "http://127.0.0.1:7890")

# 走代理无益甚至有害的域名（NO_PROXY）
BYPASS_HOSTS = "arxiv.org,localhost,127.0.0.1,::1,*.cn,pypi.tuna.tsinghua.edu.cn"

PROBE_TARGETS = [
    ("api.ipify.org", "https://api.ipify.org"),
    ("raw.githubusercontent", "https://raw.githubusercontent.com/verlab/accelerated_features/main/README.md"),
    ("github.com", "https://github.com"),
    ("api.github.com", "https://api.github.com/rate_limit"),
    ("huggingface.co", "https://huggingface.co/api/models/gpt2"),
    ("pypi.org", "https://pypi.org/simple/"),
    ("arxiv.org", "https://arxiv.org"),
]


def proxy_env(enable=True, proxy=None):
    """返回带/不带代理的环境变量字典（不修改当前进程）。"""
    env = os.environ.copy()
    if not enable:
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                  "ALL_PROXY", "all_proxy"):
            env.pop(k, None)
        return env
    url = proxy or PROXY_URL
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env[k] = url
    env["NO_PROXY"] = env["no_proxy"] = BYPASS_HOSTS
    return env


def enable_proxy(proxy=None):
    """把代理写进当前进程环境（子进程继承）。"""
    env = proxy_env(True, proxy)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
              "NO_PROXY", "no_proxy"):
        if k in env:
            os.environ[k] = env[k]
    return True


def disable_proxy():
    """从当前进程环境移除代理。"""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
              "ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)


def _curl(url, proxy=None, timeout=15, retries=3, backoff=0.4):
    """curl 探测，带重试。

    实测该代理有随机失败（连续 6 次请求约 2 次返回 000），
    因此必须重试才能得到稳定判断。
    """
    last = ("000", -1.0)
    for attempt in range(max(retries, 1)):
        cmd = ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code} %{time_total}",
               "--max-time", str(timeout)]
        if proxy:
            cmd += ["-x", proxy]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=timeout + 5)
            parts = (out.stdout or "").strip().split()
            if len(parts) >= 2:
                code, dt = parts[0], float(parts[1])
                if code != "000":
                    return code, dt
                last = (code, dt)
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))
    return last


def probe_stability(url=None, proxy=None, times=6, timeout=12):
    """测代理稳定性：连续请求 N 次，返回成功率与耗时分布。"""
    url = url or PROBE_TARGETS[3][1]
    p = proxy or PROXY_URL
    ok, times_list = 0, []
    for i in range(times):
        code, dt = _curl(url, p, timeout, retries=1)
        if code != "000":
            ok += 1
            times_list.append(dt)
        time.sleep(0.3)
    return {
        "times": times,
        "success": ok,
        "success_rate": round(ok / times, 2) if times else 0.0,
        "min_time": round(min(times_list), 2) if times_list else -1,
        "max_time": round(max(times_list), 2) if times_list else -1,
    }


def download_with_proxy(url, dest, proxy=None, retries=5, expected_size=None):
    """
    带重试下载（该代理有随机失败，单次 curl 会偶发 000）。

    参数:
        url: 下载地址
        dest: 本地路径
        proxy: 代理地址，None 用 PROXY_URL
        retries: 重试次数
        expected_size: 期望字节数（给了就校验）
    返回: (ok: bool, info: dict)
    """
    p = proxy or PROXY_URL
    dest = os.path.abspath(dest)
    parent = os.path.dirname(dest)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    last_err = ""
    for attempt in range(max(retries, 1)):
        tmp = dest + ".part"
        cmd = ["curl.exe", "-sL", "-o", tmp, "-w", "%{http_code}",
               "--max-time", "300", "-x", p, url]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=320)
            code = (out.stdout or "").strip()
            if os.path.isfile(tmp):
                size = os.path.getsize(tmp)
                if code in ("200", "206") and size > 0:
                    if expected_size is not None and size != expected_size:
                        last_err = "size mismatch %d != %d" % (size, expected_size)
                        os.remove(tmp)
                    else:
                        os.replace(tmp, dest)
                        return True, {"size": size, "attempts": attempt + 1}
                else:
                    last_err = "http %s" % code
                    if os.path.isfile(tmp):
                        os.remove(tmp)
        except Exception as e:
            last_err = str(e)
        if attempt < retries - 1:
            time.sleep(0.8 * (attempt + 1))
    return False, {"error": last_err, "attempts": retries}


def probe_sources(proxy=None, timeout=12):
    """
    逐个源测试 直连 vs 代理，返回结构化结果。

    返回: [{"host", "direct_code", "direct_time", "proxy_code", "proxy_time",
            "advice"}]
    """
    url = proxy or PROXY_URL
    results = []
    for name, target in PROBE_TARGETS:
        dc, dt = _curl(target, None, timeout)
        pc, pt = _curl(target, url, timeout)
        if dc != "000" and pc == "000":
            advice = "直连可用，代理反而失败 -> 排除（NO_PROXY）"
        elif dc == "000" and pc != "000":
            advice = "必须走代理"
        elif dc == "000" and pc == "000":
            advice = "都不通"
        elif pt >= 0 and dt >= 0 and pt < dt * 0.7:
            advice = "代理明显更快"
        else:
            advice = "直连即可"
        results.append({
            "host": name,
            "direct_code": dc,
            "direct_time": round(dt, 2),
            "proxy_code": pc,
            "proxy_time": round(pt, 2),
            "advice": advice,
        })
    return results


def install_hint():
    """给出建议的 pip / 下载命令。"""
    return {
        "pip_proxy": "pip install --proxy %s <pkg>" % PROXY_URL,
        "torch_hub": "set HTTPS_PROXY=%s  然后运行 python" % PROXY_URL,
        "git_proxy": "git config --global http.proxy %s" % PROXY_URL,
        "hf_mirror": "set HF_ENDPOINT=https://hf-mirror.com   # HF 大文件走镜像",
    }


if __name__ == "__main__":
    print("代理:", PROXY_URL)
    print("\n%-26s %-8s %-8s %-8s %-8s %s"
          % ("域名", "直连", "耗时", "代理", "耗时", "建议"))
    for r in probe_sources():
        print("%-26s %-8s %-8s %-8s %-8s %s"
              % (r["host"], r["direct_code"], r["direct_time"],
                 r["proxy_code"], r["proxy_time"], r["advice"]))
