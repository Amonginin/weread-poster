"""工具函数 — 移植自 GitHubPoster"""

import re
from itertools import count as itercount
from itertools import takewhile

import colour


def interpolate_color(color1, color2, ratio):
    """在两个颜色之间做线性插值"""
    if ratio < 0:
        ratio = 0
    elif ratio > 1:
        ratio = 1
    c1 = colour.Color(color1)
    c2 = colour.Color(color2)
    c3 = colour.Color(
        hue=((1 - ratio) * c1.hue + ratio * c2.hue),
        saturation=((1 - ratio) * c1.saturation + ratio * c2.saturation),
        luminance=((1 - ratio) * c1.luminance + ratio * c2.luminance),
    )
    return c3.hex_l


def parse_years(s):
    """解析年份字符串，返回 (from_year, to_year)"""
    m = re.match(r"^\d+$", s)
    if m:
        from_year = int(s)
        to_year = from_year
        return from_year, to_year
    m = re.match(r"^(\d+)-(\d+)$", s)
    if m:
        y1, y2 = int(m.group(1)), int(m.group(2))
        if y1 <= y2:
            from_year = y1
            to_year = y2
        else:
            from_year = y2
            to_year = y1
        return from_year, to_year
    raise ValueError(f"无法解析年份: {s}")


def make_key_times(year_count):
    """生成 SVG 动画的 keyTimes 列表"""
    s = list(takewhile(lambda n: n < 1, itercount(0, 1 / year_count)))
    s.append(1)
    return [str(round(i, 2)) for i in s]


def reduce_year_list(year_list, tracks_dict):
    """移除开头连续无数据的年份"""
    year_list_keys = list(tracks_dict.keys())
    year_list_keys.sort()
    s = set()
    for key in year_list_keys:
        if tracks_dict.get(key, 0) > 0:
            s.add(key[:4])
    year_list.sort()
    i = 0
    for year in year_list:
        if str(year) not in s:
            i += 1
        else:
            break
    return year_list[i:]


def format_duration(seconds):
    """将秒数格式化为中文时长字符串"""
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分钟"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}小时{minutes}分钟" if minutes else f"{hours}小时"
