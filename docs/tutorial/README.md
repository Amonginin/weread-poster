# 微信读书阅读时长热力图生成工具技术教程

> 面向计算机本科低年级学生，本教程从零讲解如何打通外部网关拉取数据，并使用数学插值算法结合 SVG 矢量标准，绘制出一份高颜值的动态阅读热力图海报。
> 
> **前置假设**：读者仅需掌握 Python 基础语法（变量、函数、基础控制流与 requests 库），其余领域知识（如 SVG 绘图标准、HSL 色彩空间、动画延迟算法）均会从零开始教学。

---

## 1. 章节地图

以下是为您推荐的学习路径地图。您可以按照章节顺序依次学习，也可以根据需求快速跳转到特定部分：

```
                    ┌─────────────────────────┐
                    │  必备基础：Python 语法    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   01 鉴权与数据流        │
                    │   (auth.py / loader.py) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   02 网格与着色算法      │
                    │  (poster.py / drawer.py)│
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   03 动画与主入口控制    │
                    │   (utils.py / cli.py)   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   04 自动运维与 CI/CD    │
                    │   (GitHub Actions)      │
                    └─────────────────────────┘
```

---

## 2. 教程目录

| 章节 | 标题 | 核心内容 | 层次 |
| :--- | :--- | :--- | :--- |
| **01** | [第 01 章：数据源头 — 微信读书 Agent 鉴权与数据获取](file:///d:/coding/personalProj/weread-poster/docs/tutorial/01-auth-and-loader.md) | Agent API 鉴权、`/readdata/detail` 接口、秒与分钟换算、特值计算 | 概念 + 源码 |
| **02** | [第 02 章：视觉绘制 — 54×7 年历网格与 HSL 颜色渐变引擎](file:///d:/coding/personalProj/weread-poster/docs/tutorial/02-drawer-and-interpolation.md) | 54×7 矩阵星期偏移、HSL 插值公式、颜色分级、Poster 与 Drawer 交互 | 概念 + 源码 |
| **03** | [第 03 章：动态交互 — SVG 淡入动画、悬停提示与主流程控制](file:///d:/coding/personalProj/weread-poster/docs/tutorial/03-animation-and-cli.md) | SVG `Animate` 不透明度淡入、悬停提示框注入、CLI 调度、统计摘要 | 概念 + 源码 |
| **04** | [第 04 章：自动运维 — 结合 GitHub Actions 实现每日定时渲染与发布](file:///d:/coding/personalProj/weread-poster/docs/tutorial/04-github-actions-deployment.md) | 定时 Cron、Secrets 密钥库配置、Write 写回授权、skip ci 死循环避免 | 概念 + 源码 |

---

## 3. 阅读建议

* **如果您是零基础的新手**：建议从 [第 01 章](file:///d:/coding/personalProj/weread-poster/docs/tutorial/01-auth-and-loader.md) 开始按部就班学习。在阅读时，先只阅读第一层“概念导论”，跳过“源码解析”，重点建立对 API 网关、坐标格点、HSL 的心智模型。
* **如果您已有 Python 基础但未写过绘图工具**：可以直接阅读各章的“第一层”，随后重点攻读 [第 02 章](file:///d:/coding/personalProj/weread-poster/docs/tutorial/02-drawer-and-interpolation.md) 和 [第 03 章](file:///d:/coding/personalProj/weread-poster/docs/tutorial/03-animation-and-cli.md) 的第二层“源码解析”，学习如何结合 `svgwrite` 与色彩数学公式输出无损图。
* **如果您想让项目每天在云端全自动定时执行**：请直接阅读 [第 04 章](file:///d:/coding/personalProj/weread-poster/docs/tutorial/04-github-actions-deployment.md) 获取详尽的 GitHub Actions 部署指南。
* **如果您是经验丰富的开发者，想快速改造本项目**：
  - 若要**新增配色主题**，请直接查阅 [第 02 章：4.3.2 节 theme 配色逻辑](file:///d:/coding/personalProj/weread-poster/docs/tutorial/02-drawer-and-interpolation.md)。
  - 若要**改动布局或间距**，请直接查阅 [第 02 章：5.1 节 星期网格的绘制机制](file:///d:/coding/personalProj/weread-poster/docs/tutorial/02-drawer-and-interpolation.md)。
  - 若要**修改动画效果或时间**，请直接查阅 [第 03 章：5.1 节 SVG 淡入动画的机制](file:///d:/coding/personalProj/weread-poster/docs/tutorial/03-animation-and-cli.md)。

---

## 4. 阅读前准备

### 必备知识
* Python 基础语法（类与对象、列表与字典推导式、异常捕获）。
* 基础的命令行使用技能（用于设定环境变量与运行 python 脚本）。

### 推荐知识
* 了解 HSL 与 RGB 颜色表示法。
* 熟悉 SVG 矢量图的基本标记（如 `<rect>`, `<text>` 元素）。

### 工具检查
* **Python 3.8+** 环境（确保在命令行中可以运行 `python --version`）。
* 安装项目依赖包：
  ```bash
  pip install -r requirements.txt
  ```
* 微信读书 API Key 准备：通过微信读书 Agent 获得形如 `wrk-xxxxxxxx` 的 API Key，并设置为环境变量 `WEREAD_API_KEY`。

---

## 5. 项目源码文件速查

在阅读教程和对照代码时，您可以随时在此表中查阅每个源码文件的职责和对应的核心类：

| 源码路径 | 核心类/函数 | 职责 |
| :--- | :--- | :--- |
| [weread_poster/__init__.py](file:///d:/coding/personalProj/weread-poster/weread_poster/__init__.py) | - | 模块定义文件，声明包版本 |
| [weread_poster/__main__.py](file:///d:/coding/personalProj/weread-poster/weread_poster/__main__.py) | `__main__` | `python -m weread_poster` 执行入口 |
| [weread_poster/auth.py](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py) | [WeReadAuth](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L14) | 与 API 网关的鉴权中转以及 HTTP 异常兜底拦截 |
| [weread_poster/loader.py](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py) | [WereadLoader](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L14) | 循环按月拉取网关数据，将其过滤并转换为分钟级日记录 |
| [weread_poster/config.py](file:///d:/coding/personalProj/weread-poster/weread_poster/config.py) | `THEMES` | 各种静态配置项、颜色等级主题和阅读阈值 |
| [weread_poster/poster.py](file:///d:/coding/personalProj/weread-poster/weread_poster/poster.py) | [Poster](file:///d:/coding/personalProj/weread-poster/weread_poster/poster.py#L13) | 管理绘图数据和画板的宽高配置 |
| [weread_poster/drawer.py](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py) | [Drawer](file:///d:/coding/personalProj/weread-poster/weread_poster/drawer.py#L21) | 完成具体的 SVG 画布年历绘制、格子渲染以及动画附加 |
| [weread_poster/structures.py](file:///d:/coding/personalProj/weread-poster/weread_poster/structures.py) | `XY`, `ValueRange` | 简易的二元坐标与值区间范围数据结构 |
| [weread_poster/utils.py](file:///d:/coding/personalProj/weread-poster/weread_poster/utils.py) | `interpolate_color` | 颜色线性插值、正则解析年份范围与动画帧切片生成 |
| [weread_poster/cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py) | `main` | 命令行参数解析、业务流程组装、保存数据并触发渲染 |

---

## 6. 遇到问题怎么办

* **Q: 提示 "Authentication failed: Authentication required" 错误？**
  * **A**: 请确保您在终端中正确设置了 `WEREAD_API_KEY` 环境变量。可以通过在 PowerShell 中运行 `echo $env:WEREAD_API_KEY` 或在 Bash 中运行 `echo $WEREAD_API_KEY` 检查是否生效。
* **Q: 生成的 SVG 图像部分边缘被截断了？**
  * **A**: 这通常是因为年份过多或标题过长，导致需要的画布大小超出了默认宽高。项目在 [cli.py](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L212-L214) 中会根据年份数量自动推导高度，您可以直接调整该处的高度累加倍数。
* **Q: 概念看不懂，被大段代码弄迷糊了？**
  * **A**: 别担心！每章都是“双层结构”的。您可以先忽略每章“第二层：源码解析”的全部实现细节，仅通读“第一层：概念导论”，等有了宏观感受后再行对照。
