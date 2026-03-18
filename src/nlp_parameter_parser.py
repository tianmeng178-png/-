"""
自然语言参数解析模块
用于从用户描述中提取微通道散热器设计参数
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MicrochannelParameters:
    """微通道散热器设计参数"""
    # 几何参数
    channel_width: float = 0.1e-3  # 通道宽度 [m]
    channel_height: float = 0.5e-3  # 通道高度 [m]
    channel_length: float = 0.01  # 通道长度 [m]
    channel_count: int = 10  # 通道数量
    wall_thickness: float = 0.05e-3  # 壁厚 [m]
    
    # 流动参数
    inlet_velocity: float = 0.1  # 入口速度 [m/s]
    inlet_temperature: float = 293.15  # 入口温度 [K]
    outlet_pressure: float = 0.0  # 出口压力 [Pa]
    
    # 热参数
    heat_flux: float = 10000  # 热通量 [W/m²]
    base_temperature: float = 353.15  # 基底温度 [K]
    
    # 材料参数
    fluid_type: str = "water"  # 流体类型
    solid_material: str = "copper"  # 固体材料
    
    # 求解参数
    mesh_resolution: int = 20  # 网格分辨率
    convergence_criteria: float = 1e-6  # 收敛标准


class NaturalLanguageParser:
    """自然语言参数解析器"""
    
    def __init__(self):
        self.parameters = MicrochannelParameters()
        self.fluid_properties = self._load_fluid_properties()
        self.solid_properties = self._load_solid_properties()
    
    def _load_fluid_properties(self) -> Dict[str, Dict[str, float]]:
        """加载流体物性参数"""
        return {
            "water": {
                "density": 998.2,  # 密度 [kg/m³]
                "viscosity": 0.001,  # 粘度 [Pa·s]
                "specific_heat": 4186,  # 比热容 [J/kg·K]
                "thermal_conductivity": 0.6  # 导热系数 [W/m·K]
            },
            "air": {
                "density": 1.225,
                "viscosity": 1.8e-5,
                "specific_heat": 1005,
                "thermal_conductivity": 0.024
            }
        }
    
    def _load_solid_properties(self) -> Dict[str, Dict[str, float]]:
        """加载固体材料物性参数"""
        return {
            "copper": {
                "density": 8960,
                "thermal_conductivity": 401,
                "specific_heat": 385
            },
            "aluminum": {
                "density": 2700,
                "thermal_conductivity": 237,
                "specific_heat": 897
            },
            "silicon": {
                "density": 2330,
                "thermal_conductivity": 149,
                "specific_heat": 705
            }
        }
    
    def parse_user_description(self, description: str) -> Dict[str, Any]:
        """
        解析用户描述，提取设计参数
        
        Args:
            description: 用户描述文本
            
        Returns:
            解析后的参数字典
        """
        print(f"解析用户描述: {description}")
        
        # 重置参数
        self.parameters = MicrochannelParameters()
        
        # 提取关键参数
        self._extract_geometric_parameters(description)
        self._extract_flow_parameters(description)
        self._extract_thermal_parameters(description)
        self._extract_material_parameters(description)
        
        # 验证参数合理性
        self._validate_parameters()
        
        return self._format_output()
    
    def _extract_geometric_parameters(self, description: str):
        """提取几何参数"""
        # 通道宽度
        width_patterns = [
            r'(?:通道|微通道)[\s\S]*?(?:宽度|尺寸)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:毫米|mm|微米|μm)',
            r'(?:width|channel width)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:mm|μm)'
        ]
        
        for pattern in width_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 'μm' in description.lower() or '微米' in description:
                    self.parameters.channel_width = value * 1e-6
                else:
                    self.parameters.channel_width = value * 1e-3
                break
        
        # 通道高度
        height_patterns = [
            r'(?:通道|微通道)[\s\S]*?(?:高度|深度)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:毫米|mm|微米|μm)',
            r'(?:height|channel height)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:mm|μm)'
        ]
        
        for pattern in height_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 'μm' in description.lower() or '微米' in description:
                    self.parameters.channel_height = value * 1e-6
                else:
                    self.parameters.channel_height = value * 1e-3
                break
        
        # 通道数量
        count_patterns = [
            r'(?:通道|微通道)[\s\S]*?(?:数量|个数)[\s\S]*?(\d+)',
            r'(?:channel count|number of channels)[\s\S]*?(\d+)'
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                self.parameters.channel_count = int(match.group(1))
                break
    
    def _extract_flow_parameters(self, description: str):
        """提取流动参数"""
        # 入口速度
        velocity_patterns = [
            r'(?:速度|流速)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:米/秒|m/s)',
            r'(?:velocity|flow velocity)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:m/s)'
        ]
        
        for pattern in velocity_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                self.parameters.inlet_velocity = float(match.group(1))
                break
        
        # 入口温度
        temp_patterns = [
            r'(?:温度|入口温度)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:摄氏度|°C|K)',
            r'(?:temperature|inlet temperature)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:°C|K)'
        ]
        
        for pattern in temp_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if '°C' in description or '摄氏度' in description:
                    self.parameters.inlet_temperature = value + 273.15
                else:
                    self.parameters.inlet_temperature = value
                break
    
    def _extract_thermal_parameters(self, description: str):
        """提取热参数"""
        # 热通量
        flux_patterns = [
            r'(?:热通量|热负荷)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:W/m²|W/cm²)',
            r'(?:heat flux|thermal load)[\s\S]*?(\d+(?:\.\d+)?)[\s\S]*?(?:W/m²|W/cm²)'
        ]
        
        for pattern in flux_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 'W/cm²' in description:
                    self.parameters.heat_flux = value * 10000  # 转换为W/m²
                else:
                    self.parameters.heat_flux = value
                break
    
    def _extract_material_parameters(self, description: str):
        """提取材料参数"""
        # 流体类型
        if '空气' in description or 'air' in description.lower():
            self.parameters.fluid_type = "air"
        elif '水' in description or 'water' in description.lower():
            self.parameters.fluid_type = "water"
        
        # 固体材料
        if '铜' in description or 'copper' in description.lower():
            self.parameters.solid_material = "copper"
        elif '铝' in description or 'aluminum' in description.lower():
            self.parameters.solid_material = "aluminum"
        elif '硅' in description or 'silicon' in description.lower():
            self.parameters.solid_material = "silicon"
    
    def _validate_parameters(self):
        """验证参数合理性"""
        # 几何参数验证
        if self.parameters.channel_width < 0.01e-3:  # 最小10微米
            self.parameters.channel_width = 0.1e-3
        if self.parameters.channel_height < 0.01e-3:
            self.parameters.channel_height = 0.5e-3
        if self.parameters.channel_count < 1:
            self.parameters.channel_count = 10
        
        # 流动参数验证
        if self.parameters.inlet_velocity <= 0:
            self.parameters.inlet_velocity = 0.1
        if self.parameters.inlet_temperature < 273.15:  # 最低0°C
            self.parameters.inlet_temperature = 293.15
        
        # 热参数验证
        if self.parameters.heat_flux <= 0:
            self.parameters.heat_flux = 10000
        if self.parameters.base_temperature < 273.15:
            self.parameters.base_temperature = 353.15
    
    def _format_output(self) -> Dict[str, Any]:
        """格式化输出结果"""
        return {
            "status": "success",
            "parameters": {
                "geometry": {
                    "channel_width": self.parameters.channel_width,
                    "channel_height": self.parameters.channel_height,
                    "channel_length": self.parameters.channel_length,
                    "channel_count": self.parameters.channel_count,
                    "wall_thickness": self.parameters.wall_thickness
                },
                "flow": {
                    "inlet_velocity": self.parameters.inlet_velocity,
                    "inlet_temperature": self.parameters.inlet_temperature,
                    "outlet_pressure": self.parameters.outlet_pressure
                },
                "thermal": {
                    "heat_flux": self.parameters.heat_flux,
                    "base_temperature": self.parameters.base_temperature
                },
                "materials": {
                    "fluid_type": self.parameters.fluid_type,
                    "solid_material": self.parameters.solid_material
                },
                "solver": {
                    "mesh_resolution": self.parameters.mesh_resolution,
                    "convergence_criteria": self.parameters.convergence_criteria
                }
            },
            "fluid_properties": self.fluid_properties.get(self.parameters.fluid_type, {}),
            "solid_properties": self.solid_properties.get(self.parameters.solid_material, {})
        }


def test_nlp_parser():
    """测试自然语言解析器"""
    parser = NaturalLanguageParser()
    
    # 测试用例
    test_descriptions = [
        "设计一个微通道散热器，通道宽度100微米，高度500微米，数量20个，入口速度0.2m/s，入口温度25°C，热通量50W/cm²，使用水冷却，铜材料",
        "微通道散热器设计：通道尺寸200μm×300μm，数量15个，流速0.15m/s，温度30°C，热负荷30W/cm²，空气冷却，铝基板",
        "我需要一个散热器，通道宽度150微米，高度400微米，数量25个，速度0.1m/s，温度20°C，热通量40W/cm²"
    ]
    
    for i, description in enumerate(test_descriptions, 1):
        print(f"\n=== 测试用例 {i} ===")
        result = parser.parse_user_description(description)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_nlp_parser()