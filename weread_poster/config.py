"""配置常量 — 移植自 GitHubPoster 并适配微信读书"""

# 热力图格子尺寸（mm 单位，与 GitHubPoster 一致）
DOM_BOX_TUPLE = (2.6, 2.6)
DOM_BOX_TUPLE_LIST_FOR_TWO = ((2.6, 1.3), (2.6, 1.3))
DOM_BOX_TUPLE_LIST_FOR_THREE = ((2.7, 0.9), (2.7, 0.9), (2.7, 0.9))

DOM_BOX_DICT = {
    1: {"dom": (DOM_BOX_TUPLE,)},
    2: {"dom": DOM_BOX_TUPLE_LIST_FOR_TWO},
    3: {"dom": DOM_BOX_TUPLE_LIST_FOR_THREE},
}

DEFAULT_DOM_COLOR = "#444444"

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# 时区
TIME_ZONE = "Asia/Shanghai"

# 微信读书 Agent API Gateway
GATEWAY_URL = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.3"

# 阅读时长阈值（秒），用于分级着色
READING_THRESHOLDS = {
    "light": 1800,   # 30 分钟
    "medium": 3600,  # 1 小时
    "heavy": 7200,   # 2 小时
}

# 主题配色
THEMES = {
    "github": {
        "label": "GitHub 绿",
        "levels": ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"],
        "text": "#30A14E",
        "title": "#216E39",
    },
    "weread": {
        "label": "微信读书蓝",
        "levels": ["#E8F4F8", "#B5E1FF", "#5AB6FD", "#34A7FF", "#0077CC"],
        "text": "#34A7FF",
        "title": "#0077CC",
    },
    "warm": {
        "label": "暖阳橙",
        "levels": ["#FFF8E7", "#FFF7B2", "#FFEE4A", "#FFD700", "#FFA500"],
        "text": "#FFD700",
        "title": "#FFA500",
    },
    "purple": {
        "label": "梦幻紫",
        "levels": ["#F5F0FA", "#F7D6F8", "#E5A3E6", "#CA5BCC", "#A74AA8"],
        "text": "#CA5BCC",
        "title": "#A74AA8",
    },
    "ocean": {
        "label": "海洋青",
        "levels": ["#E8F8F5", "#A8E6CF", "#55B89D", "#2D8F76", "#1A6B5A"],
        "text": "#2D8F76",
        "title": "#1A6B5A",
    },
    "rose": {
        "label": "玫瑰粉",
        "levels": ["#FFF0F3", "#FFCCD5", "#FF8FA3", "#FF477E", "#E5256C"],
        "text": "#FF477E",
        "title": "#E5256C",
    },
}

DEFAULT_THEME = "weread"
