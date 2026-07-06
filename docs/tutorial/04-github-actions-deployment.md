# 第 04 章：自动运维 — 结合 GitHub Actions 实现每日定时渲染与发布

> 本章导读
>
> 本章将进入热力图海报的“配置与部署”环节。你将学习如何利用 GitHub 提供的持续集成与部署（CI/CD）工具——GitHub Actions，配置一个每日自动拉取微信读书数据、渲染最新玫瑰粉动态热力图并无感提交回仓库的工作流。
> 
> **前置知识**：已掌握前三章的运行参数（如 `--theme`、`--with-animation`），拥有一个 GitHub 账号。
> **本章目标**：
> 1. 理解 GitHub Actions 工作流 (Workflow) 的触发机制（定时 Cron 与手动触发）。
> 2. 掌握如何在 GitHub 仓库中安全地配置密钥 (Secrets) 以存储 API Key。
> 3. 掌握如何授权 GitHub Actions 机器人在执行完任务后将代码写回仓库。
> 4. 学习分析与调试 GitHub Actions 运行日志。

---

# 第一层：概念导论

> 本层目标：用 200 行左右讲清“定时运维的必要性与安全配置核心思路”。
> 读完本层，你能够理清云端执行器的生命周期，并掌握如何防止密钥泄露的安全红线。

## 1. 为什么需要自动运维（背景与动机）

### 1.1 问题引出
在我们完成了本地热力图生成后，面临着另一个尴尬的问题：
微信读书的数据是每天都在动态累加更新的。如果我们想要保持自己 GitHub 主页或个人网页上的热力图海报永远显示最新数据，难道我们每天清晨起床后，都要手动在本地终端敲一遍 `python -m weread_poster`，然后手动执行 `git commit` 与 `git push` 上传吗？

这显然是反自动化的。我们需要一种方式，让云端服务器能够：
1. **定时醒来**：在每天我们睡觉或阅读最少的时间段（如凌晨 5 点），自动醒来帮我们跑代码。
2. **安全读取密码**：在公开的开源仓库里，既要能让代码读取到我们的 `WEREAD_API_KEY`，又不能把这个 Key 直接写在代码中（否则任何人都可以窃取我们的 Key）。
3. **自我提交**：生成出新的 `weread_heatmap.svg` 后，能够自己提交并更新到 GitHub 仓库。

### 1.2 什么是 GitHub Actions
GitHub Actions 是 GitHub 官方提供的自动化构建与部署工具。它允许我们在仓库中放一个名为 `.yml` 的配置文件。GitHub 会在特定事件发生时（如定时 Cron 触发，或者我们手动点击触发按钮），在云端临时分配一台虚拟机，拉取我们的代码，执行我们指定的步骤，最后销毁。

### 1.3 方案对比

| 部署方案 | 优点 | 缺点 | 项目中的选择 |
| :--- | :--- | :--- | :--- |
| **本地定时任务 (Windows 计划任务/Linux Cron)** | 简单，完全受自己控制 | 本地电脑必须 24 小时开机，且需要配置外网推送 | ❌ 不采用 |
| **租用云服务器 (ECS)** | 稳定，随时可调 | 需要自费购买云服务器，需要登录 Linux 维护环境 | ❌ 不采用 |
| **GitHub Actions 工作流** | 完全免费、无需自己买服务器、全自动化、配置极简 | 定时 Cron 触发可能会有一小段时间的排队延迟 | ✅ 采用此方案 |

> **项目实例**：项目中的 [.github/workflows/weread_poster.yml](file:///d:/coding/personalProj/weread-poster/.github/workflows/weread_poster.yml) 完整定义了定时执行所需的执行步骤。

---

## 2. 自动运维安全与授权设计（架构与核心概念）

### 2.1 密钥保管箱 (GitHub Secrets) 机制
绝对不能把 API Key 写在配置文件里！
GitHub 提供了 `Repository Secrets`（仓库加密密钥）机制。我们可以将 API Key 存放在仓库后台的保密箱中，在 YAML 文件中通过 `${{ secrets.WEREAD_API_KEY }}` 动态调用：

```
                              ┌─────────────────────────────┐
                              │    GitHub 仓库设置 (Web)    │
                              └──────────────┬──────────────┘
                                             │ (存入 WEREAD_API_KEY 密文)
                                             ▼
                              ┌─────────────────────────────┐
                              │    加密保密箱 Secrets       │
                              └──────────────┬──────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
       (外部不可见，严防泄露)                                (只在虚拟机运行时解密)
                       │                                           │
                       ▼                                           ▼
         public codebase (公开源码)                     ┌─────────────────────────────┐
        (❌ 严禁明文写入 wrk-xxx)                       │  GitHub Actions 运行期变量   │
                                                       └─────────────────────────────┘
```

### 2.2 自动写回 (Commit & Push) 的权限机制
新版的 GitHub Actions 为了仓库安全，默认对虚拟机内的临时 `GITHUB_TOKEN` 仅赋予“只读 (Read)”权限。如果我们的脚本生成了新的 SVG 文件并尝试 `git push`，会遭遇权限拒绝（Permission Denied）。
因此，我们必须在 YAML 文件中显式地声明对工作流读写内容的授权（`permissions: contents: write`）。

---

## 3. 快速上手（配置步骤）

要把这个项目在你的 GitHub 上跑起来，你需要依次完成以下三步：

1. **新建 Secret 密钥**：
   - 登录你的 GitHub 仓库，点击顶部的 **Settings** ➔ 导航至 **Secrets and variables** ➔ 选择 **Actions**。
   - 点击 **New repository secret**，在 Name 中填入 `WEREAD_API_KEY`，在 Secret 中贴入你的微信读书 API Key（如 `wrk-xxxxxxxx`），保存。
2. **开启写回授权**：
   - 仍在 **Settings** ➔ 找到 **Actions** 下的 **General**。
   - 滚动到最下方的 **Workflow permissions**，将默认的 *Read repository contents and packages permissions* 修改为 **Read and write permissions**，保存。
3. **手动触发运行**：
   - 点击仓库上方的 **Actions** 菜单 ➔ 在左侧选择 **Generate WeRead Heatmap**。
   - 点击右侧的 **Run workflow** 下拉按钮，点击绿色的 **Run workflow** 按钮启动测试。

---

# 第二层：源码解析

> 本层目标：深入理解自动化部署脚本的各项声明细节与语法机制。
> 读完本层，你能独立排查 Actions 报错，并能扩写脚本让其在生成海报后向你发送微信提醒。

## 4. 自动化脚本逐段解析

### 4.1 触发器配置 (Triggers)

* **配置文件路径**：[.github/workflows/weread_poster.yml](file:///d:/coding/personalProj/weread-poster/.github/workflows/weread_poster.yml)
```yaml
on:
  push:
    branches:
      - main
  schedule:
    - cron: '0 9 * * *'
    - cron: '0 21 * * *'
  workflow_dispatch:
```
* **知识点解析**：
  * `cron` 是 UNIX 定时器表达式，其格式为 `'分 时 天 月 星期'`。
  * **注意**：GitHub Actions 的时区统一为 **UTC (世界标准时)**，而中国时间 (北京时间) 是 **UTC+8**。
  * 当我们要在中国时间 05:00 运行时，应当减去 8 小时，即 UTC 21:00（表示为 `0 21 * * *`）。
  * `workflow_dispatch` 代表启用手动运行。开启此项后，网页端才会出现“Run workflow”的按钮。

---

### 4.2 运行环境与写回权限定义

```yaml
jobs:
  generate:
    runs-on: ubuntu-latest
    permissions:
      contents: write # 必须显式声明写权限，否则无法执行 git push
```
* **知识点解析**：
  * `runs-on: ubuntu-latest` 指定 GitHub 启动一台最新的开源 Ubuntu Linux 虚拟机来跑我们的任务。
  * `permissions.contents: write` 会将虚拟机的临时访问凭证权限修改为“读写写回”，允许虚拟机向当前仓库的分支推送代码变更。

---

### 4.3 执行步骤逐一解析

```yaml
    steps:
      # 1. 检出仓库代码
      - name: Checkout Repository
        uses: actions/checkout@v4

      # 2. 配置 Python 环境与依赖缓存
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip' # 自动根据 requirements.txt 的变更来缓存下载好的依赖，加速下次执行

      # 3. 安装依赖包
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      # 4. 读取 Secret 运行核心脚本
      - name: Generate Heatmap
        env:
          WEREAD_API_KEY: ${{ secrets.WEREAD_API_KEY }}
        run: |
          # 执行玫瑰粉主题且带动画的生成
          python -m weread_poster --theme rose --with-animation --output weread_heatmap.svg

      # 5. 执行免冲突写回
      - name: Commit and Push Changes
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add weread_heatmap.svg
          # git commit -m "..." 如果文件没有产生任何修改，会以错误码 1 退出。
          # 加上 || exit 0，表示没有修改时正常退出工作流，不报红色错误
          git commit -m "chore: update WeChat Reading heatmap [skip ci]" || exit 0
          git push
```

---

## 5. 实现细节深入

### 5.1 防止工作流陷入“无限循环”的技巧
在第 5 步中，我们提交信息使用了 `chore: update WeChat Reading heatmap [skip ci]`。
* **为什么需要 `[skip ci]`**：
  默认情况下，每当有人（包括机器人）向 GitHub 仓库推送（Push）代码时，GitHub 都会检测并自动触发该仓库下的工作流。
  如果我们的 Action 机器人修改并 Push 了 `weread_heatmap.svg`，而我们没有加上 `[skip ci]`，那么 GitHub Actions 就会检测到有新 Push 进而**再次启动**这个生成任务，如此往复，形成死循环，直到消耗尽你当月所有的免费额度。
  加上 `[skip ci]` 后，GitHub Actions 在检测到该提交时，会主动忽略，从而优雅地规避了无限递归的死胡同。

---

## 6. 异常与边界情况处理

### 6.1 GitHub 虚拟机时间漂移与 Cron 延迟
GitHub Actions 定时 Cron 触发的底层机制是由共享队列调度的。当在某个整点（如 UTC 0:00）全球有数百万个定时任务同时排队时，你的任务可能会延迟 15 至 45 分钟启动。
* **安全设计**：这属于正常现象。因为我们的脚本在 [loader.py 的 get_api_data](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L36) 中，是按整月拉取数据的，且在 `utils.py` 中有去除空年份的过滤机制。即使任务迟到了 1 小时启动，读到的依然是昨天的最终归档数据，不会对海报数据完整性产生任何影响。

### 6.2 密钥泄露的系统防护
如果我们在代码中不小心用 `print(f"密钥是: {os.getenv('WEREAD_API_KEY')}")` 打印了密钥，该怎么办？
GitHub Actions 具备内部敏感信息脱敏功能。任何通过 `${{ secrets.WEREAD_API_KEY }}` 传入的环境变量，在日志输出时一旦出现其密文字符，都会被自动替换为星号 `***` 输出，在系统层保护了敏感凭证的安全。

---

## 7. 本章知识总结

| 知识点 | 概念导论中的解释 | 源码中的位置 | 关键行为 |
| :--- | :--- | :--- | :--- |
| **世界标准时换算** | 中国时间减 8 小时即为 UTC 触发时间 | [.github/workflows/weread_poster.yml](file:///d:/coding/personalProj/weread-poster/.github/workflows/weread_poster.yml#L7) | `cron: '0 9 * * *'` 等对应北京 17 点与 5 点 |
| **写回权限** | 虚拟机临时 Token 必须具有 Write 权限 | [.github/workflows/weread_poster.yml](file:///d:/coding/personalProj/weread-poster/.github/workflows/weread_poster.yml#L12) | `permissions: contents: write` |
| **流水线缓存** | 利用 setup-python 缓存已下载的库 | [.github/workflows/weread_poster.yml](file:///d:/coding/personalProj/weread-poster/.github/workflows/weread_poster.yml#L22) | `cache: 'pip'` 加速后继运行 |
| **CI 循环拦截** | 使用提交修饰符跳过后续触发 | [.github/workflows/weread_poster.yml](file:///d:/coding/personalProj/weread-poster/.github/workflows/weread_poster.yml#L44) | `[skip ci]` 阻断持续触发 |

### 知识地图

```
第 04 章 知识地图：

GitHub Actions 自动运维部署
  ├── 触发源设置
  │    ├── 定时执行 ➔ cron 语法 (注意 UTC 时区偏置减 8 小时)
  │    └── 手动执行 ➔ workflow_dispatch
  ├── 安全与加密
  │    ├── API Key 严禁写入代码 ➔ 存入 GitHub Repository Secrets
  │    └── 日志流脱敏 ➔ 系统敏感字符自动转化为 ***
  └── 虚拟机生命周期 (Ubuntu)
       ├── 代码检出 ➔ Setup Python (开启 pip 缓存)
       ├── 执行 rose 动态渲染命令 ➔ weread_heatmap.svg
       └── 机器人免循环写回 ➔ commit 包含 [skip ci] ➔ 推送回分支
```

- **核心要点 1**：GitHub 运行在 UTC 时区，配置 Cron 时记得做“减 8 小时”的偏移。
- **核心要点 2**：写回权限默认是只读的，必须显式在 YAML 或后台设置中开启 Write 授权。
- **核心要点 3**：`[skip ci]` 是防止机器人推送代码自己无限循环触发构建的精妙防火墙。

---

## 8. 思考题

### 题目 1：在配置定时 Cron `'0 9 * * *'` 时，为什么不推荐将其写为零整点，如 `'0 0 * * *'`？

<details>
<summary>参考解答</summary>
因为全球有非常多的开发者会将自动化工作流默认设置在整点触发（尤其是 UTC 00:00，即中国时间上午 8 点）。
这会导致 GitHub Actions 的资源调度队列在整点出现极高的拥塞。如果将其修改为带有一些偏移的非热门时间段（如 UTC 9:00 或 21:00，或者其他奇数分钟，如 `'17 5 * * *'`），可以极大避开排队高峰，使你的工作流能够在几秒内被调度并快速执行完毕。
</details>

### 题目 2：如果在执行 `Commit and Push Changes` 步骤时，`git commit` 报错提示 `Author identity unknown`，这是因为漏掉了哪一步操作？

<details>
<summary>参考解答</summary>
这是因为在尝试提交代码前，没有为虚拟机内的临时 git 环境配置全局的用户邮箱和用户名。
Git 在提交时强制要求必须标记提交者的身份。必须通过在 `git commit` 前执行以下两行命令来给 git 一个虚拟的身份：
```bash
git config --local user.email "github-actions[bot]@users.noreply.github.com"
git config --local user.name "github-actions[bot]"
```
</details>

### 题目 3：当把 `--output` 路径设为 `docs/assets/weread_heatmap.svg`，而虚拟机中 `docs/assets/` 这个子目录并不存在，程序运行时会发生什么？工作流如何优雅解决？

<details>
<summary>参考解答</summary>
我们在 [cli.py 的第 217-219 行](file:///d:/coding/personalProj/weread-poster/weread_poster/cli.py#L217-L219) 中已经编写了防御性逻辑：
```python
out_dir = os.path.dirname(os.path.abspath(args.output))
if out_dir and not os.path.exists(out_dir):
    os.makedirs(out_dir, exist_ok=True)
```
Python 在检测到输出文件夹不存在时，会自动创建对应的父级文件夹。因此工作流不会报错崩溃，而是会在虚拟机中自动创建该目录，随后正常将生成的 svg 写入其中。
</details>

### 题目 4：[动手实践] 设想你希望在每天生成热力图的同时，也向你的微信推送一条“今日热力图已成功更新”的通知。你可以在工作流中引入 `chansly/wechat-notification` 或类似的第三方 Action。请在下方写出应当在工作流的最尾部追加的 YAML 步骤格式，并使用 Secret 保护你的微信 Token。

<details>
<summary>参考解答</summary>
在 YAML 的 `steps` 列表最末尾追加以下步骤：
```yaml
      - name: Send WeChat Notification
        # 仅在前面的生成和推送全部成功时才发送通知
        if: success()
        uses: chansly/wechat-notification@v1
        with:
          token: ${{ secrets.WECHAT_PUSH_TOKEN }}
          title: "微信读书热力图更新成功"
          message: "玫瑰粉色动态热力图已自动渲染并提交回仓库。"
```
</details>
