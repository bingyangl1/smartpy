# 变更记录

## v2.1.0 （本次）

### 新增：图色识别 `smartpy.color`

旧 `Module.py` **没有**图色能力（只有 `printc` 控制台颜色、窗口透明色等"设置颜色"的接口）。
本次新增完整的按键精灵 / 大漠插件风格的图色 API。

| 分类 | 接口 |
|---|---|
| 颜色换算 | `rgb_to_bgr` `bgr_to_rgb` `hex_to_bgr` `bgr_to_hex` |
| 取色 | `getPixel` `getColor` `getColorAt` |
| 比色 | `compareColor` `compareColorEx` |
| 找色 | `findColor` `findColorEx` `findColorBlock` `findColorClick` |
| 范围找色 | `findColorRange` `countColorRange` |
| 多点找色 | `findMultiColor` `findMultiColorEx` |
| 统计 | `countColor` |
| 等待 | `waitColor` `waitColorDisappear` `waitColorChange` `waitMultiColor` |
| 性能 | `snapshot` `clearSnapshot` |

**性能设计**：
- `snapshot()` 帧缓存 → 连续取色从 6.1ms/次 降到 0.9 微秒/次（快 7000 倍）
- 找色首点用 `cv2.findNonZero`（比 `np.where` 快 2 倍）
- 多点找色全向量化（不做 Python 逐像素循环）

基准测试（4K 分辨率）：

| 操作 | 无快照 | 有快照 |
|---|---|---|
| 单点取色 | 6.1 ms | 0.9 微秒 |
| 全屏找色（首点） | 110 ms | 21 ms |
| 全屏像素统计 | 106 ms | 16 ms |

### 新增：XFeat 特征匹配 `smartpy.xfeat`

用于弥补模板匹配在**缩放/旋转/亮度变化**下的盲区。

- `xfeat_match` / `XFeatLocator` / `xfeat_available`
- `matchTemplate(feature_fallback=True)` 自动兜底
- `findClick(feature_fallback=True)`

**能力边界（实测，重要）**：

| 场景 | XFeat | matchTemplate |
|---|---|---|
| 高纹理 · 原图同源 | 0.4px / 184ms | 0px / 19ms |
| 高纹理 · 放大 1.5× | 1.0px | 漏检 |
| 高纹理 · 亮度 -50 | 0.4px | 0px |
| 典型 Windows UI · 原图同源 | 858px（失败） | 0px / 9ms |

**结论**：XFeat 只适合高纹理画面（游戏/照片），默认关闭。

### 新增：代理助手 `smartpy.net`

- `probe_sources` 逐域名对比直连 vs 代理
- `probe_stability` 测代理成功率（部分代理对连续请求会随机失败）
- `download_with_proxy` 带重试下载
- XFeat 权重自动走代理下载

### 文档

- `docs/API.md` —— 接口文档，从 docstring 自动生成（`scripts/gen_api_docs.py`）
- `docs/COOKBOOK.md` —— 用例文档，9 大类真实场景
- `docs/CHANGELOG.md` —— 本文件
- `docs/README.md` —— 文档索引

---

## v2.0.0 （重构版）

从 `D:\smartpy\Module.py`（4436 行 / 92 函数）重构为 `smartpy` 包。

### 修复的 13 处必崩 Bug

| 问题 | 旧表现 | 修复 |
|---|---|---|
| matplotlib 顶层导入 | numpy2 下 import 失败 | 延迟导入 |
| `del template` / `del retA` / `startPoint` | UnboundLocalError / NameError | 删除无用 del |
| `WindiwTitle` 拼写 ×3 | NameError | 统一参数名 |
| `a & b == 8` 优先级 | getTopWindowExist 恒 False | 改位运算 |
| `_delta_bezier_func` = f-f | 除零 | 中心差分 |
| genLinePointList | 反向拖拽飞出终点 | 按方向生成 |
| closeWindows 的 return 在循环内 | 只关第一个窗口 | 移出循环 |
| click_it enter 只发 KEYUP | 回车不生效 | 补 KEYDOWN |
| mouseScroll lParam 用客户区坐标 | 滚轮位置错误 | 改屏幕坐标 |
| imgReSize 忽略 nSize | 固定缩放 | 真正按目标分辨率 |
| MatchTemplate show=False | del vis NameError | 修复 |
| setWindowTrans(False) | EXSTYLE 清零 | 只清 LAYERED 位 |
| WM_PAINT 回调签名 | Window 类画不出来 | 统一 `_draw(hdc)` |

### 算法优化

`matchTemplate` 新增金字塔粗到精（默认开启）：

| 场景 | 暴力 | 金字塔 | 加速 |
|---|---|---|---|
| 1080p 40×40 | 72.9 ms | 20.6 ms | 3.5× |
| 1080p 80×80 | 74.7 ms | 10.6 ms | 7.1× |
| 4K 160×160 | 319 ms | 38.5 ms | 8.3× |

- `onlyone=True` 走 `minMaxLoc` 快速路径
- SQDIFF 系方法比较方向修正
- `findClick` 只截屏一次（旧版 N 个模板截 N 次）

### 结构

```
smartpy/
├── _compat.py    pywin32 导入 + DPI 设置
├── util.py       计时 / 输出 / 文件
├── mouse.py      键鼠 / 轨迹 / 识图点击
├── screen.py     截图 / 图像读写
├── vision.py     模板匹配 / 特征匹配
├── window.py     窗口操作
├── overlay.py    遮罩窗口
├── workflow.py   任务 / 定时
├── color.py      图色识别      (v2.1 新增)
├── xfeat.py      特征匹配      (v2.1 新增)
└── net.py        代理与网络    (v2.1 新增)
```

### 兼容性

- 旧 `import Module` 通过 `Module.py` shim 继续可用
- 旧 91 个公开名全部保留，无删除
