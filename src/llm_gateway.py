# -*- coding: utf-8 -*-
"""
LLM网关模块 - 通过API网关调用大语言模型
支持多供应商：DeepSeek, Qwen, OpenAI等
"""

import json
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM网关配置"""

    gateway_url: str  # 网关地址，如: http://localhost:8000/v1
    api_key: str  # API密钥
    model: str  # 模型名称
    timeout: int = 60  # 超时时间(秒)


class LLMGateway:
    """LLM网关客户端"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    def parse_design_request(self, user_input: str) -> Dict[str, Any]:
        """
        解析用户设计请求，转换为工程参数

        Args:
            user_input: 用户自然语言输入

        Returns:
            JSON格式的工程参数
        """
        prompt = self._build_prompt(user_input)

        response = self._call_api(prompt)

        return self._parse_response(response)

    def _build_prompt(self, user_input: str) -> str:
        """构建提示词"""
        return f"""你是一个换热器设计专家。请从以下用户输入中提取设计参数，并以JSON格式返回。

用户输入：{user_input}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
    "type": "microchannel_heat_sink",
    "velocity": 数值(单位m/s),
    "inlet_temperature": 数值(单位℃),
    "wall_temperature": 数值(单位℃，热源壁面温度，默认80),
    "fluid": "water" 或其他流体名称,
    "heat_flux": 数值(单位W/m²，可选),
    "channel_width": 数值(单位mm，可选),
    "channel_height": 数值(单位mm，可选)
}}

注意：
- type 只支持 "microchannel_heat_sink"
- velocity 流速，单位 m/s
- inlet_temperature 入口流体温度，单位 ℃
- wall_temperature 热源壁面温度，单位 ℃，默认80℃
- fluid 默认使用 "water"
"""

    def _call_api(self, prompt: str) -> Dict[str, Any]:
        """调用API"""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }

        try:
            response = requests.post(
                f"{self.config.gateway_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM API调用失败: {str(e)}")

    def _parse_response(self, response: Dict) -> Dict[str, Any]:
        """解析API响应"""
        try:
            content = response["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except (KeyError, json.JSONDecodeError, IndexError) as e:
            raise RuntimeError(f"解析LLM响应失败: {str(e)}")


def create_llm_gateway(config_path: str = "config/llm_config.json") -> LLMGateway:
    """从配置文件创建LLM网关客户端"""
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    config = LLMConfig(
        gateway_url=config_dict["gateway_url"],
        api_key=config_dict["api_key"],
        model=config_dict["model"],
        timeout=config_dict.get("timeout", 60),
    )

    return LLMGateway(config)


if __name__ == "__main__":
    config = LLMConfig(
        gateway_url="http://localhost:8000/v1",
        api_key="test-key",
        model="deepseek-chat",
    )
    gateway = LLMGateway(config)

    result = gateway.parse_design_request(
        "设计一个CPU微通道散热器，入口温度30℃，流速2m/s"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
