import { create } from 'zustand'
import { 
  MicrochannelParameters, 
  SimulationStatus, 
  VisualizationData, 
  PerformanceMetrics,
  ParsingResult,
  ValidationResult 
} from '../types'

interface AppState {
  // 参数状态
  parameters: MicrochannelParameters
  parameterSuggestions: ParsingResult | null
  validationResult: ValidationResult | null
  
  // 仿真状态
  simulationStatus: SimulationStatus
  performanceMetrics: PerformanceMetrics | null
  
  // 可视化数据
  visualizationData: VisualizationData | null
  
  // UI状态
  activeTab: 'design' | 'simulation' | 'results'
  is3DView: boolean
  
  // 操作函数
  updateParameter: (key: keyof MicrochannelParameters, value: any) => void
  updateParameters: (newParams: Partial<MicrochannelParameters>) => void
  setSimulationStatus: (status: SimulationStatus | ((prev: SimulationStatus) => SimulationStatus)) => void
  setVisualizationData: (data: VisualizationData) => void
  setPerformanceMetrics: (metrics: PerformanceMetrics) => void
  setParameterSuggestions: (suggestions: ParsingResult | null) => void
  setValidationResult: (result: ValidationResult | null) => void
  setActiveTab: (tab: 'design' | 'simulation' | 'results') => void
  toggle3DView: () => void
  
  // 计算属性
  getParameterValidation: (paramName: string) => {
    status: 'valid' | 'warning' | 'error'
    message: string
  }
}

const defaultParameters: MicrochannelParameters = {
  channel_width: 0.0001,
  channel_height: 0.0005,
  channel_length: 0.01,
  channel_count: 10,
  wall_thickness: 0.00005,
  inlet_velocity: 0.1,
  inlet_temperature: 293.15,
  outlet_pressure: 0,
  heat_flux: 10000,
  base_temperature: 353.15,
  fluid_type: 'water',
  solid_material: 'copper',
  mesh_resolution: 20,
  convergence_criteria: 1e-6,
  simulation_mode: 'mock',
  use_gpu_acceleration: false
}

const defaultSimulationStatus: SimulationStatus = {
  status: 'idle',
  progress: 0,
  current_step: '等待开始',
  log_messages: []
}

export const useStore = create<AppState>((set, get) => ({
  // 初始状态
  parameters: defaultParameters,
  parameterSuggestions: null,
  validationResult: null,
  simulationStatus: defaultSimulationStatus,
  performanceMetrics: null,
  visualizationData: null,
  activeTab: 'design',
  is3DView: true,

  // 操作函数
  updateParameter: (key, value) => {
    set(state => ({
      parameters: {
        ...state.parameters,
        [key]: value
      }
    }))
  },

  updateParameters: (newParams) => {
    set(state => ({
      parameters: {
        ...state.parameters,
        ...newParams
      }
    }))
  },

  setSimulationStatus: (status) => {
    set(state => ({
      simulationStatus: typeof status === 'function' 
        ? status(state.simulationStatus)
        : status
    }))
  },

  setVisualizationData: (data) => {
    set({ visualizationData: data })
  },

  setPerformanceMetrics: (metrics) => {
    set({ performanceMetrics: metrics })
  },

  setParameterSuggestions: (suggestions) => {
    set({ parameterSuggestions: suggestions })
  },

  setValidationResult: (result) => {
    set({ validationResult: result })
  },

  setActiveTab: (tab) => {
    set({ activeTab: tab })
  },

  toggle3DView: () => {
    set(state => ({ is3DView: !state.is3DView }))
  },

  // 计算属性
  getParameterValidation: (paramName) => {
    const state = get()
    const validation = state.validationResult?.parameter_validations.find(
      v => v.parameter_name === paramName
    )
    
    if (validation) {
      return {
        status: validation.status,
        message: validation.message
      }
    }
    
    // 默认验证规则
    const paramValue = state.parameters[paramName as keyof MicrochannelParameters]
    
    // 基本范围验证
    const rules: Record<string, { min: number; max: number; unit: string }> = {
      channel_width: { min: 50e-6, max: 1000e-6, unit: 'm' },
      channel_height: { min: 100e-6, max: 2000e-6, unit: 'm' },
      inlet_velocity: { min: 0.01, max: 5, unit: 'm/s' },
      heat_flux: { min: 1000, max: 100000, unit: 'W/m²' }
    }
    
    const rule = rules[paramName]
    if (rule && typeof paramValue === 'number') {
      if (paramValue < rule.min) {
        return {
          status: 'warning',
          message: `值偏小，建议 ≥ ${rule.min}${rule.unit}`
        }
      }
      if (paramValue > rule.max) {
        return {
          status: 'warning',
          message: `值偏大，建议 ≤ ${rule.max}${rule.unit}`
        }
      }
    }
    
    return {
      status: 'valid',
      message: '参数值在合理范围内'
    }
  }
}))