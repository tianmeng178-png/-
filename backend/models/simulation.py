from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class FluidType(str, Enum):
    WATER = "water"
    AIR = "air"
    ETHYLENE_GLYCOL = "ethylene_glycol"
    ENGINE_OIL = "engine_oil"

class MaterialType(str, Enum):
    COPPER = "copper"
    ALUMINUM = "aluminum"
    STEEL = "steel"
    SILICON = "silicon"

class SimulationMode(str, Enum):
    MOCK = "mock"
    OPENFOAM = "openfoam"

class SimulationStatusEnum(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"

class SimulationParameters(BaseModel):
    """仿真参数模型"""
    
    # 几何参数
    channel_width: float = Field(..., gt=0, description="通道宽度 (m)")
    channel_height: float = Field(..., gt=0, description="通道高度 (m)")
    channel_length: float = Field(..., gt=0, description="通道长度 (m)")
    channel_count: int = Field(..., gt=0, le=1000, description="通道数量")
    wall_thickness: float = Field(..., gt=0, description="壁厚 (m)")
    
    # 流动参数
    inlet_velocity: float = Field(..., gt=0, description="入口速度 (m/s)")
    inlet_temperature: float = Field(..., gt=0, description="入口温度 (K)")
    outlet_pressure: float = Field(..., description="出口压力 (Pa)")
    
    # 热参数
    heat_flux: float = Field(..., gt=0, description="热通量 (W/m²)")
    base_temperature: float = Field(..., gt=0, description="基底温度 (K)")
    
    # 材料参数
    fluid_type: FluidType = Field(..., description="流体类型")
    solid_material: MaterialType = Field(..., description="固体材料类型")
    
    # 仿真控制参数
    mesh_resolution: float = Field(default=0.001, gt=0, description="网格分辨率 (m)")
    max_iterations: int = Field(default=1000, gt=0, description="最大迭代次数")
    convergence_criteria: float = Field(default=1e-6, gt=0, description="收敛标准")
    
    # 仿真模式
    simulation_mode: SimulationMode = Field(default=SimulationMode.MOCK, description="仿真模式")
    
    @validator('channel_width', 'channel_height', 'wall_thickness')
    def validate_microscale_dimensions(cls, v):
        """验证微尺度尺寸"""
        if v < 1e-6:  # 小于1微米
            raise ValueError('尺寸过小，建议使用大于1微米的尺寸')
        if v > 0.01:  # 大于1厘米
            raise ValueError('尺寸过大，建议使用小于1厘米的尺寸')
        return v
    
    @validator('inlet_velocity')
    def validate_velocity(cls, v):
        """验证速度范围"""
        if v > 100:  # 大于100 m/s
            raise ValueError('速度过高，建议使用小于100 m/s的速度')
        return v
    
    @validator('heat_flux')
    def validate_heat_flux(cls, v):
        """验证热通量范围"""
        if v > 1e7:  # 大于10 MW/m²
            raise ValueError('热通量过高，建议使用小于10 MW/m²的热通量')
        return v

class ValidationResult(BaseModel):
    """参数验证结果"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

class SimulationStatus(BaseModel):
    """仿真状态模型"""
    simulation_id: str
    status: SimulationStatusEnum
    progress: float = Field(..., ge=0, le=100)
    current_step: str
    estimated_time_remaining: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    log_messages: List[str] = []

class PerformanceMetrics(BaseModel):
    """性能指标模型"""
    max_temperature: float = Field(..., description="最高温度 (K)")
    min_temperature: float = Field(..., description="最低温度 (K)")
    pressure_drop: float = Field(..., description="压力降 (Pa)")
    heat_transfer_coefficient: float = Field(..., description="传热系数 (W/m²K)")
    reynolds_number: float = Field(..., description="雷诺数")
    nusselt_number: float = Field(..., description="努塞尔数")
    friction_factor: float = Field(..., description="摩擦因子")
    thermal_resistance: float = Field(..., description="热阻 (K/W)")
    efficiency: float = Field(..., ge=0, le=1, description="效率")

class SimulationResults(BaseModel):
    """仿真结果模型"""
    simulation_id: str
    parameters: SimulationParameters
    performance_metrics: PerformanceMetrics
    visualization_data: Dict[str, Any]
    case_directory: Optional[str] = None
    paraview_file: Optional[str] = None
    paraview_web_url: Optional[str] = None
    report_url: Optional[str] = None
    created_at: datetime

class ParsingResult(BaseModel):
    """自然语言解析结果"""
    parameters: SimulationParameters
    confidence: float = Field(..., ge=0, le=1)
    extracted_parameters: Dict[str, Any]
    missing_parameters: List[str]
    suggestions: List[str]

class OpenFOAMCase(BaseModel):
    """OpenFOAM案例配置"""
    case_directory: str
    mesh_quality: Dict[str, float]
    boundary_conditions: Dict[str, Any]
    solver_settings: Dict[str, Any]
    control_dict: Dict[str, Any]

class LLMParsingRequest(BaseModel):
    """LLM解析请求"""
    description: str
    context: Optional[Dict[str, Any]] = None

class LLMParsingResponse(BaseModel):
    """LLM解析响应"""
    parameters: Dict[str, Any]
    confidence: float
    reasoning: str
    validation_notes: List[str]

# 错误模型
class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class StatusUpdateMessage(WebSocketMessage):
    """状态更新消息"""
    type: str = "status_update"
    data: SimulationStatus

class ProgressUpdateMessage(WebSocketMessage):
    """进度更新消息"""
    type: str = "progress_update"
    data: Dict[str, Any]

class LogMessage(WebSocketMessage):
    """日志消息"""
    type: str = "log_message"
    data: Dict[str, str]

class ErrorMessage(WebSocketMessage):
    """错误消息"""
    type: str = "error"
    data: Dict[str, str]

class SimulationCompletedMessage(WebSocketMessage):
    """仿真完成消息"""
    type: str = "simulation_completed"
    data: Dict[str, Any]

class ResidualUpdateMessage(WebSocketMessage):
    """残差更新消息"""
    type: str = "residual_update"
    data: Dict[str, Any]

class ParaViewWebMessage(WebSocketMessage):
    """ParaViewWeb 状态消息"""
    type: str = "paraview_web"
    data: Dict[str, Any]
