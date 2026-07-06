"""
微信读书认证模块 — 通过 Agent API Gateway 获取数据
移植自 Weread_ReadTime_Heatmap 项目，适配新架构
"""

import os
from typing import Dict, Tuple

import requests

from weread_poster.config import GATEWAY_URL, SKILL_VERSION


class WeReadAuth:
    """微信读书认证管理器（API Key 方式）"""

    def __init__(self):
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

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def get_gateway_headers(self) -> Dict[str, str]:
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        return headers

    def call_gateway(self, api_name: str, **params) -> dict:
        """调用 Agent API Gateway"""
        body = {"api_name": api_name, "skill_version": SKILL_VERSION, **params}
        headers = self.get_gateway_headers()

        try:
            resp = requests.post(GATEWAY_URL, json=body, headers=headers, timeout=30)
        except requests.Timeout:
            raise Exception("Gateway API 请求超时（30s）")
        except requests.ConnectionError as e:
            raise Exception(f"Gateway API 连接失败: {e}")

        try:
            data = resp.json()
        except ValueError:
            body_preview = resp.text[:500]
            raise Exception(
                f"Gateway 返回非 JSON 响应 "
                f"(HTTP {resp.status_code}): {body_preview}"
            )

        if "upgrade_info" in data:
            print(
                f"Skill 版本升级提示: "
                f"{data['upgrade_info'].get('message', '请升级')}"
            )

        if not resp.ok:
            errmsg = data.get("errmsg", data.get("message", "未知错误"))
            errcode = data.get("errcode", resp.status_code)
            raise Exception(
                f"Gateway API 错误 (HTTP {resp.status_code}): "
                f"{errmsg} (errcode={errcode})"
            )

        if data.get("errcode", 0) != 0:
            raise Exception(
                f"Gateway API 业务错误: {data.get('errmsg', '未知错误')} "
                f"(errcode={data.get('errcode')})"
            )

        return data

    def init_auth(self) -> bool:
        if self.has_api_key():
            print("使用 API Key 认证（Agent API Gateway）")
            return True
        print("未设置 WEREAD_API_KEY 环境变量")
        return False

    def test_auth(self) -> Tuple[bool, dict]:
        """测试认证是否有效"""
        try:
            print("测试 Gateway 连通性...")
            resp = self.call_gateway("/_list")
            print("Gateway 连通正常")
            return True, resp
        except Exception as e:
            return False, {"error": str(e)}
