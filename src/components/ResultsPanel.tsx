import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import {
  Card,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Button,
  Tag,
  Tabs,
  Empty,
  Alert,
  Progress,
  List,
  Modal,
  message,
  Descriptions
} from 'antd'
import {
  BarChartOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  ShareAltOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  CompressOutlined,
  ExperimentOutlined,
  TrophyOutlined,
  CheckOutlined,
  CloseOutlined,
  HeatMapOutlined
} from '@ant-design/icons'
import { useStore } from '../stores/useStore'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  ReferenceLine
} from 'recharts'
import type { PerformanceMetrics, MicrochannelParameters } from '../types'

const { Title, Text } = Typography
const { TabPane } = Tabs

const getHeatmapColor = (value: number, min: number, max: number): string => {
  const ratio = max > min ? (value - min) / (max - min) : 0
  const clamped = Math.max(0, Math.min(1, ratio))
  const hue = 220 - clamped * 220
  return `hsl(${hue}, 80%, 55%)`
}

// 温度分布模拟数据
const generateTemperatureData = (metrics: PerformanceMetrics | null, params: MicrochannelParameters) => {
  if (!metrics) return []
  
  const data = []
  const points = 50
  const inletTemp = params.inlet_temperature
  const maxTemp = metrics.max_temperature
  
  for (let i = 0; i <= points; i++) {
    const position = i / points
    // 指数型温度分布
    const temp = inletTemp + (maxTemp - inletTemp) * Math.pow(position, 0.8)
    data.push({
      position: (position * 100).toFixed(1),
      temperature: temp.toFixed(2),
      temperatureC: (temp - 273.15).toFixed(2)
    })
  }
  return data
}

// 速度分布模拟数据
const generateVelocityData = (params: MicrochannelParameters) => {
  const data = []
  const points = 20
  const maxVelocity = params.inlet_velocity * 1.5
  
  for (let i = 0; i <= points; i++) {
    const y = i / points
    // 抛物线速度分布
    const velocity = maxVelocity * (1 - Math.pow(2 * y - 1, 2))
    data.push({
      position: (y * 100).toFixed(1),
      velocity: velocity.toFixed(3)
    })
  }
  return data
}

// 压力分布模拟数据
const generatePressureData = (metrics: PerformanceMetrics | null, _params: MicrochannelParameters) => {
  if (!metrics) return []
  
  const data = []
  const points = 30
  const pressureDrop = metrics.pressure_drop
  
  for (let i = 0; i <= points; i++) {
    const position = i / points
    // 线性压力下降
    const pressure = pressureDrop * (1 - position)
    data.push({
      position: (position * 100).toFixed(1),
      pressure: pressure.toFixed(2)
    })
  }
  return data
}

const generateTemperatureHeatmap = (metrics: PerformanceMetrics | null, params: MicrochannelParameters) => {
  const cols = 60
  const rows = 20
  if (!metrics) {
    return { cols, rows, values: [], min: 0, max: 0 }
  }

  const inletTemp = params.inlet_temperature
  const maxTemp = metrics.max_temperature
  const values: number[] = []
  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY

  for (let y = 0; y < rows; y++) {
    const yNorm = y / (rows - 1)
    const shape = 1 - 0.15 * Math.pow(2 * yNorm - 1, 2)
    for (let x = 0; x < cols; x++) {
      const xNorm = x / (cols - 1)
      const temp = inletTemp + (maxTemp - inletTemp) * Math.pow(xNorm, 0.8) * shape
      values.push(temp)
      min = Math.min(min, temp)
      max = Math.max(max, temp)
    }
  }

  return { cols, rows, values, min, max }
}

// 性能对比数据
const generateComparisonData = (metrics: PerformanceMetrics | null) => {
  if (!metrics) return []
  
  return [
    { name: '传热系数', value: metrics.heat_transfer_coefficient, unit: 'W/m²K', benchmark: 5000 },
    { name: '压力降', value: metrics.pressure_drop / 1000, unit: 'kPa', benchmark: 10 },
    { name: '雷诺数', value: metrics.reynolds_number, unit: '', benchmark: 2300 },
    { name: '努塞尔数', value: metrics.nusselt_number, unit: '', benchmark: 10 }
  ]
}

// 设计评估标准
const DESIGN_CRITERIA = [
  {
    key: 'temperature',
    name: '温度控制',
    description: '最高温度应低于85°C（电子芯片安全温度）',
    check: (metrics: PerformanceMetrics) => metrics.max_temperature < 358.15,
    getValue: (metrics: PerformanceMetrics) => `${(metrics.max_temperature - 273.15).toFixed(1)}°C`,
    getTarget: () => '< 85°C',
    weight: 0.3
  },
  {
    key: 'pressure',
    name: '压力降控制',
    description: '压力降应控制在合理范围内（< 50 kPa）',
    check: (metrics: PerformanceMetrics) => metrics.pressure_drop < 50000,
    getValue: (metrics: PerformanceMetrics) => `${(metrics.pressure_drop / 1000).toFixed(2)} kPa`,
    getTarget: () => '< 50 kPa',
    weight: 0.25
  },
  {
    key: 'flow_regime',
    name: '流动状态',
    description: '推荐层流状态（Re < 2300）以获得更好的温度均匀性',
    check: (metrics: PerformanceMetrics) => metrics.reynolds_number < 2300,
    getValue: (metrics: PerformanceMetrics) => `Re = ${metrics.reynolds_number.toFixed(0)}`,
    getTarget: () => '< 2300 (层流)',
    weight: 0.2
  },
  {
    key: 'heat_transfer',
    name: '传热性能',
    description: '传热系数应足够高（> 3000 W/m²K）',
    check: (metrics: PerformanceMetrics) => metrics.heat_transfer_coefficient > 3000,
    getValue: (metrics: PerformanceMetrics) => `${metrics.heat_transfer_coefficient.toFixed(0)} W/m²K`,
    getTarget: () => '> 3000 W/m²K',
    weight: 0.25
  }
]

const ResultsPanel: React.FC = () => {
  const { performanceMetrics, parameters } = useStore()
  const [activeTab, setActiveTab] = useState('overview')
  const [exportLoading, setExportLoading] = useState(false)
  const heatmapRef = useRef<HTMLCanvasElement>(null)

  // 计算设计评分
  const designScore = useMemo(() => {
    if (!performanceMetrics) return 0
    
    let score = 0
    DESIGN_CRITERIA.forEach(criteria => {
      if (criteria.check(performanceMetrics)) {
        score += criteria.weight * 100
      } else {
        // 部分得分
        score += criteria.weight * 50
      }
    })
    
    return Math.round(score)
  }, [performanceMetrics])

  // 获取评分等级
  const getScoreGrade = (score: number) => {
    if (score >= 90) return { grade: 'A', color: '#52c41a', text: '优秀' }
    if (score >= 80) return { grade: 'B', color: '#1890ff', text: '良好' }
    if (score >= 70) return { grade: 'C', color: '#faad14', text: '合格' }
    if (score >= 60) return { grade: 'D', color: '#fa8c16', text: '及格' }
    return { grade: 'F', color: '#ff4d4f', text: '需改进' }
  }

  // 生成图表数据
  const temperatureData = useMemo(() => 
    generateTemperatureData(performanceMetrics, parameters),
    [performanceMetrics, parameters]
  )
  
  const velocityData = useMemo(() => 
    generateVelocityData(parameters),
    [parameters]
  )
  
  const pressureData = useMemo(() => 
    generatePressureData(performanceMetrics, parameters),
    [performanceMetrics, parameters]
  )
  
  const comparisonData = useMemo(() => 
    generateComparisonData(performanceMetrics),
    [performanceMetrics]
  )

  const heatmapData = useMemo(() => 
    generateTemperatureHeatmap(performanceMetrics, parameters),
    [performanceMetrics, parameters]
  )

  useEffect(() => {
    if (!heatmapRef.current || heatmapData.values.length === 0) return

    const canvas = heatmapRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const { cols, rows, values, min, max } = heatmapData
    const width = canvas.clientWidth || 600
    const height = 240
    const dpr = window.devicePixelRatio || 1

    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    const cellWidth = width / cols
    const cellHeight = height / rows

    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const value = values[y * cols + x]
        ctx.fillStyle = getHeatmapColor(value, min, max)
        ctx.fillRect(x * cellWidth, (rows - 1 - y) * cellHeight, cellWidth + 1, cellHeight + 1)
      }
    }
  }, [heatmapData])

  // 导出PDF报告
  const exportPDF = useCallback(async () => {
    setExportLoading(true)
    try {
      // 模拟导出过程
      await new Promise(resolve => setTimeout(resolve, 1500))
      message.success('PDF报告已生成并下载')
    } catch (error) {
      message.error('导出失败')
    } finally {
      setExportLoading(false)
    }
  }, [])

  // 导出Excel数据
  const exportExcel = useCallback(async () => {
    setExportLoading(true)
    try {
      // 构建CSV数据
      const csvContent = [
        ['参数', '值', '单位'],
        ['最高温度', performanceMetrics?.max_temperature.toFixed(2) || '', 'K'],
        ['压力降', performanceMetrics?.pressure_drop.toFixed(2) || '', 'Pa'],
        ['传热系数', performanceMetrics?.heat_transfer_coefficient.toFixed(2) || '', 'W/m²K'],
        ['雷诺数', performanceMetrics?.reynolds_number.toFixed(2) || '', ''],
        ['努塞尔数', performanceMetrics?.nusselt_number.toFixed(2) || '', '']
      ].map(row => row.join(',')).join('\n')

      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `simulation-results-${Date.now()}.csv`
      link.click()
      
      message.success('数据已导出为CSV')
    } catch (error) {
      message.error('导出失败')
    } finally {
      setExportLoading(false)
    }
  }, [performanceMetrics])

  // 分享结果
  const shareResults = useCallback(() => {
    Modal.info({
      title: '分享仿真结果',
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>仿真ID: {performanceMetrics ? 'SIM-' + Date.now() : 'N/A'}</Text>
          <Text type="secondary">您可以将此ID分享给其他人查看结果</Text>
        </Space>
      )
    })
  }, [performanceMetrics])

  if (!performanceMetrics) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" align="center">
              <Text>暂无仿真结果</Text>
              <Text type="secondary">请先完成仿真计算</Text>
            </Space>
          }
        >
          <Button type="primary" disabled>
            查看结果
          </Button>
        </Empty>
      </Card>
    )
  }

  const scoreInfo = getScoreGrade(designScore)
  const tabItems = useMemo(() => ([
    {
      key: 'overview',
      label: <Space><BarChartOutlined />图表分析</Space>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Card size="small" title="温度沿流动方向分布">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={temperatureData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="position"
                  label={{ value: '相对位置 (%)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  label={{ value: '温度 (K)', angle: -90, position: 'insideLeft' }}
                />
                <RechartsTooltip
                  formatter={(value: any) => [`${value} K`, '温度']}
                  labelFormatter={(label) => `位置: ${label}%`}
                />
                <Area
                  type="monotone"
                  dataKey="temperature"
                  stroke="#ff4d4f"
                  fill="#ff4d4f"
                  fillOpacity={0.3}
                />
                <ReferenceLine
                  y={358.15}
                  stroke="#ff4d4f"
                  strokeDasharray="3 3"
                  label={{ value: '安全上限 85°C', position: 'top' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          <Card size="small" title="通道截面速度分布">
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={velocityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="position"
                  label={{ value: '相对高度 (%)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  label={{ value: '速度 (m/s)', angle: -90, position: 'insideLeft' }}
                />
                <RechartsTooltip />
                <Line
                  type="monotone"
                  dataKey="velocity"
                  stroke="#52c41a"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card size="small" title="压力沿流动方向分布">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={pressureData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="position"
                  label={{ value: '相对位置 (%)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  label={{ value: '压力 (Pa)', angle: -90, position: 'insideLeft' }}
                />
                <RechartsTooltip />
                <Area
                  type="monotone"
                  dataKey="pressure"
                  stroke="#1890ff"
                  fill="#1890ff"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Space>
      )
    },
    {
      key: 'slice2d',
      label: <Space><HeatMapOutlined />2D剖面</Space>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Card size="small" title="温度剖面(示意)">
            <div style={{ width: '100%', height: 240 }}>
              <canvas ref={heatmapRef} style={{ width: '100%', height: '240px' }} />
            </div>
            <Space style={{ marginTop: 8 }}>
              <Text type="secondary">
                最小 {(heatmapData.min - 273.15).toFixed(1)} °C
              </Text>
              <Text type="secondary">
                最大 {(heatmapData.max - 273.15).toFixed(1)} °C
              </Text>
            </Space>
            <Alert
              style={{ marginTop: 8 }}
              type="info"
              showIcon
              message="说明"
              description="该剖面为基于仿真指标的示意分布，用于快速趋势判断。真实场请使用 ParaView 查看。"
            />
          </Card>
        </Space>
      )
    },
    {
      key: 'evaluation',
      label: <Space><CheckCircleOutlined />设计评估</Space>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {DESIGN_CRITERIA.map(criteria => {
            const passed = criteria.check(performanceMetrics)
            return (
              <Card
                key={criteria.key}
                size="small"
                style={{
                  borderLeft: `4px solid ${passed ? '#52c41a' : '#ff4d4f'}`
                }}
              >
                <Row align="middle">
                  <Col span={16}>
                    <Space direction="vertical" size="small">
                      <Space>
                        <Text strong>{criteria.name}</Text>
                        {passed ? (
                          <Tag color="success" icon={<CheckOutlined />}>通过</Tag>
                        ) : (
                          <Tag color="error" icon={<CloseOutlined />}>未通过</Tag>
                        )}
                      </Space>
                      <Text type="secondary">{criteria.description}</Text>
                    </Space>
                  </Col>
                  <Col span={8} style={{ textAlign: 'right' }}>
                    <Space direction="vertical" size="small" align="end">
                      <Text strong>{criteria.getValue(performanceMetrics)}</Text>
                      <Text type="secondary">目标: {criteria.getTarget()}</Text>
                    </Space>
                  </Col>
                </Row>
              </Card>
            )
          })}

          <Alert
            message={`设计评估: ${scoreInfo.text}`}
            description={
              designScore >= 80
                ? '您的设计表现良好，满足主要工程要求。'
                : designScore >= 60
                ? '设计基本可用，但仍有优化空间。建议调整参数以提高性能。'
                : '设计存在明显问题，建议重新评估参数设置。'
            }
            type={designScore >= 80 ? 'success' : designScore >= 60 ? 'warning' : 'error'}
            showIcon
          />
        </Space>
      )
    },
    {
      key: 'comparison',
      label: <Space><ExperimentOutlined />参数对比</Space>,
      children: (
        <>
          <Card size="small" title="性能指标对比">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={comparisonData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={80} />
                <RechartsTooltip />
                <Legend />
                <Bar dataKey="value" name="当前值" fill="#1890ff" />
                <Bar dataKey="benchmark" name="参考值" fill="#d9d9d9" />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card size="small" title="设计参数汇总" style={{ marginTop: 16 }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="通道宽度">{(parameters.channel_width * 1e6).toFixed(0)} μm</Descriptions.Item>
              <Descriptions.Item label="通道高度">{(parameters.channel_height * 1e6).toFixed(0)} μm</Descriptions.Item>
              <Descriptions.Item label="通道长度">{(parameters.channel_length * 1e3).toFixed(1)} mm</Descriptions.Item>
              <Descriptions.Item label="通道数量">{parameters.channel_count} 个</Descriptions.Item>
              <Descriptions.Item label="入口速度">{parameters.inlet_velocity.toFixed(2)} m/s</Descriptions.Item>
              <Descriptions.Item label="入口温度">{(parameters.inlet_temperature - 273.15).toFixed(1)} °C</Descriptions.Item>
              <Descriptions.Item label="热通量">{(parameters.heat_flux / 1e4).toFixed(1)} W/cm²</Descriptions.Item>
              <Descriptions.Item label="流体类型">{parameters.fluid_type === 'water' ? '水' : '空气'}</Descriptions.Item>
              <Descriptions.Item label="固体材料">
                {parameters.solid_material === 'copper' ? '铜' :
                 parameters.solid_material === 'aluminum' ? '铝' : '硅'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      )
    },
    {
      key: 'suggestions',
      label: <Space><InfoCircleOutlined />优化建议</Space>,
      children: (
        <List
          header={<Text strong>基于仿真结果的优化建议</Text>}
          bordered
          dataSource={[
            ...(performanceMetrics.max_temperature > 358.15 ? [
              {
                type: 'warning',
                title: '温度过高警告',
                content: '最高温度超过85°C，建议：增加入口流速、减小通道宽度、或增加通道数量以提高散热效率。'
              }
            ] : []),
            ...(performanceMetrics.pressure_drop > 50000 ? [
              {
                type: 'warning',
                title: '压力降过大',
                content: '压力降超过50kPa，建议：增加通道宽度、减少通道长度、或降低入口流速。'
              }
            ] : []),
            ...(performanceMetrics.reynolds_number > 2300 ? [
              {
                type: 'info',
                title: '流动状态为湍流',
                content: '当前为湍流状态，传热性能较好，但压力降会增加。如需层流，请降低流速或减小水力直径。'
              }
            ] : [
              {
                type: 'success',
                title: '层流状态',
                content: '当前为层流状态，流动稳定，温度分布均匀。'
              }
            ]),
            {
              type: 'info',
              title: '传热性能分析',
              content: `当前传热系数为 ${performanceMetrics.heat_transfer_coefficient.toFixed(0)} W/m²K，` +
                `${performanceMetrics.heat_transfer_coefficient > 5000 ? '表现优秀' : '仍有提升空间'}。`
            }
          ]}
          renderItem={item => (
            <List.Item>
              <Alert
                message={item.title}
                description={item.content}
                type={item.type as 'success' | 'info' | 'warning'}
                showIcon
                style={{ width: '100%' }}
              />
            </List.Item>
          )}
        />
      )
    }
  ]), [comparisonData, designScore, heatmapData, parameters, performanceMetrics, pressureData, scoreInfo, temperatureData, velocityData])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 结果概览 */}
      <Card
        title={
          <Space>
            <TrophyOutlined />
            <Text strong>仿真结果概览</Text>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<FilePdfOutlined />}
              onClick={exportPDF}
              loading={exportLoading}
              size="small"
            >
              导出PDF
            </Button>
            <Button
              icon={<FileExcelOutlined />}
              onClick={exportExcel}
              loading={exportLoading}
              size="small"
            >
              导出数据
            </Button>
            <Button
              icon={<ShareAltOutlined />}
              onClick={shareResults}
              size="small"
            >
              分享
            </Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]}>
          {/* 设计评分 */}
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Title level={2} style={{ color: scoreInfo.color, margin: 0 }}>
                {designScore}
              </Title>
              <Text strong style={{ color: scoreInfo.color }}>
                等级 {scoreInfo.grade} - {scoreInfo.text}
              </Text>
              <Progress
                percent={designScore}
                strokeColor={scoreInfo.color}
                showInfo={false}
                size="small"
              />
            </Card>
          </Col>

          {/* 关键指标 */}
          <Col span={18}>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="最高温度"
                    value={performanceMetrics.max_temperature.toFixed(1)}
                    suffix="K"
                    valueStyle={{
                      color: performanceMetrics.max_temperature > 358.15 ? '#ff4d4f' : '#52c41a'
                    }}
                  />
                  <Text type="secondary">
                    {(performanceMetrics.max_temperature - 273.15).toFixed(1)} °C
                  </Text>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="压力降"
                    value={(performanceMetrics.pressure_drop / 1000).toFixed(3)}
                    suffix="kPa"
                    prefix={<CompressOutlined />}
                  />
                  <Text type="secondary">
                    {performanceMetrics.pressure_drop.toFixed(1)} Pa
                  </Text>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="传热系数"
                    value={performanceMetrics.heat_transfer_coefficient.toFixed(0)}
                    suffix="W/m²K"
                    prefix={<ThunderboltOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="雷诺数"
                    value={performanceMetrics.reynolds_number.toFixed(0)}
                    prefix={<ExperimentOutlined />}
                  />
                  <Tag color={performanceMetrics.reynolds_number < 2300 ? 'blue' : 'orange'}>
                    {performanceMetrics.reynolds_number < 2300 ? '层流' : '湍流'}
                  </Tag>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="努塞尔数"
                    value={performanceMetrics.nusselt_number.toFixed(1)}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="流动状态"
                    value={performanceMetrics.reynolds_number < 2300 ? '层流' : '湍流'}
                    valueStyle={{
                      color: performanceMetrics.reynolds_number < 2300 ? '#1890ff' : '#faad14'
                    }}
                  />
                </Card>
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      {/* 详细分析标签页 */}
      <Card>
        {false && (
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 概览 */}
          <TabPane
            tab={<Space><BarChartOutlined />图表分析</Space>}
            key="overview"
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 温度分布图 */}
              <Card size="small" title="温度沿流动方向分布">
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={temperatureData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="position" 
                      label={{ value: '相对位置 (%)', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis 
                      label={{ value: '温度 (K)', angle: -90, position: 'insideLeft' }}
                    />
                    <RechartsTooltip 
                      formatter={(value: any) => [`${value} K`, '温度']}
                      labelFormatter={(label) => `位置: ${label}%`}
                    />
                    <Area
                      type="monotone"
                      dataKey="temperature"
                      stroke="#ff4d4f"
                      fill="#ff4d4f"
                      fillOpacity={0.3}
                    />
                    <ReferenceLine 
                      y={358.15} 
                      stroke="#ff4d4f" 
                      strokeDasharray="3 3"
                      label={{ value: '安全上限 85°C', position: 'top' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              {/* 速度分布图 */}
              <Card size="small" title="通道截面速度分布">
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={velocityData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="position"
                      label={{ value: '相对高度 (%)', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis 
                      label={{ value: '速度 (m/s)', angle: -90, position: 'insideLeft' }}
                    />
                    <RechartsTooltip />
                    <Line
                      type="monotone"
                      dataKey="velocity"
                      stroke="#52c41a"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Card>

              {/* 压力分布图 */}
              <Card size="small" title="压力沿流动方向分布">
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={pressureData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="position"
                      label={{ value: '相对位置 (%)', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis 
                      label={{ value: '压力 (Pa)', angle: -90, position: 'insideLeft' }}
                    />
                    <RechartsTooltip />
                    <Area
                      type="monotone"
                      dataKey="pressure"
                      stroke="#1890ff"
                      fill="#1890ff"
                      fillOpacity={0.3}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
            </Space>
          </TabPane>

          <TabPane
            tab={<Space><HeatMapOutlined />2D剖面</Space>}
            key="slice2d"
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Card size="small" title="温度剖面（示意）">
                <div style={{ width: '100%', height: 240 }}>
                  <canvas ref={heatmapRef} style={{ width: '100%', height: '240px' }} />
                </div>
                <Space style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    最小: {(heatmapData.min - 273.15).toFixed(1)} °C
                  </Text>
                  <Text type="secondary">
                    最大: {(heatmapData.max - 273.15).toFixed(1)} °C
                  </Text>
                </Space>
                <Alert
                  style={{ marginTop: 8 }}
                  type="info"
                  showIcon
                  message="说明"
                  description="该剖面为基于仿真指标的示意分布，用于快速趋势判断。真实场请使用 ParaView 查看。"
                />
              </Card>
            </Space>
          </TabPane>

          {/* 设计评估 */}
          <TabPane
            tab={<Space><CheckCircleOutlined />设计评估</Space>}
            key="evaluation"
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {DESIGN_CRITERIA.map(criteria => {
                const passed = criteria.check(performanceMetrics)
                return (
                  <Card
                    key={criteria.key}
                    size="small"
                    style={{
                      borderLeft: `4px solid ${passed ? '#52c41a' : '#ff4d4f'}`
                    }}
                  >
                    <Row align="middle">
                      <Col span={16}>
                        <Space direction="vertical" size="small">
                          <Space>
                            <Text strong>{criteria.name}</Text>
                            {passed ? (
                              <Tag color="success" icon={<CheckOutlined />}>通过</Tag>
                            ) : (
                              <Tag color="error" icon={<CloseOutlined />}>未通过</Tag>
                            )}
                          </Space>
                          <Text type="secondary">{criteria.description}</Text>
                        </Space>
                      </Col>
                      <Col span={8} style={{ textAlign: 'right' }}>
                        <Space direction="vertical" size="small" align="end">
                          <Text strong>{criteria.getValue(performanceMetrics)}</Text>
                          <Text type="secondary">目标: {criteria.getTarget()}</Text>
                        </Space>
                      </Col>
                    </Row>
                  </Card>
                )
              })}

              {/* 总体评估 */}
              <Alert
                message={`设计评估: ${scoreInfo.text}`}
                description={
                  designScore >= 80
                    ? '您的设计表现良好，满足主要工程要求。'
                    : designScore >= 60
                    ? '设计基本可用，但仍有优化空间。建议调整参数以提高性能。'
                    : '设计存在明显问题，建议重新评估参数设置。'
                }
                type={designScore >= 80 ? 'success' : designScore >= 60 ? 'warning' : 'error'}
                showIcon
              />
            </Space>
          </TabPane>

          {/* 参数对比 */}
          <TabPane
            tab={<Space><ExperimentOutlined />参数对比</Space>}
            key="comparison"
          >
            <Card size="small" title="性能指标对比">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={comparisonData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={80} />
                  <RechartsTooltip />
                  <Legend />
                  <Bar dataKey="value" name="当前值" fill="#1890ff" />
                  <Bar dataKey="benchmark" name="参考值" fill="#d9d9d9" />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card size="small" title="设计参数汇总" style={{ marginTop: 16 }}>
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="通道宽度">{(parameters.channel_width * 1e6).toFixed(0)} μm</Descriptions.Item>
                <Descriptions.Item label="通道高度">{(parameters.channel_height * 1e6).toFixed(0)} μm</Descriptions.Item>
                <Descriptions.Item label="通道长度">{(parameters.channel_length * 1e3).toFixed(1)} mm</Descriptions.Item>
                <Descriptions.Item label="通道数量">{parameters.channel_count} 个</Descriptions.Item>
                <Descriptions.Item label="入口速度">{parameters.inlet_velocity.toFixed(2)} m/s</Descriptions.Item>
                <Descriptions.Item label="入口温度">{(parameters.inlet_temperature - 273.15).toFixed(1)} °C</Descriptions.Item>
                <Descriptions.Item label="热通量">{(parameters.heat_flux / 1e4).toFixed(1)} W/cm²</Descriptions.Item>
                <Descriptions.Item label="流体类型">{parameters.fluid_type === 'water' ? '水' : '空气'}</Descriptions.Item>
                <Descriptions.Item label="固体材料">
                  {parameters.solid_material === 'copper' ? '铜' : 
                   parameters.solid_material === 'aluminum' ? '铝' : '硅'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </TabPane>

          {/* 优化建议 */}
          <TabPane
            tab={<Space><InfoCircleOutlined />优化建议</Space>}
            key="suggestions"
          >
            <List
              header={<Text strong>基于仿真结果的优化建议</Text>}
              bordered
              dataSource={[
                ...(performanceMetrics.max_temperature > 358.15 ? [
                  {
                    type: 'warning',
                    title: '温度过高警告',
                    content: '最高温度超过85°C，建议：增加入口流速、减小通道宽度、或增加通道数量以提高散热效率。'
                  }
                ] : []),
                ...(performanceMetrics.pressure_drop > 50000 ? [
                  {
                    type: 'warning',
                    title: '压力降过大',
                    content: '压力降超过50kPa，建议：增加通道宽度、减少通道长度、或降低入口流速。'
                  }
                ] : []),
                ...(performanceMetrics.reynolds_number > 2300 ? [
                  {
                    type: 'info',
                    title: '流动状态为湍流',
                    content: '当前为湍流状态，传热性能较好，但压力降会增加。如需层流，请降低流速或减小水力直径。'
                  }
                ] : [
                  {
                    type: 'success',
                    title: '层流状态',
                    content: '当前为层流状态，流动稳定，温度分布均匀。'
                  }
                ]),
                {
                  type: 'info',
                  title: '传热性能分析',
                  content: `当前传热系数为 ${performanceMetrics.heat_transfer_coefficient.toFixed(0)} W/m²K，` +
                    `${performanceMetrics.heat_transfer_coefficient > 5000 ? '表现优秀' : '仍有提升空间'}。`
                }
              ]}
              renderItem={item => (
                <List.Item>
                  <Alert
                    message={item.title}
                    description={item.content}
                    type={item.type as 'success' | 'info' | 'warning'}
                    showIcon
                    style={{ width: '100%' }}
                  />
                </List.Item>
              )}
            />
          </TabPane>
        </Tabs>
        )}
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          destroyInactiveTabPane
        />
      </Card>
    </Space>
  )
}

export default ResultsPanel
