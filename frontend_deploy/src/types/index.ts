// 微通道散热器参数类型定义

export interface MicrochannelParameters {
  // 几何参数
  channel_width: number;        // 通道宽度 [m]
  channel_height: number;      // 通道高度 [m]
  channel_length: number;      // 通道长度 [m]
  channel_count: number;       // 通道数量
  wall_thickness: number;      // 壁厚 [m]
  
  // 流动参数
  inlet_velocity: number;      // 入口速度 [m/s]
  inlet_temperature: number;   // 入口温度 [K]
  outlet_pressure: number;     // 出口压力 [Pa]
  
  // 热参数
  heat_flux: number;           // 热通量 [W/m²]
  base_temperature: number;    // 基底温度 [K]
  
  // 材料参数
  fluid_type: 'water' | 'air'; // 流体类型
  solid_material: 'copper' | 'aluminum' | 'silicon'; // 固体材料
  
  // 求解参数
  mesh_resolution: number;     // 网格分辨率
  convergence_criteria: number; // 收敛标准
}

export interface ParameterValidation {
  parameter_name: string;
  status: 'valid' | 'warning' | 'error';
  message: string;
  suggested_value?: number;
}

export interface SimulationStatus {
  status: 'idle' | 'running' | 'completed' | 'error';
  progress: number;           // 0-100
  current_step: string;
  estimated_time_remaining?: number; // 秒
  log_messages: string[];
}

export interface VisualizationData {
  geometry: {
    vertices: number[];
    faces: number[];
    colors: number[];
  };
  temperature_field: {
    values: number[];
    positions: number[];
  };
  velocity_field: {
    vectors: number[];
    positions: number[];
  };
  pressure_field: {
    values: number[];
    positions: number[];
  };
}

export interface PerformanceMetrics {
  max_temperature: number;    // 最高温度 [K]
  pressure_drop: number;      // 压力降 [Pa]
  heat_transfer_coefficient: number; // 传热系数 [W/m²K]
  reynolds_number: number;    // 雷诺数
  nusselt_number: number;     // 努塞尔数
}

export interface ParameterSuggestion {
  parameter_name: string;
  suggested_value: number;
  confidence: number;          // 0-1
  source: 'extracted' | 'inferred' | 'default';
  original_text?: string;
  unit?: string;
}

export interface ParsingResult {
  description: string;
  extracted_parameters: Record<string, ParameterSuggestion>;
  inferred_parameters: Record<string, ParameterSuggestion>;
  default_parameters: Record<string, ParameterSuggestion>;
  parsing_confidence: number;
  warnings: string[];
  recommendations: string[];
}

export interface ValidationResult {
  overall_status: 'valid' | 'warning' | 'error';
  parameter_validations: ParameterValidation[];
  suggestions: string[];
  safety_assessment: {
    status: 'safe' | 'warning' | 'danger';
    messages: string[];
  };
  performance_estimation: PerformanceMetrics;
}