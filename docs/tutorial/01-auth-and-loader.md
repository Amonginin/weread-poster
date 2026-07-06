# 第 01 章：数据源头 — 微信读书 Agent 鉴权与数据获取

> 本章导读
>
> 本章将带领大家探索 [weread-poster](file:///d:/coding/personalProj/weread-poster/) 项目如何打通数据源头。你将学习微信读书 Agent API Gateway 的 Bearer Token 认证机制，以及如何设计一个多月份轮询加载器，将网关回传的原始秒级数据转换并过滤为分钟级的按日阅读字典。
> 
> **前置知识**：已掌握 Python requests 库发送 HTTP POST 请求的基础，了解环境变量的作用。
> **本章目标**：
> 1. 理解微信读书 API Gateway 的 Bearer 认证机制。
> 2. 掌握多月份自动轮询拉取与未来月份过滤逻辑。
> 3. 掌握如何把 Unix 时间戳（秒）转换为以日期为 Key、分钟为 Value 的数据结构。
> 4. 学习如何用分位数方法动态计算高亮阈值。

---

# 第一层：概念导论

> 本层目标：用 200~300 行介绍“API 鉴权与数据流设计思路”。
> 读完本层，你能够在大脑中建立本工具与外部网关请求通信的完整心智模型，掌握秒转分钟和阈值分类的宏观意图。

## 1. 为什么需要 Agent 网关（背景与动机）

### 1.1 问题引出
如果我们要统计自己的阅读时长，怎么才能安全地拿到微信读书官方的数据？
最朴素的想法是直接模拟浏览器登录微信读书网页端，然后通过写爬虫去抓取接口。但很快我们就会发现以下问题：
1. **扫码登录态易失效**：网页端的 Cookie 只有几天有效期，过期了就需要重新扫码，无法实现脚本在后台自动化执行。
2. **账号封禁风险**：频繁的自动化请求极易触发官方防爬校验，有被封号的隐患。

为了解决这个问题，新版方案接入了微信读书 Agent API Gateway，即一个安全的 Skill 接口网关。

### 1.2 什么是 Agent API Gateway
Agent 网关是微信读书官方提供的专用外部应用通道，它使用了一种特殊的 **API Key**（格式为 `wrk-xxxxxxxx`，代表特定的用户授权身份）。
我们无需扫码登录，只需在发送请求时，在 HTTP 的 Header 头中携带这个 API Key 即可。

### 1.3 方案对比

| 方案 | 优点 | 缺点 | 项目中的选择 |
| :--- | :--- | :--- | :--- |
| **网页端 Cookie 爬虫** | 数据内容最丰富 | 极易过期、需频繁扫码、有封号危险 | ❌ 不采用 |
| **Agent API Gateway** | 凭证长期有效、免扫码、安全稳定 | 接口功能较专一，仅返回阅读时长数据 | ✅ 采用此方案 |

> **项目实例**：在 [auth.py](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L89) 中，[test_auth](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L89) 方法通过向网关发送一个简单的列表测试接口 `/_list` 来快速验证当前的 API Key 是否有效。

---

## 2. 数据流与转换设计（架构与核心概念）

### 2.1 整体架构与数据流向
微信读书的阅读数据是以**“月份”**为周期进行管理的。请求接口时，我们要向网关发送参数 `mode="monthly"` 并指定当前月份内的一个代表时间戳 `baseTime`。
数据流向设计如下：

```
     ┌────────────────────────┐         (月度轮询请求)         ┌────────────────────────┐
     │      WereadLoader      │ ────────────────────────────➔ │   Agent API Gateway    │
     └───────────▲────────────┘                               └───────────┬────────────┘
                 │                                                        │
                 │ (按天汇总、秒换算为分钟、Top百分比计算)                │ (返回单月数据 readTimes)
                 │                                                        ▼
     ┌───────────┴────────────┐                               ┌────────────────────────┐
     │   本地数据字典 Tracks   │ ⎪──────────────────────────── │ { 1749830400: 1824 }   │
     │ { "2025-06-14": 30.4 } │                               └────────────────────────┘
     └────────────────────────┘
```

### 2.2 核心转换逻辑
1. **时间戳转日期**：网关回传的 `readTimes` 是一个 JSON 字典，其 Key 是 Unix 时间戳（例如 `"1749830400"`），Value 是当天阅读的累计**秒数**（例如 `1824` 秒）。我们必须把这个时间戳转换为东八区时间，格式化为日期字符串 `"2025-06-14"`。
2. **秒转分钟**：渲染引擎期望输入的数据单位是“分钟”，因此我们需要将秒数除以 `60.0` 并保留两位小数（例如 `1824 / 60.0 = 30.4` 分钟）。

> **项目实例**：这一核心转换在 [loader.py](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L74-L82) 的 [make_track_dict](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L54) 中执行，为后续的绘图模块提供纯净的数据集。

---

## 3. 快速上手（最小可用示例）

以下是一个最小的可执行脚本 `demo_loader.py`，展示了如何用最简代码建立 Bearer 认证，并调用网关抓取单月数据：

```python
# 必须先安装 requests 依赖
import datetime
import requests

# 1. 模拟 WeReadAuth 鉴权信息
api_key = "wrk-test_key" # 请替换为真实的 API Key
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# 2. 模拟 WereadLoader 选择 baseTime 并发出请求
# 取 2025 年 6 月 15 日作为 baseTime 基准
base_time = int(datetime.datetime(2025, 6, 15).timestamp())
body = {
    "api_name": "/readdata/detail",
    "skill_version": "1.0.3",
    "mode": "monthly",
    "baseTime": base_time
}

resp = requests.post("https://i.weread.qq.com/api/agent/gateway", json=body, headers=headers)
if resp.ok:
    print("获取成功，数据摘要:", resp.json().get("readTimes", {}))
else:
    print("获取失败，错误码:", resp.status_code)
```

---

# 第二层：源码解析

> 本层目标：逐行剖析模块源码实现。
> 读完本层，你能独立调试网关交互、改写异常捕获机制，并深刻理解高亮分位数的统计算法。

## 4. 接口与模块源码逐一解析

### 4.1 WeReadAuth 认证管理器

`WeReadAuth` 主要实现 API Key 的环境读取、请求头拼装以及 HTTP 通信和异常拦截。

* **源码位置**：[weread_poster/auth.py](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py)
* **类定义**：
```python
class WeReadAuth:
    """微信读书认证管理器（API Key 方式）"""

    def __init__(self):
        # 自动读取环境变量
        self.api_key = os.getenv("WEREAD_API_KEY", "")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://weread.qq.com/",
        }
```

* **WeReadAuth 核心方法列表**：

| 方法名 | 参数 | 返回值 | 职责与关键行为 |
| :--- | :--- | :--- | :--- |
| [get_gateway_headers](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L33) | 无 | `Dict[str, str]` | 复制基本请求头，将 `Bearer <API_KEY>` 注入到 `Authorization` 字段。 |
| [call_gateway](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L39) | `api_name: str`, `**params` | `dict` | 拼接参数，发送 HTTP POST 请求，并在收到响应后，对 HTTP 状态码以及返回数据中的 `errcode` 进行校验。 |
| [test_auth](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L89) | 无 | `Tuple[bool, dict]` | 请求 `/_list` 网关，验证当前 API Key 权限。 |

---

### 4.2 WereadLoader 数据加载器

`WereadLoader` 负责时间跨度循环，将多个单月的响应合拢为一体。

* **源码位置**：[weread_poster/loader.py](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py)
* **核心类定义**：
```python
class WereadLoader:
    track_color = "#2EA8F7"
    unit = "mins"  # 与绘图器约定的基本时间单位

    def __init__(self, from_year: int, to_year: int, **kwargs):
        assert to_year >= from_year
        self.from_year = from_year
        self.to_year = to_year
        self.time_zone = TIME_ZONE
        self.number_by_date_dict = defaultdict(int) # 最终按日存储的字典
        self.number_list = []                      # 所有有阅读天数的时长列表
        self.year_list = list(range(from_year, to_year + 1))
        self.special_number1 = None                # 重度阅读分位数 (Top 20%)
        self.special_number2 = None                # 中度阅读分位数 (Top 50%)
        self.auth = WeReadAuth()
```

* **WereadLoader 核心方法列表**：

| 方法名 | 参数 | 返回值 | 职责与关键行为 |
| :--- | :--- | :--- | :--- |
| [get_api_data](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L36) | `year: int`, `month: int` | `dict` | 用月中 15 日的时间戳调用网关获取数据。如果请求月份是未来的月份，则直接返回空字典 `{}`。 |
| [make_track_dict](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L54) | 无 | 无 | 循环每一年的 12 个月调用网关。将得到的原始时间戳转换为东八区 `%Y-%m-%d` 格式，秒数除以 60 转成以“分钟”为单位存入 `number_by_date_dict`。 |
| [make_special_number](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L87) | 无 | 无 | 对非零时长列表排序，取倒数 20% 位置和 50% 位置的值作为颜色渐变的基准和强制特殊渲染的阈值。 |

---

## 5. 实现细节深入

### 5.1 时间区段过滤与未来时间截断
在 [loader.py 的 get_api_data](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L36-L41) 中，如果用户请求的年份跨度很大（例如 `2023-2026` ），我们必须防止发出未来月份的数据请求：
```python
# 源码位置：weread_poster/loader.py
now = datetime.datetime.now()
# 如果年份大于今年，或者年份相同但月份大于本月，立即截断返回空
if year > now.year or (year == now.year and month > now.month):
    return {}
```
* **为什么要使用 15 日作为 baseTime**：
  微信读书 API 网关的 `baseTime` 指示了查询该时间戳所在的月份。如果使用 1 日或 31 日，可能会因为格林威治时间转换带来的小时级时差，导致查询范围偏移到前一个月或后一个月。使用月中 15 日的时间戳（例如 `datetime.datetime(year, month, 15)`）是确保查询百分百落入当前月份的工程实践。

### 5.2 动态高亮阈值的数学计算
为什么我们要动态计算 `special_number1` 和 `special_number2`，而不是写死一个固定时长？
因为不同用户的阅读习惯截然不同（有的极客每天读 3 小时，有的用户每天读 20 分钟）。如果把“重度阅读”强制写死为 120 分钟，阅读量低的用户画出来的图将是单一的浅色，完全没有层次感。
在 [loader.py 的 make_special_number](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L87-L99) 中：
```python
# 排除相同数值后排序
number_list_set = sorted(list(set(self.number_list)))
number_list_set_len = len(number_list_set)
# 取前 20% 作为 special_number1，前 50% 作为 special_number2
self.special_number1 = number_list_set[-1 * int(number_list_set_len * 0.2)]
self.special_number2 = number_list_set[-1 * int(number_list_set_len * 0.50)]
```
* **效果**：这个分位数的选取能够保证无论用户的总阅读时间高低，渲染出来的热力图总会有 20% 左右最亮眼的最深色方格，50% 的中等亮方格，其余是淡色，达到了千人千面的完美层次感。

---

## 6. 异常与边界情况处理

### 6.1 网络连接断开与超时兜底
微信网关在国外或者部分局域网下可能存在访问困难。我们在 [auth.py](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L44-L49) 中加入了双重兜底异常捕获：
```python
try:
    resp = requests.post(GATEWAY_URL, json=body, headers=headers, timeout=30)
except requests.Timeout:
    raise Exception("Gateway API 请求超时（30s）")
except requests.ConnectionError as e:
    raise Exception(f"Gateway API 连接失败: {e}")
```
这样能够避免 Python 报出长篇的栈追踪（Traceback）引发新手用户恐慌，而是输出一句清晰易懂的报错。

### 6.2 脏数据过滤
在 [loader.py](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L60-L66) 的月循环中，如果用户请求的某一月因为接口抖动或未开放而返回了空，我们通过 `if read_times:` 校验数据完整性，过滤掉无效响应，避免因为读取 `None.values()` 导致程序崩溃。

---

## 7. 本章知识总结

| 知识点 | 概念导论中的解释 | 源码中的位置 | 关键行为 |
| :--- | :--- | :--- | :--- |
| **网关 Bearer 鉴权** | 将 API Key 封装入 Request Headers 中 | [auth.py:WeReadAuth](file:///d:/coding/personalProj/weread-poster/weread_poster/auth.py#L33-L37) | `headers["Authorization"] = f"Bearer {api_key}"` |
| **月中基准时间** | 选取 15 日时间戳防止时区边界抖动 | [loader.py:WereadLoader](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L43) | `base_time = int(datetime.datetime(year, month, 15).timestamp())` |
| **时间单位规整** | 将秒级原始时长除以 60 并保留两位小数 | [loader.py:WereadLoader](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L82) | `round(duration_seconds / 60.0, 2)` 存入字典 |
| **动态分位数阈值** | 计算 Top 20% 和 50% 处的时长值 | [loader.py:WereadLoader](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L87-L99) | 排序去重列表后取指定比例位置的值 |

### 知识地图

```
第 01 章 知识地图：
  
WeRead 数据拉取与过滤
  ├── 身份鉴权 (auth.py)
  │    ├── 读取 WEREAD_API_KEY
  │    └── 封装 Authorization Headers
  └── 月度数据循环 (loader.py)
       ├── 跳过未来月份限制
       ├── 按月中 15 日生成基准时间戳 (baseTime)
       ├── 将 Unix 时间戳解析为东八区 YYYY-MM-DD
       ├── 秒数 ➔ 分钟数浮点转换
       └── 动态分位数计算 (Top 20% & Top 50% 阈值)
```

- **核心要点 1**：本项目的数据安全性是通过 API Key 传递 Bearer token 在外部网关中实现的。
- **核心要点 2**：对月份请求的 baseTime 使用月中 15 日是避开时区溢出的核心小技巧。
- **核心要点 3**：利用 Top 20% 与 Top 50% 分位数排序提取高亮颜色界限，让每个人渲染出的海报都有完美光暗对比。

→ 下一章：[第 02 章：视觉绘制 — 54×7 年历网格与 HSL 颜色渐变引擎](file:///d:/coding/personalProj/weread-poster/docs/tutorial/02-drawer-and-interpolation.md)

---

## 8. 思考题

### 题目 1：在 `WeReadAuth.call_gateway` 中，为什么要针对非 JSON 响应进行单独的 `try...except ValueError` 拦截？

<details>
<summary>参考解答</summary>
当 API 网关服务器遭遇了灾难性错误（例如 Nginx 网关 502 Bad Gateway 或是 504 Gateway Timeout）时，网关返回的响应通常是 HTML 格式的系统报错页，而不是常规的 JSON 数据。
如果直接调用 `resp.json()` 会导致 Python 抛出 `JSONDecodeError` 崩溃。通过专门的 `ValueError` 捕获，可以截取前 500 个字符的 HTML 错误提示（例如 Nginx 的提示），让排错更加快速直观。
</details>

### 题目 2：如果 `make_track_dict` 中未对 Unix 时间戳强制指定东八区（UTC+8）时区，可能会引发什么显示异常？

<details>
<summary>参考解答</summary>
如果不显式地指定东八区（`datetime.timezone(datetime.timedelta(hours=8))`），Python 的 `datetime.fromtimestamp` 会在不同的机器上默认使用操作系统本地时区（例如如果部署在海外云主机上，可能会默认使用 UTC 时间）。
这会导致数据产生 8 小时的时差偏移。举个例子，用户在东八区 6 月 14 日凌晨 3 点（对应时间戳）产生的阅读数据，由于时差偏移会被解析为 6 月 13 日产生的阅读，导致热力图的格子日期和真实阅读日期错位一天。
</details>

### 题目 3：当用户是第一天使用微信读书时（有阅读数据天数少于 3 天），`make_special_number` 会如何处理阈值？为什么要这样处理？

<details>
<summary>参考解答</summary>
根据 `make_special_number` 的源码：
```python
if number_list_set_len < 3:
    self.special_number1 = self.special_number2 = float("inf")
    return
```
如果天数少于 3 天，计算分位数没有统计学意义。代码会将高亮阈值设定为正无穷大（`float("inf")`）。这意味着所有的格子都不会被高亮主题色特殊渲染，只会使用普通的插值色彩，从而防止格子颜色对比过于突兀。
</details>

### 题目 4：[动手实践] 修改 `WereadLoader.get_api_data` 中的时间截断规则，使程序不仅能拦截未来的年和月，还能拦截“由于尚未产生数据而请求的当前月份”。预期输出为：如果请求的是当前月份且今天是 1 号（微信读书尚未更新），则不发网络请求，直接返回空字典。

<details>
<summary>参考解答</summary>
打开 [loader.py](file:///d:/coding/personalProj/weread-poster/weread_poster/loader.py#L36-L41)，将 `get_api_data` 中的时间判断逻辑修改如下：
```python
now = datetime.datetime.now()
# 拦截未来月份
if year > now.year or (year == now.year and month > now.month):
    return {}
# 新增拦截：如果是今年本月，且当前日期是 1 号的凌晨（例如 8 点之前尚未生成读书统计）
if year == now.year and month == now.month and now.day == 1 and now.hour < 8:
    print(f"  {year}-{month:02d} 月首防抖：跳过当日未结算的本月请求")
    return {}
```
</details>
