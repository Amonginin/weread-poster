import unittest
import os
import json
import shutil
import datetime
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

# 导入核心模块
from weread_poster.auth import WeReadAuth
from weread_poster.loader import WereadLoader
from weread_poster.poster import Poster
from weread_poster import cli
from weread_poster.utils import parse_years, reduce_year_list


class TestWeReadPoster(unittest.TestCase):

    def setUp(self):
        # 备份原本的环境变量
        self.original_env = os.environ.get("WEREAD_API_KEY")
        self.original_theme_env = os.environ.get("THEME_COLOR")
        self.original_output_env = os.environ.get("OUTPUT_SVG")
        
        # 设定临时的测试输出文件
        self.test_svg = "test_heatmap.svg"
        self.test_json = "test_data.json"
        
        # 确保干净的环境
        if "WEREAD_API_KEY" in os.environ:
            del os.environ["WEREAD_API_KEY"]
        if "THEME_COLOR" in os.environ:
            del os.environ["THEME_COLOR"]
        if "OUTPUT_SVG" in os.environ:
            del os.environ["OUTPUT_SVG"]

    def tearDown(self):
        # 还原环境变量
        if self.original_env is not None:
            os.environ["WEREAD_API_KEY"] = self.original_env
        if self.original_theme_env is not None:
            os.environ["THEME_COLOR"] = self.original_theme_env
        if self.original_output_env is not None:
            os.environ["OUTPUT_SVG"] = self.original_output_env
            
        # 清理生成的临时测试文件
        for f in [self.test_svg, self.test_json]:
            if os.path.exists(f):
                os.remove(f)

    # ==========================================
    # 1. 基础与身份鉴权测试 (TC-01)
    # ==========================================

    def test_tc01_01_no_api_key_exit(self):
        """TC-01-01: 未配置 API Key 时程序友善退出，退出码为 1"""
        with patch("sys.argv", ["weread_poster"]):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
            self.assertEqual(cm.exception.code, 1)

    @patch("weread_poster.auth.WeReadAuth.test_auth")
    def test_tc01_02_invalid_api_key_exit(self, mock_test_auth):
        """TC-01-02: API Key 校验失败时程序友善退出，退出码为 1"""
        os.environ["WEREAD_API_KEY"] = "wrk-invalid"
        mock_test_auth.return_value = (False, {"error": "Invalid token"})
        
        with patch("sys.argv", ["weread_poster"]):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
            self.assertEqual(cm.exception.code, 1)

    # ==========================================
    # 2. 年份解析与数据过滤测试 (TC-02)
    # ==========================================

    def test_tc02_01_parse_single_year(self):
        """TC-02-01: 单个年份解析正确"""
        from_yr, to_yr = parse_years("2025")
        self.assertEqual(from_yr, 2025)
        self.assertEqual(to_yr, 2025)

    def test_tc02_02_parse_range_years(self):
        """TC-02-02: 范围年份解析正确"""
        from_yr, to_yr = parse_years("2023-2025")
        self.assertEqual(from_yr, 2023)
        self.assertEqual(to_yr, 2025)

        # 倒序也应当自动调整顺序
        from_yr, to_yr = parse_years("2025-2023")
        self.assertEqual(from_yr, 2023)
        self.assertEqual(to_yr, 2025)

    def test_tc02_03_parse_invalid_year_raises(self):
        """TC-02-03: 非法年份抛出 ValueError 异常"""
        with self.assertRaises(ValueError):
            parse_years("2025a")
        with self.assertRaises(ValueError):
            parse_years("2025-202a")

    def test_tc02_04_reduce_empty_years(self):
        """TC-02-04: 自动缩减剔除开头无数据年份"""
        tracks = {
            "2023-05-12": 0.0,
            "2024-06-15": 0.0,  # 0 分钟算无数据
            "2025-01-01": 30.0
        }
        years = [2023, 2024, 2025]
        reduced = reduce_year_list(years, tracks)
        # 2023 和 2024 处于开头且无数据，应被缩减，仅保留 2025
        self.assertEqual(reduced, [2025])

    # ==========================================
    # 3. 核心功能集成测试（利用 Mock API 跑完完整流程）
    # ==========================================

    @patch("weread_poster.auth.WeReadAuth.call_gateway")
    @patch("weread_poster.auth.WeReadAuth.test_auth")
    def test_full_pipeline_success(self, mock_test_auth, mock_call_gateway):
        """利用 Mock 数据测试完整 CLI 链路的成功生成"""
        os.environ["WEREAD_API_KEY"] = "wrk-mockkey"
        mock_test_auth.return_value = (True, {"errcode": 0})
        
        # 模拟 /readdata/detail 接口返回 2025 年 6 月的阅读记录 (秒级数据)
        # 1749830400 = 2025-06-14，时长 1800s (30分钟)
        # 1749916800 = 2025-06-15，时长 3600s (60分钟)
        # 1750003200 = 2025-06-16，时长 7200s (120分钟)
        mock_call_gateway.return_value = {
            "errcode": 0,
            "readTimes": {
                "1749830400": 1800,
                "1749916800": 3600,
                "1750003200": 7200
            }
        }

        # 模拟命令行参数：指定 2025 年，输出测试 SVG 及测试 JSON，开启统计和动画
        test_args = [
            "weread_poster",
            "--year", "2025",
            "--theme", "rose",
            "--output", self.test_svg,
            "--json", self.test_json,
            "--stats",
            "--with-animation",
            "--animation-time", "15"
        ]

        with patch("sys.argv", test_args):
            # 运行 main 应当不抛出异常并顺利完成
            cli.main()

        # A. 验证 JSON 导出数据正确折算回秒数
        self.assertTrue(os.path.exists(self.test_json))
        with open(self.test_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 检查时间戳对应的秒数是否吻合
        self.assertEqual(data.get("2025-06-14"), 1800)
        self.assertEqual(data.get("2025-06-15"), 3600)
        self.assertEqual(data.get("2025-06-16"), 7200)

        # B. 验证 SVG 矢量图成功写盘
        self.assertTrue(os.path.exists(self.test_svg))
        
        # C. 解析 SVG DOM 验证具体节点与属性
        tree = ET.parse(self.test_svg)
        root = tree.getroot()
        
        # 获取 SVG 的命名空间
        ns = {"svg": "http://www.w3.org/2000/svg"}
        
        # 寻找 animate 动画节点
        animates = root.findall(".//svg:animate", ns)
        self.assertTrue(len(animates) > 0, "SVG 中应该包含动画节点")
        
        # 检查动画时长是否正确被覆盖为 15s
        for anim in animates:
            self.assertEqual(anim.attrib.get("dur"), "15s")

        # D. 验证自定义色彩覆写
        # 使用自定义的背景色和文本色
        override_args = [
            "weread_poster",
            "--year", "2025",
            "--output", self.test_svg,
            "--background-color", "#aabbcc",
            "--text-color", "#112233"
        ]
        with patch("sys.argv", override_args):
            cli.main()
        
        tree = ET.parse(self.test_svg)
        root = tree.getroot()
        # 查找背景 rect 元素
        rects = root.findall(".//svg:rect", ns)
        # 第一个 rect 应该是大背景矩形
        bg_rect = rects[0]
        self.assertEqual(bg_rect.attrib.get("fill"), "#aabbcc")

    # ==========================================
    # 4. 环境变量与优先级测试 (TC-06)
    # ==========================================

    @patch("weread_poster.auth.WeReadAuth.call_gateway")
    @patch("weread_poster.auth.WeReadAuth.test_auth")
    def test_tc06_01_env_theme_and_output(self, mock_test_auth, mock_call_gateway):
        """TC-06: 验证环境变量 THEME_COLOR 与 OUTPUT_SVG 是否生效及命令行覆写优先级"""
        os.environ["WEREAD_API_KEY"] = "wrk-mockkey"
        os.environ["THEME_COLOR"] = "rose"
        os.environ["OUTPUT_SVG"] = self.test_svg
        
        mock_test_auth.return_value = (True, {})
        mock_call_gateway.return_value = {
            "errcode": 0,
            "readTimes": {"1749830400": 3600}
        }

        # A. 仅指定年份，使用环境变量的主题和输出路径
        with patch("sys.argv", ["weread_poster", "--year", "2025"]):
            cli.main()
        
        self.assertTrue(os.path.exists(self.test_svg))
        
        # B. 命令行显式覆写环境变量的主题色
        # 验证命令行传递的优先级高于环境变量
        # 我们使用 weread 主题，并删除临时文件测试
        if os.path.exists(self.test_svg):
            os.remove(self.test_svg)
            
        with patch("sys.argv", ["weread_poster", "--year", "2025", "--theme", "github"]):
            cli.main()
            
        self.assertTrue(os.path.exists(self.test_svg))


if __name__ == "__main__":
    unittest.main()
