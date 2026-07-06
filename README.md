# weread-poster

微信读书阅读时长热力图生成工具。

**数据获取**：通过微信读书 Agent API Gateway（官方 Skill 接口）获取每日阅读时长  
**图片生成**：使用 GitHubPoster 风格的 SVG 渲染引擎，支持颜色渐变、动画、多主题

## 效果

生成 GitHub 贡献图风格的热力图：
- 深色背景 + 渐变色格子
- 每格代表一天，颜色深浅反映阅读时长
- 支持动画效果（格子逐个淡入）
- 年度总时长标注
- 鼠标悬停显示具体日期和时长

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 API Key

微信读书 API Key 格式为 `wrk-xxxxxxxx`，通过微信读书 Skill 获取。

### 3. 设置环境变量

```bash
# Linux / macOS
export WEREAD_API_KEY=wrk-xxxxxxxx

# Windows PowerShell
$env:WEREAD_API_KEY = "wrk-xxxxxxxx"
```

### 4. 生成热力图

```bash
# 默认今年
python -m weread_poster

# 指定年份范围
python -m weread_poster --year 2023-2025

# 自定义主题和标题
python -m weread_poster --theme weread --me "我的阅读"

# 带动画效果
python -m weread_poster --year 2025 --with-animation

# 导出原始数据
python -m weread_poster --year 2025 --json data.json --stats
```

## CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--year` | 今年 | 年份范围，如 `2025` 或 `2023-2025` |
| `--me` | 微信阅读热力图 | 海报标题 |
| `--theme` | weread | 配色主题 |
| `--background-color` | #222222 | 背景色 |
| `--track-color` | 主题色 | 轨道色 |
| `--text-color` | #FFFFFF | 文字色 |
| `--special-color1` | yellow | 特殊色1 |
| `--special-color2` | red | 特殊色2 |
| `--with-animation` | false | 添加动画效果 |
| `--animation-time` | 10 | 动画时长（秒） |
| `--output` | weread_heatmap.svg | SVG 输出路径 |
| `--json` | 无 | 导出原始数据 JSON |
| `--stats` | false | 打印统计摘要 |

## 可用主题

| 主题 | 说明 |
|------|------|
| `weread` | 微信读书蓝（默认） |
| `github` | GitHub 绿 |
| `warm` | 暖阳橙 |
| `purple` | 梦幻紫 |
| `ocean` | 海洋青 |
| `rose` | 玫瑰粉 |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `WEREAD_API_KEY` | 是 | API Key，格式 `wrk-xxxxxxxx` |
| `THEME_COLOR` | 否 | 配色主题（CLI 参数优先） |
| `OUTPUT_SVG` | 否 | SVG 输出路径（CLI 参数优先） |

## 项目结构

```
weread-poster/
├── weread_poster/
│   ├── __init__.py
│   ├── __main__.py        # python -m weread_poster 入口
│   ├── cli.py             # CLI 参数解析和主流程
│   ├── auth.py            # 微信读书 API 认证（Agent API Gateway）
│   ├── loader.py          # 数据加载器（/readdata/detail 接口）
│   ├── poster.py          # Poster 数据管理
│   ├── drawer.py          # SVG 绘图器（GitHub 风格）
│   ├── structures.py      # 数据结构（ValueRange, XY）
│   ├── config.py          # 配置常量和主题
│   └── utils.py           # 工具函数（颜色插值、动画等）
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 数据来源

通过微信读书 Agent API Gateway 调用 `/readdata/detail` 接口：

- 逐月调用 `mode=monthly`，`readTimes` 按天分桶
- 数据单位：秒 → 转为分钟存储 → 渲染时转为小时显示
- 接口文档：[weread-skills/readdata.md](weread-skills/readdata.md)

## 技术架构

```
WeReadAuth (认证)
    ↓
WereadLoader (数据获取) → /readdata/detail API
    ↓
Poster (数据管理) → tracks, years, colors
    ↓
Drawer (SVG 渲染) → GitHub 风格热力图
```

**数据获取**来自 [Weread_ReadTime_Heatmap](https://github.com/) 项目  
**图片生成**来自 [GitHubPoster](https://github.com/yihong0618/GitHubPoster) 项目

## 项目技术教程

为了帮助你更深地理解项目源码、进行二次开发（如新增自定义配色主题或调整网格间距与布局），我们提供了详细的双层结构分章技术教程，请查阅：
👉 **[项目技术教程 (TUTORIAL)](docs/tutorial/README.md)**

## GitHub Actions 自动定时运行

你可以配置项目在 GitHub Actions 中每天自动运行，定时更新你的玫瑰粉（或其他主题）动态热力图：

1. **配置 Secret 密钥**：在 GitHub 仓库的 **Settings ➔ Secrets and variables ➔ Actions** 中，点击 **New repository secret**，添加名为 `WEREAD_API_KEY` 的密钥，内容填入你的微信读书 API Key。
2. **开启读写授权**：导航到 **Settings ➔ Actions ➔ General**，滚动至最下方的 **Workflow permissions**，将权限选项修改为 **Read and write permissions** 并保存（这允许机器人定时运行后自动提交生成的 SVG 回仓库）。
3. **配置文件位置**：工作流配置在 [.github/workflows/weread_poster.yml](.github/workflows/weread_poster.yml) 中，默认每天北京时间 05:00 和 17:00 自动执行一次。
4. **深入了解 Actions**：更详细的定时原理、防死循环构建（[skip ci]）等高级细节请阅读教程：[第 04 章：自动运维 — 结合 GitHub Actions 实现每日定时渲染与发布](docs/tutorial/04-github-actions-deployment.md)。

## 自动化测试

项目内配有完整的本地 Mock 单元测试套件。你可以通过以下命令在本地执行全量功能验证：
```bash
python -m unittest tests/test_weread_poster.py
```
