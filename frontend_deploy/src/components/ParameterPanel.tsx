import React from 'react'
import { Card, InputNumber, Slider, Select, Space, Typography, Alert, Button } from 'antd'
import { 
  SettingOutlined, 
  BulbOutlined, 
  SafetyOutlined,
  ThunderboltOutlined 
} from '@ant-design/icons'
import { useStore } from '../stores/useStore'

const { Title, Text } = Typography
const { Option } = Select

const ParameterPanel: React.FC = () => {
  const { 
    parameters, 
    updateParameter, 
    getParameterValidation,
    parameterSuggestions,
    validationResult 
  } = useStore()

  // 参数配置
  const parameterConfigs = [
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
          scale: 1e6, // 转换为微米显示
          description: '微通道宽度，影响流动阻力和传热效率'
        },
        {
          key: 'channel_height',
          label: '通道高度',
          unit: 'μm',
          min: 100,
          max: 2000,
          step: 50,
          scale: 1e6,
          description: '微通道高度，与宽度共同决定纵横比'
        },
        {
          key: 'channel_length',
          label: '通道长度',
          unit: 'mm',
          min: 1,
          max: 50,
          step: 1,
          scale: 1e3,
          description: '微通道长度，影响压力降和温升'
        },
        {
          key: 'channel_count',
          label: '通道数量',
          unit: '个',
          min: 1,
          max: 100,
          step: 1,
          scale: 1,
          description: '并行通道数量，决定总散热面积'
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
          step: 0.05,
          scale: 1,
          description: '冷却流体入口速度，影响流动状态和散热能力'
        },
        {
          key: 'inlet_temperature',
          label: '入口温度',
          unit: '°C',
          min: 10,
          max: 80,
          step: 1,
          scale: 1,
          offset: -273.15, // K转°C
          description: '冷却流体入口温度'
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
          min: 10,
          max: 100,
          step: 5,
          scale: 1e-4, // W/m²转W/cm²
          description: '单位面积热负荷，决定散热需求'
        },
        {
          key: 'base_temperature',
          label: '基底温度',
          unit: '°C',
          min: 50,
          max: 150,
          step: 5,
          scale: 1,
          offset: -273.15,
          description: '散热器基底目标温度'
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
          type: 'select' as const,
          options: [
            { label: '水', value: 'water' },
            { label: '空气', value: 'air' }
          ],
          description: '冷却介质选择'
        },
        {
          key: 'solid_material',
          label: '固体材料',
          type: 'select' as const,
          options: [
            { label: '铜', value: 'copper' },
            { label: '铝', value: 'aluminum' },
            { label: '硅', value: 'silicon' }
          ],
          description: '散热器材料选择'
        }
      ]
    }
  ]

  const handleParameterChange = (key: string, value: any) => {
    const config = parameterConfigs.flatMap(cat => cat.parameters).find(p => p.key === key)
    if (!config) return

    // 处理单位转换
    let finalValue = value
    if (config.scale && config.type !== 'select') {
      finalValue = value / config.scale
    }
    if (config.offset && config.type !== 'select') {
      finalValue = value - config.offset
    }

    updateParameter(key as any, finalValue)
  }

  const getDisplayValue = (key: string, value: any) => {
    const config = parameterConfigs.flatMap(cat => cat.parameters).find(p => p.key === key)
    if (!config) return value

    let displayValue = value
    if (config.scale && config.type !== 'select') {
      displayValue = value * config.scale
    }
    if (config.offset && config.type !== 'select') {
      displayValue = value + config.offset
    }

    return Math.round(displayValue * 100) / 100 // 保留两位小数
  }

  return (
    <div className="parameter-panel">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        
        {/* 参数建议提示 */}
        {parameterSuggestions && (
          <Alert
            message="智能参数建议"
            description={
              <Space direction="vertical">
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
          />
        )}

        {/* 验证结果 */}
        {validationResult && (
          <Alert
            message={`参数验证: ${validationResult.overall_status === 'valid' ? '通过' : '需要调整'}`}
            description={
              <Space direction="vertical">
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
            type={validationResult.overall_status === 'valid' ? 'success' : 'warning'}
          />
        )}

        {/* 参数输入区域 */}
        {parameterConfigs.map((category) => (
          <Card 
            key={category.category}
            title={
              <Space>
                {category.icon}
                <Text strong>{category.category}</Text>
              </Space>
            }
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {category.parameters.map((param) => {
                const value = parameters[param.key as keyof typeof parameters]
                const displayValue = getDisplayValue(param.key, value)
                const validation = getParameterValidation(param.key)
                
                return (
                  <div key={param.key}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <Text strong>{param.label}</Text>
                        <Text type="secondary" className="engineering-unit">
                          {param.unit}
                        </Text>
                      </Space>
                      
                      {param.type === 'select' ? (
                        <Select
                          value={value}
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
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Slider
                            min={param.min}
                            max={param.max}
                            step={param.step}
                            value={displayValue as number}
                            onChange={(val) => handleParameterChange(param.key, val)}
                            tooltip={{ formatter: (val) => `${val} ${param.unit}` }}
                            className="parameter-slider"
                          />
                          <InputNumber
                            min={param.min}
                            max={param.max}
                            step={param.step}
                            value={displayValue}
                            onChange={(val) => handleParameterChange(param.key, val)}
                            addonAfter={param.unit}
                            style={{ width: '100%' }}
                          />
                        </Space>
                      )}
                      
                      {/* 验证状态显示 */}
                      <div className={`validation-status ${validation.status}`}>
                        {validation.status === 'valid' ? '✅' : 
                         validation.status === 'warning' ? '⚠️' : '❌'} {validation.message}
                      </div>
                      
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {param.description}
                      </Text>
                    </Space>
                  </div>
                )
              })}
            </Space>
          </Card>
        ))}

        {/* 操作按钮 */}
        <Space>
          <Button type="primary" icon={<BulbOutlined />}>
            智能优化
          </Button>
          <Button icon={<SafetyOutlined />}>
            验证参数
          </Button>
          <Button type="dashed">
            重置默认值
          </Button>
        </Space>
      </Space>
    </div>
  )
}

export default ParameterPanel