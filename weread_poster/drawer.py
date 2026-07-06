"""
Drawer 模块 — GitHub 风格热力图绘图器
移植自 GitHubPoster 的 drawer.py，保留颜色渐变、动画等丰富效果
适配微信读书阅读时长数据（单位：分钟）
"""

import calendar
import datetime

import svgwrite.animate

from weread_poster.config import (
    DEFAULT_DOM_COLOR,
    DOM_BOX_DICT,
    DOM_BOX_TUPLE,
    MONTH_NAMES,
)
from weread_poster.utils import interpolate_color, make_key_times, format_duration


class Drawer:
    """GitHub 风格热力图绘图器"""

    name = "github"

    def __init__(self, p):
        self.poster = p
        self.year_size = 200 * 4.0 / 80.0
        self.year_style = f"font-size:{self.year_size}px; font-family:Arial;"
        self.year_length_style = f"font-size:{110 * 3.0 / 80.0}px; font-family:Arial;"
        self.month_names_style = "font-size:2.5px; font-family:Arial"

    @property
    def type_color_dict(self):
        return dict(zip(self.poster.type_list, ["#4DD2FF"]))

    def make_color(self, length_range, length):
        """根据数值在颜色范围内做渐变插值"""
        sp2 = self.poster.special_number.get("special_number2")
        sp1 = self.poster.special_number.get("special_number1")
        has_special = False
        if sp2 and sp1 and length:
            has_special = sp2 < length < sp1
        color_from = (
            self.poster.colors["special"]
            if has_special
            else self.poster.colors["track"]
        )
        color_to = self.poster.colors["special2"]
        diff = length_range.diameter()
        if diff == 0:
            return color_from

        return interpolate_color(
            color_from, color_to, (length - length_range.lower()) / diff
        )

    def _add_animation(self, rect, key_times, animate_index):
        """为格子添加淡入动画"""
        values = (
            ";".join(["0"] * animate_index)
            + ";"
            + ";".join(["1"] * (len(key_times) - animate_index))
        )
        rect.add(
            svgwrite.animate.Animate(
                "opacity",
                dur=f"{self.poster.animation_time}s",
                values=values,
                keyTimes=";".join(key_times),
                repeatCount="1",
            )
        )
        return rect

    def _gen_day_box(
        self,
        dr,
        rect_x,
        rect_y,
        date_title,
        day_tracks,
        with_animation,
        key_times,
        animate_index,
    ):
        """生成单个日历格子"""
        color = DEFAULT_DOM_COLOR
        if day_tracks:
            color = self.make_color(self.poster.length_range_by_date, day_tracks)
            if day_tracks >= self.poster.special_number["special_number1"]:
                color = self.poster.colors.get("special2") or self.poster.colors.get(
                    "special"
                )
            # 格式化时长（分钟 → 小时分钟）
            date_title = f"{date_title} {format_duration_mins(day_tracks)}"
        rect = dr.rect((rect_x, rect_y), DOM_BOX_TUPLE, fill=color)
        if with_animation:
            rect = self._add_animation(rect, key_times, animate_index)
        rect.set_desc(title=date_title)
        yield rect

    def _draw_one_calendar(self, dr, year, offset, _type=None):
        """绘制单年的日历热力图"""
        start_date_weekday, _ = calendar.monthrange(year, 1)
        github_rect_first_day = datetime.date(year, 1, 1)
        github_rect_day = github_rect_first_day + datetime.timedelta(
            -start_date_weekday
        )

        # 年度总时长（分钟 → 小时）
        year_length = self.poster.total_sum_year_dict.get(year, 0)
        year_units = self.poster.units
        if year_units == "mins":
            year_length = int(year_length / 60)
            year_units = "hours"
        year_length_str = str(int(year_length)) + f" {year_units}"

        # 年份标签
        dr.add(
            dr.text(
                f"{year}" if _type is None else f"{_type}",
                insert=offset.tuple(),
                fill=self.poster.colors["text"],
                dominant_baseline="hanging",
                style=self.year_style,
            )
        )

        # 年度总时长标签
        if not self.poster.is_multiple_type:
            dr.add(
                dr.text(
                    f"{year_length_str}",
                    insert=(offset.tuple()[0] + 165, offset.tuple()[1] + 5),
                    fill=self.poster.colors["text"],
                    dominant_baseline="hanging",
                    style=self.year_length_style,
                )
            )

        # 月份标签
        for num, name in enumerate(MONTH_NAMES):
            dr.add(
                dr.text(
                    f"{name}",
                    insert=(offset.tuple()[0] + 15.5 * num, offset.tuple()[1] + 14),
                    fill=self.poster.colors["text"],
                    style=self.month_names_style,
                )
            )

        rect_x = 10.0
        animate_index = 1
        year_count, key_times = 0, ""
        if self.poster.with_animation:
            year_count = self.poster.year_tracks_date_count_dict.get(str(year), 10)
            key_times = make_key_times(year_count)

        # 绘制 54 周 × 7 天的格子
        for _ in range(54):
            rect_y = offset.y + self.year_size + 2
            for _ in range(7):
                if int(github_rect_day.year) > year:
                    break
                rect_y += 3.5
                date_title = str(github_rect_day)
                day_tracks = None
                if date_title in self.poster.tracks:
                    day_tracks = self.poster.tracks[date_title]
                    if animate_index < len(key_times) - 1:
                        animate_index += 1

                for rect in self._gen_day_box(
                    dr,
                    rect_x,
                    rect_y,
                    date_title,
                    day_tracks,
                    self.poster.with_animation,
                    key_times,
                    animate_index,
                ):
                    dr.add(rect)
                github_rect_day += datetime.timedelta(1)
            rect_x += 3.5
        offset.y += 3.5 * 9 + self.year_size + 1.0

    def draw(self, dr, offset, is_summary=False):
        """绘制所有年份的热力图"""
        if self.poster.tracks is None:
            raise Exception("No tracks to draw")

        for year in range(self.poster.years[0], self.poster.years[-1] + 1)[::-1]:
            self._draw_one_calendar(dr, year, offset)
        print(f"{str(self.poster.type_list)} poster drawer done")

    def draw_footer(self, dr):
        """绘制底部图例"""
        from weread_poster.config import COLOR_TUPLE
        text_color = self.poster.colors["text"]
        header_style = "font-size:4px; font-family:Arial"
        x = 10
        y = self.poster.height - 2.5
        index = 0
        for _type in self.poster.type_list:
            dr.add(dr.rect((x, y - 2.5), DOM_BOX_TUPLE, fill=COLOR_TUPLE[index][0]))
            dr.add(
                dr.text(
                    f": {_type}",
                    insert=(x + 3, y),
                    fill=text_color,
                    style=header_style,
                )
            )
            x += 20
            index += 1


def format_duration_mins(minutes):
    """将分钟格式化为中文时长字符串"""
    if minutes < 1:
        return f"{int(minutes * 60)}秒"
    if minutes < 60:
        return f"{int(minutes)}分钟"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}小时{mins}分钟" if mins else f"{hours}小时"
