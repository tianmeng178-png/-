import React, { useState, useEffect } from 'react'
import { Card, Progress, Space, Typography, List, Button, Tag, Alert, message, Modal } from 'antd'
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  StopOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons'
import { useStore } from '../stores/useStore'
import { ApiService, WebSocketService, handleApiError } from '../services/api'

const { Title, Text } = Typography

const SimulationMonitor: React.FC = () => {
  const { 
    simulationStatus, 
    performanceMetrics, 
    parameters,
    setSimulationStatus,
    setPerformanceMetrics,
    setVisualizationData
  } = useStore()
  
  const [currentSimulationId, setCurrentSimulationId] = useState<string | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [wsService, setWsService] = useState<WebSocketService | null>(null)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'blue'
      case 'completed': return 'green'
      case 'error': return 'red'
      default: return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <PlayCircleOutlined />
      case 'completed': return <CheckCircleOutlined />
      case 'error': return <ExclamationCircleOutlined />
      default: return <ClockCircleOutlined />
    }
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
    return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
  }

  // WebSocket消息处理
  const handleWebSocketMessage = (data: any) => {
    console.log('📡 WebSocket消息:', data.type, data)
    
    switch (data.type) {
      case 'connected':
        console.log('✅ WebSocket连接成功:', data.message)
        break
      
      case 'subscribed':
        console.log('✅ 订阅成功:', data.message)
        break
      
      case 'status_update':
        setSimulationStatus(data.status)
        break
      
      case 'progress_update':
        setSimulationStatus(prev => ({
          ...prev,
          progress: data.progress,
          current_step: data.current_step,
          estimated_time_remaining: data.estimated_time_remaining
        }))
        break
      
      case 'log_message':
        setSimulationStatus(prev => ({
          ...prev,
          log_messages: [...prev.log_messages, data.message]
        }))
        break
      
      case 'simulation_completed':
        setSimulationStatus({
          status: 'completed',
          progress: 100,
          current_step: '仿真完成',
          log_messages: [...simulationStatus.log_messages, '仿真已完成']
        })
        setPerformanceMetrics(data.performance_metrics)
        setVisualizationData(data.visualization_data)
        message.success('仿真已完成！')
        break
      
      case 'error':
        setSimulationStatus({
          status: 'error',
          progress: simulationStatus.progress,
          current_step: '仿真错误',
          log_messages: [...simulationStatus.log_messages, `错误: ${data.message}`]
        })
        message.error(`仿真错误: ${data.message}`)
        break
      
      case 'heartbeat':
      case 'pong':
        // 心跳消息，不做处理
        break
      
      default:
        console.warn('未知的WebSocket消息类型:', data.type)
    }
  }

  const handleWebSocketError = (error: Event) => {
    console.error('WebSocket错误:', error)
    message.error('WebSocket连接错误')
  }

  const handleWebSocketClose = (event: CloseEvent) => {
    console.log('WebSocket连接关闭:', event.code, event.reason)
    
    // 根据错误代码显示不同的消息
    switch (event.code) {
      case 1000: // 正常关闭
        console.log('WebSocket正常关闭')
        break
      case 1006: // 异常关闭
        message.warning('WebSocket连接异常断开，正在尝试重连...')
        break
      case 1008: // 策略违规
        message.error('WebSocket连接被服务器拒绝，请检查仿真ID')
        break
      default:
        message.warning('WebSocket连接已断开，正在尝试重连...')
    }
  }

  // 开始仿真
  const handleStartSimulation = async () => {
    if (!parameters) {
      message.error('请先设置仿真参数')
      return
    }

    setIsConnecting(true)
    
    try {
      // 1. 开始仿真
      const response = await ApiService.startSimulation(parameters)
      const simulationId = response.simulation_id
      setCurrentSimulationId(simulationId)
      
      // 2. 更新状态
      setSimulationStatus({
        status: 'running',
        progress: 0,
        current_step: '初始化仿真环境',
        log_messages: ['开始仿真...']
      })
      
      // 3. 连接WebSocket
      const ws = new WebSocketService(
        handleWebSocketMessage,
        handleWebSocketError,
        handleWebSocketClose
      )
      ws.connect(simulationId)
      setWsService(ws)
      
      message.success('仿真已开始！')
      
    } catch (error) {
      console.error('开始仿真失败:', error)
      handleApiError(error)
      setSimulationStatus({
        status: 'error',
        progress: 0,
        current_step: '启动失败',
        log_messages: ['仿真启动失败']
      })
    } finally {
      setIsConnecting(false)
    }
  }

  // 暂停仿真
  const handlePauseSimulation = async () => {
    if (!currentSimulationId) return
    
    try {
      await ApiService.pauseSimulation(currentSimulationId)
      message.info('仿真已暂停')
    } catch (error) {
      console.error('暂停仿真失败:', error)
      handleApiError(error)
    }
  }

  // 停止仿真
  const handleStopSimulation = async () => {
    if (!currentSimulationId) return
    
    Modal.confirm({
      title: '确认停止仿真',
      content: '确定要停止当前仿真吗？已完成的进度将丢失。',
      onOk: async () => {
        try {
          await ApiService.stopSimulation(currentSimulationId)
          setSimulationStatus({
            status: 'idle',
            progress: 0,
            current_step: '等待开始',
            log_messages: []
          })
          setCurrentSimulationId(null)
          wsService?.disconnect()
          message.info('仿真已停止')
        } catch (error) {
          console.error('停止仿真失败:', error)
          handleApiError(error)
        }
      }
    })
  }

  // 获取仿真结果
  const handleGetResults = async () => {
    if (!currentSimulationId || simulationStatus.status !== 'completed') {
      message.warning('仿真尚未完成')
      return
    }
    
    try {
      const results = await ApiService.getSimulationResults(currentSimulationId)
      setPerformanceMetrics(results.performance_metrics)
      setVisualizationData(results.visualization_data)
      message.success('结果已加载')
    } catch (error) {
      console.error('获取结果失败:', error)
      handleApiError(error)
    }
  }

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (wsService) {
        wsService.disconnect()
      }
    }
  }, [wsService])

  return (
    <Card 
      title={
        <Space>
          <PlayCircleOutlined />
          <Text strong>仿真监控</Text>
        </Space>
      }
      className="simulation-status"
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        
        {/* 状态指示器 */}
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            {getStatusIcon(simulationStatus.status)}
            <Text strong style={{ color: 'white' }}>
              仿真状态: {simulationStatus.status === 'idle' ? '等待开始' : 
                       simulationStatus.status === 'running' ? '运行中' :
                       simulationStatus.status === 'completed' ? '已完成' : '错误'}
            </Text>
            <Tag color={getStatusColor(simulationStatus.status)}>
              {simulationStatus.status.toUpperCase()}
            </Tag>
          </Space>
          
          <Progress 
            percent={simulationStatus.progress}
            status={simulationStatus.status === 'error' ? 'exception' : 
                   simulationStatus.status === 'completed' ? 'success' : 'active'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          
          <Text style={{ color: 'white' }}>
            当前步骤: {simulationStatus.current_step}
          </Text>
          
          {simulationStatus.estimated_time_remaining && (
            <Text style={{ color: 'white' }}>
              <ClockCircleOutlined /> 预计剩余时间: {formatTime(simulationStatus.estimated_time_remaining)}
            </Text>
          )}
        </Space>

        {/* 操作按钮 */}
        <Space>
          <Button 
            type="primary" 
            icon={isConnecting ? <LoadingOutlined /> : <PlayCircleOutlined />}
            disabled={simulationStatus.status === 'running' || isConnecting}
            onClick={handleStartSimulation}
            loading={isConnecting}
          >
            {isConnecting ? '连接中...' : '开始仿真'}
          </Button>
          <Button 
            icon={<PauseCircleOutlined />}
            disabled={simulationStatus.status !== 'running'}
            onClick={handlePauseSimulation}
          >
            暂停
          </Button>
          <Button 
            danger 
            icon={<StopOutlined />}
            disabled={simulationStatus.status === 'idle'}
            onClick={handleStopSimulation}
          >
            停止
          </Button>
          {simulationStatus.status === 'completed' && (
            <Button 
              type="dashed" 
              icon={<CheckCircleOutlined />}
              onClick={handleGetResults}
            >
              获取结果
            </Button>
          )}
        </Space>

        {/* 性能指标 */}
        {performanceMetrics && (
          <Card size="small" title="性能指标">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Text strong>最高温度:</Text>
                <Text>{performanceMetrics.max_temperature.toFixed(1)} K</Text>
                <Text type="secondary">{(performanceMetrics.max_temperature - 273.15).toFixed(1)} °C</Text>
              </Space>
              
              <Space>
                <Text strong>压力降:</Text>
                <Text>{performanceMetrics.pressure_drop.toFixed(1)} Pa</Text>
                <Text type="secondary">{(performanceMetrics.pressure_drop / 1000).toFixed(3)} kPa</Text>
              </Space>
              
              <Space>
                <Text strong>传热系数:</Text>
                <Text>{performanceMetrics.heat_transfer_coefficient.toFixed(0)} W/m²K</Text>
              </Space>
              
              <Space>
                <Text strong>雷诺数:</Text>
                <Text>{performanceMetrics.reynolds_number.toFixed(0)}</Text>
                <Tag color={performanceMetrics.reynolds_number < 2300 ? 'blue' : 'orange'}>
                  {performanceMetrics.reynolds_number < 2300 ? '层流' : '湍流'}
                </Tag>
              </Space>
              
              <Space>
                <Text strong>努塞尔数:</Text>
                <Text>{performanceMetrics.nusselt_number.toFixed(1)}</Text>
              </Space>
            </Space>
          </Card>
        )}

        {/* 调试信息 */}
        <Card size="small" title="调试信息">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              仿真ID: {currentSimulationId || '无'}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              WebSocket状态: {wsService ? wsService.getConnectionState() : '未连接'}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              连接状态: {isConnecting ? '连接中...' : '就绪'}
            </Text>
          </Space>
        </Card>

        {/* 日志信息 */}
        {simulationStatus.log_messages.length > 0 && (
          <Card size="small" title="仿真日志">
            <List
              size="small"
              dataSource={simulationStatus.log_messages.slice(-5)} // 显示最近5条
              renderItem={(item, index) => (
                <List.Item>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    [{index + 1}] {item}
                  </Text>
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* 警告信息 */}
        {simulationStatus.status === 'error' && (
          <Alert
            message="仿真错误"
            description="仿真过程中出现错误，请检查参数设置和系统配置"
            type="error"
            showIcon
          />
        )}

        {simulationStatus.status === 'completed' && performanceMetrics && (
          <Alert
            message="仿真完成"
            description="仿真已成功完成，可以查看详细结果和分析报告"
            type="success"
            showIcon
          />
        )}
      </Space>
    </Card>
  )
}

export default SimulationMonitor