"""
数据模型转换器 - 解决前端和后端数据模型不匹配问题
"""
from typing import Dict, Any
from models.simulation import SimulationParameters, SimulationStatus, PerformanceMetrics


class DataConverter:
    """数据模型转换器"""
    
    @staticmethod
    def frontend_to_backend_parameters(frontend_params: Dict[str, Any]) -> SimulationParameters:
        """将前端参数转换为后端参数模型"""
        # 字段映射
        mapping = {
            'solid_material': 'material_type'
        }
        
        # 转换字段名
        backend_params = {}
        for key, value in frontend_params.items():
            backend_key = mapping.get(key, key)
            backend_params[backend_key] = value
        
        # 处理枚举类型
        if 'fluid_type' in backend_params:
            backend_params['fluid_type'] = backend_params['fluid_type'].upper()
        
        if 'material_type' in backend_params:
            backend_params['material_type'] = backend_params['material_type'].upper()
        
        # 添加默认值
        defaults = {
            'simulation_mode': 'mock',
            'mesh_resolution': 0.001,
            'max_iterations': 1000,
            'convergence_criteria': 1e-6
        }
        
        for key, value in defaults.items():
            if key not in backend_params:
                backend_params[key] = value
        
        return SimulationParameters(**backend_params)
    
    @staticmethod
    def backend_to_frontend_status(backend_status: SimulationStatus) -> Dict[str, Any]:
        """将后端状态转换为前端状态格式"""
        return {
            'status': backend_status.status.value,
            'progress': backend_status.progress,
            'current_step': backend_status.current_step,
            'estimated_time_remaining': backend_status.estimated_time_remaining,
            'log_messages': backend_status.log_messages
        }
    
    @staticmethod
    def backend_to_frontend_metrics(backend_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """将后端性能指标转换为前端格式"""
        return {
            'max_temperature': backend_metrics.max_temperature,
            'min_temperature': backend_metrics.min_temperature,
            'pressure_drop': backend_metrics.pressure_drop,
            'heat_transfer_coefficient': backend_metrics.heat_transfer_coefficient,
            'reynolds_number': backend_metrics.reynolds_number,
            'nusselt_number': backend_metrics.nusselt_number,
            'friction_factor': backend_metrics.friction_factor,
            'thermal_resistance': backend_metrics.thermal_resistance,
            'efficiency': backend_metrics.efficiency
        }
    
    @staticmethod
    def validate_frontend_parameters(frontend_params: Dict[str, Any]) -> Dict[str, Any]:
        """验证前端参数格式"""
        required_fields = [
            'channel_width', 'channel_height', 'channel_length', 'channel_count',
            'wall_thickness', 'inlet_velocity', 'inlet_temperature', 'outlet_pressure',
            'heat_flux', 'base_temperature', 'fluid_type', 'solid_material'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in frontend_params:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                'is_valid': False,
                'errors': [f'缺少必要参数: {missing_fields}'],
                'warnings': [],
                'suggestions': []
            }
        
        # 验证数值范围
        warnings = []
        suggestions = []
        
        if frontend_params.get('channel_width', 0) < 1e-6:
            warnings.append('通道宽度过小，建议使用大于1微米的尺寸')
        
        if frontend_params.get('inlet_velocity', 0) > 100:
            warnings.append('速度过高，建议使用小于100 m/s的速度')
        
        if frontend_params.get('heat_flux', 0) > 1e7:
            warnings.append('热通量过高，建议使用小于10 MW/m²的热通量')
        
        return {
            'is_valid': True,
            'errors': [],
            'warnings': warnings,
            'suggestions': suggestions
        }