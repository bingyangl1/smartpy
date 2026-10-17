# smartpy 文档

| 文档 | 内容 | 维护方式 |
|---|---|---|
| [API.md](API.md) | 全部接口的签名、参数、返回值、示例 | 自动生成（勿手改） |
| [COOKBOOK.md](COOKBOOK.md) | 9 大类真实用例，可直接运行 | 手工维护 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更、Bug 修复、性能数据 | 手工维护 |
| [../README.md](../README.md) | 项目总览、安装、目录结构、实测结论 | 手工维护 |

## 接口文档怎么更新

`API.md` 是从源码 docstring 生成的，不要手工改。改完代码后：

```powershell
cd F:\smartpy

# 重新生成
python scripts\gen_api_docs.py

# 或只校验是否过期（CI 用，过期返回退出码 1）
python scripts\gen_api_docs.py --check
```

## 写 docstring 的约定

生成器按固定小标题切分，这样能被正确解析：

```python
def my_func(a, b=0):
    """
    一句话简述（会作为接口说明）。

    参数:
        a: 参数 a 的说明
        b: 参数 b 的说明
    返回: 返回值的说明
    示例:
        my_func(1, 2)
    注意:
        需要特别提醒的内容（可选）
    """
```

支持的小标题：`参数` / `返回值`（或 `返回`） / `示例` / `注意`（或 `注`、`性能说明`） / `说明` / `用法`。

## 测试

```powershell
cd F:\smartpy
python -m pytest tests -q                                       # 全部（网络用例自动跳过）
$env:AUTOPY_NET_TEST=1; python -m pytest tests\test_net.py -q   # 含真实网络
```

测试文件与模块的对应关系：

| 测试文件 | 覆盖 |
|---|---|
| `tests/test_regression.py` | 旧版 13 处必崩 Bug + 核心算法 |
| `tests/test_color.py` | 图色识别全部接口 |
| `tests/test_xfeat.py` | XFeat 能力边界 |
| `tests/test_net.py` | 代理配置逻辑 |

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/gen_api_docs.py` | 生成/校验接口文档 |
| `scripts/api_diff.py` | 对比旧 `Module.py`，确认没丢接口 |
| `scripts/smoke.py` | 端到端冒烟（截图→匹配→遮罩窗） |
| `scripts/bench3.py` | 模板匹配性能基准 |
| `scripts/xfeat_boundary.py` | XFeat 能力边界复测 |

## 口径说明

文档里的性能数字全部是**本机实测**（4K 3840×2160，Windows，Python 3.12 / numpy 2.4.4 /
OpenCV 4.11 / pywin32 305）。换机器会有差异，但量级关系可用作选型参考。

能力边界的结论（尤其 XFeat 在 UI 上无效）也是实测得出，不是推测——可以用
`scripts/xfeat_boundary.py` 复跑验证。
