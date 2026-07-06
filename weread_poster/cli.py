#!/usr/bin/env python3
"""
微信读书阅读时长热力图 CLI
数据获取：Agent API Gateway（新项目方式）
图片生成：GitHubPoster 风格 Drawer（旧项目方式）
"""

import argparse
import datetime
import json
import os
import sys

from weread_poster.auth import WeReadAuth
from weread_poster.config import THEMES, DEFAULT_THEME, READING_THRESHOLDS
from weread_poster.drawer import Drawer
from weread_poster.loader import WereadLoader
from weread_poster.poster import Poster
from weread_poster.utils import parse_years, reduce_year_list, format_duration


def build_parser():
    theme_list = ", ".join(f"{k}({v['label']})" for k, v in THEMES.items())
    parser = argparse.ArgumentParser(
        description="微信读书阅读时长热力图 — Agent API Gateway 数据 + GitHub 风格渲染",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例:
  python -m weread_poster                              # 默认今年
  python -m weread_poster --year 2023-2025             # 指定年份范围
  python -m weread_poster --theme weread --me 我的阅读   # 自定义主题和标题
  python -m weread_poster --with-animation              # 带动画效果
  python -m weread_poster --year 2025 --json data.json  # 导出原始数据

可用主题: {theme_list}

环境变量:
  WEREAD_API_KEY  微信读书 API Key（必填，格式 wrk-xxxxxxxx）
        """,
    )
    parser.add_argument(
        "--year",
        type=str,
        default=str(datetime.datetime.now().year),
        help='年份范围，如 "2025" 或 "2023-2025"（默认: 今年）',
    )
    parser.add_argument(
        "--me",
        metavar="NAME",
        type=str,
        default="微信阅读热力图",
        help='海报标题（默认: "微信阅读热力图"）',
    )
    parser.add_argument(
        "--theme",
        default=os.getenv("THEME_COLOR", DEFAULT_THEME),
        help=f"配色主题（默认: {DEFAULT_THEME}）",
    )
    parser.add_argument(
        "--background-color",
        dest="background_color",
        metavar="COLOR",
        type=str,
        default="#222222",
        help='背景色（默认: "#222222"）',
    )
    parser.add_argument(
        "--track-color",
        dest="track_color",
        metavar="COLOR",
        type=str,
        default=None,
        help="轨道色（默认: 主题色或 #4DD2FF）",
    )
    parser.add_argument(
        "--text-color",
        dest="text_color",
        metavar="COLOR",
        type=str,
        default=None,
        help="文字色（默认: 使用主题文字色）",
    )
    parser.add_argument(
        "--special-color1",
        dest="special_color1",
        metavar="COLOR",
        default=None,
        help="特殊色1（默认: 使用主题色1）",
    )
    parser.add_argument(
        "--special-color2",
        dest="special_color2",
        metavar="COLOR",
        default=None,
        help="特殊色2（默认: 使用主题色2）",
    )
    parser.add_argument(
        "--with-animation",
        dest="with_animation",
        action="store_true",
        help="添加动画效果",
    )
    parser.add_argument(
        "--animation-time",
        dest="animation_time",
        type=int,
        default=10,
        help="动画时长秒数（默认: 10）",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("OUTPUT_SVG", "weread_heatmap.svg"),
        help="SVG 输出路径（默认: weread_heatmap.svg）",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        default=None,
        help="同时导出原始数据到 JSON 文件",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="打印统计摘要",
    )
    return parser


def apply_theme(p: Poster, theme_name: str):
    """应用主题配色到 Poster"""
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    levels = theme["levels"]

    p.colors["track"] = levels[0]
    p.colors["special"] = levels[1]
    p.colors["special2"] = levels[4]


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 认证
    auth = WeReadAuth()
    if not auth.init_auth():
        print("请设置环境变量: export WEREAD_API_KEY=<你的API Key>")
        sys.exit(1)

    is_valid, info = auth.test_auth()
    if not is_valid:
        print(f"认证失败: {info.get('error', '未知错误')}")
        sys.exit(1)
    print("认证成功")

    # 解析年份
    from_year, to_year = parse_years(args.year)
    print(f"正在获取 {from_year}–{to_year} 年阅读数据...")

    # 获取数据
    loader = WereadLoader(from_year, to_year)
    loader.auth = auth  # 复用已认证的 auth 实例
    tracks, years = loader.get_all_track_data()

    if not tracks:
        print("未获取到阅读数据")
        sys.exit(1)

    years = reduce_year_list(years, tracks)
    if not years:
        print("指定年份范围内无有效数据")
        sys.exit(1)

    print(f"共获取 {len(tracks)} 天的阅读记录")

    # 初始化 Poster
    p = Poster()
    p.units = loader.unit  # "mins"

    # 应用主题
    apply_theme(p, args.theme)

    # 命令行参数覆盖
    if args.background_color:
        p.colors["background"] = args.background_color
    if args.track_color:
        p.colors["track"] = args.track_color
    if args.text_color:
        p.colors["text"] = args.text_color
    if args.special_color1:
        p.colors["special"] = args.special_color1
    if args.special_color2:
        p.colors["special2"] = args.special_color2

    # 动画
    p.set_with_animation(args.with_animation)
    p.set_animation_time(args.animation_time)

    # 设置数据
    p.set_tracks(tracks, years, ["weread"])

    # 设置标题
    p.title = args.me

    # 特殊数字
    p.special_number = {
        "special_number1": loader.special_number1,
        "special_number2": loader.special_number2,
    }

    # 计算 SVG 尺寸
    poster_length = len(p.years)
    p.height = 35 + poster_length * 43
    p.width = 200

    # 输出目录
    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # 保存 JSON
    if args.json_output:
        # 转为秒数输出（更直观）
        tracks_seconds = {k: round(v * 60, 2) for k, v in tracks.items()}
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(tracks_seconds, f, ensure_ascii=False, indent=2)
        print(f"原始数据已保存到: {args.json_output}")

    # 生成 SVG
    d = Drawer(p)
    p.draw(d, args.output)
    print(f"热力图已生成: {args.output}")

    # 统计摘要
    if args.stats:
        print("\n===== 阅读统计摘要 =====")
        for year in sorted(p.total_sum_year_dict.keys()):
            total_mins = p.total_sum_year_dict[year]
            total_seconds = total_mins * 60
            days = len([d for d in tracks if d.startswith(str(year)) and tracks[d] > 0])
            avg_seconds = total_seconds // days if days else 0
            print(f"\n{year} 年:")
            print(f"  阅读天数: {days}")
            print(f"  总时长: {format_duration(int(total_seconds))}")
            print(f"  日均: {format_duration(int(avg_seconds))}")


if __name__ == "__main__":
    main()
