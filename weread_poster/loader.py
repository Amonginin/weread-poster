"""
微信读书数据加载器 — 使用 Agent API Gateway 获取阅读数据
数据获取方式来自新项目，接口适配旧项目 Poster/Drawer 架构
"""

import calendar
import datetime
from collections import defaultdict

from weread_poster.auth import WeReadAuth
from weread_poster.config import TIME_ZONE


class WereadLoader:
    """微信读书数据加载器

    通过 Agent API Gateway 的 /readdata/detail 接口获取每日阅读时长。
    逐月调用 mode=monthly，readTimes 按天分桶，提取日粒度数据。
    """

    track_color = "#2EA8F7"
    unit = "mins"  # 旧项目 Poster 架构期望的单位（分钟）

    def __init__(self, from_year: int, to_year: int, **kwargs):
        assert to_year >= from_year
        self.from_year = from_year
        self.to_year = to_year
        self.time_zone = TIME_ZONE
        self.number_by_date_dict = defaultdict(int)
        self.number_list = []
        self.year_list = list(range(from_year, to_year + 1))
        self.special_number1 = None
        self.special_number2 = None
        self.auth = WeReadAuth()

    def get_api_data(self, year: int, month: int) -> dict:
        """调用 /readdata/detail 获取单月数据"""
        # 跳过未来月份
        now = datetime.datetime.now()
        if year > now.year or (year == now.year and month > now.month):
            return {}

        base_time = int(datetime.datetime(year, month, 15).timestamp())
        try:
            resp = self.auth.call_gateway(
                "/readdata/detail", mode="monthly", baseTime=base_time
            )
        except Exception as e:
            print(f"  {year}-{month:02d} 获取失败: {e}")
            return {}

        return resp

    def make_track_dict(self):
        """构建 {date_str: minutes} 字典"""
        raw_read_times = {}

        for year in range(self.from_year, self.to_year + 1):
            year_total = 0
            for month in range(1, 13):
                api_data = self.get_api_data(year, month)
                read_times = api_data.get("readTimes", {})
                if read_times:
                    raw_read_times.update(read_times)
                    month_total = sum(read_times.values())
                    year_total += month_total

            days_count = len([
                k for k in raw_read_times
                if str(year) in str(datetime.datetime.fromtimestamp(int(k)).year)
            ])
            print(f"{year} 年: 累计 {days_count} 天有阅读记录")

        # 将 {timestamp: seconds} 转为 {date_str: minutes}
        for timestamp, duration_seconds in raw_read_times.items():
            date = datetime.datetime.fromtimestamp(
                int(timestamp), tz=datetime.timezone(
                    datetime.timedelta(hours=8)
                )
            ).strftime("%Y-%m-%d")
            # 转为分钟，保留 2 位小数（与旧项目 weread_loader 一致）
            self.number_by_date_dict[date] = round(duration_seconds / 60.0, 2)

        for v in self.number_by_date_dict.values():
            self.number_list.append(v)

    def make_special_number(self):
        """计算特殊颜色阈值（top 20% 和 top 20%-50%）"""
        number_list_set = sorted(list(set(self.number_list)))
        number_list_set_len = len(number_list_set)
        if number_list_set_len < 3:
            self.special_number1 = self.special_number2 = float("inf")
            return
        elif len(self.number_list) < 10:
            self.special_number1 = number_list_set[-1]
            self.special_number2 = number_list_set[-2]
        else:
            self.special_number1 = number_list_set[-1 * int(number_list_set_len * 0.2)]
            self.special_number2 = number_list_set[-1 * int(number_list_set_len * 0.50)]

    def get_all_track_data(self):
        """获取所有跟踪数据，返回 (tracks_dict, year_list)"""
        self.make_track_dict()
        self.make_special_number()
        return self.number_by_date_dict, self.year_list
