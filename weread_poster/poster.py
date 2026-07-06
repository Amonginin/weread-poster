"""
Poster 模块 — 管理热力图数据和绘图配置
移植自 GitHubPoster 的 poster.py，适配微信读书场景
"""

from collections import defaultdict

import svgwrite

from weread_poster.structures import XY, ValueRange


class Poster:
    """热力图 Poster，存储绘图所需的数据和配置"""

    def __init__(self):
        self.title = None
        self.tracks = {}
        self.type_list = []
        self.length_range_by_date = ValueRange()
        self.length_range_by_date_dict = defaultdict(ValueRange)
        self.units = "mins"
        self.colors = {
            "background": "#222222",
            "text": "#FFFFFF",
            "special": "#FFFF00",
            "track": "#4DD2FF",
        }
        self.width = 200
        self.height = 300
        self.years = None
        self.tracks_drawer = None
        self.with_animation = False
        self.animation_time = 10
        self.year_tracks_date_count_dict = defaultdict(int)
        self.year_tracks_type_dict = defaultdict(dict)
        self.is_summary = False
        self.special_number = {
            "special_number1": float("inf"),
            "special_number2": float("inf"),
        }
        self.total_sum_year_dict = defaultdict(int)

    def set_tracks(self, tracks, years, type_list):
        self.type_list.extend(type_list)
        self.tracks = tracks
        self.years = years
        for date, num in tracks.items():
            self.year_tracks_date_count_dict[date[:4]] += 1
            if type(num) is dict:
                for k, v in num.items():
                    self.length_range_by_date_dict[k].extend(v)
            else:
                self.length_range_by_date.extend(num)
        for t in type_list:
            self.compute_track_statistics(t)

    @property
    def is_multiple_type(self):
        return len(self.type_list) > 1

    def set_with_animation(self, with_animation):
        self.with_animation = with_animation

    def set_animation_time(self, animation_time):
        self.animation_time = animation_time

    def draw(self, drawer, output):
        assert self.type_list, "type_list is empty"
        self._draw_github(drawer, output)

    def _draw_github(self, drawer, output):
        height = self.height
        width = self.width
        self.tracks_drawer = drawer
        d = svgwrite.Drawing(output, (f"{width}mm", f"{height}mm"))
        d.viewbox(0, 0, self.width, height)
        d.add(d.rect((0, 0), (width, height), fill=self.colors["background"]))
        self._draw_header(d)
        self._draw_tracks(d, XY(10, 30))
        d.save()

    def _draw_tracks(self, d, offset):
        self.tracks_drawer.draw(d, offset, self.is_summary)

    def _draw_header(self, d):
        text_color = self.colors["text"]
        title_style = "font-size:12px; font-family:Arial; font-weight:bold;"
        d.add(d.text(self.title, insert=(10, 20), fill=text_color, style=title_style))

    def compute_track_statistics(self, t):
        total_sum_year_dict = defaultdict(int)
        for date, num in self.tracks.items():
            if type(num) is dict:
                total_sum_year_dict[int(date[:4])] += num.get(t, 0)
            else:
                total_sum_year_dict[int(date[:4])] += num
        self.total_sum_year_dict = total_sum_year_dict
        return total_sum_year_dict
