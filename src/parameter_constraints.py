"""
工程参数约束数据库
基于工程经验定义参数范围和关联约束
"""

from typing import Dict, Any, Tuple, List, Callable
from dataclasses import dataclass
import math


@dataclass
class ParameterConstraint:
    """参数约束定义"""
    name: str
    min_value: float
    max_value: float
    recommended_range: Tuple[float, float]
    unit: str
    description: str
    
    def validate(self, value: float) -> Dict[str, Any]:
        """验证参数值"""
        if value < self.min_value:
            return {
                "valid": False,
                "status": "error",
                "message": f"{self.name} ({value} {self.unit}) 低于最小值 {self.min_value} {self.unit}",
                "suggestion": f"建议增加到至少 {self.min_value} {self.unit}"
            }
        elif value > self.max_value:
            return {
                "valid": False,
                "status": "error", 
                "message": f"{self.name} ({value} {self.unit}) 超过最大值 {self.max_value} {self.unit}",
                "suggestion": f"建议降低到最多 {self.max_value} {self.unit}"
            }
        elif value < self.recommended_range[0]:
            return {
                "valid": True,
                "status": "warning",
                "message": f"{self.name} ({value} {self.unit}) 低于推荐范围",
                "suggestion": f"建议增加到 {self.recommended_range[0]} {self.unit} 以上"
            }
        elif value > self.recommended_range[1]:
            return {
                "valid": True,
                "status": "warning",
                "message": f"{self.name} ({value} {self.unit}) 高于推荐范围",
                "suggestion": f"建议降低到 {self.recommended_range[1]} {self.unit} 以下"
            }
        else:
            return {
                "valid": True,
                "status": "optimal",
                "message": f"{self.name} ({value} {self.unit}) 在推荐范围内",
                "suggestion": "参数设置合理"
            }


@dataclass
class ParameterRelationship:
    """参数关联关系定义"""
    name: str
    parameters: List[str]
    calculation: Callable
    constraint: Callable
    recommended_range: Tuple[float, float]
    description: str
    
    def validate(self, parameter_values: Dict[str, float]) -> Dict[str, Any]:
        """验证参数关联关系"""
        # 检查是否有所需参数
        missing_params = [p for p in self.parameters if p not in parameter_values]
        if missing_params:
            return {
                "valid": False,
                "status": "error",
                "message": f"缺少参数: {', '.join(missing_params)}",
                "suggestion": "请提供完整的参数信息"
            }
        
        # 计算关联参数值
        values = [parameter_values[p] for p in self.parameters]
        calculated_value = self.calculation(*values)
        
        # 验证约束
        if not self.constraint(calculated_value):
            return {
                "valid": False,
                "status": "error",
                "message": f"{self.name} ({calculated_value:.4f}) 违反约束条件",
                "suggestion": self.description
            }
        elif calculated_value < self.recommended_range[0]:
            return {
                "valid": True,
                "status": "warning",
                "message": f"{self.name} ({calculated_value:.4f}) 低于推荐范围",
                "suggestion": f"建议调整参数使其达到 {self.recommended_range[0]} 以上"
            }
        elif calculated_value > self.recommended_range[1]:
            return {
                "valid": True,
                "status": "warning",
                "message": f"{self.name} ({calculated_value:.4f}) 高于推荐范围",
                "suggestion": f"建议调整参数使其达到 {self.recommended_range[1]} 以下"
            }
        else:
            return {
                "valid": True,
                "status": "optimal",
                "message": f"{self.name} ({calculated_value:.4f}) 在推荐范围内",
                "suggestion": "参数关联关系合理"
            }


class EngineeringConstraints:
    """工程约束数据库"""
    
    def __init__(self):
        # 几何参数约束
        self.geometry_constraints = {
            'channel_width': ParameterConstraint(
                name='通道宽度',
                min_value=50e-6,      # 50微米
                max_value=1000e-6,    # 1毫米
                recommended_range=(100e-6, 500e-6),  # 100-500微米
                unit='m',
                description='微通道宽度约束，考虑制造可行性和流动特性'
            ),
            'channel_height': ParameterConstraint(
                name='通道高度',
                min_value=100e-6,     # 100微米
                max_value=2000e-6,    # 2毫米
                recommended_range=(200e-6, 800e-6),  # 200-800微米
                unit='m',
                description='微通道高度约束，考虑结构强度和散热效果'
            ),
            'channel_length': ParameterConstraint(
                name='通道长度',
                min_value=0.001,      # 1毫米
                max_value=0.1,        # 10厘米
                recommended_range=(0.005, 0.05),  # 5-50毫米
                unit='m',
                description='微通道长度约束，考虑压力损失和散热效率'
            ),
            'channel_count': ParameterConstraint(
                name='通道数量',
                min_value=1,
                max_value=100,
                recommended_range=(5, 30),  # 5-30个通道
                unit='个',
                description='通道数量约束，考虑制造复杂性和散热面积'
            )
        }
        
        # 流动参数约束
        self.flow_constraints = {
            'inlet_velocity': ParameterConstraint(
                name='入口速度',
                min_value=0.01,       # 0.01 m/s
                max_value=5.0,        # 5 m/s
                recommended_range=(0.1, 0.5),  # 0.1-0.5 m/s
                unit='m/s',
                description='入口速度约束，考虑流动状态和压力损失'
            ),
            'inlet_temperature': ParameterConstraint(
                name='入口温度',
                min_value=273.15,     # 0°C
                max_value=373.15,     # 100°C
                recommended_range=(293.15, 353.15),  # 20-80°C
                unit='K',
                description='入口温度约束，考虑流体物性和应用场景'
            )
        }
        
        # 热参数约束
        self.thermal_constraints = {
            'heat_flux': ParameterConstraint(
                name='热通量',
                min_value=1000,       # 0.1 W/cm²
                max_value=10000000,   # 100 W/cm²
                recommended_range=(100000, 500000),  # 10-50 W/cm²
                unit='W/m²',
                description='热通量约束，考虑散热能力和材料极限'
            ),
            'base_temperature': ParameterConstraint(
                name='基底温度',
                min_value=293.15,     # 20°C
                max_value=473.15,     # 200°C
                recommended_range=(323.15, 393.15),  # 50-120°C
                unit='K',
                description='基底温度约束，考虑电子设备工作温度'
            )
        }
        
        # 材料参数约束
        self.material_constraints = {
            'fluid_viscosity': ParameterConstraint(
                name='流体粘度',
                min_value=0.0001,     # 0.1 mPa·s
                max_value=0.1,        # 100 mPa·s
                recommended_range=(0.00089, 0.001),  # 水在20-30°C的粘度
                unit='Pa·s',
                description='流体粘度约束，考虑流动特性和泵送功率'
            ),
            'fluid_density': ParameterConstraint(
                name='流体密度',
                min_value=800,        # 轻质流体
                max_value=1200,       # 重质流体
                recommended_range=(997, 1000),  # 水在20-30°C的密度
                unit='kg/m³',
                description='流体密度约束，考虑流动惯性和热容量'
            )
        }
        
        # 参数关联关系
        self.parameter_relationships = {
            'aspect_ratio': ParameterRelationship(
            name='纵横比',
            parameters=['channel_width', 'channel_height'],
            calculation=lambda w, h: h / w if w > 0 else float('inf'),
            constraint=lambda ratio: 1 <= ratio <= 10,
            recommended_range=(2, 5),
            description='通道纵横比约束，考虑结构稳定性和流动特性'
        ),
            'hydraulic_diameter': ParameterRelationship(
            name='水力直径',
            parameters=['channel_width', 'channel_height'],
            calculation=lambda w, h: 2 * w * h / (w + h) if (w + h) > 0 else 0,
            constraint=lambda d: 50e-6 <= d <= 1000e-6,
            recommended_range=(100e-6, 500e-6),
            description='水力直径约束，影响流动阻力和传热效率'
        ),
            'reynolds_number': ParameterRelationship(
                name='雷诺数',
                parameters=['inlet_velocity', 'hydraulic_diameter', 'fluid_viscosity'],
                calculation=lambda v, d, mu: v * d * 1000 / mu,  # 假设水密度1000kg/m³
                constraint=lambda re: re < 4000,  # 确保层流或过渡流
                recommended_range=(100, 2000),
                description='雷诺数约束，确保流动状态在合理范围内'
            )
        }
    
    def get_all_constraints(self) -> Dict[str, Dict[str, ParameterConstraint]]:
        """获取所有约束"""
        return {
            'geometry': self.geometry_constraints,
            'flow': self.flow_constraints,
            'thermal': self.thermal_constraints,
            'materials': self.material_constraints
        }
    
    def get_recommended_ranges(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """获取所有参数的推荐范围"""
        ranges = {}
        
        for category, constraints in self.get_all_constraints().items():
            ranges[category] = {}
            for param_name, constraint in constraints.items():
                ranges[category][param_name] = constraint.recommended_range
        
        return ranges
    
    def validate_parameter(self, category: str, param_name: str, value: float) -> Dict[str, Any]:
        """验证单个参数"""
        constraints = self.get_all_constraints().get(category, {})
        if param_name not in constraints:
            return {
                "valid": False,
                "status": "error",
                "message": f"未知参数: {param_name}",
                "suggestion": "请检查参数名称"
            }
        
        return constraints[param_name].validate(value)
    
    def validate_relationship(self, relationship_name: str, parameter_values: Dict[str, float]) -> Dict[str, Any]:
        """验证参数关联关系"""
        if relationship_name not in self.parameter_relationships:
            return {
                "valid": False,
                "status": "error",
                "message": f"未知关联关系: {relationship_name}",
                "suggestion": "请检查关联关系名称"
            }
        
        return self.parameter_relationships[relationship_name].validate(parameter_values)
    
    def validate_all_relationships(self, parameter_values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """验证所有参数关联关系"""
        results = {}
        
        for rel_name, relationship in self.parameter_relationships.items():
            results[rel_name] = relationship.validate(parameter_values)
        
        return results
    
    def get_parameter_suggestions(self, current_values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """获取参数优化建议"""
        suggestions = {}
        
        # 验证所有参数
        for category, constraints in self.get_all_constraints().items():
            for param_name, constraint in constraints.items():
                if param_name in current_values:
                    validation = constraint.validate(current_values[param_name])
                    if validation["status"] in ["warning", "error"]:
                        suggestions[param_name] = {
                            "category": category,
                            "current_value": current_values[param_name],
                            "recommended_range": constraint.recommended_range,
                            "validation": validation
                        }
        
        # 验证关联关系
        relationship_results = self.validate_all_relationships(current_values)
        for rel_name, result in relationship_results.items():
            if result["status"] in ["warning", "error"]:
                suggestions[f"relationship_{rel_name}"] = {
                    "category": "relationship",
                    "relationship": rel_name,
                    "validation": result
                }
        
        return suggestions


def test_constraints():
    """测试约束系统"""
    print("🧪 测试工程约束数据库...")
    
    constraints = EngineeringConstraints()
    
    # 测试参数验证
    test_cases = [
        ("geometry", "channel_width", 50e-6),   # 最小值
        ("geometry", "channel_width", 300e-6),  # 推荐值
        ("geometry", "channel_width", 2000e-6), # 超过最大值
        ("flow", "inlet_velocity", 0.001),      # 低于最小值
        ("flow", "inlet_velocity", 0.3),        # 推荐值
    ]
    
    for category, param, value in test_cases:
        result = constraints.validate_parameter(category, param, value)
        print(f"{category}.{param} = {value}: {result['status']} - {result['message']}")
    
    # 测试关联关系验证
    test_params = {
        'channel_width': 150e-6,
        'channel_height': 400e-6,
        'inlet_velocity': 0.25,
        'fluid_viscosity': 0.001
    }
    
    relationship_results = constraints.validate_all_relationships(test_params)
    for rel_name, result in relationship_results.items():
        print(f"{rel_name}: {result['status']} - {result['message']}")
    
    # 测试建议生成
    suggestions = constraints.get_parameter_suggestions(test_params)
    print(f"\n生成 {len(suggestions)} 条优化建议")
    
    print("✅ 工程约束数据库测试完成!")


if __name__ == "__main__":
    test_constraints()