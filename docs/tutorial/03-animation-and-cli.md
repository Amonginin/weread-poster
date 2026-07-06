# 第 03 章：动态交互 — SVG 淡入动画、悬停提示与命令行主流程控制

> 本章导读
>
> 本章将引领你探索热力图海报的“交互与控制”奥秘。你将学习如何通过 SVG 标准在矢量图中嵌入原生不透明度淡入动画，掌握利用浏览器原生的 `desc` 提示框实现鼠标悬浮交互，并深入剖析 `cli.py` 是如何作为大脑，将鉴权、加载、配置与渲染各模块有机融合，提供灵活友好的命令行操作界面的。
> 
> **前置知识**：已掌握前两章的数据流与网格渲染，了解命令行传参（Arguments）的基本概念。
> **本章目标**：
> 1. 理解 SVG 原生动画标签 `<animate>` 的运作方式与 `keyTimes` 控制。
> 2. 掌握鼠标悬停（Hover）在 SVG 矩形元素上显示日历详情的实现原理。
> 3. 理解命令行解析器 `argparse` 的参数定义与覆写逻辑。
> 4. 能够编写并集成一个新的命令行参数以扩展海报功能。

---

# 第一层：概念导论

> 本层目标：用 250 行左右讲清“SVG 动画分配逻辑与主控调度思路”。
> 读完本层，你将掌握如何通过划分时间切片来控制 365 个格子按顺序平滑淡入，以及 CLI 入口包装的协调策略。

## 1. 为什么需要动画和命令行包装（背景与动机）

### 1.1 问题引出
如果生成出来的热力图只是一个平平无奇的静态网格图，用户在使用时可能会觉得单调枯燥，也无法直观感受到数据“从年初到年末”的时间推移流动感。
另外，如果我们把海报的标题、背景颜色、配色主题全部在 Python 代码里写死，那么普通用户想要定制自己的个性化海报时，就必须手动修改 Python 源码。这对于不具备编程基础的用户来说是一个极高的门槛。

这就需要我们实现以下两项特性：
1. **轻量级动效**：不需要依赖复杂的 JavaScript 库（如 D3.js），仅通过纯 SVG 矢量的原生标签在浏览器内实现格子逐个平滑淡入。
2. **极简操作交互**：将所有绘图配置封装为 CLI 命令行参数，用户在终端敲入一行参数就能随意变换主题、微调颜色或导出 JSON 数据。

### 1.2 解决方案
1. **SVG 原生 `<animate>` 注入**：利用 SVG 支持的 `Animate` 标记，控制矩形格子的 `opacity`（不透明度）。计算格子在一年 365 天中的位置权重，为每一个格子注入独特的启动延时，形成时间流的淡入动效。
2. **`argparse` 主控协调**：在入口处构建统一的参数接收器，应用对应主题色，完成对 Poster 颜色常量的替换，最后调用渲染。

### 1.3 方案对比

| 热力图交互方案 | 优点 | 缺点 | 项目中的选择 |
| :--- | :--- | :--- | :--- |
| **纯静态图片 (PNG/JPG)** | 兼容性极佳，几乎所有平台都能直接展示 | 零交互、无悬浮提示、无动画、缩放模糊 | ❌ 不采用 |
| **HTML + JS 动态画板** | 动画与交互功能极其强大，逻辑丰富 | 无法直接作为一张单独的图片插入 GitHub 个人主页 | ❌ 不采用 |
| **带有原生嵌入 Animate 的 SVG** | 兼顾矢量无损缩放、带平滑淡入动画与悬浮提示，能被 GitHub 直接渲染 | 少量老旧浏览器可能不兼容动画标签 | ✅ 采用此方案 |

> **项目实例**：在 [cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L98-L109) 中，`--with-animation` 与 `--animation-time` 参数允许用户在生成海报时开启该动效并自由指定淡入动画的总生命周期（默认 10 秒）。

---

## 2. 动画时间轴与主入口参数设计（架构与核心概念）

### 2.1 动画关键帧的分帧设计
如果所有的格子在动画启动时同时淡入，视觉上只会看到一片模糊的闪烁，没有“时间推移”的动态层次。
本项目的核心思路是**“依时间顺序排队淡入”**：
* 设一年中累计有阅读记录的天数为 $N$。
* 我们将 10 秒的总动画时长均匀切分为 $N$ 个时间刻度（时间片）。
* 第 1 天的格子在 0% 时间点立刻变亮；第 $i$ 天的格子在第 $i/N$ 的进度刻度前保持 `0`（全透明），在到达该刻度的瞬间跳变为 `1`（完全可见）并一直保持：

```
                    SVG 动画时间轴关键帧 (以 10s 为例)
 
 时间轴比例:  0.0  ...  1/N  ...  i/N  ......   1.0 (10s 结束)
             ├─────┼─────┼─────┼─────┼──────────┤
 格子 1 透明度: 0 ➔ 1 ──────────────────────────➔ 1 (一直保持可见)
 格子 i 透明度: 0 ─────────────────➔ 1 ─────────➔ 1 (在 i/N 点淡入)
```

### 2.2 CLI 主控的控制漏斗
命令行主入口扮演了控制漏斗的角色，它接收输入，依次向下传导：

```
                ┌───────────────────────────────────┐
                │        Terminal 命令行参数        │
                └─────────────────┬─────────────────┘
                                  ▼
                ┌───────────────────────────────────┐
                │      cli.py: build_parser()       │
                └─────────────────┬─────────────────┘
                                  ▼
                ┌───────────────────────────────────┐
                │      cli.py: apply_theme()        │
                │     (加载对应的 THEME 配色矩阵)    │
                └─────────────────┬─────────────────┘
                                  ▼
                ┌───────────────────────────────────┐
                │      命令行覆盖：background_color   │
                │      special_color / text_color   │
                └─────────────────┬─────────────────┘
                                  ▼
                ┌───────────────────────────────────┐
                │      Poster / Drawer 执行渲染      │
                └───────────────────────────────────┘
```

这种金字塔设计能确保默认配置是可用的，同时给予高级用户无死角的微调权限。

---

## 3. 快速上手（构造淡入动画）

你可以通过运行以下精简脚本 `demo_animate.py`，直接在本地生成一个带有平滑渐现动画的 SVG 矢量图：

```python
import svgwrite
import svgwrite.animate

# 1. 创建画板 (100mm * 50mm)
d = svgwrite.Drawing("demo_anim.svg", size=("100mm", "50mm"))
d.viewbox(0, 0, 100, 50)
d.add(d.rect((0, 0), (100, 50), fill="#1a1a1a"))

# 2. 构造两个矩形
rect1 = d.rect((10, 15), (20, 20), fill="#34A7FF")
rect2 = d.rect((40, 15), (20, 20), fill="#0077CC")

# 3. 为 rect1 绑定 0s-3s 保持透明，3s 变亮的 animate 属性
# keyTimes 接受 0.0 到 1.0 的百分比分片
rect1.add(svgwrite.animate.Animate(
    "opacity", dur="5s", values="0;0;1", keyTimes="0.0;0.6;1.0", repeatCount="1"
))

# 4. 为 rect2 绑定 0s-4s 保持透明，4s 后变亮的 animate
rect2.add(svgwrite.animate.Animate(
    "opacity", dur="5s", values="0;0;1", keyTimes="0.0;0.8;1.0", repeatCount="1"
))

d.add(rect1)
d.add(rect2)
d.save()
print("已成功生成 demo_anim.svg，请在浏览器中打开查看动态淡现效果！")
```

---

# 第二层：源码解析

> 本层目标：逐方法解析动画生成与主入口控制逻辑。
> 读完本层，你能独立为 CLI 添加新功能（如指定文字字体等），掌握 SVG 交互框架。

## 4. 接口与模块源码逐一解析

### 4.1 动画帧分片算法

在 [utils.py 的 make_key_times](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L46-L50) 中，使用迭代器计算动画时间片百分比序列：

```python
# 源码位置：weread_poster/utils.py
def make_key_times(year_count):
    # itercount 生成从 0 开始以 1/year_count 为步长的无限序列
    # takewhile 截取其中小于 1 的部分
    s = list(takewhile(lambda n: n < 1, itercount(0, 1 / year_count)))
    s.append(1) # 最终补上 1.0 结束边界
    # 将浮点数转换为字符串形式，保留 2 位小数，符合 SVG 标准
    return [str(round(i, 2)) for i in s]
```
* **工作机理**：如果一年中有阅读天数 `year_count = 10`，此函数会返回：
  `['0.0', '0.1', '0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9', '1.0']`。

---

### 4.2 Drawer 动画附加器

在 [drawer.py 的 _add_animation](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L58-L74) 中，根据格子的序号动态组装 opacity 字符串：

```python
# 源码位置：weread_poster/drawer.py
def _add_animation(self, rect, key_times, animate_index):
    # values 控制透明度状态的跳变
    # 从第 0 帧到第 animate_index-1 帧全部填入 "0" (全透明)
    # 自第 animate_index 帧到最后一帧填入 "1" (完全可见)
    values = (
        ";".join(["0"] * animate_index)
        + ";"
        + ";".join(["1"] * (len(key_times) - animate_index))
    )
    rect.add(
        svgwrite.animate.Animate(
            "opacity",
            dur=f"{self.poster.animation_time}s", # 动画播放总时间
            values=values,
            keyTimes=";".join(key_times),
            repeatCount="1", # 仅播放一次
        )
    )
    return rect
```

---

### 4.3 CLI 入口调度控制器

`cli.py` 定义了命令行接口选项，驱动整个业务流水线。

* **源码位置**：[weread_poster/cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py)
* **核心模块主控制流**：

```python
# 源码位置：weread_poster/cli.py
def main():
    parser = build_parser()
    args = parser.parse_args()

    # 1. 初始化并运行鉴权连通性校验
    auth = WeReadAuth()
    if not auth.init_auth():
        print("请设置环境变量: export WEREAD_API_KEY=<你的API Key>")
        sys.exit(1)

    is_valid, info = auth.test_auth()
    if not is_valid:
        print(f"认证失败: {info.get('error')}")
        sys.exit(1)
    print("认证成功")

    # 2. 解析时间范围并拉取数据
    from_year, to_year = parse_years(args.year)
    loader = WereadLoader(from_year, to_year)
    loader.auth = auth
    tracks, years = loader.get_all_track_data()
    ...
    
    # 3. 初始化 Poster 并加载主题
    p = Poster()
    p.units = loader.unit # "mins"
    apply_theme(p, args.theme) # 初始配置主题色

    # 4. 根据 CLI 参数强行覆写自定义色彩
    if args.background_color:
        p.colors["background"] = args.background_color
    if args.track_color:
        p.colors["track"] = args.track_color
    ...
    
    # 5. 执行 SVG 绘图写盘
    d = Drawer(p)
    p.draw(d, args.output)
    print(f"热力图已生成: {args.output}")
```

---

## 5. 实现细节深入

### 5.1 鼠标悬停提示 (Tooltip) 的 SVG 表现
当鼠标移动到某个格子上时，浏览器怎么知道要弹出一个包含“2025-06-14 30分钟”的小气泡提示？
其实，这是利用了 SVG 的 `desc` (Description) 子节点的特性。
在 [drawer.py 的 _gen_day_box](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L76-L101) 中：

```python
# 源码位置：weread_poster/drawer.py
def _gen_day_box(self, dr, rect_x, rect_y, date_title, day_tracks, ...):
    ...
    if day_tracks:
        color = self.make_color(self.poster.length_range_by_date, day_tracks)
        # 将分钟数格式化为易读的“X小时Y分钟”
        date_title = f"{date_title} {format_duration_mins(day_tracks)}"
        
    rect = dr.rect((rect_x, rect_y), DOM_BOX_TUPLE, fill=color)
    ...
    # set_desc 会在 <rect> 标签下生成一个 <desc> 和 <title> 标签
    rect.set_desc(title=date_title)
    yield rect
```
浏览器对包含 `<title>` 子节点的矢量 `<rect>`，在鼠标 Hover 悬停时会自动触发浮动提示框，展现 `title` 里面的文字内容。这样既保证了纯静态的 SVG 交互体验，又不需要运行任何 JS 代码。

---

## 6. 异常与边界情况处理

### 6.1 年份参数格式校验与正则防御
如果用户输入了非法的年份选项（例如 `--year 202b` 或是 `--year 2025-202`），在没有预先正则检查的情况下，`int(year)` 会触发程序异常崩溃。
我们在 [utils.py 的 parse_years](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L26-L43) 中引入了精准的正则表达式过滤：
```python
# 匹配单个数字
m = re.match(r"^\d+$", s)
# 匹配范围数字
m = re.match(r"^(\d+)-(\d+)$", s)
```
如果不匹配任何一项，则主动抛出 `ValueError(f"无法解析年份: {s}")` 异常。然后在 [cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L157-L158) 中捕获此异常，退出并给予用户明确的纠错指引。

### 6.2 导出 JSON 文件覆写保护
当使用 `--json data.json` 保存原始数据时，我们需要保护用户已有的文件，并在转换时进行安全性重写。
由于内部数据为了计算渐变使用了分钟制（浮点数），而在导出 JSON 供用户做外部可视化时，以“秒”输出更直观、数据也更精准。我们在 [cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L222-L227) 中进行了逆向秒级转换：
```python
tracks_seconds = {k: round(v * 60, 2) for k, v in tracks.items()}
with open(args.json_output, "w", encoding="utf-8") as f:
    json.dump(tracks_seconds, f, ensure_ascii=False, indent=2)
```
使用 `encoding="utf-8"` 是为了防止在部分中文 Windows 系统中默认用 GBK 编码导致写盘字符乱码。

---

## 7. 本章知识总结

| 知识点 | 概念导论中的解释 | 源码中的位置 | 关键行为 |
| :--- | :--- | :--- | :--- |
| **关键帧分割** | 将动画总长等比例划分为小数百分比片 | [utils.py:make_key_times](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py#L46) | 利用 itercount 计算均匀的 0.0-1.0 列表 |
| **Opacity 渐现** | 某帧前为 0，某帧后保持为 1 的 values 组 | [drawer.py:_add_animation](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L60) | 拼接 `0;0;1` 串赋给 `svgwrite.animate.Animate` |
| **悬停 Tooltip** | 网页浏览器自动浮现矢量图 title 内容 | [drawer.py:_gen_day_box](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L100) | 对 rect 执行 `rect.set_desc(title=text)` |
| **命令行总控** | 使用 argparse 暴露开关控制各项画画属性 | [cli.py:build_parser](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L22) | 定义 `--theme`, `--with-animation` 等接口 |

### 知识地图

```
第 03 章 知识地图：

动画嵌入与命令行流程调度
  ├── 交互效果
  │    ├── 原生悬停提示 ➔ rect.set_desc(title=...) 产生浮现 tooltip
  │    └── 时间淡入动效
  │         ├── 时间均匀切片 ➔ make_key_times() 返回 [0.0, ..., 1.0]
  │         └── opacity 节点挂载 ➔ 前 N 帧透明，第 N 帧瞬时显现变 1
  └── 主程序调度 (cli.py)
       ├── 参数解析器 build_parser()
       ├── 主题应用 apply_theme() ➔ 参数覆写
       └── 主干逻辑串联 ➔ 鉴权 ➔ 加载数据 ➔ JSON写盘 ➔ SVG绘制
```

- **核心要点 1**：纯 SVG 的原生 `<animate>` 特性可以避免依赖 JS，实现完全静态的网页 GIF 式淡入动效。
- **核心要点 2**：通过正则防护 `parse_years` 和指定 UTF-8 编码，可极大增强命令行工具的跨平台稳定性。
- **核心要点 3**：`cli.py` 将界面属性和底色常量从绘制代码中解耦，提供了干净的接口漏斗。

---

## 8. 思考题

### 题目 1：在 `_add_animation` 方法中，为什么 values 字符串拼装时，前 `animate_index` 个元素全为 `"0"`，后续全为 `"1"`？如果把后面全写成 `"1"` 改为“从 0 渐变到 1”会发生什么？

<details>
<summary>参考解答</summary>
当前的 values 设计：前 `animate_index` 帧对应格子尚未“轮到”显现，故保持全透明；当进度条到达 `animate_index` 时，格子立刻出现并一直亮着。这能保证整齐利落的“时间推进”扫描淡入。
如果把后面改写成让每一格都有自己的 `0 -> 1` 平滑渐变过渡，会因为每个格子淡入时都在变亮，导致画面的总动画时间极长或呈现复杂的闪烁，且需要在 `values` 中插入多帧插值比例，这会使得 SVG 节点的体积由于复杂字符串而急剧增大数十倍，降低渲染性能。
</details>

### 题目 2：如果在 Windows 控制台中直接运行 `python -m weread_poster --me "我的读书海报"`，当控制台默认编码为 GBK 时，可能会发生什么潜在故障？如何预防？

<details>
<summary>参考解答</summary>
如果操作系统控制台的编码是 GBK，在接收传入的命令行字符串 `"我的读书海报"` 时，可能会发生中文字符集解码异常，导致海报上最终生成的标题显示为一串乱码。
为了预防此类问题，可以在 `cli.py` 头部通过 `sys.stdout.reconfigure(encoding='utf-8')` 重新指定标准输出流字符集，或者提醒 Windows 用户在运行脚本前，在 PowerShell 中执行 `$env:PYTHONUTF8 = 1` 强制开启 Python 的 UTF-8 运行模式。
</details>

### 题目 3：当把 `--animation-time` 设为 `60` 秒，而当年有阅读记录的天数仅有 5 天时，热力图的动画效果在视觉上会有什么现象？

<details>
<summary>参考解答</summary>
当有阅读天数 $N=5$，时间切片仅被分成 5 段。由于总动画时长为 60 秒，每一段间隔时间高达 $60 / 5 = 12$ 秒。
在视觉上，用户会看到海报在前 12 秒内完全没有任何变化，随后在第 12 秒瞬间出现一格，再过 12 秒又出现一格。画面变化极其迟钝缓慢，缺乏动画的流畅与生机。这说明动画总时长应根据天数的多少合理动态设置。
</details>

### 题目 4：[动手实践] 尝试在 [cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py) 的 `build_parser` 中新增一个命令行参数 `--font`，允许用户自定义热力图中的文字字体（默认使用 "Arial"）。请写出添加该参数的代码片段，并说明如何将此参数传递给 `Drawer` 并在 SVG 绘图时生效。

<details>
<summary>参考解答</summary>
1. 在 [cli.py 的 build_parser](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L41-L125) 中添加参数定义：
```python
parser.add_argument(
    "--font",
    type=str,
    default="Arial",
    help="海报文本字体名称（默认: Arial）"
)
```
2. 在 [cli.py 的 main](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L183) 参数覆盖部分，将该属性写入 Poster 实例：
```python
p.font_family = args.font # 新增该配置项
```
3. 在 [drawer.py](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L29-L31) 中，读取此字体配置来构建文本样式：
```python
self.year_style = f"font-size:{self.year_size}px; font-family:{p.font_family};"
self.year_length_style = f"font-size:{110 * 3.0 / 80.0}px; font-family:{p.font_family};"
self.month_names_style = f"font-size:2.5px; font-family:{p.font_family}"
```
</details>
