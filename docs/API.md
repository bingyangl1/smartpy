# smartpy 接口文档

> 本文件由 `scripts/gen_api_docs.py` 从源码 docstring **自动生成**，请勿手工编辑。
> 重新生成: `python scripts/gen_api_docs.py`

版本: `2.1.0`

## 目录
- [图色识别](#mod-color) — `smartpy.color` · 24 个接口
- [识图匹配](#mod-vision) — `smartpy.vision` · 3 个接口
- [截图与图像](#mod-screen) — `smartpy.screen` · 8 个接口
- [键鼠操作](#mod-mouse) — `smartpy.mouse` · 25 个接口
- [窗口操作](#mod-window) — `smartpy.window` · 30 个接口
- [遮罩窗口](#mod-overlay) — `smartpy.overlay` · 1 个接口
- [工具与输出](#mod-util) — `smartpy.util` · 13 个接口
- [任务与定时](#mod-workflow) — `smartpy.workflow` · 5 个接口
- [特征匹配（XFeat）](#mod-xfeat) — `smartpy.xfeat` · 3 个接口
- [代理与网络](#mod-net) — `smartpy.net` · 7 个接口

<a id="mod-color"></a>

## 图色识别 `smartpy.color`

smartpy.color —— 图色识别（找色 / 比色 / 多点找色 / 色块统计）。

### `rgb_to_bgr(color)`

0xRRGGBB -> (B, G, R) 元组

### `bgr_to_rgb(b, g, r)`

(B,G,R) -> 0xRRGGBB 整数

### `hex_to_bgr(color)`

0xRRGGBB / '#RRGGBB' / (r,g,b) -> (b, g, r)

### `bgr_to_hex(bgr)`

(B,G,R) -> 0xRRGGBB

### `getPixel(x, y, hwnd=None)`

取单点颜色，返回 0xRRGGBB 整数。

**参数**

| 参数 | 说明 |
|---|---|
| `hwnd` | 窗口句柄（可选，从该窗口截图取值） 返回: 0xRRGGBB；失败返回 None |

> **注意**: 有 snapshot() 快照时走内存索引（约 1 微秒）；     没快照时截 1x1 区域（约 20~30ms，含截图开销）。     连续取色请先 snapshot()。

### `getColor(x, y, hwnd=None)`

getPixel 的别名（按键精灵习惯名）

### `getColorAt(img, x, y)`

从已给的图（ndarray）里取 (x, y) 的 0xRRGGBB 颜色。

### `compareColor(x, y, color, sim=0, hwnd=None)`

比色：判断指定点颜色是否等于给定色。

**参数**

| 参数 | 说明 |
|---|---|
| `color` | 0xRRGGBB 或 '#RRGGBB' 或 (r,g,b) |
| `sim` | 每通道容差 0~255，0 为精确比色 |
| `hwnd` | 窗口句柄（可选） 返回: True / False |

### `compareColorEx(actual, expected, sim=0)`

两个 0xRRGGBB 颜色的相似比较。

**参数**

| 参数 | 说明 |
|---|---|
| `actual` | 实际颜色 0xRRGGBB |
| `expected` | 期望颜色 0xRRGGBB |
| `sim` | 每通道容差 返回: True / False |

### `findColor(color, region=None, sim=0, hwnd=None, img=_UNSET, all_points=False)`

找色：在区域内找指定颜色的**第一个**坐标（优先屏幕坐标）。

**参数**

| 参数 | 说明 |
|---|---|
| `color` | 0xRRGGBB / '#RRGGBB' / (r,g,b) |
| `region` | (x, y, w, h) 搜索区域；None 表示全屏/整窗 |
| `sim` | 每通道容差 0~255 |
| `hwnd` | 窗口句柄（可选） |
| `img` | 直接给定图像（给了就不截图；显式传 None 会返回未命中） |
| `all_points` | True 时返回全部命中坐标 |

**返回值**: (x, y) 或 None；all_points=True 时返回 [(x, y), ...]

### `findColorEx(color, region=None, sim=0, hwnd=None, img=_UNSET, limit=0)`

找色（全部）：返回所有匹配坐标。

**参数**

| 参数 | 说明 |
|---|---|
| `limit` | 最多返回多少个（0 为不限） |

### `findColorBlock(color, region=None, sim=0, hwnd=None, img=_UNSET, min_area=20)`

找色块：找出指定颜色的连通区域（比单点找色更抗噪）。

**参数**

| 参数 | 说明 |
|---|---|
| `min_area` | 最小连通面积（像素），小于此值忽略 返回: [{"x": 左, "y": 上, "w": 宽, "h": 高, "cx": 中心x, "cy": 中心y, "area": 面积}, ...] |

### `findMultiColor(first_color, offsets, region=None, sim=0, hwnd=None, img=_UNSET, all_points=False)`

多点找色：先找主色，再校验一组偏移点的颜色 —— 抗干扰最强的方式。

**参数**

| 参数 | 说明 |
|---|---|
| `first_color` | 主色 0xRRGGBB |
| `offsets` | [((dx, dy), color), ...] 偏移点与对应颜色 也接受 [(dx, dy, color), ...] 写法 |
| `region` | 搜索区域 |
| `sim` | 每通道容差 hwnd / img: 同 findColor |
| `all_points` | True 返回全部命中，False 只返回第一个 返回: (x, y) / None，或 [(x, y), ...] |

**示例**

```python
# 找「左上角红 + 右侧 10px 绿 + 下方 5px 蓝」的图案
findMultiColor(0xFF0000,
[((10, 0), 0x00FF00), ((0, 5), 0x0000FF)],
region=(0, 0, 800, 600), sim=10)
```

### `findMultiColorEx(first_color, offsets, region=None, sim=0, hwnd=None, img=_UNSET, limit=0)`

多点找色（全部）。

### `countColor(color, region=None, sim=0, hwnd=None, img=_UNSET)`

统计区域内指定颜色的像素数。

### `findColorClick(color, offsets=None, region=None, sim=0, hwnd=None, isclick=True, button="left", offset=3, all_points=False)`

找色并点击（与 findClick 的用法对齐，但按颜色而非图片定位）。

**参数**

| 参数 | 说明 |
|---|---|
| `color` | 主色 0xRRGGBB |
| `offsets` | 给了就走多点找色，否则单色找色 region / sim / hwnd: 同 findColor |
| `isclick` | 是否真的点击 |
| `button` | left / right / doubleleft / enter |
| `offset` | 点击随机偏移 |
| `all_points` | 是否点击全部命中 返回: 找到的坐标（全部时返回列表），未找到返回 None / [] |

### `findColorRange(low, high, region=None, hwnd=None, img=_UNSET, all_points=False, limit=0)`

颜色范围找色：在 [low, high] 颜色区间内找像素。

**参数**

| 参数 | 说明 |
|---|---|
| `low` | 颜色下界 0xRRGGBB（如 0x800000 深红） |
| `high` | 颜色上界 0xRRGGBB（如 0xFF3333 浅红） region / hwnd / img: 同 findColor |
| `all_points` | True 返回全部 |
| `limit` | 全部模式下最多返回多少个 返回: (x, y) / None，或 [(x, y), ...] |

**示例**

```python
# 找屏幕上任意偏红的像素
findColorRange(0x800000, 0xFF4040)
# 找深色按钮区域（深灰到中灰）
findColorRange(0x303030, 0x707070, region=(0, 0, 1920, 1080))
```

### `countColorRange(low, high, region=None, hwnd=None, img=_UNSET)`

统计落在颜色区间内的像素数。

### `waitColor(color, timeout=10.0, interval=0.05, region=None, sim=0, hwnd=None, all_points=False)`

等待颜色出现（带超时）——挂机脚本最常用的等待原语。

**参数**

| 参数 | 说明 |
|---|---|
| `color` | 目标色 0xRRGGBB |
| `timeout` | 最长等待秒数；<=0 表示只检测一次 |
| `interval` | 轮询间隔秒数 region / sim / hwnd: 同 findColor |
| `all_points` | True 返回全部命中点 |

**返回值**: 命中: (x, y) 或 [(x, y), ...]     超时: None / []

### `waitColorDisappear(color, timeout=10.0, interval=0.05, region=None, sim=0, hwnd=None)`

等待颜色消失（例如等 loading 转圈的某个色块消失）。

### `waitColorChange(x, y, timeout=10.0, interval=0.05, hwnd=None)`

等待某点颜色变化（点击后等界面响应）。

**参数**

| 参数 | 说明 |
|---|---|
| `timeout` | 最长等待秒数 返回: 变化后的新颜色 0xRRGGBB；超时返回 None |

### `waitMultiColor(first_color, offsets, timeout=10.0, interval=0.05, region=None, sim=0, hwnd=None)`

等待多点找色命中（比单色等待更抗干扰）。
返回: (x, y) 或 None

### `snapshot(hwnd=None)`

拍一张快照并缓存，后续 getPixel / findColor / ... 自动复用它。

**示例**

```python
smartpy.snapshot(hwnd)          # 拍一帧
smartpy.getPixel(100, 200)      # 复用快照，~微秒级
smartpy.findColor(0xFF0000)     # 复用快照
smartpy.clearSnapshot()         # 用完清理
```

### `clearSnapshot()`

清除快照缓存。

---

<a id="mod-vision"></a>

## 识图匹配 `smartpy.vision`

smartpy.vision —— 模板匹配与特征匹配。

### `matchTemplate(template, src_rgb=None, threshold=0.95, mode="rgb", hwnd=None, isclient=False, show=False, onlyone=False, method=1, zeroPoint=(0, 0), midpoint=True, duplicateRemoval=5, offset=False, pyramid=True, feature_fallback=False)`

功能: 大图找小图，返回小图相对大图的坐标

**参数**

| 参数 | 说明 |
|---|---|
| `template` | 小图 ndarray |
| `src_rgb` | 大图 ndarray；不给则自动截图（hwnd 给则截窗口） |
| `threshold` | 阈值 默认 0.95（SQDIFF 系为「小于阈值」命中） |
| `mode` | 'gray' / 'rgb'（gray 约快 2.5 倍） |
| `hwnd` | 只匹配指定窗口（坐标换算基准） |
| `isclient` | 返回客户区坐标（相对客户区左上角，已修正旧版整窗偏移） |
| `show` | 显示匹配结果 |
| `onlyone` | 只返回第一个 |
| `method` | 0~5 对应 TM_CCOEFF / TM_CCOEFF_NORMED / TM_CCORR / TM_CCORR_NORMED / TM_SQDIFF / TM_SQDIFF_NORMED |
| `zeroPoint` | 大图为局部图时提供的原点偏移 |
| `midpoint` | 返回中心点（否则左上角） |
| `duplicateRemoval` | 相邻匹配点去重阈值（像素） |
| `offset` | 随机偏移后返回（范围模板宽高 1/4） |
| `pyramid` | 金字塔粗到精加速（1/4 分辨率粗扫 + 局部精修）。 1080p 实测 110ms -> 6ms，4K 130ms -> 8ms，坐标一致。 需要绝对精确（对阈值边界敏感）时置 False。 |
| `feature_fallback` | 模板匹配失败时自动用 XFeat 特征匹配重试 （能扛缩放/旋转/亮度变化；弱纹理模板会自动跳过）。 返回: [(x, y), ...]；无匹配返回 [] |

### `MatchTemplate(src_img, template, mode="sift", threshold=0.8, show=False, FLANN_INDEX_KDTREE=1, FLANN_INDEX_LSH=6, duplicateRemoval=5)`

特征匹配（SIFT / SURF / ORB / AKAZE / BRISK），不支持太小的图
返回: 匹配点列表 [(x, y), ...]

### `async_matchTemplate(template, src_rgb=None, threshold=0.95, mode="rgb", hwnd=None, isclient=False, show=False, onlyone=False, method=1, zeroPoint=(0, 0), midpoint=True, duplicateRemoval=5)`

匹配函数的兼容包装（与 matchTemplate 参数一致）。

---

<a id="mod-screen"></a>

## 截图与图像 `smartpy.screen`

smartpy.screen —— 截图 / 图像读写 / 显示。

### `readImage(src, dtype="uint8")`

从 src 路径读取图片（numpy + cv2，支持中文路径）
返回: ndarray；读取失败返回 None

### `saveImage(name, image, endswitch=".jpg")`

保存图片（支持中文路径）

### `screenCapture(hwnd=None, save="", show=False, region=(0, 0, 0, 0), client_region=False)`

功能: 对窗口/桌面截图（默认全屏）

**参数**

| 参数 | 说明 |
|---|---|
| `hwnd` | 窗口句柄；None = 桌面 |
| `save` | 保存文件名（空字符串不保存） |
| `show` | 是否显示 |
| `region` | (x, y, w, h) 截取区域；0 表示整幅。 默认相对窗口左上角；client_region=True 时相对客户区左上角。 |
| `client_region` | region 是否以客户区为原点 返回: BGRA ndarray；失败返回 None 并打印原因 |

### `window_capture(hwnd)`

后台截图（整窗）
返回: BGRA ndarray

### `imageConcatenate(hwnd=None, save="", show=False)`

分 4 块截图后拼接（同步实现）

**参数**

| 参数 | 说明 |
|---|---|
| `hwnd` | 窗口句柄（可选） |
| `save` | 保存位置（可选） |
| `show` | 显示（可选） 返回: ndarray uint8 |

### `imshow(img, namespace="screenCapture", waitkey=None)`

显示图片

### `imgReSize(img, nSize, rSize=None)`

将图像按比例缩放到目标分辨率 nSize = (w, h)

**参数**

| 参数 | 说明 |
|---|---|
| `img` | ndarray |
| `nSize` | 目标 (宽, 高) |
| `rSize` | 来源分辨率 (宽, 高)，缺省取图像自身尺寸 旧版 BUG：算完缩放比不用，硬编码 1136/820、640/462，此处修复。 |

### `async_screenCapture(hwnd=None, save="", show=False, region=(0, 0, 0, 0))`

截图函数的异步包装（兼容旧名；内部仍是同步实现，可在 asyncio 中调用）。

---

<a id="mod-mouse"></a>

## 键鼠操作 `smartpy.mouse`

smartpy.mouse —— 键鼠操作、轨迹生成、识图点击。

### `SetCursorPos(pos)`

设置鼠标位置 (x, y)

### `click1(x, y, offset=0, reduction=True, debug=False)`

功能: 前台点击（win32api.mouse_event 实现）

### `click2(x, y, offset=0, reduction=True, debug=False)`

功能: 前台点击（ctypes.windll.user32.mouse_event 实现）
参数同 click1

### `click3(x, y, offset=0, debug=False)`

功能: 通过 SendMessage 向窗口发点击消息（不动物理鼠标）

### `click_it(x=None, y=None, button="left", offset=3, debug=False)`

功能: 移动鼠标并点击，坐标带随机偏移

**参数**

| 参数 | 说明 |
|---|---|
| `button` | left / right / doubleleft / enter |
| `offset` | 偏移范围 返回: 实际点击坐标 (x, y) |

### `mouseScroll(pos=(0, 0), hwnd=None, scrollbutton=1, rotate=1, debug=False, isClient=False)`

模拟鼠标滚动

**参数**

| 参数 | 说明 |
|---|---|
| `hwnd` | 句柄；不给则按 pos 取窗口 |
| `pos` | 坐标（屏幕坐标；isClient=True 时为客户区坐标） |
| `rotate` | 滚动行数 正数向上，负数向下 |
| `scrollbutton` | 滚轮键位标志（0 无修饰键，1 MK_LBUTTON） |
| `isClient` | pos 是否为客户区坐标 |

### `CubicBezier(c1=(0, 0), c2=(1, 1), begin=(0, 0), end=(1, 1))`

三次贝塞尔曲线

### `cubic_bezier_gen(start, end, dv=10)`

贝塞尔曲线轨迹生成器

**参数**

| 参数 | 说明 |
|---|---|
| `start` | 起点 (x, y) |
| `end` | 终点 (x, y) |
| `dv` | 轨迹点数 生成: 从 start 到 end 的 (x, y) 序列 |

### `moveMouse1(start, end, reduction=True, debug=False, offset=0)`

功能: 拖拽鼠标从 start 到 end（win32api.mouse_event，绝对坐标）

**参数**

| 参数 | 说明 |
|---|---|
| `reduction` | 是否恢复原坐标 |
| `offset` | 随机偏移 |

### `mouseMove(hwnd, pos)`

### `mouseUp(hwnd, pos)`

### `mouseDown(hwnd, pos)`

### `SendMessage(hwnd, Param1, Param2, Param3)`

同步发送消息（旧版被同名坏实现覆盖，这里统一为正确的直通封装）

### `PostMessage(hwnd, Param1, Param2, Param3)`

异步投递消息

### `moveMouse2(start, end, hwnd=None, debug=False, offset=1, isClient=False)`

拖拽（SendMessage 一步到位）

### `moveMouse3(start, end, movePointList=None, hwnd=None, debug=False, offset=1, isClient=False)`

拖拽（SendMessage 沿轨迹逐点发送）

### `moveMouse4(start, end, movePointList=None, hwnd=None, debug=False, offset=1, cost=1, isClient=False)`

拖拽（贝塞尔轨迹）

### `genLinePointList(start, end, offset=0)`

根据指定点生成直线轨迹点集合（保持顺序）

**参数**

| 参数 | 说明 |
|---|---|
| `start` | 起点 (x, y) |
| `end` | 终点 (x, y) |
| `offset` | 每点随机偏移 返回: 轨迹列表 [(x1,y1),...,(xn,yn)]，首点=start，末点=end |

### `findClick(findName, filePathList, endswith=".png", mode="rgb", isclick=True, clickAll=False, hwnd=None, retHwnd=False, threshold=0.95, pyramid=True, preload=True, onlyone=False, feature_fallback=False)`

介绍: 在文件夹中找到包含 findName 且以 endswith 结尾的文件，作为模板
      在屏幕上寻找并点击

**参数**

| 参数 | 说明 |
|---|---|
| `findName` | 文件名关键词 str |
| `filePathList` | 图片目录或文件路径列表 |
| `endswith` | 扩展名 默认 '.png' |
| `mode` | 'gray' 或 'rgb' |
| `isclick` | 是否点击 |
| `clickAll` | 是否点击全部匹配 |
| `hwnd` | 指定窗口范围（句柄或句柄列表） |
| `retHwnd` | 返回 {(x, y): hwnd} |
| `threshold` | 匹配阈值（透传给 matchTemplate） |
| `pyramid` | 金字塔粗到精加速（透传给 matchTemplate） |
| `preload` | 只截屏一次、缓存模板（N 个模板共享一张大图） |
| `onlyone` | 只找一个模板命中点 |
| `feature_fallback` | 模板匹配失败时用 XFeat 特征匹配兜底 （抗缩放/旋转/亮度变化） 返回: 坐标 (x, y) / [(x, y)] / {(x,y): hwnd} / [] 或 {} |

### `click_point(pos, hwnd=None, offset=0, debug=False, isClient=False)`

功能: 点击指定的坐标（默认屏幕坐标；传 hwnd 后台点击）

**参数**

| 参数 | 说明 |
|---|---|
| `pos` | (x, y) |
| `hwnd` | 窗口句柄 |
| `offset` | 随机偏移 |
| `isClient` | pos 是否为客户区坐标 返回: 实际点击坐标 |

### `click_pointForClient(pos, hwnd=None, offset=0, debug=False)`

功能: 以客户区坐标点击（不动物理鼠标；未传 hwnd 时按屏幕坐标反查窗口）

**参数**

| 参数 | 说明 |
|---|---|
| `pos` | 客户区坐标 (x, y)（hwnd=None 时视为屏幕坐标） |
| `hwnd` | 窗口句柄 |
| `offset` | 随机偏移 |

### `send_enter(hwnd=None, ClassName=None, WindowTitle=None)`

发送 Enter 键

### `send_str(text, hwnd=None, ClassName=None, WindowTitle=None)`

向指定窗口发送字符串（WM_CHAR）

### `set_clipboard_text(text)`

将字符串复制到剪贴板

### `clipboard_paste(hwnd=None, ClassName=None, WindowTitle=None)`

从剪贴板粘贴到指定窗口

---

<a id="mod-window"></a>

## 窗口操作 `smartpy.window`

smartpy.window —— 窗口查找 / 样式 / 位置 / 关闭 / 标题。

### `findWindow(className=None, windowTitle=None)`

获取指定的窗口句柄
参数: className 类名 / windowTitle 标题（均可不传）
返回: hwnd；两个都不传时返回桌面句柄

### `ScreenToClient(hwnd, pos)`

### `ClientToScreen(hwnd, pos)`

### `WindowFromPoint(pos)`

### `MAKELONG(x, y)`

### `get_focus(hwnd=None)`

获取窗口焦点

### `getWindowRect(hwnd=None, ClassName=None, WindowTitle=None, mode=0)`

获取窗口位置。参数优先级: hwnd > ClassName/WindowTitle
mode: 0 -> (left, top, right, bottom)；1 -> (left, top, w, h)

### `setWindowRect(hwnd=None, ClassName=None, WindowTitle=None, Rect=(None, None, None, None))`

设置窗口位置 (x, y, w, h)，None 项保持不变

### `setWindowState(hwnd=None, state=0, ClassName=None, WindowTitle=None)`

设置窗口状态：0 还原 / 1 最小化 / 2 最大化

### `getCurpos()`

获取当前鼠标位置

### `gePosWindowHandle(pos)`

获取指定坐标位置的窗口句柄

### `closeWindows(hwndList)`

关闭窗口列表（先发 WM_CLOSE，收不到再终止进程）
返回: 0 全部处理完，-1 有失败

### `Rename(ClassName=None, WindowTitle=None, rename=None, hwndList=None)`

修改窗口标题

### `printWindowTitle(hwndList)`

打印 hwndList 中每个窗口的类名 / 标题 / 句柄

### `getChildWindows(parent)`

获得 parent 的所有子窗口句柄

### `getWindowTitle(hwnd)`

### `setWindowTitle(hwnd, title)`

### `getClassName(hwnd)`

### `getChildWindow(parent, ClassName=None, WindowTitle=None, strict=False)`

获得父窗口下符合类名 / 标题的子窗口
strict: True 用 == 精确匹配；False 用 in 包含匹配

### `enumWindow(ClassName=None, WindowTitle=None, debug=False)`

按类名 / 标题（子串，模糊）查找窗口
返回: 句柄列表

### `enumWindows(debug=False)`

枚举所有窗口
返回: [{"className": ..., "windowTitle": ..., "hwnd": ...}, ...]

### `showWindow(hwnd)`

前台显示窗口

### `sortWindow(ClassName=None, WindowTitle=None, hwndList=None, x=0, y=0, w=836, h=501)`

前台显示并网格化排列窗口

### `kill(ClassName=None, WindowTitle=None)`

按类名 / 标题关闭程序（多开场景重写）

### `setTopWindow(hwnd, setTop=True)`

置顶 / 取消置顶窗口

### `getTopWindowExist(hwnd)`

查看指定窗口是否置顶。

### `setWindowTrans(hwnd, transColor=16777215, Alpha=220, isTrans=True)`

设置窗口透明度
isTrans=False 时恢复不透明（只清除 LAYERED 位，保留其它扩展样式）

### `showTaskBar(hwnd, show=True)`

设置任务栏图标显示 / 隐藏

### `setMousePenetration(hwnd, Penetration=True)`

设置 / 取消鼠标穿透

### `HideTitleAndBorder(hwnd, hide=True)`

隐藏 / 恢复标题栏和边框

---

<a id="mod-overlay"></a>

## 遮罩窗口 `smartpy.overlay`

smartpy.overlay —— 置顶透明鼠标穿透遮罩窗（Window 类重构版）。

### `Window(className="TranPy", windowTitle="TranPy", windowX=0, windowY=0, windowWidth=None, windowHeight=None, cxClient=None, cyClient=None, bgColor=16515071, TransparentColor=16515071, Alpha=220, isDaemon=False, debug=False)`

置顶、无标题栏、透明、鼠标穿透的遮罩窗口。

**参数**

| 参数 | 说明 |
|---|---|
| `bgColor` | 背景色 |
| `TransparentColor` | 透明色（colorkey） |
| `Alpha` | 整体透明度 [0, 255] |
| `isDaemon` | 线程是否守护 |
| `debug` | 调试输出 |

---

<a id="mod-util"></a>

## 工具与输出 `smartpy.util`

smartpy.util —— 计时装饰器、格式化输出、文件操作。

### `Timer(show=True)`

功能:
    装饰器，用于计算函数运行的时间

**示例**

```python
@Timer()
def func():
print(f'func name:{func.__name__}')
```

### `timer()`

功能:
    装饰器，用于计算函数运行的时间（wrapt 实现，保留原签名/文档）

### `prints(strs="", width=60, fillchar="", pre="|", end="|", isPrint=True, cls=False)`

介绍: 格式化输出字符串（居中填充）

**参数**

| 参数 | 说明 |
|---|---|
| `strs` | 要输出的字符串 |
| `width` | 填充宽度 默认60 |
| `fillchar` | 填充字符 默认 '' |
| `pre` | 前缀 默认 '\|' |
| `end` | 后缀 默认 '\|' |
| `isPrint` | 是否输出 默认 True |
| `cls` | 是否清屏 |

### `printf(strs="", width=60, fillchar="", pre="|", end="|", isPrint=True, cls=False, debug=False)`

介绍: 格式化输出字符串（居中填充，中文按全角宽度对齐）
参数同 prints，另有 debug 输出宽度信息

### `printc(message, color, end="\n", defaultColor=10)`

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

### `printa(strs="", width=60, fillchar=" ", pre="|", end="|", cls=False, debug=False, EOL="\r", showTime=0, printEOF="")`

介绍: 按宽度自动换行 + 居中填充输出

**参数**

| 参数 | 说明 |
|---|---|
| `strs` | 要输出的字符串 |
| `width` | 每行宽度（不含前缀后缀） 默认60 |
| `fillchar` | 填充字符 默认 ' ' pre / end: 前缀 / 后缀 |
| `cls` | 是否清屏 |
| `EOL` | 行首控制符（'\r' 回到行首，'\n' 换行，'\t' 制表） |
| `showTime` | 每行输出间隔秒数 |
| `printEOF` | print 的 end 参数 |

### `copyFile(srcFile, dstDir)`

功能: 复制 srcFile 到 dstDir

**参数**

| 参数 | 说明 |
|---|---|
| `srcFile` | 源文件 str |
| `dstDir` | 目标目录（D:/）或目标文件路径（D:/test.txt） str |

### `getFile(path, show=False)`

功能: 获取 path 路径下的所有文件
返回值: 确定顺序（按名称排序）的文件路径 list

### `moveFiles(srcDir, dstDir)`

功能: 将 srcDir 文件夹下的所有文件移动到 dstDir

### `moveFile(srcFile, dstDir)`

功能: 将 srcFile 移动至 dstDir

**参数**

| 参数 | 说明 |
|---|---|
| `srcFile` | 源文件 |
| `dstDir` | 目标目录（D:/）或目标文件路径（D:/test.txt） |

### `getDir(path, show=False)`

功能: 获取 path 下的所有文件夹
返回值: 确定顺序（按名称排序）的目录路径 list

### `TraverseDir(rootDir, level=1, show=False)`

功能: 遍历 rootDir 路径

### `matchFile(key, pathList)`

功能: 从指定的 pathList 中匹配包含 key 的条目

**参数**

| 参数 | 说明 |
|---|---|
| `key` | str 返回第一个匹配；list 返回全部匹配 |

---

<a id="mod-workflow"></a>

## 任务与定时 `smartpy.workflow`

smartpy.workflow —— 配置驱动的任务执行 + 定时内存回收线程。

### `runWork(func, workList, num=1, max_workers=4)`

功能: 用线程池执行任务列表

**参数**

| 参数 | 说明 |
|---|---|
| `func` | 待执行函数 |
| `workList` | 参数列表 [{kw: v}, ...] |
| `num` | 整个列表重复执行次数 |
| `max_workers` | 线程数 返回: 结果 list |

### `runWorkN(func, workList, num=1, max_workers=4)`

同 runWork（保留旧名）

### `runWorkConfig(func)`

装饰器：把被装饰配置函数返回的 [{kw: v}] 列表用线程池执行

### `runTimer(sleep=60, func=None)`

启动一个一次性定时器，sleep 秒后执行 func

### `repeat(sleep=60, func=None, forever=True)`

循环定时执行 func

**参数**

| 参数 | 说明 |
|---|---|
| `sleep` | 间隔秒数 |
| `func` | 回调 |
| `forever` | True 无限循环；False 执行一次 返回: 停止函数 stop() |

---

<a id="mod-xfeat"></a>

## 特征匹配（XFeat） `smartpy.xfeat`

smartpy.xfeat —— XFeat (CVPR 2024) 特征匹配适配器。

### `xfeat_match(template, screenshot, midpoint=True, debug=False)`

XFeat 特征匹配定位（与 matchTemplate 同风格：返回 [(x, y)]）。

**参数**

| 参数 | 说明 |
|---|---|
| `template` | 模板 ndarray |
| `screenshot` | 大图 ndarray |
| `midpoint` | 返回中心点 / 左上角 |
| `debug` | 输出诊断 返回: [(x, y)] 或 [] |

### `xfeat_available()`

XFeat 依赖是否就绪（torch + kornia 可导入）。

### `XFeatLocator(top_k=2048, ratio=0.95, min_sim=0.5, min_inliers=6, min_texture=0.25)`

XFeat 定位器（可复用实例，模板特征缓存）。

**示例**

```python
loc = XFeatLocator()
pts = loc.locate(template, screenshot)   # [(x, y)]
```

---

<a id="mod-net"></a>

## 代理与网络 `smartpy.net`

代理环境助手 —— 检测/启用本地代理，并验证各源可达性。

### `enable_proxy(proxy=None)`

把代理写进当前进程环境（子进程继承）。

### `disable_proxy()`

从当前进程环境移除代理。

### `probe_sources(proxy=None, timeout=12)`

逐个源测试 直连 vs 代理，返回结构化结果。

### `proxy_env(enable=True, proxy=None)`

返回带/不带代理的环境变量字典（不修改当前进程）。

### `install_hint()`

给出建议的 pip / 下载命令。

### `probe_stability(url=None, proxy=None, times=6, timeout=12)`

测代理稳定性：连续请求 N 次，返回成功率与耗时分布。

### `download_with_proxy(url, dest, proxy=None, retries=5, expected_size=None)`

带重试下载（该代理有随机失败，单次 curl 会偶发 000）。

**参数**

| 参数 | 说明 |
|---|---|
| `url` | 下载地址 |
| `dest` | 本地路径 |
| `proxy` | 代理地址，None 用 PROXY_URL |
| `retries` | 重试次数 |
| `expected_size` | 期望字节数（给了就校验） 返回: (ok: bool, info: dict) |
