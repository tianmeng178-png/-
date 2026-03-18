import React, { useState, useEffect, useRef, useCallback, useDeferredValue, startTransition } from 'react'
import { 
  Card, 
  Progress, 
  Space, 
  Typography, 
  List, 
  Button, 
  Tag, 
  Alert, 
  message, 
  Modal,
  Badge,
  Timeline,
  Statistic,
  Row,
  Col,
  Empty,
  Switch,
  Tooltip
} from 'antd'
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  StopOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  DownloadOutlined,
  FileTextOutlined,
  BugOutlined,
  HistoryOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  CompressOutlined,
  FolderOpenOutlined,
  EyeOutlined,
  SyncOutlined
} from '@ant-design/icons'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as ReTooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { useStore } from '../stores/useStore'
import { ApiService, WebSocketService } from '../services/api'
import type { SimulationStatus } from '../types'
import ParaViewRemoteView from './ParaViewRemoteView'

const { Text } = Typography

// 仿真步骤定义
const SIMULATION_STEPS = [
  { key: 'initialization', label: '初始化环境', description: '准备仿真工作目录和配置文件' },
  { key: 'mesh_generation', label: '网格生成', description: '生成计算网格' },
  { key: 'solver_setup', label: '求解器设置', description: '配置物理模型和边界条件' },
  { key: 'running', label: '求解计算', description: '执行CFD求解计算' },
  { key: 'post_processing', label: '后处理', description: '处理仿真结果数据' },
  { key: 'completed', label: '完成', description: '仿真任务已完成' }
]

// 日志级别颜色
const LOG_LEVEL_COLORS: Record<string, string> = {
  'INFO': '#1890ff',
  'WARN': '#faad14',
  'ERROR': '#ff4d4f',
  'DEBUG': '#722ed1',
  'SUCCESS': '#52c41a'
}

const RESIDUAL_COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2']

// 格式化时间
const formatTime = (seconds: number): string => {
  if (!seconds || seconds < 0) return '--:--'
  if (seconds < 60) return `${Math.floor(seconds)}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.floor(seconds % 60)}秒`
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
}

// 格式化日期时间
const formatDateTime = (date: Date): string => {
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit',
    hour12: false 
  })
}

interface LogEntry {
  id: string
  timestamp: Date
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'SUCCESS'
  message: string
  step?: string
}

interface ResidualPoint {
  time: number
  [key: string]: number
}

interface SimulationHistory {
  id: string
  startTime: Date
  endTime?: Date
  status: SimulationStatus['status']
  parameters: string
}

const SimulationMonitor: React.FC = () => {
  const { 
    simulationStatus, 
    performanceMetrics, 
    parameters,
    setSimulationStatus,
    setPerformanceMetrics,
    setVisualizationData,
    setActiveTab
  } = useStore()
  
  const [currentSimulationId, setCurrentSimulationId] = useState<string | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [wsService, setWsService] = useState<WebSocketService | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [showDebugInfo, setShowDebugInfo] = useState(false)
  const [simulationHistory, setSimulationHistory] = useState<SimulationHistory[]>([])
  const [elapsedTime, setElapsedTime] = useState(0)
  const [startTime, setStartTime] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [paraviewWebUrl, setParaviewWebUrl] = useState<string | null>(null)
  const [paraviewWebStatus, setParaviewWebStatus] = useState<string>('idle')
  const [paraviewWebWsUrl, setParaviewWebWsUrl] = useState<string | null>(null)
  const [paraviewViewStatus, setParaviewViewStatus] = useState<'idle' | 'connecting' | 'connected' | 'error' | 'closed'>('idle')
  const [residualSeries, setResidualSeries] = useState<ResidualPoint[]>([])
  const [residualFields, setResidualFields] = useState<string[]>([])
  const [solverLogs, setSolverLogs] = useState<string[]>([])
  const [solverAutoScroll, setSolverAutoScroll] = useState(true)
  const [residualChartReady, setResidualChartReady] = useState(false)

  const logContainerRef = useRef<HTMLDivElement>(null)
  const solverLogContainerRef = useRef<HTMLDivElement>(null)
  const residualChartRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastWsMessageRef = useRef<number>(0)
  const resultsFetchedRef = useRef(false)
  const residualFieldSetRef = useRef<Set<string>>(new Set())
  const logStickToBottomRef = useRef(true)
  const solverStickToBottomRef = useRef(true)
  const deferredResidualSeries = useDeferredValue(residualSeries)
  const deferredSolverLogs = useDeferredValue(solverLogs)

  const handleLogScroll = useCallback(() => {
    const container = logContainerRef.current
    if (!container) return
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight
    logStickToBottomRef.current = distance < 24
    if (!logStickToBottomRef.current && autoScroll) {
      setAutoScroll(false)
    }
  }, [autoScroll])

  const handleSolverLogScroll = useCallback(() => {
    const container = solverLogContainerRef.current
    if (!container) return
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight
    solverStickToBottomRef.current = distance < 24
    setSolverAutoScroll(solverStickToBottomRef.current)
  }, [])

  // 自动滚动到日志底部
  useEffect(() => {
    const container = logContainerRef.current
    if (!container || !autoScroll || !logStickToBottomRef.current) return
    container.scrollTop = container.scrollHeight
  }, [logs, autoScroll])

  useEffect(() => {
    const container = solverLogContainerRef.current
    if (!container || !solverAutoScroll || !solverStickToBottomRef.current) return
    container.scrollTop = container.scrollHeight
  }, [solverLogs, solverAutoScroll])

  useEffect(() => {
    const container = residualChartRef.current
    if (!container) return
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      setResidualChartReady(width > 10 && height > 10)
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  // 计时器
  useEffect(() => {
    if (simulationStatus.status === 'running' && startTime) {
      timerRef.current = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime.getTime()) / 1000))
      }, 1000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [simulationStatus.status, startTime])

  // 添加日志
  const addLog = useCallback((message: string, level: LogEntry['level'] = 'INFO', step?: string) => {
    const newLog: LogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      level,
      message,
      step
    }
    setLogs(prev => [...prev, newLog])
  }, [])

  // WebSocket消息处理
  const handleWebSocketMessage = useCallback((data: any) => {
    console.log('📡 WebSocket消息:', data.type, data)
    
    switch (data.type) {
      case 'connected':
        setWsConnected(true)
        addLog('WebSocket连接成功', 'SUCCESS')
        break
      
      case 'subscribed':
        addLog(`已订阅仿真任务: ${data.simulation_id}`, 'INFO')
        break

      case 'paraview_web': {
        const pvData = data.data || data
        setParaviewWebStatus(pvData.status || 'idle')
        if (pvData.ws_url) {
          setParaviewWebWsUrl(pvData.ws_url)
        }
        if (pvData.url) {
          setParaviewWebUrl(pvData.url)
          setParaviewViewStatus('connecting')
          addLog(`ParaViewWeb 已就绪: ${pvData.url}`, 'SUCCESS')
        } else if (pvData.message) {
          addLog(`ParaViewWeb: ${pvData.message}`, 'WARN')
        }
        if (pvData.details) {
          const detailLine = String(pvData.details).split('\n')[0]
          if (detailLine) {
            addLog(`ParaViewWeb 详情: ${detailLine}`, 'WARN')
          }
        }
        break
      }

      case 'residual_update': {
        const resData = data.data || data
        const field = resData.field
        const timeValue = typeof resData.time === 'number' ? resData.time : Date.now() / 1000
        const value = Number(
          resData.final_residual ?? resData.final ?? resData.initial_residual ?? resData.residual
        )
        if (field && Number.isFinite(value)) {
          startTransition(() => {
            setResidualSeries(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last && last.time === timeValue) {
                next[next.length - 1] = { ...last, [field]: value }
              } else {
                next.push({ time: timeValue, [field]: value })
              }
              return next.slice(-500)
            })
          })

          if (!residualFieldSetRef.current.has(field)) {
            residualFieldSetRef.current.add(field)
            setResidualFields(Array.from(residualFieldSetRef.current))
          }
        }
        break
      }

      case 'solver_log': {
        const line = (data.data && data.data.line) || data.line
        if (line) {
          startTransition(() => {
            setSolverLogs(prev => [...prev, line].slice(-300))
          })
        }
        break
      }
      
      case 'status':
      case 'status_update':
        const statusData = data.data || data
        lastWsMessageRef.current = Date.now()
        setSimulationStatus(prev => ({
          ...prev,
          status: statusData.status || prev.status,
          progress: typeof statusData.progress === 'number' ? statusData.progress : prev.progress,
          current_step: statusData.current_step || prev.current_step
        }))
        if (statusData.current_step) {
          addLog(`当前步骤: ${statusData.current_step}`, 'INFO', statusData.current_step)
        }
        break
      
      case 'progress':
      case 'progress_update':
        const progressData = data.data || data
        lastWsMessageRef.current = Date.now()
        setSimulationStatus(prev => ({
          ...prev,
          progress: typeof progressData.progress === 'number' ? progressData.progress : prev.progress,
          current_step: progressData.current_step || prev.current_step,
          log_messages: progressData.log_messages || prev.log_messages
        }))
        
        // 处理日志消息
        if (progressData.log_messages && progressData.log_messages.length > 0) {
          const lastLog = progressData.log_messages[progressData.log_messages.length - 1]
          if (lastLog) {
            const level = lastLog.includes('✅') ? 'SUCCESS' : 
                         lastLog.includes('❌') ? 'ERROR' : 
                         lastLog.includes('⚠️') ? 'WARN' : 'INFO'
            addLog(lastLog, level, progressData.current_step)
          }
        }
        break
      
      case 'log_message':
        addLog(data.message, data.level || 'INFO', data.step)
        break
      
      case 'completed':
      case 'simulation_completed':
        const completedData = data.data || data
        lastWsMessageRef.current = Date.now()
        resultsFetchedRef.current = true
        setSimulationStatus({
          status: 'completed',
          progress: 100,
          current_step: completedData.current_step || '仿真完成',
          log_messages: [...simulationStatus.log_messages, '仿真已完成']
        })
        if (completedData.performance_metrics) {
          setPerformanceMetrics(completedData.performance_metrics)
        }
        if (completedData.visualization_data) {
          setVisualizationData(completedData.visualization_data)
        }
        if (completedData.paraview_web_url) {
          setParaviewWebUrl(completedData.paraview_web_url)
          setParaviewWebStatus('running')
          setParaviewViewStatus('connecting')
        }
        if (completedData.paraview_web_ws_url) {
          setParaviewWebWsUrl(completedData.paraview_web_ws_url)
        }
        addLog('仿真计算完成', 'SUCCESS')
        message.success('仿真已完成！')
        
        // 自动跳转到结果页面
        setTimeout(() => {
          setActiveTab('results')
        }, 1500)
        
        // 更新历史记录
        if (currentSimulationId) {
          setSimulationHistory(prev => prev.map(h => 
            h.id === currentSimulationId 
              ? { ...h, endTime: new Date(), status: 'completed' }
              : h
          ))
        }
        break
      
      case 'error':
        const errorData = data.data || data
        lastWsMessageRef.current = Date.now()
        setSimulationStatus(prev => ({
          ...prev,
          status: 'error',
          current_step: '仿真错误'
        }))
        const errorMessage = errorData.error || errorData.message || '未知错误'
        addLog(`错误: ${errorMessage}`, 'ERROR')
        message.error(`仿真错误: ${errorMessage}`)
        
        // 更新历史记录
        if (currentSimulationId) {
          setSimulationHistory(prev => prev.map(h => 
            h.id === currentSimulationId 
              ? { ...h, endTime: new Date(), status: 'error' }
              : h
          ))
        }
        break
      
      case 'heartbeat':
      case 'pong':
      case 'ping':
      case 'info':
        // 心跳包和信息消息，无需处理，保持连接活跃
        break
      
      default:
        console.warn('未知的WebSocket消息类型:', data.type)
    }
  }, [addLog, setSimulationStatus, setPerformanceMetrics, setVisualizationData, simulationStatus.log_messages, currentSimulationId])

  const handleWebSocketError = useCallback((error: Event) => {
    console.error('WebSocket错误:', error)
    setWsConnected(false)
    addLog('WebSocket连接错误', 'ERROR')
    message.error('WebSocket连接错误')
  }, [addLog])

  const handleWebSocketClose = useCallback((event: CloseEvent) => {
    console.log('WebSocket连接关闭:', event.code, event.reason)
    setWsConnected(false)
    
    switch (event.code) {
      case 1000:
        addLog('WebSocket连接正常关闭', 'INFO')
        break
      case 1006:
        addLog('WebSocket连接异常断开', 'WARN')
        message.warning('WebSocket连接异常断开')
        break
      case 1008:
        addLog('WebSocket连接被服务器拒绝', 'ERROR')
        message.error('WebSocket连接被服务器拒绝')
        break
      default:
        addLog(`WebSocket连接关闭 (代码: ${event.code})`, 'WARN')
    }
  }, [addLog])

  // 兜底轮询状态（避免 WebSocket 断开导致步骤卡住）
  useEffect(() => {
    if (!currentSimulationId) return

    const pollStatus = async () => {
      if (simulationStatus.status !== 'running' && simulationStatus.status !== 'paused') {
        return
      }

      const now = Date.now()
      const lastUpdate = lastWsMessageRef.current
      const shouldPoll = !wsConnected || (lastUpdate > 0 && now - lastUpdate > 8000)

      if (!shouldPoll) return

      try {
        const status = await ApiService.getSimulationStatus(currentSimulationId)
        setSimulationStatus(prev => ({
          ...prev,
          status: status.status || prev.status,
          progress: typeof status.progress === 'number' ? status.progress : prev.progress,
          current_step: status.current_step || prev.current_step,
          log_messages: status.log_messages || prev.log_messages
        }))

        if (status.status === 'completed' && !resultsFetchedRef.current) {
          resultsFetchedRef.current = true
          const results = await ApiService.getSimulationResults(currentSimulationId)
          setPerformanceMetrics(results.performance_metrics)
          if (results.visualization_data) {
            setVisualizationData(results.visualization_data)
          }
        }
      } catch (error) {
        console.warn('状态轮询失败:', error)
      }
    }

    const interval = setInterval(pollStatus, 5000)
    return () => clearInterval(interval)
  }, [
    currentSimulationId,
    simulationStatus.status,
    wsConnected,
    setSimulationStatus,
    setPerformanceMetrics,
    setVisualizationData
  ])

  // 开始仿真
  const handleStartSimulation = async () => {
    if (!parameters) {
      message.error('请先设置仿真参数')
      return
    }

    setIsConnecting(true)
    setLogs([])
    setElapsedTime(0)
    setResidualSeries([])
    setResidualFields([])
    residualFieldSetRef.current.clear()
    setSolverLogs([])
    setSolverAutoScroll(true)
    setParaviewWebUrl(null)
    setParaviewWebStatus('idle')
    setParaviewWebWsUrl(null)
    setParaviewViewStatus('idle')
    lastWsMessageRef.current = Date.now()
    resultsFetchedRef.current = false
    const newStartTime = new Date()
    setStartTime(newStartTime)
    
    try {
      addLog('正在启动仿真...', 'INFO')
      
      const response = await ApiService.startSimulation(parameters)
      const simulationId = response.simulation_id
      setCurrentSimulationId(simulationId)
      
      // 添加到历史记录
      setSimulationHistory(prev => [{
        id: simulationId,
        startTime: newStartTime,
        status: 'running',
        parameters: `通道: ${parameters.channel_count}个, 速度: ${parameters.inlet_velocity}m/s`
      }, ...prev])
      
      setSimulationStatus({
        status: 'running',
        progress: 0,
        current_step: '初始化仿真环境',
        log_messages: ['开始仿真...']
      })
      
      addLog(`仿真任务已创建: ${simulationId}`, 'SUCCESS')
      
      // 连接WebSocket
      addLog('正在连接WebSocket...', 'INFO')
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
      addLog('仿真启动失败', 'ERROR')
      message.error('仿真启动失败')
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

    if (parameters?.simulation_mode === 'openfoam') {
      message.warning('真实 OpenFOAM 模式暂不支持暂停')
      return
    }
    
    try {
      await ApiService.pauseSimulation(currentSimulationId)
      setSimulationStatus(prev => ({
        ...prev,
        status: 'paused',
        current_step: '已暂停'
      }))
      addLog('仿真已暂停', 'WARN')
      message.info('仿真已暂停')

      if (currentSimulationId) {
        setSimulationHistory(prev => prev.map(h =>
          h.id === currentSimulationId ? { ...h, status: 'paused' } : h
        ))
      }
    } catch (error) {
      console.error('暂停仿真失败:', error)
      addLog('暂停仿真失败', 'ERROR')
      message.error('暂停仿真失败')
    }
  }

  const handleResumeSimulation = async () => {
    if (!currentSimulationId) return

    if (parameters?.simulation_mode === 'openfoam') {
      message.warning('真实 OpenFOAM 模式暂不支持继续')
      return
    }

    try {
      await ApiService.resumeSimulation(currentSimulationId)
      setSimulationStatus(prev => ({
        ...prev,
        status: 'running',
        current_step: prev.current_step || '继续运行'
      }))
      addLog('仿真已继续', 'INFO')
      message.success('仿真已继续')

      if (currentSimulationId) {
        setSimulationHistory(prev => prev.map(h =>
          h.id === currentSimulationId ? { ...h, status: 'running' } : h
        ))
      }
    } catch (error) {
      console.error('继续仿真失败:', error)
      addLog('继续仿真失败', 'ERROR')
      message.error('继续仿真失败')
    }
  }

  // 停止仿真
  const handleStopSimulation = async () => {
    if (!currentSimulationId) return
    
    Modal.confirm({
      title: '确认停止仿真',
      content: '确定要停止当前仿真吗？已完成的进度将丢失。',
      okText: '停止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await ApiService.stopSimulation(currentSimulationId)
          addLog('仿真已停止', 'WARN')
          setSimulationStatus({
            status: 'stopped',
            progress: simulationStatus.progress,
            current_step: '已停止',
            log_messages: [...simulationStatus.log_messages, '仿真已停止']
          })
          setCurrentSimulationId(null)
          setStartTime(null)
          setElapsedTime(0)
          setParaviewWebUrl(null)
          setParaviewWebStatus('idle')
          setParaviewWebWsUrl(null)
          setParaviewViewStatus('idle')
          setResidualSeries([])
          setResidualFields([])
          residualFieldSetRef.current.clear()
          setSolverLogs([])
          setSolverAutoScroll(true)
          wsService?.disconnect()
          setWsConnected(false)
          message.info('仿真已停止')

          if (currentSimulationId) {
            setSimulationHistory(prev => prev.map(h =>
              h.id === currentSimulationId ? { ...h, endTime: new Date(), status: 'stopped' } : h
            ))
          }
        } catch (error) {
          console.error('停止仿真失败:', error)
          addLog('停止仿真失败', 'ERROR')
          message.error('停止仿真失败')
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
      addLog('正在获取仿真结果...', 'INFO')
      const results = await ApiService.getSimulationResults(currentSimulationId)
      setPerformanceMetrics(results.performance_metrics)
      setVisualizationData(results.visualization_data)
      if (results.paraview_web_url) {
        setParaviewWebUrl(results.paraview_web_url)
        setParaviewWebStatus('running')
        setParaviewViewStatus('connecting')
      }
      if (results.paraview_web_ws_url) {
        setParaviewWebWsUrl(results.paraview_web_ws_url)
      }
      addLog('结果数据已加载', 'SUCCESS')
      message.success('结果已加载')
    } catch (error) {
      console.error('获取结果失败:', error)
      addLog('获取结果失败', 'ERROR')
      message.error('获取结果失败')
    }
  }

  const handleRefreshStatus = async () => {
    if (!currentSimulationId) {
      message.warning('暂无仿真任务')
      return
    }

    setIsRefreshing(true)
    try {
      const status = await ApiService.getSimulationStatus(currentSimulationId)
      setSimulationStatus(prev => ({
        ...prev,
        status: status.status || prev.status,
        progress: typeof status.progress === 'number' ? status.progress : prev.progress,
        current_step: status.current_step || prev.current_step,
        log_messages: status.log_messages || prev.log_messages
      }))
      message.success('状态已刷新')
    } catch (error) {
      console.error('刷新状态失败:', error)
      message.error('刷新状态失败')
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleOpenParaview = async () => {
    if (!currentSimulationId) {
      message.warning('暂无仿真任务')
      return
    }

    try {
      const results = await ApiService.getSimulationResults(currentSimulationId)
      await ApiService.launchParaview(results.paraview_file)
      message.success('已尝试启动 ParaView')
    } catch (error) {
      console.error('启动 ParaView 失败:', error)
      message.error('启动 ParaView 失败')
    }
  }

  const paraviewCardRef = useRef<HTMLDivElement>(null)

  const handleOpenParaviewWeb = async () => {
    if (!currentSimulationId) {
      message.warning('暂无仿真任务')
      return
    }

    try {
      if (!paraviewWebWsUrl && !paraviewWebUrl) {
        const info = await ApiService.getParaviewWeb(currentSimulationId)
        setParaviewWebStatus(info.status || 'idle')
        if (info.ws_url) setParaviewWebWsUrl(info.ws_url)
        if (info.url) setParaviewWebUrl(info.url)
        if (!info.url && !info.ws_url && info.message) {
          message.warning(info.message)
          return
        }
      }

      if (paraviewCardRef.current) {
        paraviewCardRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
        message.info('3D 流场视图在本页下方展示（请勿在新标签页打开，服务端仅提供 WebSocket）', 4)
      } else {
        message.info('3D 流场视图请在本页「3D 实时流场」卡片中查看')
      }
    } catch (error) {
      console.error('打开 ParaViewWeb 失败:', error)
      message.error('打开 ParaViewWeb 失败')
    }
  }

  const handleOpenCaseFolder = async () => {
    if (!currentSimulationId) {
      message.warning('暂无仿真任务')
      return
    }

    try {
      const results = await ApiService.getSimulationResults(currentSimulationId)
      if (!results.case_directory) {
        message.warning('未找到结果目录')
        return
      }
      await ApiService.openPath(results.case_directory)
      message.success('已打开结果目录')
    } catch (error) {
      console.error('打开结果目录失败:', error)
      message.error('打开结果目录失败')
    }
  }

  // 导出日志
  const exportLogs = useCallback(() => {
    const logText = logs.map(log => 
      `[${formatDateTime(log.timestamp)}] [${log.level}] ${log.message}`
    ).join('\n')
    
    const blob = new Blob([logText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `simulation-logs-${currentSimulationId || 'unknown'}-${Date.now()}.txt`
    link.click()
    URL.revokeObjectURL(url)
    
    message.success('日志已导出')
  }, [logs, currentSimulationId])

  // 清空日志
  const clearLogs = useCallback(() => {
    Modal.confirm({
      title: '确认清空日志',
      content: '确定要清空所有日志吗？',
      onOk: () => {
        setLogs([])
        message.success('日志已清空')
      }
    })
  }, [])

  // 获取状态图标
  const getStatusIcon = (status: string): React.ReactNode => {
    switch (status) {
      case 'running': return <LoadingOutlined />
      case 'paused': return <PauseCircleOutlined style={{ color: '#faad14' }} />
      case 'stopped': return <StopOutlined style={{ color: '#999999' }} />
      case 'completed': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'error': return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      default: return <ClockCircleOutlined />
    }
  }

  const normalizeStepKey = (step: string): string => {
    const text = (step || '').toLowerCase()
    if (!text) return ''
    if (text.includes('初始化') || text.includes('环境') || text.includes('准备') || text.includes('init')) {
      return 'initialization'
    }
    if (text.includes('网格') || text.includes('mesh')) {
      return 'mesh_generation'
    }
    if (text.includes('配置') || text.includes('设置') || text.includes('solver') || text.includes('求解器')) {
      return 'solver_setup'
    }
    if (text.includes('求解') || text.includes('运行') || text.includes('cfd') || text.includes('计算流动') || text.includes('计算')) {
      return 'running'
    }
    if (text.includes('后处理') || text.includes('结果') || text.includes('提取') || text.includes('报告')) {
      return 'post_processing'
    }
    if (text.includes('完成') || text.includes('completed')) {
      return 'completed'
    }
    return ''
  }

  // 获取当前步骤索引
  const getCurrentStepIndex = (): number => {
    if (simulationStatus.status === 'completed') {
      return SIMULATION_STEPS.length - 1
    }

    const stepMap: Record<string, number> = {
      'initialization': 0,
      'mesh_generation': 1,
      'solver_setup': 2,
      'running': 3,
      'post_processing': 4,
      'completed': 5
    }
    const normalized = normalizeStepKey(simulationStatus.current_step)
    if (normalized && stepMap[normalized] !== undefined) {
      return stepMap[normalized]
    }

    const progress = simulationStatus.progress || 0
    if (progress >= 100) return 5
    if (progress >= 85) return 4
    if (progress >= 60) return 3
    if (progress >= 35) return 2
    if (progress >= 15) return 1
    return 0
  }

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (wsService) {
        wsService.disconnect()
      }
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [wsService])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 状态概览卡片 */}
      <Card 
        title={
          <Space>
            <DashboardOutlined />
            <Text strong>仿真状态监控</Text>
            <Badge 
              status={wsConnected ? 'success' : 'error'} 
              text={wsConnected ? 'WebSocket已连接' : 'WebSocket未连接'}
            />
          </Space>
        }
        extra={
          <Space>
            <Button
              size="small"
              onClick={handleRefreshStatus}
              loading={isRefreshing}
              icon={<SyncOutlined />}
            >
              刷新
            </Button>
            <Switch 
              id="sim-monitor-debug-switch"
              name="showDebugInfo"
              checked={showDebugInfo} 
              onChange={setShowDebugInfo}
              size="small"
              checkedChildren="调试"
              unCheckedChildren="调试"
            />
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 状态指示器 */}
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="仿真状态"
                  value={simulationStatus.status === 'idle' ? '等待开始' : 
                         simulationStatus.status === 'running' ? '运行中' :
                         simulationStatus.status === 'paused' ? '已暂停' :
                         simulationStatus.status === 'stopped' ? '已停止' :
                         simulationStatus.status === 'completed' ? '已完成' : '错误'}
                  valueStyle={{ 
                    color: simulationStatus.status === 'running' ? '#1890ff' :
                           simulationStatus.status === 'paused' ? '#faad14' :
                           simulationStatus.status === 'stopped' ? '#999999' :
                           simulationStatus.status === 'completed' ? '#52c41a' :
                           simulationStatus.status === 'error' ? '#ff4d4f' : '#666'
                  }}
                  prefix={getStatusIcon(simulationStatus.status)}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="运行时间"
                  value={formatTime(elapsedTime)}
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="预计剩余"
                  value={simulationStatus.estimated_time_remaining ? 
                    formatTime(simulationStatus.estimated_time_remaining) : '--:--'}
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* 进度条 */}
          <div>
            <Text strong>总体进度</Text>
            <Progress 
              percent={Math.round(simulationStatus.progress)}
              status={simulationStatus.status === 'error' ? 'exception' : 
                     simulationStatus.status === 'completed' ? 'success' :
                     simulationStatus.status === 'paused' ? 'normal' :
                     simulationStatus.status === 'stopped' ? 'normal' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              format={(percent) => `${percent}%`}
            />
          </div>

          {/* 仿真步骤时间线 */}
          {simulationStatus.status !== 'idle' && (
            <Card size="small" title="仿真步骤">
              <Timeline 
                mode="left"
                items={SIMULATION_STEPS.map((step, index) => {
                  const currentIndex = getCurrentStepIndex()
                  const isCompleted = index < currentIndex
                  const isCurrent = index === currentIndex
                  
                  return {
                    label: step.label,
                    children: (
                      <div>
                        <Text strong={isCurrent}>{step.label}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {step.description}
                        </Text>
                      </div>
                    ),
                    color: isCompleted ? 'green' : isCurrent ? 'blue' : 'gray',
                    dot: isCurrent ? <LoadingOutlined /> : undefined
                  }
                })}
              />
            </Card>
          )}

          {/* 操作按钮 */}
          <Row gutter={[8, 8]}>
            <Col span={8}>
              <Button 
                type="primary" 
                icon={isConnecting ? <LoadingOutlined /> : <PlayCircleOutlined />}
                disabled={simulationStatus.status === 'running' || simulationStatus.status === 'paused' || isConnecting}
                onClick={handleStartSimulation}
                loading={isConnecting}
                block
              >
                {isConnecting ? '连接中...' : '开始仿真'}
              </Button>
            </Col>
            <Col span={8}>
              {simulationStatus.status === 'paused' ? (
                <Tooltip title={parameters?.simulation_mode === 'openfoam' ? '真实 OpenFOAM 模式暂不支持继续' : ''}>
                  <Button
                    icon={<PlayCircleOutlined />}
                    disabled={parameters?.simulation_mode === 'openfoam'}
                    onClick={handleResumeSimulation}
                    block
                  >
                    继续
                  </Button>
                </Tooltip>
              ) : (
                <Tooltip title={parameters?.simulation_mode === 'openfoam' ? '真实 OpenFOAM 模式暂不支持暂停' : ''}>
                  <Button 
                    icon={<PauseCircleOutlined />}
                    disabled={simulationStatus.status !== 'running' || parameters?.simulation_mode === 'openfoam'}
                    onClick={handlePauseSimulation}
                    block
                  >
                    暂停
                  </Button>
                </Tooltip>
              )}
            </Col>
            <Col span={8}>
              <Button 
                danger 
                icon={<StopOutlined />}
                disabled={simulationStatus.status === 'idle' || simulationStatus.status === 'completed'}
                onClick={handleStopSimulation}
                block
              >
                停止
              </Button>
            </Col>
            {simulationStatus.status === 'completed' && (
              <>
                <Col span={24}>
                  <Button 
                    type="dashed" 
                    icon={<CheckCircleOutlined />}
                    onClick={handleGetResults}
                    block
                  >
                    获取结果
                  </Button>
                </Col>
                <Col span={12}>
                  <Button 
                    icon={<EyeOutlined />}
                    onClick={handleOpenParaview}
                    block
                  >
                    打开 ParaView
                  </Button>
                </Col>
                <Col span={12}>
                  <Button 
                    icon={<FolderOpenOutlined />}
                    onClick={handleOpenCaseFolder}
                    block
                  >
                    打开结果目录
                  </Button>
                </Col>
              </>
            )}
          </Row>
        </Space>
      </Card>

      {/* 性能指标卡片 */}
      {performanceMetrics && (
        <Card 
          title={
            <Space>
              <ThunderboltOutlined />
              <Text strong>性能指标</Text>
            </Space>
          }
        >
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="最高温度"
                  value={performanceMetrics.max_temperature.toFixed(1)}
                  suffix="K"
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {(performanceMetrics.max_temperature - 273.15).toFixed(1)} °C
                </Text>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="压力降"
                  value={(performanceMetrics.pressure_drop / 1000).toFixed(3)}
                  suffix="kPa"
                  prefix={<CompressOutlined />}
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {performanceMetrics.pressure_drop.toFixed(1)} Pa
                </Text>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="传热系数"
                  value={performanceMetrics.heat_transfer_coefficient.toFixed(0)}
                  suffix="W/m²K"
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="雷诺数"
                  value={performanceMetrics.reynolds_number.toFixed(0)}
                />
                <Tag color={performanceMetrics.reynolds_number < 2300 ? 'blue' : 'orange'}>
                  {performanceMetrics.reynolds_number < 2300 ? '层流' : '湍流'}
                </Tag>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* 残差监控 - 始终展示卡片，仅在 openfoam 模式下显示图表 */}
      <Card
        title={
          <Space>
            <DashboardOutlined />
            <Text strong>求解残差</Text>
          </Space>
        }
        extra={
          parameters?.simulation_mode === 'openfoam' ? (
            <Tag color={residualSeries.length > 0 ? 'green' : 'default'}>
              {residualSeries.length > 0 ? '实时更新' : '等待输出'}
            </Tag>
          ) : (
            <Tag color="default">需真实 OpenFOAM 模式</Tag>
          )
        }
      >
        {parameters?.simulation_mode !== 'openfoam' ? (
          <Empty
            description="请在设计参数中选择「真实OpenFOAM」模式并启动仿真后查看求解残差"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : deferredResidualSeries.length === 0 ? (
          <Empty description="暂无残差信息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div
            ref={residualChartRef}
            style={{ width: '100%', height: '320px', minHeight: '320px' }}
          >
            {residualChartReady ? (
              <ResponsiveContainer>
                <LineChart data={deferredResidualSeries}>
                  <XAxis dataKey="time" />
                  <YAxis domain={['auto', 'auto']} />
                  <ReTooltip />
                  <Legend />
                  {residualFields.map((field, index) => (
                    <Line
                      key={field}
                      type="monotone"
                      dataKey={field}
                      dot={false}
                      stroke={RESIDUAL_COLORS[index % RESIDUAL_COLORS.length]}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="图表布局中..." image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </div>
        )}
      </Card>

      {/* 3D 实时流场 - 始终展示卡片，仅在 openfoam 模式下显示视图 */}
      <div ref={paraviewCardRef}>
      <Card
        title={
          <Space>
            <EyeOutlined />
            <Text strong>3D 实时流场</Text>
          </Space>
        }
        extra={
          parameters?.simulation_mode === 'openfoam' ? (
            <Space>
              <Tag color={paraviewViewStatus === 'connected' ? 'green' : paraviewWebStatus === 'running' ? 'blue' : 'default'}>
                {paraviewViewStatus === 'connected' ? '已连接' : paraviewWebStatus}
              </Tag>
              <Button size="small" onClick={handleOpenParaviewWeb}>
                打开 3D 视图
              </Button>
            </Space>
          ) : (
            <Tag color="default">需真实 OpenFOAM 模式</Tag>
          )
        }
      >
        {parameters?.simulation_mode !== 'openfoam' ? (
          <Empty
            description="请在设计参数中选择「真实OpenFOAM」模式并启动仿真后查看 3D 流场"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <div
            style={{
              width: '100%',
              height: '480px',
              border: '1px solid #f0f0f0',
              borderRadius: '4px',
              overflow: 'hidden'
            }}
          >
            <ParaViewRemoteView
              url={paraviewWebWsUrl || paraviewWebUrl}
              height="100%"
              onStatusChange={setParaviewViewStatus}
            />
          </div>
        )}
      </Card>
      </div>

      {/* 求解器日志 */}
      {parameters?.simulation_mode === 'openfoam' && (
        <Card
          title={
            <Space>
              <FileTextOutlined />
              <Text strong>求解器日志</Text>
            </Space>
          }
          extra={
            <Tag color={solverAutoScroll ? 'green' : 'default'}>
              {solverAutoScroll ? '自动跟随' : '已停止跟随'}
            </Tag>
          }
        >
          <div
            ref={solverLogContainerRef}
            onScroll={handleSolverLogScroll}
            style={{
              maxHeight: '260px',
              overflowY: 'auto',
              backgroundColor: '#0f0f0f',
              padding: '12px',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '12px'
            }}
          >
            {deferredSolverLogs.length === 0 ? (
              <Empty description="暂无求解器日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              deferredSolverLogs.map((line, idx) => (
                <div key={`${idx}-${line}`} style={{ color: '#d9d9d9', marginBottom: '4px' }}>
                  {line}
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {/* 日志监控 */}
      <Card 
        title={
          <Space>
            <FileTextOutlined />
            <Text strong>仿真日志</Text>
            <Badge count={logs.length} style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={
          <Space>
            <Switch 
              id="sim-monitor-autoscroll-switch"
              name="autoScroll"
              checked={autoScroll} 
              onChange={setAutoScroll}
              size="small"
              checkedChildren="自动滚动"
              unCheckedChildren="自动滚动"
            />
            <Button size="small" icon={<DownloadOutlined />} onClick={exportLogs}>
              导出
            </Button>
            <Button size="small" danger onClick={clearLogs}>
              清空
            </Button>
          </Space>
        }
      >
        <div 
          ref={logContainerRef}
          onScroll={handleLogScroll}
          style={{ 
            maxHeight: '400px', 
            overflowY: 'auto',
            backgroundColor: '#1e1e1e',
            padding: '12px',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '12px'
          }}
        >
          {logs.length === 0 ? (
            <Empty description="暂无日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            logs.map((log) => (
              <div key={log.id} style={{ marginBottom: '4px' }}>
                <Text style={{ color: '#666' }}>[{formatDateTime(log.timestamp)}]</Text>
                <Tag 
                  color={LOG_LEVEL_COLORS[log.level]} 
                  style={{ marginLeft: '8px', marginRight: '8px', fontSize: '10px' }}
                >
                  {log.level}
                </Tag>
                <Text style={{ color: '#fff' }}>{log.message}</Text>
                {log.step && (
                  <Tag style={{ marginLeft: '8px', fontSize: '10px' }}>
                    {log.step}
                  </Tag>
                )}
              </div>
            ))
          )}
        </div>
      </Card>

      {/* 调试信息 */}
      {showDebugInfo && (
        <Card 
          size="small" 
          title={
            <Space>
              <BugOutlined />
              <Text strong>调试信息</Text>
            </Space>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text type="secondary" copyable>
              仿真ID: {currentSimulationId || '无'}
            </Text>
            <Text type="secondary">
              WebSocket状态: {wsConnected ? '已连接' : '未连接'}
            </Text>
            <Text type="secondary">
              连接状态: {isConnecting ? '连接中...' : '就绪'}
            </Text>
            <Text type="secondary">
              日志数量: {logs.length}
            </Text>
            <Text type="secondary">
              开始时间: {startTime ? formatDateTime(startTime) : '未开始'}
            </Text>
          </Space>
        </Card>
      )}

      {/* 仿真历史 */}
      {simulationHistory.length > 0 && (
        <Card 
          size="small"
          title={
            <Space>
              <HistoryOutlined />
              <Text strong>仿真历史</Text>
            </Space>
          }
        >
          <List
            size="small"
            dataSource={simulationHistory.slice(0, 5)}
            renderItem={(item) => (
              <List.Item>
                <Space>
                  {getStatusIcon(item.status)}
                  <Text strong>{item.id.slice(0, 8)}...</Text>
                  <Text type="secondary">{item.parameters}</Text>
                  <Text type="secondary">
                    {formatDateTime(item.startTime)}
                  </Text>
                  {item.endTime && (
                    <Text type="secondary">
                      耗时: {formatTime(Math.floor((item.endTime.getTime() - item.startTime.getTime()) / 1000))}
                    </Text>
                  )}
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 警告信息 */}
      {simulationStatus.status === 'error' && (
        <Alert
          message="仿真错误"
          description="仿真过程中出现错误，请检查参数设置和系统配置。您可以查看日志获取详细信息。"
          type="error"
          showIcon
          closable
        />
      )}

      {simulationStatus.status === 'completed' && performanceMetrics && (
        <Alert
          message="仿真完成"
          description="仿真已成功完成！您可以查看性能指标和可视化结果。"
          type="success"
          showIcon
          closable
        />
      )}
    </Space>
  )
}

export default SimulationMonitor
