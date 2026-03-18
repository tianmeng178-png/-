"""
参数计算器 - 用于计算衍生参数和工程参数
"""
import math
from typing import Dict, Any


class ParameterCalculator:
    """参数计算器"""
    
    @staticmethod
    def calculate_hydraulic_diameter(width: float, height: float) -> float:
        """计算水力直径"""
        if width <= 0 or height <= 0:
            raise ValueError("通道宽度和高度必须大于0")
        
        # 矩形通道的水力直径公式: 4 * 面积 / 周长
        area = width * height
        perimeter = 2 * (width + height)
        
        return 4 * area / perimeter
    
    @staticmethod
    def calculate_reynolds_number(velocity: float, hydraulic_diameter: float, 
                                 density: float, viscosity: float) -> float:
        """计算雷诺数"""
        if hydraulic_diameter <= 0 or viscosity <= 0:
            raise ValueError("水力直径和粘度必须大于0")
        
        return (velocity * hydraulic_diameter * density) / viscosity
    
    @staticmethod
    def calculate_nusselt_number(reynolds_number: float, prandtl_number: float) -> float:
        """计算努塞尔数（简化公式）"""
        # 层流条件下的简化公式
        if reynolds_number < 2300:
            return 3.66  # 恒温壁面层流
        else:
            # 湍流条件下的简化公式
            return 0.023 * (reynolds_number ** 0.8) * (prandtl_number ** 0.4)
    
    @staticmethod
    def calculate_heat_transfer_coefficient(nusselt_number: float, 
                                          thermal_conductivity: float,
                                          hydraulic_diameter: float) -> float:
        """计算传热系数"""
        if hydraulic_diameter <= 0:
            raise ValueError("水力直径必须大于0")
        
        return (nusselt_number * thermal_conductivity) / hydraulic_diameter
    
    @staticmethod
    def get_fluid_properties(fluid_type: str, temperature: float) -> Dict[str, float]:
        """获取流体物性参数"""
        # 简化物性参数（实际应用中应从数据库获取）
        if fluid_type.lower() == "water":
            # 水的物性参数（300K）
            return {
                "density": 997.0,  # kg/m³
                "viscosity": 0.000855,  # Pa·s
                "thermal_conductivity": 0.613,  # W/(m·K)
                "specific_heat": 4182.0,  # J/(kg·K)
                "prandtl_number": 5.83
            }
        elif fluid_type.lower() == "air":
            # 空气的物性参数（300K）
            return {
                "density": 1.177,  # kg/m³
                "viscosity": 0.0000186,  # Pa·s
                "thermal_conductivity": 0.0263,  # W/(m·K)
                "specific_heat": 1005.0,  # J/(kg·K)
                "prandtl_number": 0.707
            }
        else:
            # 默认值（水）
            return {
                "density": 997.0,
                "viscosity": 0.000855,
                "thermal_conductivity": 0.613,
                "specific_heat": 4182.0,
                "prandtl_number": 5.83
            }
    
    @staticmethod
    def get_material_properties(material_type: str) -> Dict[str, float]:
        """获取材料物性参数"""
        if material_type.lower() == "copper":
            return {
                "thermal_conductivity": 401.0,  # W/(m·K)
                "density": 8960.0,  # kg/m³
                "specific_heat": 385.0  # J/(kg·K)
            }
        elif material_type.lower() == "aluminum":
            return {
                "thermal_conductivity": 237.0,
                "density": 2700.0,
                "specific_heat": 903.0
            }
        elif material_type.lower() == "silicon":
            return {
                "thermal_conductivity": 149.0,
                "density": 2330.0,
                "specific_heat": 705.0
            }
        else:
            # 默认值（铝）
            return {
                "thermal_conductivity": 237.0,
                "density": 2700.0,
                "specific_heat": 903.0
            }
    
    @staticmethod
    def calculate_derived_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算所有衍生参数"""
        derived = {}
        
        try:
            # 计算水力直径
            width = parameters.get('channel_width', 0)
            height = parameters.get('channel_height', 0)
            if width > 0 and height > 0:
                derived['hydraulic_diameter'] = ParameterCalculator.calculate_hydraulic_diameter(width, height)
            
            # 获取流体物性
            fluid_type = parameters.get('fluid_type', 'water')
            temperature = parameters.get('inlet_temperature', 300.0)
            fluid_props = ParameterCalculator.get_fluid_properties(fluid_type, temperature)
            derived.update(fluid_props)
            
            # 获取材料物性
            material_type = parameters.get('solid_material', 'aluminum')
            material_props = ParameterCalculator.get_material_properties(material_type)
            derived.update(material_props)
            
            # 计算雷诺数
            velocity = parameters.get('inlet_velocity', 0)
            if 'hydraulic_diameter' in derived:
                reynolds = ParameterCalculator.calculate_reynolds_number(
                    velocity, derived['hydraulic_diameter'], 
                    derived['density'], derived['viscosity']
                )
                derived['reynolds_number'] = reynolds
            
            # 计算努塞尔数
            if 'reynolds_number' in derived:
                nusselt = ParameterCalculator.calculate_nusselt_number(
                    derived['reynolds_number'], derived['prandtl_number']
                )
                derived['nusselt_number'] = nusselt
            
            # 计算传热系数
            if 'hydraulic_diameter' in derived and 'nusselt_number' in derived:
                htc = ParameterCalculator.calculate_heat_transfer_coefficient(
                    derived['nusselt_number'], derived['thermal_conductivity'],
                    derived['hydraulic_diameter']
                )
                derived['heat_transfer_coefficient'] = htc
            
            # 计算通道总面积
            if all(k in parameters for k in ['channel_width', 'channel_height', 'channel_count', 'channel_length']):
                single_area = parameters['channel_width'] * parameters['channel_height']
                total_area = single_area * parameters['channel_count']
                derived['total_flow_area'] = total_area
                
                # 计算总热交换面积
                perimeter = 2 * (parameters['channel_width'] + parameters['channel_height'])
                heat_exchange_area = perimeter * parameters['channel_length'] * parameters['channel_count']
                derived['heat_exchange_area'] = heat_exchange_area
            
            return derived
            
        except Exception as e:
            print(f"参数计算错误: {e}")
            return {}
    
    @staticmethod
    def validate_engineering_constraints(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证工程约束条件"""
        warnings = []
        suggestions = []
        
        # 检查雷诺数范围
        reynolds = parameters.get('reynolds_number', 0)
        if reynolds < 500:
            warnings.append("雷诺数过低，可能影响计算精度")
            suggestions.append("建议增加流速或减小通道尺寸")
        elif reynolds > 10000:
            warnings.append("雷诺数过高，可能超出层流模型适用范围")
            suggestions.append("建议减小流速或增加通道尺寸")
        
        # 检查水力直径
        hydraulic_diameter = parameters.get('hydraulic_diameter', 0)
        if hydraulic_diameter < 1e-6:
            warnings.append("水力直径过小，可能影响制造可行性")
            suggestions.append("建议增加通道尺寸")
        
        # 检查传热系数
        htc = parameters.get('heat_transfer_coefficient', 0)
        if htc < 1000:
            warnings.append("传热系数较低，散热效果可能不理想")
            suggestions.append("建议优化通道几何形状或增加流速")
        
        return {
            'warnings': warnings,
            'suggestions': suggestions
        }