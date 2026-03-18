# -*- coding: utf-8 -*-
"""
结果解析与可视化模块
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class SimulationResult:
    """仿真结果数据类"""

    status: str
    max_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    avg_temperature: Optional[float] = None
    pressure_drop: Optional[float] = None
    max_velocity: Optional[float] = None
    heat_transfer_coefficient: Optional[float] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "max_temperature": self.max_temperature,
            "min_temperature": self.min_temperature,
            "avg_temperature": self.avg_temperature,
            "pressure_drop": self.pressure_drop,
            "max_velocity": self.max_velocity,
            "heat_transfer_coefficient": self.heat_transfer_coefficient,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
        }

    def to_json(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationResult":
        return cls(**data)


class ResultParser:
    """结果解析器"""

    def __init__(self, case_dir: str):
        self.case_dir = Path(case_dir)

    def parse(self, foam_results: Dict[str, Any]) -> SimulationResult:
        """解析foamlib返回的结果"""
        result = SimulationResult(status="success")

        if "temperature" in foam_results:
            temp_data = foam_results["temperature"]
            result.max_temperature = temp_data.get("max")
            result.min_temperature = temp_data.get("min")
            result.avg_temperature = temp_data.get("average")

        if "pressure" in foam_results:
            pressure_data = foam_results["pressure"]
            result.pressure_drop = pressure_data.get("max") - pressure_data.get(
                "min", 0
            )

        if "velocity" in foam_results:
            result.max_velocity = foam_results["velocity"].get("max")

        result.heat_transfer_coefficient = self._calculate_heat_transfer_coefficient(
            result
        )

        return result

    def _calculate_heat_transfer_coefficient(
        self, result: SimulationResult
    ) -> Optional[float]:
        """计算平均换热系数"""
        if result.avg_temperature is None or result.max_temperature is None:
            return None

        delta_t = result.max_temperature - result.avg_temperature

        if delta_t <= 0:
            return None

        q = 10000

        h = q / delta_t

        return round(h, 2)


class ResultVisualizer:
    """结果可视化器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def check_availability(self) -> bool:
        """检查可视化库是否可用"""
        try:
            import matplotlib

            return True
        except ImportError:
            return False

    def plot_temperature_distribution(self, result: SimulationResult) -> Optional[str]:
        """绘制温度分布图"""
        if not self.check_availability():
            print("警告: matplotlib未安装，跳过可视化")
            return None

        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(10, 6))

        categories = ["Min", "Average", "Max"]
        temperatures = [
            result.min_temperature or 0,
            result.avg_temperature or 0,
            result.max_temperature or 0,
        ]

        bars = ax.bar(categories, temperatures, color=["blue", "green", "red"])

        ax.set_ylabel("Temperature (°C)")
        ax.set_title("Temperature Distribution")

        for bar, temp in zip(bars, temperatures):
            height = bar.get_height()
            ax.annotate(
                f"{temp:.1f}°C",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
            )

        plt.tight_layout()

        filepath = self.output_dir / "temperature_distribution.png"
        plt.savefig(filepath)
        plt.close()

        return str(filepath)

    def plot_summary(self, result: SimulationResult) -> Optional[str]:
        """绘制结果汇总图"""
        if not self.check_availability():
            return None

        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        metrics = {
            "Temperature (°C)": [
                result.min_temperature or 0,
                result.avg_temperature or 0,
                result.max_temperature or 0,
            ],
            "Pressure Drop (Pa)": [result.pressure_drop or 0],
            "Velocity (m/s)": [result.max_velocity or 0],
            "Heat Transfer Coeff (W/m²·K)": [result.heat_transfer_coefficient or 0],
        }

        for ax, (title, values) in zip(axes.flat, metrics.items()):
            ax.bar(range(len(values)), values, color="steelblue")
            ax.set_title(title)
            ax.set_xticks(range(len(values)))
            if len(values) == 1:
                ax.set_xticklabels(["Value"])
            else:
                ax.set_xticklabels(["Min", "Avg", "Max"][: len(values)])

        plt.tight_layout()

        filepath = self.output_dir / "simulation_summary.png"
        plt.savefig(filepath)
        plt.close()

        return str(filepath)

    def generate_report(self, result: SimulationResult) -> str:
        """生成文本报告"""
        def fmt_val(val, fmt=".2f"):
            if val is None:
                return "N/A"
            return f"{val:{fmt}}"
        
        report = f"""
========================================
换热器设计仿真结果报告
========================================

状态: {result.status.upper()}

温度分布:
  - 最低温度: {fmt_val(result.min_temperature)} °C
  - 平均温度: {fmt_val(result.avg_temperature)} °C
  - 最高温度: {fmt_val(result.max_temperature)} °C

流动特性:
  - 压降: {fmt_val(result.pressure_drop)} Pa
  - 最大速度: {fmt_val(result.max_velocity)} m/s

换热性能:
  - 换热系数: {fmt_val(result.heat_transfer_coefficient)} W/m²·K

{"=" * 40}
"""

        if result.execution_time:
            report += f"仿真时间: {result.execution_time:.2f} 秒\n"

        return report


def process_results(
    case_dir: str, foam_results: Dict[str, Any], output_dir: str = "output"
) -> SimulationResult:
    """处理仿真结果的主函数"""
    parser = ResultParser(case_dir)
    result = parser.parse(foam_results)

    visualizer = ResultVisualizer(output_dir)

    temp_plot = visualizer.plot_temperature_distribution(result)
    if temp_plot:
        print(f"温度分布图已保存: {temp_plot}")

    summary_plot = visualizer.plot_summary(result)
    if summary_plot:
        print(f"汇总图已保存: {summary_plot}")

    report = visualizer.generate_report(result)
    try:
        print(report)
    except UnicodeEncodeError:
        print("[报告已保存到文件]")
    
    report_path = Path(output_dir) / "report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"报告已保存: {report_path}")

    return result


if __name__ == "__main__":
    test_result = SimulationResult(
        status="success",
        max_temperature=45.5,
        min_temperature=30.0,
        avg_temperature=35.2,
        pressure_drop=120.5,
        max_velocity=2.0,
        heat_transfer_coefficient=850.0,
    )

    visualizer = ResultVisualizer()
    print(visualizer.generate_report(test_result))
