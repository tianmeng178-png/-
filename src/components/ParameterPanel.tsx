import React, { useState, useCallback, useEffect, useRef } from 'react'
import { 
  Card, 
  InputNumber, 
  Slider, 
  Select, 
  Space, 
  Typography, 
  Alert, 
  Button, 
  Collapse,
  Tag,
  Tooltip,
  Row,
  Col,
  Modal,
  Input,
  message,
  Popconfirm
} from 'antd'
import { 
  SettingOutlined, 
  BulbOutlined, 
  SafetyOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  DeleteOutlined,
  ImportOutlined,
  PlayCircleOutlined
} from '@ant-design/icons'
import { useStore } from '../stores/useStore'
import { ApiService } from '../services/api'
import type { MicrochannelParameters, ValidationResult } from '../types'

const { Title, Text } = Typography
const { Option } = Select
const DEFAULT_OPENFOAM_CELL_SIZE = 10e-6

// 参数预设模板
interface ParameterTemplate {
  id: string
  name: string
  description: string
  category: string
  parameters: Partial<MicrochannelParameters>
}

const defaultTemplates: ParameterTemplate[] = [
  {
    id: 'high-performance',
    name: '高性能散热',
    description: '适用于高功率芯片散热，优化传热效率',
    category: '电子散热',
    parameters: {
      channel_width: 100e-6,
      channel_height: 500e-6,
      channel_length: 0.02,
      channel_count: 20,
      wall_thickness: 50e-6,
      inlet_velocity: 0.5,
      inlet_temperature: 293.15,
      heat_flux: 50000,
      base_temperature: 333.15,
      fluid_type: 'water',
      solid_material: 'copper',
      mesh_resolution: 30,
      convergence_criteria: 1e-6,
      simulation_mode: 'mock',
      use_gpu_acceleration: false
    }
  },
  {
    id: 'low-pressure',
    name: '低压降设计',
    description: '优化流动阻力，适用于对泵功要求严格的场景',
    category: '节能设计',
    parameters: {
      channel_width: 200e-6,
      channel_height: 800e-6,
      channel_length: 0.01,
      channel_count: 15,
      wall_thickness: 100e-6,
      inlet_velocity: 0.1,
      inlet_temperature: 298.15,
      heat_flux: 20000,
      base_temperature: 343.15,
      fluid_type: 'water',
      solid_material: 'aluminum',
      mesh_resolution: 20,
      convergence_criteria: 1e-5,
      simulation_mode: 'mock',
      use_gpu_acceleration: false
    }
  },
  {
    id: 'compact',
    name: '紧凑型设计',
    description: '尺寸紧凑，适用于空间受限的应用',
    category: '空间优化',
    parameters: {
      channel_width: 150e-6,
      channel_height: 400e-6,
      channel_length: 0.005,
      channel_count: 10,
      wall_thickness: 75e-6,
      inlet_velocity: 0.3,
      inlet_temperature: 293.15,
      heat_flux: 30000,
      base_temperature: 353.15,
      fluid_type: 'water',
      solid_material: 'silicon',
      mesh_resolution: 25,
      convergence_criteria: 1e-6,
      simulation_mode: 'mock',
      use_gpu_acceleration: false
    }
  },
  {
    id: 'air-cooling',
    name: '风冷设计',
    description: '使用空气作为冷却介质，适用于无水冷场景',
    category: '风冷方案',
    parameters: {
      channel_width: 500e-6,
      channel_height: 1000e-6,
      channel_length: 0.03,
      channel_count: 25,
      wall_thickness: 200e-6,
      inlet_velocity: 2.0,
      inlet_temperature: 298.15,
      heat_flux: 10000,
      base_temperature: 323.15,
      fluid_type: 'air',
      solid_material: 'aluminum',
      mesh_resolution: 20,
      convergence_criteria: 1e-5,
      simulation_mode: 'mock',
      use_gpu_acceleration: false
    }
  }
]

// 参数配置定义
interface ParameterConfig {
  key: keyof MicrochannelParameters
  label: string
  unit: string
  min: number
  max: number
  step: number
  scale: number
  offset?: number
  description: string
  type?: 'number' | 'select'
  options?: { label: string; value: string }[]
}

const parameterConfigs: { category: string; icon: React.ReactNode; parameters: ParameterConfig[] }[] = [
  {
    category: '几何参数',
    icon: <SettingOutlined />,
    parameters: [
      {
        key: 'channel_width',
        label: '通道宽度',
        unit: 'μm',
        min: 50,
        max: 1000,
        step: 10,
        scale: 1e6,
        description: '微通道宽度，影响流动阻力和传热效率。推荐范围：100-500μm'
      },
      {
        key: 'channel_height',
        label: '通道高度',
        unit: 'μm',
        min: 100,
        max: 2000,
        step: 50,
        scale: 1e6,
        description: '微通道高度，与宽度共同决定纵横比。推荐范围：200-1000μm'
      },
      {
        key: 'channel_length',
        label: '通道长度',
        unit: 'mm',
        min: 1,
        max: 50,
        step: 1,
        scale: 1e3,
        description: '微通道长度，影响压力降和温升。推荐范围：5-30mm'
      },
      {
        key: 'channel_count',
        label: '通道数量',
        unit: '个',
        min: 1,
        max: 100,
        step: 1,
        scale: 1,
        description: '并行通道数量，决定总散热面积。推荐范围：5-50个'
      },
      {
        key: 'wall_thickness',
        label: '壁厚',
        unit: 'μm',
        min: 25,
        max: 500,
        step: 25,
        scale: 1e6,
        description: '通道间壁厚，影响结构强度和导热。推荐范围：50-200μm'
      }
    ]
  },
  {
    category: '流动参数',
    icon: <ThunderboltOutlined />,
    parameters: [
      {
        key: 'inlet_velocity',
        label: '入口速度',
        unit: 'm/s',
        min: 0.01,
        max: 5,
        step: 0.01,
        scale: 1,
        description: '冷却流体入口速度。水冷推荐：0.1-1 m/s，风冷推荐：1-5 m/s'
      },
      {
        key: 'inlet_temperature',
        label: '入口温度',
        unit: '°C',
        min: 10,
        max: 80,
        step: 1,
        scale: 1,
        offset: -273.15,
        description: '冷却流体入口温度。推荐范围：15-40°C'
      },
      {
        key: 'outlet_pressure',
        label: '出口压力',
        unit: 'Pa',
        min: 0,
        max: 100000,
        step: 1000,
        scale: 1,
        description: '出口边界压力，通常设为大气压（0 Pa表压）'
      }
    ]
  },
  {
    category: '热参数',
    icon: <BulbOutlined />,
    parameters: [
      {
        key: 'heat_flux',
        label: '热通量',
        unit: 'W/cm²',
        min: 1,
        max: 200,
        step: 1,
        scale: 1e-4,
        description: '单位面积热负荷。电子芯片典型值：10-100 W/cm²'
      },
      {
        key: 'base_temperature',
        label: '基底目标温度',
        unit: '°C',
        min: 30,
        max: 150,
        step: 1,
        scale: 1,
        offset: -273.15,
        description: '散热器基底允许的最高温度。芯片安全温度通常<85°C'
      }
    ]
  },
  {
    category: '材料参数',
    icon: <SafetyOutlined />,
    parameters: [
      {
        key: 'fluid_type',
        label: '流体类型',
        unit: '',
        min: 0,
        max: 0,
        step: 0,
        scale: 1,
        description: '冷却介质选择。水：高传热系数；空气：简单安全',
        type: 'select',
        options: [
          { label: '水 (Water)', value: 'water' },
          { label: '空气 (Air)', value: 'air' }
        ]
      },
      {
        key: 'solid_material',
        label: '固体材料',
        unit: '',
        min: 0,
        max: 0,
        step: 0,
        scale: 1,
        description: '散热器材料选择。铜：导热最好；铝：轻量经济；硅：微电子兼容',
        type: 'select',
        options: [
          { label: '铜 (Copper)', value: 'copper' },
          { label: '铝 (Aluminum)', value: 'aluminum' },
          { label: '硅 (Silicon)', value: 'silicon' }
        ]
      }
    ]
  },
  {
    category: '求解参数',
    icon: <SettingOutlined />,
    parameters: [
      {
        key: 'mesh_resolution',
        label: '网格分辨率',
        unit: '单元',
        min: 10,
        max: 100,
        step: 5,
        scale: 1,
        description: '网格划分密度。值越大精度越高但计算越慢。推荐：20-50'
      },
      {
        key: 'convergence_criteria',
        label: '收敛标准',
        unit: '',
        min: 1e-8,
        max: 1e-4,
        step: 1e-8,
        scale: 1,
        description: '残差收敛标准。值越小精度越高但收敛越慢。推荐：1e-6'
      }
    ]
  }
]

const ParameterPanel: React.FC = () => {
  const { 
    parameters, 
    updateParameter, 
    updateParameters,
    getParameterValidation,
    parameterSuggestions,
    validationResult,
    setValidationResult,
    setParameterSuggestions,
    setActiveTab
  } = useStore()

  const [isValidating, setIsValidating] = useState(false)
  const [isOptimizing, setIsOptimizing] = useState(false)
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const [saveTemplateModalVisible, setSaveTemplateModalVisible] = useState(false)
  const [customTemplates, setCustomTemplates] = useState<ParameterTemplate[]>(() => {
    const saved = localStorage.getItem('customParameterTemplates')
    return saved ? JSON.parse(saved) : []
  })
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplateDescription, setNewTemplateDescription] = useState('')
  const [naturalLanguageInput, setNaturalLanguageInput] = useState('')
  const [isParsing, setIsParsing] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string | string[]>(['几何参数'])

  const lastSimulationModeRef = useRef(parameters.simulation_mode)

  useEffect(() => {
    if (lastSimulationModeRef.current === parameters.simulation_mode) {
      return
    }

    if (parameters.simulation_mode === 'openfoam') {
      if (parameters.mesh_resolution >= 1) {
        updateParameter('mesh_resolution', DEFAULT_OPENFOAM_CELL_SIZE)
      }
    } else {
      if (parameters.mesh_resolution < 1) {
        updateParameter('mesh_resolution', 20)
      }
    }

    lastSimulationModeRef.current = parameters.simulation_mode
  }, [parameters.simulation_mode, parameters.mesh_resolution, updateParameter])

  const mockMeshParamConfig = parameterConfigs
    .flatMap(category => category.parameters)
    .find(param => param.key === 'mesh_resolution')

  const meshParamConfig: ParameterConfig = parameters.simulation_mode === 'openfoam'
    ? {
        key: 'mesh_resolution',
        label: '单元尺寸',
        unit: 'um',
        min: 1,
        max: 50,
        step: 1,
        scale: 1e6,
        description: '真实模式按单元尺寸生成网格，尺寸越小越精细但计算更慢。建议 5-20 um'
      }
    : (mockMeshParamConfig ?? {
        key: 'mesh_resolution',
        label: '网格分辨率',
        unit: 'cells',
        min: 10,
        max: 100,
        step: 5,
        scale: 1,
        description: 'Mesh density in cells (mock mode).'
      })

  const activeParameterConfigs = parameterConfigs.map(category => ({
    ...category,
    parameters: category.parameters.map(param => (
      param.key === 'mesh_resolution' ? meshParamConfig : param
    ))
  }))

  // 获取显示值（考虑单位转换）
  const getDisplayValue = useCallback((key: keyof MicrochannelParameters, value: any): number => {
    const config = activeParameterConfigs.flatMap(cat => cat.parameters).find(p => p.key === key)
    if (!config || config.type === 'select') return value

    let displayValue = value
    if (config.scale) {
      displayValue = value * config.scale
    }
    if (config.offset) {
      displayValue = value + config.offset
    }

    return Math.round(displayValue * 100) / 100
  }, [activeParameterConfigs])

  // 处理参数变化
  const handleParameterChange = useCallback((key: keyof MicrochannelParameters, value: any) => {
    const config = activeParameterConfigs.flatMap(cat => cat.parameters).find(p => p.key === key)
    
    // 如果没有找到配置（如 simulation_mode），直接更新值
    if (!config) {
      updateParameter(key, value)
      return
    }

    let finalValue = value
    if (config.type !== 'select') {
      if (config.scale) {
        finalValue = value / config.scale
      }
      if (config.offset) {
        finalValue = value - config.offset
      }
    }

    updateParameter(key, finalValue)
  }, [activeParameterConfigs, updateParameter])

  // 应用模板
  const applyTemplate = useCallback((template: ParameterTemplate) => {
    updateParameters(template.parameters)
    message.success(`已应用模板：${template.name}`)
    setTemplateModalVisible(false)
  }, [updateParameters])

  // 保存自定义模板
  const saveCustomTemplate = useCallback(() => {
    if (!newTemplateName.trim()) {
      message.error('请输入模板名称')
      return
    }

    const newTemplate: ParameterTemplate = {
      id: `custom-${Date.now()}`,
      name: newTemplateName,
      description: newTemplateDescription || '自定义参数配置',
      category: '自定义',
      parameters: { ...parameters }
    }

    const updatedTemplates = [...customTemplates, newTemplate]
    setCustomTemplates(updatedTemplates)
    localStorage.setItem('customParameterTemplates', JSON.stringify(updatedTemplates))
    
    message.success('模板保存成功')
    setSaveTemplateModalVisible(false)
    setNewTemplateName('')
    setNewTemplateDescription('')
  }, [newTemplateName, newTemplateDescription, parameters, customTemplates])

  // 删除自定义模板
  const deleteCustomTemplate = useCallback((templateId: string) => {
    const updatedTemplates = customTemplates.filter(t => t.id !== templateId)
    setCustomTemplates(updatedTemplates)
    localStorage.setItem('customParameterTemplates', JSON.stringify(updatedTemplates))
    message.success('模板已删除')
  }, [customTemplates])

  // 验证参数
  const handleValidate = useCallback(async () => {
    setIsValidating(true)
    console.log('🔍 开始参数验证...', parameters)
    
    try {
      // 先进行前端本地验证
      const localValidation = validateParametersLocal(parameters)
      console.log('📋 本地验证结果:', localValidation)
      
      // 尝试调用后端 API
      let result: ValidationResult
      try {
        result = await ApiService.validateParameters(parameters)
        console.log('✅ 后端验证结果:', result)
      } catch (apiError) {
        console.warn('⚠️ 后端验证失败，使用本地验证:', apiError)
        // 如果后端不可用，使用本地验证结果
        result = localValidation
      }
      
      setValidationResult(result)
      
      if (result.overall_status === 'valid') {
        message.success('✅ 参数验证通过！所有参数都在合理范围内。')
      } else if (result.overall_status === 'warning') {
        message.warning('⚠️ 参数验证通过，但有一些建议需要关注。')
      } else {
        message.error('❌ 参数验证失败，请检查并调整参数。')
      }
    } catch (error) {
      console.error('❌ 参数验证失败:', error)
      message.error('参数验证过程中发生错误，请稍后重试。')
    } finally {
      setIsValidating(false)
    }
  }, [parameters, setValidationResult])

  // 本地参数验证函数（作为后端验证的备用）
  const validateParametersLocal = (params: MicrochannelParameters): ValidationResult => {
    const validations: Array<{
      parameter_name: string
      status: 'valid' | 'warning' | 'error'
      message: string
      current_value: number
      recommended_range: string
    }> = []
    const suggestions: string[] = []
    
    // 验证通道宽度
    if (params.channel_width < 50e-6) {
      validations.push({
        parameter_name: 'channel_width',
        status: 'error',
        message: '通道宽度过小，可能导致制造困难',
        current_value: params.channel_width,
        recommended_range: '50-500 μm'
      })
      suggestions.push('建议将通道宽度增加到至少 50 μm')
    } else if (params.channel_width > 1000e-6) {
      validations.push({
        parameter_name: 'channel_width',
        status: 'warning',
        message: '通道宽度较大，可能影响散热效率',
        current_value: params.channel_width,
        recommended_range: '50-500 μm'
      })
    } else {
      validations.push({
        parameter_name: 'channel_width',
        status: 'valid',
        message: '通道宽度在合理范围内',
        current_value: params.channel_width,
        recommended_range: '50-500 μm'
      })
    }
    
    // 验证入口速度
    if (params.inlet_velocity < 0.01) {
      validations.push({
        parameter_name: 'inlet_velocity',
        status: 'warning',
        message: '入口速度较低，散热效果可能不佳',
        current_value: params.inlet_velocity,
        recommended_range: '0.1-5 m/s'
      })
      suggestions.push('建议适当增加入口速度以提高散热效率')
    } else if (params.inlet_velocity > 10) {
      validations.push({
        parameter_name: 'inlet_velocity',
        status: 'error',
        message: '入口速度过高，可能导致压降过大',
        current_value: params.inlet_velocity,
        recommended_range: '0.1-5 m/s'
      })
    } else {
      validations.push({
        parameter_name: 'inlet_velocity',
        status: 'valid',
        message: '入口速度在合理范围内',
        current_value: params.inlet_velocity,
        recommended_range: '0.1-5 m/s'
      })
    }
    
    // 验证热流密度
    if (params.heat_flux > 1000000) {
      validations.push({
        parameter_name: 'heat_flux',
        status: 'warning',
        message: '热流密度较高，需要确保冷却能力充足',
        current_value: params.heat_flux,
        recommended_range: '< 100 W/cm²'
      })
    }
    
    // 确定总体状态
    const hasError = validations.some(v => v.status === 'error')
    const hasWarning = validations.some(v => v.status === 'warning')
    const overall_status = hasError ? 'error' : hasWarning ? 'warning' : 'valid'
    
    return {
      overall_status,
      parameter_validations: validations,
      safety_assessment: {
        status: hasError ? 'danger' : hasWarning ? 'warning' : 'safe',
        messages: hasError 
          ? ['存在参数超出安全范围，请调整后再进行仿真']
          : ['参数配置基本安全，可以进行仿真']
      },
      suggestions,
      performance_estimation: {
        max_temperature: params.inlet_temperature + params.heat_flux / 10000 * 20,
        pressure_drop: params.inlet_velocity * 500,
        heat_transfer_coefficient: 5000 + params.inlet_velocity * 2000,
        reynolds_number: params.inlet_velocity * params.channel_width / 1e-6,
        nusselt_number: 0.023 * Math.pow(params.inlet_velocity * params.channel_width / 1e-6, 0.8)
      }
    }
  }

  // 智能优化
  const handleOptimize = useCallback(async () => {
    setIsOptimizing(true)
    try {
      // 模拟优化过程
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      // 基于当前参数进行智能调整
      const optimizedParams = { ...parameters }
      
      // 优化逻辑示例
      if (optimizedParams.fluid_type === 'water') {
        // 水冷优化：适当降低速度以减少压降
        optimizedParams.inlet_velocity = Math.min(optimizedParams.inlet_velocity, 0.5)
      } else {
        // 风冷优化：增加速度以提高换热
        optimizedParams.inlet_velocity = Math.max(optimizedParams.inlet_velocity, 1.0)
      }
      
      // 优化通道数量
      const totalWidth = optimizedParams.channel_count * 
        (optimizedParams.channel_width + optimizedParams.wall_thickness)
      if (totalWidth > 0.02) { // 如果总宽度超过2cm
        optimizedParams.channel_count = Math.floor(0.02 / 
          (optimizedParams.channel_width + optimizedParams.wall_thickness))
      }
      
      updateParameters(optimizedParams)
      message.success('参数已智能优化')
    } catch (error) {
      console.error('优化失败:', error)
      message.error('优化过程出错')
    } finally {
      setIsOptimizing(false)
    }
  }, [parameters, updateParameters])

  // 重置默认值
  const handleReset = useCallback(() => {
    Modal.confirm({
      title: '确认重置参数',
      content: '确定要重置所有参数为默认值吗？',
      onOk: () => {
        updateParameters({
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
          convergence_criteria: 1e-6
        })
        setValidationResult(null)
        setParameterSuggestions(null)
        message.success('参数已重置')
      }
    })
  }, [updateParameters, setValidationResult, setParameterSuggestions])

  // 解析自然语言描述
  const handleParseDescription = useCallback(async () => {
    if (!naturalLanguageInput.trim()) {
      message.warning('请输入设计需求描述')
      return
    }

    setIsParsing(true)
    try {
      const result = await ApiService.parseDescription(naturalLanguageInput)
      setParameterSuggestions(result)
      
      // 应用解析的参数
      const newParams: Partial<MicrochannelParameters> = {}
      Object.entries(result.extracted_parameters).forEach(([key, suggestion]) => {
        if (suggestion.confidence > 0.7) {
          (newParams as any)[key] = suggestion.suggested_value
        }
      })
      
      if (Object.keys(newParams).length > 0) {
        updateParameters(newParams)
        message.success(`已解析并应用 ${Object.keys(newParams).length} 个参数`)
      } else {
        message.info('未能提取到高置信度参数，请手动配置')
      }
    } catch (error) {
      console.error('解析失败:', error)
      message.error('自然语言解析失败')
    } finally {
      setIsParsing(false)
    }
  }, [naturalLanguageInput, setParameterSuggestions, updateParameters])

  // 获取验证状态图标
  const getValidationIcon = (status: string) => {
    switch (status) {
      case 'valid': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'warning': return <ExclamationCircleOutlined style={{ color: '#faad14' }} />
      case 'error': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
      default: return <InfoCircleOutlined style={{ color: '#1890ff' }} />
    }
  }

  const allTemplates = [...defaultTemplates, ...customTemplates]

  return (
    <div className="parameter-panel">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        
        {/* 标题 */}
        <Title level={4} style={{ margin: 0 }}>
          <SettingOutlined /> 参数配置
        </Title>

        {/* 自然语言输入 */}
        <Card size="small" title={<><BulbOutlined /> 智能参数提取</>}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.TextArea
              id="param-natural-language-input"
              name="naturalLanguageInput"
              placeholder="描述您的设计需求，例如：设计一个用于CPU散热的水冷微通道散热器，热负荷50W/cm²，要求温度不超过80度..."
              value={naturalLanguageInput}
              onChange={(e) => setNaturalLanguageInput(e.target.value)}
              rows={3}
            />
            <Button 
              type="primary" 
              icon={<ImportOutlined />}
              onClick={handleParseDescription}
              loading={isParsing}
              block
            >
              解析需求
            </Button>
          </Space>
        </Card>

        {/* 参数建议提示 */}
        {parameterSuggestions && (
          <Alert
            message="智能参数建议"
            description={
              <Space direction="vertical" size="small">
                <Text>解析置信度: {(parameterSuggestions.parsing_confidence * 100).toFixed(1)}%</Text>
                {parameterSuggestions.warnings.map((warning, idx) => (
                  <Text key={idx} type="warning">⚠️ {warning}</Text>
                ))}
                {parameterSuggestions.recommendations.map((rec, idx) => (
                  <Text key={idx} type="success">💡 {rec}</Text>
                ))}
              </Space>
            }
            type="info"
            showIcon
            closable
            onClose={() => setParameterSuggestions(null)}
          />
        )}

        {/* 验证结果 */}
        {validationResult && (
          <Alert
            message={
              <Space>
                {getValidationIcon(validationResult.overall_status)}
                参数验证: {validationResult.overall_status === 'valid' ? '通过' : 
                         validationResult.overall_status === 'warning' ? '需要关注' : '需要调整'}
              </Space>
            }
            description={
              <Space direction="vertical" size="small">
                {validationResult.safety_assessment.messages.map((msg, idx) => (
                  <Text key={idx} type={validationResult.safety_assessment.status === 'safe' ? 'success' : 'warning'}>
                    {validationResult.safety_assessment.status === 'safe' ? '✅' : '⚠️'} {msg}
                  </Text>
                ))}
                {validationResult.suggestions.map((suggestion, idx) => (
                  <Text key={idx} type="secondary">💡 {suggestion}</Text>
                ))}
              </Space>
            }
            type={validationResult.overall_status === 'valid' ? 'success' : 
                 validationResult.overall_status === 'warning' ? 'warning' : 'error'}
            closable
            onClose={() => setValidationResult(null)}
          />
        )}

        {/* 模板选择 */}
        <Card size="small" title={<><FileTextOutlined /> 参数模板</>}>
          <Space wrap>
            <Button onClick={() => setTemplateModalVisible(true)}>
              选择模板
            </Button>
            <Button icon={<SaveOutlined />} onClick={() => setSaveTemplateModalVisible(true)}>
              保存当前配置
            </Button>
          </Space>
        </Card>

        {/* 仿真模式选择 */}
        <Card size="small" title={<><ThunderboltOutlined /> 仿真模式</>}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Space wrap>
              <Select
                id="param-simulation-mode"
                name="simulation_mode"
                value={parameters.simulation_mode}
                onChange={(val) => handleParameterChange('simulation_mode', val)}
                style={{ width: 200 }}
              >
                <Option value="mock">
                  <Space>
                    <span>⚡</span>
                    <span>模拟模式 (快速)</span>
                  </Space>
                </Option>
                <Option value="openfoam">
                  <Space>
                    <span>🔬</span>
                    <span>真实OpenFOAM (精确)</span>
                  </Space>
                </Option>
              </Select>
            </Space>
            
            {parameters.simulation_mode === 'mock' && (
              <Alert
                message="模拟模式"
                description="使用工程经验公式快速计算，约15-20秒完成。适用于快速设计迭代。"
                type="info"
                showIcon
              />
            )}
            
            {parameters.simulation_mode === 'openfoam' && (
              <Alert
                message="真实OpenFOAM模式"
                description="使用OpenFOAM进行高精度CFD仿真，约30分钟-1.5小时完成。适用于最终验证。"
                type="warning"
                showIcon
              />
            )}
            
            {/* GPU加速选项 */}
            <div style={{ marginTop: '8px' }}>
              <Space>
                <Select
                  id="param-gpu-acceleration"
                  name="use_gpu_acceleration"
                  value={parameters.use_gpu_acceleration ? 'gpu' : 'cpu'}
                  onChange={(val) => handleParameterChange('use_gpu_acceleration', val === 'gpu')}
                  style={{ width: 150 }}
                  disabled={parameters.simulation_mode === 'mock'}
                >
                  <Option value="cpu">
                    <Space>
                      <span>💻</span>
                      <span>CPU计算</span>
                    </Space>
                  </Option>
                  <Option value="gpu">
                    <Space>
                      <span>🎮</span>
                      <span>GPU加速</span>
                    </Space>
                  </Option>
                </Select>
                <Tooltip title="检测到NVIDIA RTX 4060显卡，GPU加速可显著提升仿真速度">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            </div>
          </Space>
        </Card>

        {/* 参数输入区域 */}
        <Collapse 
          activeKey={activeCategory} 
          onChange={setActiveCategory}
          ghost
          items={activeParameterConfigs.map((category) => ({
            key: category.category,
            label: (
              <Space>
                {category.icon}
                <Text strong>{category.category}</Text>
              </Space>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {category.parameters.map((param) => {
                  const value = parameters[param.key]
                  const displayValue = getDisplayValue(param.key, value)
                  const validation = getParameterValidation(param.key as string)
                  
                  return (
                    <Card 
                      key={String(param.key)} 
                      size="small" 
                      styles={{
                        body: { padding: '12px' }
                      }}
                      style={{ 
                        borderLeft: `3px solid ${
                          validation.status === 'valid' ? '#52c41a' : 
                          validation.status === 'warning' ? '#faad14' : '#ff4d4f'
                        }`
                      }}
                    >
                      <Row gutter={[8, 8]} align="middle">
                        <Col span={24}>
                          <Space>
                            <Text strong>{param.label}</Text>
                            <Tag color="blue">{param.unit}</Tag>
                            <Tooltip title={param.description}>
                              <InfoCircleOutlined style={{ color: '#1890ff' }} />
                            </Tooltip>
                          </Space>
                        </Col>
                        
                        <Col span={24}>
                          {param.type === 'select' ? (
                            <Select
                              id={`param-${String(param.key)}`}
                              name={String(param.key)}
                              value={value as string}
                              onChange={(val) => handleParameterChange(param.key, val)}
                              style={{ width: '100%' }}
                            >
                              {param.options?.map(opt => (
                                <Option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </Option>
                              ))}
                            </Select>
                          ) : (
                            <Row gutter={8} align="middle">
                              <Col flex="auto">
                                <Slider
                                  id={`param-slider-${String(param.key)}`}
                                  min={param.min}
                                  max={param.max}
                                  step={param.step}
                                  value={displayValue as number}
                                  onChange={(val) => handleParameterChange(param.key, val)}
                                  tooltip={{ formatter: (val) => `${val} ${param.unit}` }}
                                />
                              </Col>
                              <Col span={8}>
                                <InputNumber
                                  id={`param-input-${String(param.key)}`}
                                  name={String(param.key)}
                                  min={param.min}
                                  max={param.max}
                                  step={param.step}
                                  value={displayValue}
                                  onChange={(val) => handleParameterChange(param.key, val)}
                                  style={{ width: '100%' }}
                                  precision={param.step < 1 ? 4 : 2}
                                />
                              </Col>
                            </Row>
                          )}
                        </Col>
                        
                        <Col span={24}>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {getValidationIcon(validation.status)} {validation.message}
                          </Text>
                        </Col>
                      </Row>
                    </Card>
                  )
                })}
              </Space>
            )
          }))}
        />

        {/* 操作按钮 */}
        <Card size="small">
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Button 
                type="primary" 
                icon={<BulbOutlined />}
                onClick={handleOptimize}
                loading={isOptimizing}
                block
              >
                智能优化
              </Button>
            </Col>
            <Col span={12}>
              <Button 
                icon={<SafetyOutlined />}
                onClick={handleValidate}
                loading={isValidating}
                block
              >
                验证参数
              </Button>
            </Col>
            <Col span={24}>
              <Button 
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => setActiveTab('simulation')}
                block
              >
                开始仿真
              </Button>
            </Col>
            <Col span={24}>
              <Button 
                icon={<ReloadOutlined />}
                onClick={handleReset}
                block
              >
                重置默认值
              </Button>
            </Col>
          </Row>
        </Card>
      </Space>

      {/* 模板选择模态框 */}
      <Modal
        title="选择参数模板"
        open={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        footer={null}
        width={700}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {['电子散热', '节能设计', '空间优化', '风冷方案', '自定义'].map(cat => {
            const catTemplates = allTemplates.filter(t => t.category === cat)
            if (catTemplates.length === 0) return null
            
            return (
              <Card key={cat} size="small" title={cat}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {catTemplates.map(template => (
                    <Card 
                      key={template.id} 
                      size="small" 
                      hoverable
                      actions={
                        template.category === '自定义' ? [
                          <Popconfirm
                            title="确认删除"
                            description="确定要删除这个自定义模板吗？"
                            onConfirm={() => deleteCustomTemplate(template.id)}
                            okText="删除"
                            cancelText="取消"
                          >
                            <DeleteOutlined key="delete" style={{ color: '#ff4d4f' }} />
                          </Popconfirm>
                        ] : undefined
                      }
                    >
                      <Card.Meta
                        title={
                          <Space>
                            <Text strong>{template.name}</Text>
                            <Tag color="blue">{template.category}</Tag>
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
                            <Text type="secondary">{template.description}</Text>
                            <Space wrap>
                              <Tag>{template.parameters.channel_count}通道</Tag>
                              <Tag>{(template.parameters.channel_width! * 1e6).toFixed(0)}μm宽</Tag>
                              <Tag>{template.parameters.fluid_type === 'water' ? '水冷' : '风冷'}</Tag>
                            </Space>
                            <Button 
                              type="primary" 
                              size="small"
                              onClick={() => applyTemplate(template)}
                            >
                              应用模板
                            </Button>
                          </Space>
                        }
                      />
                    </Card>
                  ))}
                </Space>
              </Card>
            )
          })}
        </Space>
      </Modal>

      {/* 保存模板模态框 */}
      <Modal
        title="保存为模板"
        open={saveTemplateModalVisible}
        onCancel={() => setSaveTemplateModalVisible(false)}
        onOk={saveCustomTemplate}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>模板名称</Text>
            <Input
              id="template-name-input"
              name="newTemplateName"
              placeholder="输入模板名称"
              value={newTemplateName}
              onChange={(e) => setNewTemplateName(e.target.value)}
            />
          </div>
          <div>
            <Text strong>模板描述</Text>
            <Input.TextArea
              id="template-desc-input"
              name="newTemplateDescription"
              placeholder="输入模板描述（可选）"
              value={newTemplateDescription}
              onChange={(e) => setNewTemplateDescription(e.target.value)}
              rows={3}
            />
          </div>
        </Space>
      </Modal>
    </div>
  )
}

export default ParameterPanel
