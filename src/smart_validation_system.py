"""
智能验证系统
基于工程约束数据库的多级验证机制
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from parameter_constraints import EngineeringConstraints


@dataclass
class ValidationResult:
    """验证结果"""
    overall_status: str  # 'valid', 'warning', 'error'
    parameter_validations: Dict[str, Dict[str, Any]]
    relationship_validations: Dict[str, Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    safety_assessment: Dict[str, Any]
    performance_estimation: Dict[str, Any]


@dataclass
class SafetyAssessment:
    """安全性评估"""
    status: str  # 'safe', 'warning', 'danger'
    extreme_conditions: List[Dict[str, Any]]
    material_compatibility: List[Dict[str, Any]]
    operational_limits: List[Dict[str, Any]]
    recommendations: List[str]


@dataclass
class PerformanceEstimation:
    """性能预估"""
    expected_temperature_rise: float
    expected_pressure_drop: float
    expected_heat_transfer_coefficient: float
    confidence_level: float  # 0-1
    potential_issues: List[str]


class SmartValidationSystem:
    """智能验证系统"""
    
    def __init__(self):
        self.constraints = EngineeringConstraints()
    
    def validate_parameters(self, parameters: Dict[str, float]) -> ValidationResult:
        """全面验证参数"""
        print("🔍 开始智能参数验证...")
        
        # 1. 参数范围验证
        parameter_validations = self._validate_parameter_ranges(parameters)
        
        # 2. 参数关联验证
        relationship_validations = self.constraints.validate_all_relationships(parameters)
        
        # 3. 安全性评估
        safety_assessment = self._assess_safety(parameters)
        
        # 4. 性能预估
        performance_estimation = self._estimate_performance(parameters)
        
        # 5. 生成优化建议
        suggestions = self._generate_suggestions(parameter_validations, relationship_validations)
        
        # 6. 确定总体状态
        overall_status = self._determine_overall_status(
            parameter_validations, relationship_validations, safety_assessment
        )
        
        return ValidationResult(
            overall_status=overall_status,
            parameter_validations=parameter_validations,
            relationship_validations=relationship_validations,
            suggestions=suggestions,
            safety_assessment=safety_assessment,
            performance_estimation=performance_estimation
        )
    
    def _validate_parameter_ranges(self, parameters: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """验证参数范围"""
        validations = {}
        
        # 按参数类别验证
        categories = self.constraints.get_all_constraints()
        
        for category, constraints in categories.items():
            for param_name, constraint in constraints.items():
                if param_name in parameters:
                    validation = constraint.validate(parameters[param_name])
                    validations[param_name] = {
                        'category': category,
                        'validation': validation,
                        'constraint_info': {
                            'min': constraint.min_value,
                            'max': constraint.max_value,
                            'recommended': constraint.recommended_range,
                            'unit': constraint.unit
                        }
                    }
        
        return validations
    
    def _assess_safety(self, parameters: Dict[str, float]) -> Dict[str, Any]:
        """安全性评估"""
        extreme_conditions = []
        material_compatibility = []
        operational_limits = []
        recommendations = []
        
        # 检查极端条件
        if parameters.get('heat_flux', 0) > 1000000:  # 100 W/cm²
            extreme_conditions.append({
                'type': 'high_heat_flux',
                'message': '热通量较高，可能存在热管理挑战',
                'severity': 'warning'
            })
            recommendations.append('建议热通量不超过50 W/cm²')
        
        if parameters.get('inlet_velocity', 0) > 3.0:  # 3 m/s
            extreme_conditions.append({
                'type': 'high_velocity',
                'message': '流速较高，可能导致过大压力损失',
                'severity': 'warning'
            })
            recommendations.append('建议流速不超过1 m/s')
        
        # 检查材料兼容性
        if parameters.get('base_temperature', 293.15) > 423.15:  # 150°C
            material_compatibility.append({
                'type': 'high_temperature',
                'message': '基底温度较高，需确保材料耐热性',
                'severity': 'warning'
            })
            recommendations.append('建议使用高温材料')
        
        # 检查操作限制
        if parameters.get('channel_width', 0) < 80e-6:  # 80微米
            operational_limits.append({
                'type': 'small_channel',
                'message': '通道尺寸较小，可能存在制造困难',
                'severity': 'warning'
            })
            recommendations.append('建议通道宽度不小于100微米')
        
        # 确定总体安全状态
        if any(cond['severity'] == 'danger' for cond in extreme_conditions + material_compatibility + operational_limits):
            status = 'danger'
        elif any(cond['severity'] == 'warning' for cond in extreme_conditions + material_compatibility + operational_limits):
            status = 'warning'
        else:
            status = 'safe'
        
        return {
            'status': status,
            'extreme_conditions': extreme_conditions,
            'material_compatibility': material_compatibility,
            'operational_limits': operational_limits,
            'recommendations': recommendations
        }
    
    def _estimate_performance(self, parameters: Dict[str, float]) -> Dict[str, Any]:
        """性能预估"""
        # 基于经验公式进行性能预估
        
        # 估算温升 (简化模型)
        heat_flux = parameters.get('heat_flux', 100000)  # W/m²
        velocity = parameters.get('inlet_velocity', 0.1)  # m/s
        channel_width = parameters.get('channel_width', 200e-6)  # m
        channel_height = parameters.get('channel_height', 400e-6)  # m
        
        # 水力直径
        if channel_width + channel_height > 0:
            hydraulic_diameter = 2 * channel_width * channel_height / (channel_width + channel_height)
        else:
            hydraulic_diameter = 0
        
        # 简化温升估算
        if velocity > 0 and hydraulic_diameter > 0:
            temperature_rise = heat_flux / (1000 * velocity * hydraulic_diameter * 1000)  # 简化公式
        else:
            temperature_rise = 50  # 默认值
        
        # 压力降估算 (简化模型)
        viscosity = parameters.get('fluid_viscosity', 0.001)  # Pa·s
        channel_length = parameters.get('channel_length', 0.01)  # m
        
        if hydraulic_diameter > 0:
            pressure_drop = (32 * viscosity * velocity * channel_length) / (hydraulic_diameter ** 2)
        else:
            pressure_drop = 1000  # 默认值
        
        # 传热系数估算
        if hydraulic_diameter > 0:
            heat_transfer_coefficient = 1000 + 500 * velocity / hydraulic_diameter  # 简化公式
        else:
            heat_transfer_coefficient = 2000  # 默认值
        
        # 置信度评估
        confidence_level = self._calculate_confidence(parameters)
        
        # 潜在问题识别
        potential_issues = []
        if temperature_rise > 30:
            potential_issues.append('预计温升较高，可能需要优化散热设计')
        if pressure_drop > 10000:  # 10 kPa
            potential_issues.append('预计压力损失较大，可能需要降低流速')
        
        return {
            'expected_temperature_rise': max(1, min(100, temperature_rise)),
            'expected_pressure_drop': max(10, min(50000, pressure_drop)),
            'expected_heat_transfer_coefficient': max(500, min(10000, heat_transfer_coefficient)),
            'confidence_level': confidence_level,
            'potential_issues': potential_issues
        }
    
    def _calculate_confidence(self, parameters: Dict[str, float]) -> float:
        """计算预估置信度"""
        confidence = 0.7  # 基础置信度
        
        # 基于参数完整性调整置信度
        required_params = ['channel_width', 'channel_height', 'inlet_velocity', 'heat_flux']
        provided_count = sum(1 for param in required_params if param in parameters)
        
        # 参数完整性贡献
        completeness_ratio = provided_count / len(required_params)
        confidence += 0.2 * completeness_ratio
        
        # 参数合理性贡献
        validations = self._validate_parameter_ranges(parameters)
        optimal_count = sum(1 for val in validations.values() 
                           if val['validation']['status'] == 'optimal')
        
        if validations:
            optimal_ratio = optimal_count / len(validations)
            confidence += 0.1 * optimal_ratio
        
        return min(0.95, max(0.3, confidence))
    
    def _generate_suggestions(self, 
                            parameter_validations: Dict[str, Dict[str, Any]], 
                            relationship_validations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []
        
        # 参数优化建议
        for param_name, validation_info in parameter_validations.items():
            validation = validation_info['validation']
            if validation['status'] in ['warning', 'error']:
                suggestions.append({
                    'type': 'parameter_optimization',
                    'parameter': param_name,
                    'category': validation_info['category'],
                    'current_value': validation.get('current_value', '未知'),
                    'issue': validation['message'],
                    'suggestion': validation['suggestion'],
                    'priority': 'high' if validation['status'] == 'error' else 'medium'
                })
        
        # 关联关系优化建议
        for rel_name, validation in relationship_validations.items():
            if validation['status'] in ['warning', 'error']:
                suggestions.append({
                    'type': 'relationship_optimization',
                    'relationship': rel_name,
                    'issue': validation['message'],
                    'suggestion': validation['suggestion'],
                    'priority': 'high' if validation['status'] == 'error' else 'medium'
                })
        
        return suggestions
    
    def _determine_overall_status(self, 
                                parameter_validations: Dict[str, Dict[str, Any]],
                                relationship_validations: Dict[str, Dict[str, Any]],
                                safety_assessment: Dict[str, Any]) -> str:
        """确定总体验证状态"""
        
        # 检查是否有错误
        has_errors = any(
            val['validation']['status'] == 'error' 
            for val in parameter_validations.values()
        ) or any(
            val['status'] == 'error' 
            for val in relationship_validations.values()
        ) or safety_assessment['status'] == 'danger'
        
        # 检查是否有警告
        has_warnings = any(
            val['validation']['status'] == 'warning' 
            for val in parameter_validations.values()
        ) or any(
            val['status'] == 'warning' 
            for val in relationship_validations.values()
        ) or safety_assessment['status'] == 'warning'
        
        if has_errors:
            return 'error'
        elif has_warnings:
            return 'warning'
        else:
            return 'valid'
    
    def get_validation_summary(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """获取验证摘要"""
        total_parameters = len(validation_result.parameter_validations)
        optimal_parameters = sum(
            1 for val in validation_result.parameter_validations.values()
            if val['validation']['status'] == 'optimal'
        )
        
        return {
            'overall_status': validation_result.overall_status,
            'parameter_summary': {
                'total': total_parameters,
                'optimal': optimal_parameters,
                'warning': sum(1 for val in validation_result.parameter_validations.values() 
                              if val['validation']['status'] == 'warning'),
                'error': sum(1 for val in validation_result.parameter_validations.values() 
                            if val['validation']['status'] == 'error')
            },
            'relationship_summary': {
                'total': len(validation_result.relationship_validations),
                'optimal': sum(1 for val in validation_result.relationship_validations.values() 
                              if val['status'] == 'optimal'),
                'warning': sum(1 for val in validation_result.relationship_validations.values() 
                              if val['status'] == 'warning'),
                'error': sum(1 for val in validation_result.relationship_validations.values() 
                            if val['status'] == 'error')
            },
            'safety_status': validation_result.safety_assessment['status'],
            'suggestion_count': len(validation_result.suggestions)
        }


def test_smart_validation():
    """测试智能验证系统"""
    print("🧪 测试智能验证系统...")
    
    validator = SmartValidationSystem()
    
    # 测试用例1：合理参数
    print("\n📋 测试用例1：合理参数")
    reasonable_params = {
        'channel_width': 150e-6,
        'channel_height': 400e-6,
        'channel_length': 0.01,
        'channel_count': 20,
        'inlet_velocity': 0.25,
        'inlet_temperature': 303.15,
        'heat_flux': 200000,
        'base_temperature': 343.15,
        'fluid_viscosity': 0.001,
        'fluid_density': 1000
    }
    
    result1 = validator.validate_parameters(reasonable_params)
    summary1 = validator.get_validation_summary(result1)
    print(f"总体状态: {summary1['overall_status']}")
    print(f"参数验证: {summary1['parameter_summary']['optimal']}/{summary1['parameter_summary']['total']} 个参数最优")
    print(f"安全性: {summary1['safety_status']}")
    print(f"建议数量: {summary1['suggestion_count']}")
    
    # 测试用例2：问题参数
    print("\n📋 测试用例2：问题参数")
    problematic_params = {
        'channel_width': 20e-6,      # 过小
        'channel_height': 3000e-6,   # 过大
        'inlet_velocity': 0.001,     # 过小
        'heat_flux': 2000000,        # 过大
    }
    
    result2 = validator.validate_parameters(problematic_params)
    summary2 = validator.get_validation_summary(result2)
    print(f"总体状态: {summary2['overall_status']}")
    print(f"参数验证: {summary2['parameter_summary']}")
    print(f"安全性: {summary2['safety_status']}")
    print(f"建议数量: {summary2['suggestion_count']}")
    
    # 显示具体建议
    if result2.suggestions:
        print("\n💡 优化建议:")
        for i, suggestion in enumerate(result2.suggestions[:3], 1):
            print(f"{i}. {suggestion['issue']}")
            print(f"   建议: {suggestion['suggestion']}")
    
    # 显示性能预估
    print("\n📊 性能预估:")
    perf = result1.performance_estimation
    print(f"预计温升: {perf['expected_temperature_rise']:.1f}°C")
    print(f"预计压力降: {perf['expected_pressure_drop']:.1f} Pa")
    print(f"预计传热系数: {perf['expected_heat_transfer_coefficient']:.0f} W/m²·K")
    print(f"置信度: {perf['confidence_level']:.1%}")
    
    print("✅ 智能验证系统测试完成!")


if __name__ == "__main__":
    test_smart_validation()