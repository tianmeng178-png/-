# -*- coding: utf-8 -*-
"""
AI驱动的换热器智能设计系统 - 主程序
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

from src.llm_gateway import LLMGateway, LLMConfig
from src.foam_controller import OpenFOAMController, SimulationConfig
from src.result_processor import process_results, SimulationResult


class HeatExchangerDesignSystem:
    """换热器智能设计系统主类"""

    def __init__(self, config_path: str = "config/system_config.json"):
        self.config = self._load_config(config_path)
        self.llm_gateway = self._init_llm_gateway()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_llm_gateway(self) -> LLMGateway:
        """初始化LLM网关"""
        llm_config = LLMConfig(
            gateway_url=self.config["llm"]["gateway_url"],
            api_key=self.config["llm"]["api_key"],
            model=self.config["llm"]["model"],
            timeout=self.config["llm"].get("timeout", 60),
        )
        return LLMGateway(llm_config)

    def design(self, user_input: str) -> SimulationResult:
        """
        执行换热器设计

        Args:
            user_input: 用户自然语言输入

        Returns:
            仿真结果
        """
        print(f"\n{'=' * 50}")
        print(f"收到设计请求: {user_input}")
        print(f"{'=' * 50}\n")

        print("步骤1: 解析设计参数...")
        params = self.llm_gateway.parse_design_request(user_input)
        print(f"解析结果: {json.dumps(params, indent=2, ensure_ascii=False)}\n")

        template_dir = self.config["simulation"]["template_dir"]
        output_dir = self._prepare_output_dir(params)

        print(f"步骤2: 创建OpenFOAM案例...")
        controller = OpenFOAMController.from_template(
            template_dir=template_dir, target_dir=output_dir, params=params
        )
        print(f"案例目录: {output_dir}\n")

        print("步骤3: 运行仿真...")
        success = controller.run()

        if not success:
            return SimulationResult(status="failed", error_message="Simulation failed")

        print("\n步骤4: 解析结果...")
        foam_results = controller.get_results()
        print(f"原始结果: {json.dumps(foam_results, indent=2)}\n")

        print("步骤5: 生成报告...")
        result = process_results(
            case_dir=output_dir,
            foam_results=foam_results,
            output_dir=os.path.join(output_dir, "output"),
        )

        print("\n" + "=" * 50)
        print("设计完成!")
        print("=" * 50)

        return result

    def _prepare_output_dir(self, params: Dict[str, Any]) -> str:
        """准备输出目录"""
        import hashlib
        import time

        hash_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        output_dir = os.path.join(
            self.config["simulation"]["output_base_dir"], f"case_{hash_str}"
        )

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        return output_dir


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI驱动的换热器智能设计系统")
    parser.add_argument("-i", "--input", type=str, help="自然语言设计输入")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config/system_config.json",
        help="配置文件路径",
    )
    parser.add_argument("--interactive", action="store_true", help="交互模式")

    args = parser.parse_args()

    if args.interactive:
        print("=" * 50)
        print("AI换热器智能设计系统 (输入 'quit' 退出)")
        print("=" * 50)

        system = HeatExchangerDesignSystem(args.config)

        while True:
            user_input = input("\n请描述您的设计需求: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("再见!")
                break

            if not user_input:
                continue

            try:
                result = system.design(user_input)
                print(f"\n设计结果: {result.to_dict()}")
            except Exception as e:
                print(f"\n错误: {str(e)}")

    elif args.input:
        system = HeatExchangerDesignSystem(args.config)
        result = system.design(args.input)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
