# smartpy 用例文档

> 全部用例都是**可直接运行**的代码片段，基于真实场景。
> 完整参数见 [API.md](API.md)。

## 目录

- [1. 环境准备](#1-环境准备)
- [2. 图色识别场景](#2-图色识别场景)
- [3. 识图匹配场景](#3-识图匹配场景)
- [4. 键鼠操作场景](#4-键鼠操作场景)
- [5. 窗口控制场景](#5-窗口控制场景)
- [6. 遮罩窗口场景](#6-遮罩窗口场景)
- [7. 多开 / 并发场景](#7-多开--并发场景)
- [8. 网络与依赖场景](#8-网络与依赖场景)
- [9. 踩坑与性能](#9-踩坑与性能)

---

## 1. 环境准备

### 1.1 最小可运行

```python
import sys
sys.path.insert(0, r"F:\smartpy")
import smartpy

img = smartpy.screenCapture()
print(img.shape)        # (高, 宽, 4) —— BGRA
```

### 1.2 旧脚本迁移（`import Module` 仍然可用）

```python
import sys
sys.path.insert(0, r"F:\smartpy")
import Module           # shim，转发到 smartpy

Module.findClick("按钮", r"imgs", isclick=False)
```

### 1.3 API 兼容自检

```powershell
python scripts\api_diff.py     # 对比旧 Module.py，确认没有丢接口
```

---

## 2. 图色识别场景

### 2.1 判断某个状态点是什么颜色（看血条/指示灯）

```python
import smartpy

# 单点取色
c = smartpy.getPixel(120, 340)
print(hex(c))                                   # 0x3cb371

# 比色（容差 8，抗压缩噪声）
if smartpy.compareColor(120, 340, 0x3CB371, sim=8):
    print("血条是绿色 → 满血")
```

**性能提示**：连续判断多个点时先 `snapshot()`，否则每次都要截图（4K 一次约 25ms）。

```python
smartpy.snapshot()
print(smartpy.getPixel(120, 340))
print(smartpy.getPixel(121, 340))
print(smartpy.getPixel(122, 340))     # 三个点合计 < 10 微秒
smartpy.clearSnapshot()
```

### 2.2 找纯色按钮并点击

```python
import smartpy

pt = smartpy.findColor(0x1E90FF, region=(0, 0, 1920, 1080))
if pt:
    print("找到蓝色按钮:", pt)
    smartpy.click_it(*pt)

# 或者一步到位
smartpy.findColorClick(0x1E90FF, region=(0, 0, 1920, 1080), offset=3)
```

### 2.3 找色块并点它的中心（比找首点可靠）

```python
import smartpy

blocks = smartpy.findColorBlock(0xFF4444, region=(0, 0, 1920, 1080), min_area=200)
if blocks:
    b = blocks[0]              # 已按面积从大到小排序
    print("最大红块: 位置(%d,%d) 尺寸%dx%d 面积%d" % (b["x"], b["y"], b["w"], b["h"], b["area"]))
    smartpy.click_it(b["cx"], b["cy"])
```

**为什么更好**：`findColor` 返回最上方第一个命中像素（可能是按钮边缘的 1px），
`findColorBlock` 返回连通区域的真实中心。

### 2.4 「任意红」——颜色范围找色

界面上的红色因渲染/压缩会抖动，精确色往往找不到：

```python
import smartpy

# 深红 ~ 浅红 全区间
pt = smartpy.findColorRange(0x800000, 0xFF5050, region=(0, 0, 1920, 1080))
print("任意红:", pt)

# 统计红色像素占比（做进度条判断）
total = 1920 * 1080
ratio = smartpy.countColorRange(0x800000, 0xFF5050, region=(0, 0, 1920, 1080)) / total
print("红色占比: %.2f%%" % (ratio * 100))
```

### 2.5 多点找色（抗干扰最强）

单个颜色容易被背景误伤。多点找色要求「主色 + 多个偏移点的颜色」同时成立：

```python
import smartpy

# 目标是一个「红色方块 + 右侧绿条 + 下方蓝条」的小图标
first = 0xFF0000                       # 左上角红
offsets = [
    ((12, 0), 0x00FF00),               # 右侧 12px 是绿
    ((0, 8), 0x0000FF),                # 下方 8px 是蓝
]

pt = smartpy.findMultiColor(first, offsets, region=(0, 0, 1920, 1080), sim=10)
if pt:
    smartpy.click_it(*pt)
```

### 2.6 等界面响应（挂机脚本核心）

```python
import smartpy

# 点击"开始"按钮后，等加载完成的绿点出现（最多 15 秒）
smartpy.click_it(800, 600)
if smartpy.waitColor(0x00FF00, timeout=15, region=(700, 100, 400, 60)):
    print("加载完成")
else:
    print("加载超时")

# 等 loading 转圈的某色消失
smartpy.waitColorDisappear(0xFFFF00, timeout=10, region=(0, 0, 200, 200))

# 等某个点颜色变了（点击生效判断）
new_color = smartpy.waitColorChange(400, 300, timeout=5)
if new_color:
    print("界面已响应，新颜色:", hex(new_color))
```

### 2.7 多点找色 + 等待组合

```python
import smartpy

target = smartpy.waitMultiColor(
    0xFF0000,
    [((12, 0), 0x00FF00), ((0, 8), 0x0000FF)],
    timeout=20,
    sim=10,
)
if target:
    smartpy.findColorClick(0xFF0000, region=(0, 0, 1920, 1080), sim=10)
```

---

## 3. 识图匹配场景

### 3.1 找图并点击（最常用）

```python
import smartpy

# 图片目录里放 button.png / start.png / ...
smartpy.findClick("button", r"F:\imgs", endswith=".png", isclick=True)
```

### 3.2 只找不点（做判断）

```python
import smartpy

result = smartpy.findClick("elite", r"F:\imgs", isclick=False)
if result:
    print("精英怪出现于:", result)
```

### 3.3 精确控制阈值与性能

```python
import smartpy

# gray 模式比 rgb 快约 2.5 倍，阈值略放宽
pt = smartpy.findClick("icon", r"F:\imgs", mode="gray", threshold=0.9,
                      isclick=False, pyramid=True)

# 需要绝对精确（对阈值边界敏感）时关掉金字塔
pt2 = smartpy.findClick("icon", r"F:\imgs", isclick=False, pyramid=False)
```

### 3.4 直接做模板匹配（不落盘图片）

```python
import smartpy

screen = smartpy.screenCapture()
template = screen[100:160, 200:340]        # 直接截图里切一块

pts = smartpy.matchTemplate(template, screen, threshold=0.9, onlyone=True)
print(pts)                                  # [(cx, cy)]
```

### 3.5 目标被缩放 / 旋转（XFeat 兜底）

⚠️ **只在画面纹理丰富时有效**（游戏画面 / 照片）。典型 Windows UI 会失败，
这是实测结论，见 [README](../README.md)。

```python
import smartpy

# 方式一：matchTemplate 失败后自动兜底
pts = smartpy.matchTemplate(template, screen, threshold=0.9,
                           onlyone=True, feature_fallback=True)

# 方式二：findClick 里打开
smartpy.findClick("boss", r"F:\imgs", isclick=False, feature_fallback=True)

# 方式三：直接调用
pts = smartpy.xfeat_match(template, screen, debug=True)
```

### 3.6 多窗口批量找图

```python
import smartpy

hwnds = smartpy.enumWindow(WindowTitle="游戏窗口")
for h in hwnds:
    pt = smartpy.findClick("start", r"F:\imgs", isclick=False, hwnd=h)
    print("窗口 %s -> %s" % (h, pt))
```

---

## 4. 键鼠操作场景

### 4.1 前台点击（会动物理鼠标）

```python
import smartpy

smartpy.click_it(500, 300, offset=3)          # 带 ±3 随机偏移
smartpy.click1(500, 300)                       # 固定点
smartpy.click_it(500, 300, button="right")     # 右键
smartpy.click_it(500, 300, button="doubleleft")# 双击
```

### 4.2 后台点击（不动物理鼠标）

```python
import smartpy

hwnd = smartpy.findWindow(windowTitle="记事本")
smartpy.click_point((100, 200), hwnd=hwnd)                # 屏幕坐标
smartpy.click_pointForClient((100, 200), hwnd=hwnd)       # 客户区坐标
```

### 4.3 拖拽（带轨迹）

```python
import smartpy

# 贝塞尔曲线拖拽（更像人）
smartpy.moveMouse4((100, 300), (600, 300), hwnd=hwnd, cost=2)

# 直线轨迹拖拽
smartpy.moveMouse3((100, 300), (600, 300), hwnd=hwnd)

# 物理鼠标拖拽
smartpy.moveMouse1((100, 300), (600, 300))
```

### 4.4 生成轨迹点（可复用）

```python
import smartpy

pts = smartpy.genLinePointList((0, 0), (300, 200), offset=2)
print(len(pts), pts[0], pts[-1])         # 首尾精确等于起点/终点

curve = list(smartpy.cubic_bezier_gen((0, 0), (300, 200), 20))
```

### 4.5 发送文本 / 按键

```python
import smartpy

smartpy.send_str("hello 世界", hwnd=hwnd)     # 逐字符 WM_CHAR
smartpy.send_enter(hwnd=hwnd)

smartpy.set_clipboard_text("复制的内容")
smartpy.clipboard_paste(hwnd=hwnd)
```

---

## 5. 窗口控制场景

### 5.1 查找窗口

```python
import smartpy

hwnd = smartpy.findWindow(windowTitle="记事本")          # 精确标题
infos = smartpy.enumWindows()                            # 全部窗口
hits = smartpy.enumWindow(WindowTitle="游戏")             # 标题含"游戏"
print(len(hits), "个匹配")
```

### 5.2 移动 / 置顶 / 透明

```python
import smartpy

smartpy.setWindowRect(hwnd, Rect=(100, 100, 800, 600))
smartpy.setTopWindow(hwnd, setTop=True)
smartpy.setWindowTrans(hwnd, transColor=smartpy.win32api.RGB(0, 0, 0), Alpha=200)
smartpy.setMousePenetration(hwnd, Penetration=True)
```

### 5.3 窗口是否置顶

```python
import smartpy

print(smartpy.getTopWindowExist(hwnd))    # True / False
```

### 5.4 关闭窗口

```python
import smartpy

smartpy.closeWindows(smartpy.enumWindow(WindowTitle="计算器"))
```

---

## 6. 遮罩窗口场景

### 6.1 显示一个透明覆盖层

```python
import smartpy
import time

win = smartpy.Window(
    className="MyOverlay",
    windowTitle="overlay",
    windowWidth=600,
    windowHeight=300,
    Alpha=180,
    isDaemon=True,
)
win.start()

deadline = time.time() + 5
while time.time() < deadline and win.hwnd is None:
    time.sleep(0.05)

print("窗口句柄:", win.hwnd)
time.sleep(3)
win.close()
```

### 6.2 自定义绘制（继承 Window）

```python
import smartpy


class BoxOverlay(smartpy.Window):
    def _draw(self, hdc):
        self._drawRectangle(hdc, (50, 50, 300, 200),
                            penColor=self._getRGB(255, 0, 0),
                            bgColor=self._getRGB(0, 255, 0),
                            rType=1)
        self._drawText(hdc, "HELLO", (50, 50, 300, 200))


win = BoxOverlay(windowWidth=400, windowHeight=300, isDaemon=True)
win.start()
```

---

## 7. 多开 / 并发场景

### 7.1 线程池批量执行

```python
import smartpy

work = [
    {"findName": "start", "filePathList": r"F:\imgs", "hwnd": h, "isclick": False}
    for h in smartpy.enumWindow(WindowTitle="游戏")
]
results = smartpy.runWork(smartpy.findClick, work, max_workers=4)
print(results)
```

### 7.2 配置驱动

```python
import smartpy


@smartpy.runWorkConfig(smartpy.findClick)
def config():
    base = {"findName": None, "filePathList": r"F:\imgs",
            "isclick": False, "endswith": ".png"}
    return [
        dict(base, findName="start"),
        dict(base, findName="exit"),
    ]


results = config()
```

### 7.3 多窗口并发找色

```python
import smartpy
from concurrent.futures import ThreadPoolExecutor

hwnds = smartpy.enumWindow(WindowTitle="游戏")


def check(h):
    smartpy.snapshot(hwnd=h)          # 每个线程用自己那一帧
    return h, smartpy.getPixel(100, 100, hwnd=h)


with ThreadPoolExecutor(max_workers=4) as pool:
    for h, color in pool.map(check, hwnds):
        print(h, hex(color) if color else None)
```

### 7.4 定时回收内存

```python
import smartpy
import gc

stop = smartpy.repeat(sleep=60, func=gc.collect)
# ... 脚本运行 ...
stop()
```

---

## 8. 网络与依赖场景

### 8.1 代理探测

```powershell
python -m smartpy.net
```

```python
from smartpy import net

net.enable_proxy()                    # 写进当前进程环境
print(net.probe_sources())            # 逐域名对比
print(net.probe_stability(times=6))   # 成功率
```

### 8.2 带重试下载

```python
from smartpy import net

ok, info = net.download_with_proxy(
    "https://raw.githubusercontent.com/xxx/yyy/main/model.bin",
    r"F:\models\model.bin",
    retries=5,
)
print(ok, info)
```

### 8.3 装依赖

```powershell
# pip 走代理
pip install --proxy http://127.0.0.1:7890 <pkg>

# HuggingFace 大模型走镜像（代理对 cdn-lfs 无效）
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

---

## 9. 踩坑与性能

### 9.1 ★ 图色连续查询一定要 snapshot

```python
# 慢：每次 6ms（都要截图）
for i in range(100):
    smartpy.getPixel(i, 100)

# 快：每次 < 1 微秒
smartpy.snapshot()
for i in range(100):
    smartpy.getPixel(i, 100)
smartpy.clearSnapshot()
```

**注意**：快照是"某一帧"。画面会变时（等动画、等加载）**不要**用快照，
或者每次重新 `snapshot()`。`waitColor` 内部会自动重新截图，不受快照影响。

### 9.2 坐标语义容易混

| 函数 | 输入坐标系 | 返回坐标系 |
|---|---|---|
| `findColor` / `findColorEx` | 屏幕 | 屏幕 |
| `findColor(hwnd=...)` | — | 屏幕（内部换算） |
| `findColor(img=...)` | 图内 | 图内（不加偏移） |
| `click_point(pos, hwnd)` | 屏幕 | 屏幕 |
| `click_pointForClient(pos, hwnd)` | 客户区 | 客户区 |
| `matchTemplate(isclient=True)` | — | 客户区 |

### 9.3 模板匹配的坑

- **常量模板**（纯色 GIF/PNG）会让 `CCOEFF_NORMED` 退化、全图恒命中
  → 用 `mode="gray"` + `method=5`(SQDIFF_NORMED)，或换带纹理的模板
- **小模板**（<48px）金字塔会自动退化到全分辨率，不会漏检
- **缩放/旋转的模板** → `matchTemplate` 必漏，用 `feature_fallback=True`

### 9.4 XFeat 别用在 UI 上

实测：典型 Windows UI（纯色+文字）XFeat 误差 858px、完全失败。
它只适合高纹理画面（游戏场景/照片）。

### 9.5 多线程注意事项

- `snapshot()` 是**进程级全局状态**，多线程同时用会互相覆盖
  → 每个线程自己管理，或者改用 `img=` 参数传图
- 截图（GDI BitBlt）本身线程安全，可以并发
- 点击/按键会争用输入队列，建议串行或加锁

### 9.6 性能速查

| 操作 | 4K 耗时 |
|---|---|
| 截图一次 | 25~30 ms |
| 单点取色（有快照） | 0.9 微秒 |
| 单点取色（无快照） | 6 ms |
| 全屏找色（有快照） | 21 ms |
| 全屏找色（无快照） | 110 ms |
| 模板匹配 40×40（金字塔） | 20 ms |
| 模板匹配 40×40（暴力） | 73 ms |
| 模板匹配 160×160 @4K（金字塔） | 38 ms |
| XFeat 匹配（1280×720） | 150~650 ms |
| 多点找色 200×200（含截图） | 55 ms |

### 9.7 调试技巧

```python
import smartpy

# 找色失败时，先看图
img = smartpy.screenCapture()
smartpy.saveImage(r"F:\debug\screen.jpg", img)

# 检查目标区域颜色分布
c = smartpy.getColorAt(img, 100, 200)
print("该点颜色:", hex(c))
print("该色全屏像素数:", smartpy.countColor(c, img=img))

# XFeat 诊断
smartpy.xfeat_match(template, img, debug=True)
```
