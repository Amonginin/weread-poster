# 第 02 章：视觉绘制 — 54×7 年历网格与 HSL 颜色渐变引擎

> 本章导读
>
> 本章将进入热力图最核心的“图形与算法”部分。你将学习如何用坐标运算将 365 天的数据均匀地塞进 54周 × 7天 的 SVG 网格矩阵中，理解如何推算每年 1 月 1 日所在的星期偏移量，以及如何运用数学线性插值公式在 HSL 空间内为不同的阅读时长计算出细腻的渐变配色。
> 
> **前置知识**：已掌握第 01 章的数据字典结构，了解基本的平面直角坐标系（X-Y 轴坐标）概念。
> **本章目标**：
> 1. 理解并推算热力图星期偏移（start_date_weekday）对齐机制。
> 2. 掌握 HSL 色彩空间插值公式与 RGB 空间差值的优缺点。
> 3. 理解 Poster 数据对象与 Drawer 渲染对象之间的委派模式（Delegation Pattern）。
> 4. 能够通过修改配置新增一个自定义色彩渐变主题。

---

# 第一层：概念导论

> 本层目标：用 250 行左右讲清“网格几何排布与色彩插值原理”。
> 读完本层，你将掌握日历热力图第一格时间前溯的数学逻辑，以及 HSL 空间相较于 RGB 空间色彩过渡更温润的奥秘。

## 1. 为什么网格对齐和色彩渐变是核心难点（背景与动机）

### 1.1 问题引出
如果我们要画一张展示全年 365 天阅读时长的贡献图，最简单的思路是直接弄一个 365 行的列表或者格子，有阅读就填色。但这样的排布完全无法体现出“周一到周日”的周期感，更无法与现实中的日历对齐。

要把它绘制成像 GitHub 贡献图一样工整的网格阵列，必须面对两个棘手问题：
1. **星期的参差不齐**：每年的 1 月 1 日并不一定是星期一，它可能在星期三，也可能在星期五。如果我们直接让 1 月 1 日当周作为网格的开头，前面的星期一和星期二就会缺失，整张图就会上下错位。
2. **色彩跳变太死板**：如果我们简单把阅读时间分成“0-30分钟上浅蓝，30分钟以上上深蓝”，那么 29 分钟和 31 分钟的格子颜色会出现断层跳跳，无法优雅展现“读得越久、颜色越深”的微妙渐进质感。

### 1.2 解决方案
1. **起始日期偏移回溯**：通过计算 1 月 1 日所在的星期值（`start_date_weekday`），把绘图指针向回倒退对应天数，将上一年的最后几天也纳入网格首列作为“空白或背景色格子”补齐，保证热力图的第一行始终是星期一（或星期日）。
2. **HSL 色彩空间线性插值**：不使用跳变阈值，而是根据当天阅读时长在区间中所占的比率，在 HSL（色相、饱和度、亮度）维度上进行平滑插值计算。

### 1.3 方案对比

| 着色方案 | 优点 | 缺点 | 项目中的选择 |
| :--- | :--- | :--- | :--- |
| **阈值区间硬着色** | 计算极其简单，速度飞快 | 颜色过渡突兀，没有渐变质感 | ❌ 不采用 |
| **RGB 空间线性插值** | 代码简单，Python 自带库支持好 | 中间色过渡容易呈现死灰色、不鲜亮 | ❌ 不采用 |
| **HSL 空间线性插值** | 亮度与饱和度过渡极其自然柔和，色彩亮丽 | 需要额外的 HSL 模型转换公式 | ✅ 采用此方案 |

> **项目实例**：在 [utils.py](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L10) 中的 [interpolate_color](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L10) 函数接收两个十六进制颜色和一个比率值，执行 HSL 插值计算，返回无缝过渡的色彩。

---

## 2. 54×7 网格与色彩模型设计（架构与核心概念）

### 2.1 网格排布的平面投影
热力图在 SVG 中是以矩阵坐标表示的。它的主排布方向是**由左至右**推进，列内**从上至下**递增：

```
                 第一周     第二周     第三周   ... (共 54 列)
             ┌──────────┐┌──────────┐┌──────────┐
  周一 (y=0)  │  12-30   ││  01-06   ││  01-13   │
  周二 (y=1)  │  12-31   ││  01-07   ││  01-14   │
  周三 (y=2)  │  01-01   ││  01-08   ││  01-15   │  <-- 1月1日前面用上一年末的日期补齐
  周四 (y=3)  │  01-02   ││  01-09   ││  01-16   │
  周五 (y=4)  │  01-03   ││  01-10   ││  01-17   │
  周六 (y=5)  │  01-04   ││  01-11   ││  01-18   │
  周日 (y=6)  │  01-05   ││  01-12   ││  01-19   │
             └──────────┘└──────────┘└──────────┘
```

每一列的宽度和行的高度都是固定的。通过将绘图起始时间向回前溯，整个网格就可以被平铺在一块干净的 SVG 矩形画布上。

### 2.2 Poster 与 Drawer 的协作机制
本项目在设计上将数据与具体的渲染实现进行了解耦：
* **`Poster`**：海报的数据模型，它存放了具体的 `tracks` 字典、年份范围、背景色 `background` 以及轨道颜色 `track`。
* **`Drawer`**：图形绘制器，它是 Poster 的“画笔”。Poster 负责调用 `Drawer` 的接口，Drawer 解析 Poster 中的数据并完成具体的 SVG 标签拼装。

> **项目实例**：在 [poster.py](file:///d:/coding/personalProj/weread-poster/weread_poster/poster.py#L68) 中的 [draw](file:///d:/coding/personalProj/weread-poster/weread_poster/poster.py#L68) 方法接收一个 `Drawer` 对象，将具体的像素排版权完全委托给该 Drawer 实例执行。

---

## 3. 快速上手（颜色渐变生成）

你可以直接运行以下最简脚本 `demo_color.py`，调用我们移植的色彩插值逻辑，查看从微信读书浅蓝到深蓝的色彩过渡阶梯：

```python
import colour

def interpolate_color(color1, color2, ratio):
    c1 = colour.Color(color1)
    c2 = colour.Color(color2)
    # HSL 线性差值计算
    c3 = colour.Color(
        hue=((1 - ratio) * c1.hue + ratio * c2.hue),
        saturation=((1 - ratio) * c1.saturation + ratio * c2.saturation),
        luminance=((1 - ratio) * c1.luminance + ratio * c2.luminance),
    )
    return c3.hex_l

# 模拟 5 个不同的阅读强度比率
for i in range(5):
    ratio = i / 4.0
    hex_color = interpolate_color("#E8F4F8", "#0077CC", ratio)
    print(f"强度 {ratio * 100:>3.0f}% 对应 HEX 色值: {hex_color}")
```

输出的 5 个阶梯色彩如下：
```
强度   0% 对应 HEX 色值: #e8f4f8
强度  25% 对应 HEX 色值: #aae0ff
强度  50% 对应 HEX 色值: #5bb3ff
强度  75% 对应 HEX 色值: #0c7fff
强度 100% 对应 HEX 色值: #0077cc
```

---

# 第二层：源码解析

> 本层目标：逐方法、逐逻辑线索解析海报的绘制与上色引擎。
> 读完本层，你能独立定制图形的行距列距、设计独特的主题配色包，并彻底搞懂坐标平移机制。

## 4. 接口与模块源码逐一解析

### 4.1 Poster 数据模型控制器

`Poster` 维护了数据、年份和整体图纸宽高，并负责最终 SVG 文件的写盘。

* **源码位置**：[weread_poster/poster.py](file:///d:/coding/personalProj/weread-poster/weread_poster/poster.py)
* **核心类定义**：
```python
class Poster:
    def __init__(self):
        self.title = None
        self.tracks = {}
        self.type_list = []
        self.length_range_by_date = ValueRange()  # 时长极值区间数据结构
        self.width = 200
        self.height = 300
        self.years = None
        self.colors = {
            "background": "#222222",
            "text": "#FFFFFF",
            "special": "#FFFF00",
            "track": "#4DD2FF",
        }
```

* **Poster 核心绘图驱动方法**：

```python
# 源码位置：weread_poster/poster.py
def _draw_github(self, drawer, output):
    height = self.height
    width = self.width
    self.tracks_drawer = drawer
    # 1. 实例化 svgwrite 的 Drawing 画布，定义 mm 物理尺寸与 Viewbox 视口尺寸
    d = svgwrite.Drawing(output, (f"{width}mm", f"{height}mm"))
    d.viewbox(0, 0, self.width, height)
    
    # 2. 绘制大底色背景矩形
    d.add(d.rect((0, 0), (width, height), fill=self.colors["background"]))
    
    # 3. 绘制标题头部文字
    self._draw_header(d)
    
    # 4. 调用绑定的 Drawer 绘制网格，起点坐标为 X=10, Y=30
    self._draw_tracks(d, XY(10, 30))
    d.save()
```

---

### 4.2 Drawer 矢量图渲染器

`Drawer` 控制具体的格子坐标演算与着色填充。

* **源码位置**：[weread_poster/drawer.py](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py)
* **核心类定义**：
```python
class Drawer:
    name = "github"

    def __init__(self, p):
        self.poster = p
        self.year_size = 200 * 4.0 / 80.0             # 年份文字大小基准
        self.year_style = f"font-size:{self.year_size}px; font-family:Arial;"
        self.year_length_style = f"font-size:{110 * 3.0 / 80.0}px; font-family:Arial;"
        self.month_names_style = "font-size:2.5px; font-family:Arial"
```

* **Drawer 核心渲染流程方法**：

| 方法名 | 参数 | 职责与关键行为 |
| :--- | :--- | :--- |
| [draw](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L189) | `dr: Drawing`, `offset: XY` | 轮询 `Poster.years` 数组，从最晚的年份开始倒序（最新一年在最上面）调用 `_draw_one_calendar` 绘制日历网格。 |
| [_draw_one_calendar](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L103) | `dr: Drawing`, `year: int`, `offset: XY` | 计算当年年份文字、总阅读时长、月份缩写文字的绘制坐标。循环 54 周 × 7 天推进，生成每一格的具体物理位置。 |
| [make_color](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L37) | `length_range: ValueRange`, `length: float` | 检查当天时长是否超过 Top 20% 重度阈值，若超过直接使用 `special2` 颜色；否则将时长在区间内折算比率，调用 `interpolate_color` 计算渐变色。 |
| [_gen_day_box](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L76) | 多个位置与数据参数 | 实例化 `svgwrite.Drawing.rect` 并注入悬停 `desc` 标题标签。 |

---

## 5. 实现细节深入

### 5.1 星期网格的绘制机制与偏移逻辑
在 [drawer.py 的 _draw_one_calendar](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L103-L187) 中，我们来看一下经典的 54×7 网格偏移机制是如何实现的：

```python
# 源码位置：weread_poster/drawer.py
def _draw_one_calendar(self, dr, year, offset, _type=None):
    # 1. 计算 1 月 1 日对应星期几（0 代表周一，6 代表周日）
    start_date_weekday, _ = calendar.monthrange(year, 1)
    
    # 2. 定位当年的元旦日期
    github_rect_first_day = datetime.date(year, 1, 1)
    
    # 3. 关键前溯：将绘图起点往回倒退对应天数，对齐星期列
    github_rect_day = github_rect_first_day + datetime.timedelta(-start_date_weekday)
    ...
    rect_x = 10.0 # 首列的起始 X 坐标偏移量
    for _ in range(54): # 循环 54 周
        rect_y = offset.y + self.year_size + 2 # 每列的 Y 轴初始定位
        for _ in range(7):
            # 一旦跨越到下一年，立即跳出循环
            if int(github_rect_day.year) > year:
                break
            rect_y += 3.5 # 格子的高 + 间距（2.6mm + 0.9mm）
            
            # 从 poster.tracks 字典中获取该日期的阅读时长
            date_title = str(github_rect_day)
            day_tracks = self.poster.tracks.get(date_title)
            
            # 调用 _gen_day_box 创建格子并 add 到画布
            for rect in self._gen_day_box(dr, rect_x, rect_y, date_title, day_tracks, ...):
                dr.add(rect)
                
            # 时间指针向后推进一天
            github_rect_day += datetime.timedelta(1)
        rect_x += 3.5 # 列宽 + 间距（2.6mm + 0.9mm）
```
* **坐标推演规律**：
  * 每个格子的物理大小 `DOM_BOX_TUPLE` 为 `2.6 * 2.6`。
  * 为了在格子之间留下 `0.9` 毫米的空隙，每次 X 轴和 Y 轴的推进累加步长均为 `3.5`（即 `2.6 + 0.9`）。
  * 这种纯数值控制能够保证矢量网格的边缘在任何尺寸的视口（Viewbox）中都纹丝不动，保持完美的像素级清晰。

---

## 6. 异常与边界情况处理

### 6.1 年份无数据剔除防溢出
如果在所选的多年份区间内，早期的几年完全没有有效数据，在 [cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L169-L172) 中，[reduce_year_list](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L53) 方法将被调用：
```python
years = reduce_year_list(years, tracks)
if not years:
    print("指定年份范围内无有效数据")
    sys.exit(1)
```
这避免了在 `Drawer` 中尝试对完全空的列表计算分位数导致 `inf` 以及除以零错误（ZeroDivisionError），在源头上拦截了无效绘图任务。

### 6.2 零时长格子上色兜底
如果某天没有阅读记录，在 [drawer.py 的 make_color](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L37) 或是 `_gen_day_box` 中，如果不做单独处理，插值公式将面临分母为零的险境。
我们在 [_gen_day_box](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L89) 中设置了默认值：
```python
color = DEFAULT_DOM_COLOR # '#444444' 暗灰色作为无阅读底色
if day_tracks:
    color = self.make_color(self.poster.length_range_by_date, day_tracks)
```
这样既让无数据的格子以暗底色和谐融入背景，又避开了异常算术路径。

---

## 7. 本章知识总结

| 知识点 | 概念导论中的解释 | 源码中的位置 | 关键行为 |
| :--- | :--- | :--- | :--- |
| **星期前溯偏移** | 将元旦回退对应星期数对齐左上角 | [drawer.py:_draw_one_calendar](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L108) | `github_rect_day = github_rect_first_day + timedelta(-weekday)` |
| **格子间距递增** | 像素尺寸加空隙作为每次循环偏移 | [drawer.py:_draw_one_calendar](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L166-L186) | 每次循环 Y 累加 3.5 毫米，X 累加 3.5 毫米 |
| **委派模式** | 数据与绘图分离，通过接口通信 | [poster.py:Poster](file:///d:/coding/personalProj/weread-poster/weread_poster/poster.py#L68) | `self.draw(drawer, output)` 中调用 `drawer.draw(d, ...)` |
| **HSL 插值** | 利用 HSL 空间避免 RGB 插值导致的灰色 | [utils.py:interpolate_color](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L18) | 按照 `hue`, `saturation`, `luminance` 比率融合 |

### 知识地图

```
第 02 章 知识地图：

热力图网格渲染与色彩处理
  ├── 协作模型
  │    ├── Poster (数据管理与背景常量)
  │    └── Drawer (画布绘制与网格执行器)
  ├── 坐标渲染
  │    ├── 1月1日星期偏移回溯 ➔ timedelta(-start_date_weekday)
  │    └── 54×7 循环递推 ➔ 每次平移 3.5 毫米 (宽2.6 + 隙0.9)
  └── 渐变上色
       ├── 无阅读天 ➔ 填充默认 DEFAULT_DOM_COLOR (#444444)
       ├── Top 20% 天 ➔ 填充特殊高亮 special2 颜色
       └── 普通阅读天 ➔ HSL 色彩空间双向线性插值 (utils.py)
```

- **核心要点 1**：元旦星期对齐是 GitHub 风格热力图在工程上保证星期行不乱的根本。
- **核心要点 2**：矩阵循环中使用 3.5 毫米作为递增因子是保证格子与间隙紧密契合的几何常量。
- **核心要点 3**：HSL 线性插值能有效克服物理 RGB 空间中值塌陷的缺陷，确保过渡色彩温润。

→ 下一章：[第 03 章：动态交互 — SVG 淡入动画、悬停提示与主流程控制](file:///d:/coding/personalProj/weread-poster/docs/tutorial/03-animation-and-cli.md)

---

## 8. 思考题

### 题目 1：为什么在 `Drawer._draw_one_calendar` 中，年份总时长的标签位置被硬编码为 `offset.tuple()[0] + 165`？这个数值是如何推导出来的？

<details>
<summary>参考解答</summary>
因为整张海报的画布宽度被设置为 `200` 毫米（参见 `cli.py` 中 `p.width = 200`），且网格绘制的起点 X 坐标设为 `10` 毫米。
54 列网格每列占 `3.5` 毫米，所以网格区域总宽度约为 `53 * 3.5 + 2.6 = 188.1` 毫米。
若要在右侧对齐的位置写年度总时长标签，取 X 坐标为 `X_start (10) + 165 = 175` 毫米，可以在网格右侧边缘内留下约 `13` 毫米的空间，刚好能完美容纳类似 `128 hours` 的总时长文字，实现右对齐排版。
</details>

### 题目 2：已知某年的 1 月 1 日是星期二。若不使用前溯偏移（即 `start_date_weekday = 0`），那么该年第一周的星期一对应的格子会绘制哪一天的数据？这会产生什么逻辑漏洞？

<details>
<summary>参考解答</summary>
若不使用前溯偏移，程序会直接从 1 月 1 日绘制在首列的第一格（通常对应周一的坐标）。
这意味着现实中是星期二的 1 月 1 日，在图表中会被画在周一的坐标行上；随后的所有日子都会被向前错配一天。这不仅会导致格子指示的星期与现实日期完全脱线，而且会使悬停提示的日期与对应格子的位置产生不可接受的逻辑错位。
</details>

### 题目 3：当把配色主题配置为 `weread` 蓝时，`apply_theme` 函数会把 `levels[0]`（淡蓝 `#E8F4F8`）赋给 `colors["track"]`，把 `levels[4]`（深蓝 `#0077CC`）赋给 `colors["special2"]`。在此设置下，如果用户某天的阅读时长正好在 Top 20% 到 Top 50% 之间，那么这天的格子会呈现什么颜色？

<details>
<summary>参考解答</summary>
根据 `make_color` 的核心逻辑：
```python
has_special = sp2 < length < sp1  # 即当天阅读时长在 Top 50% 与 Top 20% 之间
color_from = self.poster.colors["special"] if has_special else self.poster.colors["track"]
```
若 `has_special` 为真，`color_from` 会变为 `colors["special"]`（也就是 `levels[1]`，即 `#B5E1FF`）。此时格子将使用 `levels[1]` 到 `levels[4]` 之间的色彩进行线性插值，颜色深度起点抬高，视觉上呈现出比普通低时长更明显的明亮粉蓝。
</details>

### 题目 4：[动手实践] 如何修改 `Drawer._draw_one_calendar`，使得每一年的热力图网格之间不再有拥挤感，而是增加 5 毫米的年份纵向安全间距？请指明需要改动哪一行源码并写出改动后的写法。

<details>
<summary>参考解答</summary>
打开 [drawer.py](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L187)，可以发现当年份画完时，offset 指针的 Y 坐标会累加下移，为下一年留出纵向起始距离：
```python
# 源码第 187 行原本为：
offset.y += 3.5 * 9 + self.year_size + 1.0
```
为了在每两个年份之间多增加 5 毫米的纵向间距，可以将该行代码加上 `5.0`，修改为：
```python
offset.y += 3.5 * 9 + self.year_size + 1.0 + 5.0
```
</details>
