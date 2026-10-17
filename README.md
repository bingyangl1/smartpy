# smartpy —— Module.py 重构版

旧版 [D:\smartpy\Module.py](D:\smartpy\Module.py)（4436 行、92 函数 + 3 类，Jupyter 导出体）在
Python 3.12 + numpy 2.x 环境已经 import 失败，且存在 13 处必崩 Bug。
本目录是按现环境（Python 3.12.7 / numpy 2.4.4 / OpenCV 4.11 / pywin32 305）重构的包版本。

## 目录结构

```
F:\smartpy
├── smartpy/              包本体
│   ├── __init__.py      统一导出（旧 API 全兼容）
│   ├── _compat.py       pywin32 导入 + 一次性 DPI 设置
│   ├── util.py          计时装饰器 / 格式化输出 / 文件操作
│   ├── mouse.py         键鼠 / 轨迹 / 识图点击 / 剪贴板
│   ├── screen.py        截图（BitBlt + PrintWindow 后备）/ 图像读写
│   ├── vision.py        模板匹配 / 特征匹配
│   ├── window.py        窗口查找 / 样式 / 关闭 / 标题
│   ├── overlay.py       置顶透明穿透遮罩窗（Window 类）
│   ├── workflow.py      配置驱动任务 / 定时线程
│   ├── color.py         图色识别（找色/比色/多点找色/等待）
│   ├── xfeat.py         XFeat 特征匹配适配器
│   └── net.py           代理检测 / 带重试下载
├── docs/                文档
│   ├── README.md        文档索引
│   ├── API.md           接口文档（自动生成）
│   ├── COOKBOOK.md      用例文档（9 大类场景）
│   └── CHANGELOG.md     变更记录
├── Module.py            旧 `import Module` 的兼容 shim
├── tests/               回归测试（77+ 条）
├── examples/            示例
├── scripts/             文档生成 / 基准 / 冒烟 / 兼容检查
└── pyproject.toml
```

## 文档

| 文档 | 内容 |
|---|---|
| [docs/API.md](docs/API.md) | 全部接口签名/参数/返回值/示例，**从 docstring 自动生成** |
| [docs/COOKBOOK.md](docs/COOKBOOK.md) | 9 大类真实用例，可直接运行 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 版本变更、Bug 修复、性能数据 |
| [docs/README.md](docs/README.md) | 文档索引、docstring 约定、测试说明 |

改完代码后记得同步接口文档：

```powershell
python scripts\gen_api_docs.py           # 重新生成
python scripts\gen_api_docs.py --check    # 校验是否过期（CI 用）
```

> `tests/test_docs.py` 会自动检查文档与代码是否一致，过期会导致测试失败。

## 快速使用

```python
import sys
sys.path.insert(0, r"F:\smartpy")

import smartpy            # 新方式
# 或
import Module            # 旧方式（shim，行为一致）

# 截图
img = smartpy.screenCapture()                       # 全屏
img = smartpy.screenCapture(hwnd=hwnd)              # 指定窗口（含标题栏）

# 识图点击
smartpy.findClick("按钮", r"F:\smartpy\examples\img") # 找图并点击

# 模板匹配（不点击）
pts = smartpy.matchTemplate(template, img, threshold=0.9, onlyone=True)

# 后台点击
smartpy.click_point((100, 200), hwnd=hwnd)

# 遮罩窗
win = smartpy.Window(windowTitle="my overlay")
win.start()
...
win.close()
```

## 相对旧版的关键修复（均有回归测试）

| 问题 | 旧表现 | 修复 |
|---|---|---|
| matplotlib 顶层导入 | numpy2 下 import 直接失败 | 延迟导入 |
| `del template` / `del retA` / `startPoint` 未赋值 | UnboundLocalError / NameError | 删除无用 del |
| `WindiwTitle` 拼写 ×3 | NameError | 统一参数名 |
| `a & b == 8` 优先级 | getTopWindowExist 恒 False | 改位运算实现 |
| `x<<16-x` 优先级 | moveMouse1 ValueError | 标准绝对坐标公式 |
| `_delta_bezier_func` = f-f | 除零 | 中心差分 |
| genLinePointList | 反向拖拽飞出终点、顺序被打乱 | 按方向生成、保持顺序 |
| closeWindows 的 return 在循环内 | 只关第一个窗口 | 移出循环 |
| click_it enter 只发 KEYUP | 回车不生效 | 补 KEYDOWN |
| click_it LEFTUP\|LEFTDOWN 一次调用 | 行为未定义 | 拆成两次 |
| mouseScroll lParam 用客户区坐标 | 滚轮位置错误 | 改屏幕坐标 |
| imgReSize 忽略 nSize | 固定缩放 | 真正按目标分辨率 |
| MatchTemplate show=False | del vis NameError | 修复 |
| setWindowTrans(False) | EXSTYLE 清零 | 只清 LAYERED 位 |
| WM_PAINT 回调签名 | Window 类画不出来 | 统一 `_draw(hdc)` |
| GBK 字节算宽度 | emoji 报错 | east_asian_width |
| 遮罩窗置顶 | ShowWindow 前 SetWindowPos 不生效 | 先 Show 再置顶 |

## 算法优化（bench3.py 实测）

| 场景 | 暴力 rgb | 金字塔 rgb | 金字塔 gray | 加速比 |
|---|---|---|---|---|
| 1080p 40×40 模板 | 72.9 ms | 20.6 ms | 9.7 ms | 3.5× / 7.5× |
| 1080p 80×80 模板 | 74.7 ms | 10.6 ms | 4.4 ms | 7.1× / 17.1× |
| 4K 160×160 模板 | 319 ms | 38.5 ms | 17.2 ms | 8.3× / 18.6× |

- `matchTemplate` 新增 `pyramid=True`（默认开启）：1/4 分辨率粗扫候选 + 原图局部精修，
  精修用严格阈值验收，坐标与暴力法一致（有回归测试比对）。
- `mode='gray'` 比 rgb 再快约 2.5 倍；模板小于 48px 时自动退化为全分辨率。
- SQDIFF 系方法比较方向修正；`onlyone=True` 走 minMaxLoc 快速路径。
- `findClick` 现在只截屏一次、模板只读一次（旧版 N 个模板截 N 次屏），
  新增 threshold / pyramid / preload / onlyone 参数透传。
- `clickAll=True` 修复旧版「每个模板只保留最后一个命中点」的覆盖 bug。

## XFeat 特征匹配（可选兜底，实测有明确边界）

`smartpy.xfeat` 接入 XFeat (CVPR 2024)——一个轻量局部特征匹配器，
用于补 matchTemplate 的盲区（模板被缩放 / 旋转 / 亮度变化时）。

```python
# 直接用
pts = smartpy.xfeat_match(template, screenshot)          # [(x, y)] 或 []

# 或让 matchTemplate 自动兜底：模板匹配失败时才走特征匹配
pts = smartpy.matchTemplate(tpl, img, feature_fallback=True)

# findClick 也支持
smartpy.findClick("按钮", r"imgs", isclick=False, feature_fallback=True)
```

### ⚠️ 实测能力边界（重要，别用在 UI 上）

`scripts/xfeat_boundary.py` 在 1280×720 上的实测数据：

| 场景 | XFeat | matchTemplate |
|---|---|---|
| 高纹理图 · 原图同源 | 误差 0.4px / 184ms | 误差 0px / 19ms |
| 高纹理图 · **放大 1.5×** | **误差 1.0px / 532ms** | **漏检** |
| 高纹理图 · **亮度 -50** | **误差 0.4px / 151ms** | 误差 0px |
| 高纹理图 · 旋转 20° | 误差 34px（勉强） | 漏检 |
| **典型 Windows UI · 原图同源** | **误差 858px（完全失败）** | **误差 0px / 9ms** |
| 典型 UI · 放大 1.5× | 误差 195px | 漏检 |

**结论**：
- XFeat 只对**高纹理画面**有效（游戏画面、照片、复杂图标）
- **典型 Windows UI（纯色面板 + 文字 + 按钮）它是无效的**——这类画面纹理不足，
  提不出足够特征点，连原图同源都会定位到几百像素外
- 速度比 matchTemplate 慢 10~100 倍（150~650ms vs 3~20ms）
- 因此：**默认关闭**，只在你确认目标画面有丰富纹理时作为兜底打开

依赖：`pip install torch kornia`（首次运行会下载约 6MB 权重）。
默认走 CPU；要用 GPU 设 `AUTOPY_XFEAT_GPU=1`。

## 图色识别（smartpy.color）

旧脚本**没有**图色能力（只有 `printc` 控制台颜色和窗口透明色）。这块是新增的，
按键精灵 / 大漠插件那套 API 的 Python 实现。

### 颜色约定
统一用 **`0xRRGGBB` 整数**（`0xFF0000` 是纯红），也接受 `'#FF0000'` 和 `(r,g,b)`。
内部按 BGR 处理（OpenCV 原生顺序），转换在边界完成。

### API 一览

```python
# 取色 / 比色
c = smartpy.getPixel(100, 200)                  # -> 0xRRGGBB
c = smartpy.getColorAt(img, 10, 10)             # 从已有 ndarray 取
smartpy.compareColor(100, 200, 0xFF0000, sim=0)      # 单点比色
smartpy.compareColorEx(0xFE0100, 0xFF0000, sim=3)    # 两色比较

# 找色
smartpy.findColor(0xFF0000)                          # 全屏首个命中 -> (x,y)
smartpy.findColor(0xFF0000, region=(0,0,800,600))    # 限定区域
smartpy.findColorEx(0xFF0000)                        # 全部命中 -> [(x,y),...]
smartpy.countColor(0xFF0000, region=(0,0,800,600))   # 像素计数
smartpy.findColorBlock(0xFF0000, min_area=20)        # 连通色块 -> [{x,y,w,h,cx,cy,area}]

# 多点找色（抗干扰最强）
smartpy.findMultiColor(0xFF0000, [((10,0), 0x00FF00), ((0,5), 0x0000FF)], sim=10)

# 找色即点击
smartpy.findColorClick(0xFF0000, region=(0,0,800,600), offset=3)
```

### ★ 关键：用 snapshot() 复用截图

每次操作都截图代价很大（4K 一次约 25~30ms）。一帧内做多次查询时先拍快照：

```python
smartpy.snapshot()            # 拍一帧，之后所有查询复用它
smartpy.getPixel(100, 200)    # 0.9 微秒（不是 6ms）
smartpy.findColor(0xFF0000)   # 21ms（省掉 89ms 截图）
smartpy.clearSnapshot()       # 画面变化后清理
```

### 实测性能（4K 3840×2160）

| 操作 | 无快照 | 有快照 |
|---|---|---|
| 单点取色 | 6.1 ms | **0.9 微秒**（快 7000 倍） |
| 全屏找色（首点） | 110 ms | **21 ms** |
| 全屏色数统计 | 106 ms | **16 ms** |
| 区域找色 1920×1080 | — | 50 ms |
| 多点找色 200×200 | — | 55 ms含截图 / 2 ms纯计算 |

实现细节：找色首点用 `cv2.findNonZero`（比 `np.where` 快 2 倍）；
多点找色用向量化偏移校验（一次性取整批候选的偏移像素，不做 Python 逐像素循环）。

### 与 findClick / matchTemplate 的关系

| 场景 | 推荐 |
|---|---|
| 找固定图标（有完整模板图） | `matchTemplate` / `findClick` |
| 找纯色按钮 / 血条 / 进度条 | `findColor` / `findColorBlock` |
| 找带特定配色的小图案 | `findMultiColor` |
| 判断某个状态点颜色 | `compareColor` |

## 代理配置

`smartpy.net` 提供代理探测与带重试下载。代理地址通过环境变量 `AUTOPY_PROXY` 指定：

```powershell
$env:AUTOPY_PROXY = "http://127.0.0.1:7890"     # 你的本地代理地址
```

典型场景下的可达性差异（不同网络环境结果会不同）：

| 域名 | 直连 | 经代理 | 建议 |
|---|---|---|---|
| github.com | 慢 | 快 | 走代理 |
| raw.githubusercontent | 可用但慢 | 快 | 走代理下权重 |
| huggingface.co (API) | 常不通 | 可用 | 走代理 |
| cdn-lfs.huggingface.co | 不通 | 不通 | 用 hf-mirror 镜像 |
| pypi.org | 可用 | 视代理而定 | 建议用国内镜像源 |
| arxiv.org | 可用 | 可能更慢 | 加进 NO_PROXY 排除 |

> 部分代理对连续请求会随机失败，因此工具内部统一带重试。

### 用法

```python
from smartpy import net

net.enable_proxy()                       # 写进当前进程环境
net.probe_sources()                      # 逐域名对比 直连 vs 代理
net.probe_stability(times=6)             # 测代理成功率
net.download_with_proxy(url, dest, retries=5)   # 带重试下载
net.install_hint()                       # 给出 pip/git/HF 命令
```

命令行直接跑探测表：

```powershell
python -m smartpy.net
```

### XFeat 权重已接代理

`smartpy.xfeat` 检测到本地无权重时，会自动走代理 + 重试下载。
权重缓存在 `~/.cache/torch/hub/checkpoints/xfeat.pt`（6247949 bytes）。

### 常用命令

```powershell
# pip 装包走代理
pip install --proxy http://127.0.0.1:7890 <pkg>

# git 走代理（clone 大仓库）
git config --global http.proxy http://127.0.0.1:7890

# HuggingFace 大模型走镜像（代理对 cdn-lfs 无效）
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

## 测试

```powershell
cd <项目根目录>
python -m pytest tests -q
```

## 环境

- Python 3.9+（开发验证于 3.12）
- numpy / opencv-python / pywin32 / wrapt
- 可选：torch + kornia（XFeat 特征匹配）

> 若 matplotlib 版本与 numpy 不匹配（ABI 冲突），不影响本包导入——
> matplotlib 只在 `matchTemplate(show=True)` 等可视化路径才延迟导入。
