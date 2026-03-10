import axios from 'axios'
import { MicrochannelParameters, SimulationStatus, PerformanceMetrics, ParsingResult, ValidationResult } from '../types'

// API基础配置
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log(`🚀 API请求: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('❌ API请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API响应: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('❌ API响应错误:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// API服务类
export class ApiService {
  
  // 解析自然语言描述
  static async parseDescription(description: string): Promise<ParsingResult> {
    const response = await apiClient.post('/parse-description', { description })
    return response.data
  }

  // 验证参数
  static async validateParameters(parameters: MicrochannelParameters): Promise<ValidationResult> {
    const response = await apiClient.post('/validate-parameters', parameters)
    return response.data
  }

  // 开始仿真
  static async startSimulation(parameters: MicrochannelParameters): Promise<{ simulation_id: string }> {
    const response = await apiClient.post('/simulation/start', parameters)
    return response.data
  }

  // 获取仿真状态
  static async getSimulationStatus(simulationId: string): Promise<SimulationStatus> {
    const response = await apiClient.get(`/simulation/${simulationId}/status`)
    return response.data
  }

  // 暂停仿真
  static async pauseSimulation(simulationId: string): Promise<void> {
    await apiClient.post(`/simulation/${simulationId}/pause`)
  }

  // 停止仿真
  static async stopSimulation(simulationId: string): Promise<void> {
    await apiClient.post(`/simulation/${simulationId}/stop`)
  }

  // 获取仿真结果
  static async getSimulationResults(simulationId: string): Promise<{
    performance_metrics: PerformanceMetrics
    visualization_data: any
    report_url?: string
  }> {
    const response = await apiClient.get(`/simulation/${simulationId}/results`)
    return response.data
  }

  // 获取实时数据流（用于WebSocket备用方案）
  static async getRealtimeData(simulationId: string): Promise<any> {
    const response = await apiClient.get(`/simulation/${simulationId}/realtime`)
    return response.data
  }

  // 生成工程报告
  static async generateReport(simulationId: string, template?: string): Promise<{ report_url: string }> {
    const response = await apiClient.post(`/simulation/${simulationId}/report`, { template })
    return response.data
  }

  // 获取系统配置
  static async getSystemConfig(): Promise<any> {
    const response = await apiClient.get('/system/config')
    return response.data
  }

  // 检查系统健康状态
  static async healthCheck(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy'
    services: {
      openfoam: boolean
      llm: boolean
      database: boolean
    }
  }> {
    const response = await apiClient.get('/health')
    return response.data
  }
}

// WebSocket服务类
export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 3000 // 3秒

  constructor(
    private onMessage: (data: any) => void,
    private onError: (error: Event) => void,
    private onClose: (event: CloseEvent) => void
  ) {}

  // 连接到WebSocket
  connect(simulationId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket已连接')
      return
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_WS_HOST || window.location.hostname
    const wsPort = import.meta.env.VITE_WS_PORT || '8000'
    const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/simulation/${simulationId}`
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = async () => {
        console.log('✅ WebSocket连接成功')
        this.reconnectAttempts = 0
        
        // 发送订阅消息
        this.send({
          type: 'subscribe',
          simulation_id: simulationId
        })
      }
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('📡 WebSocket消息:', data.type, data)
          this.onMessage(data)
        } catch (error) {
          console.error('WebSocket消息解析错误:', error)
        }
      }
      
      this.ws.onerror = (error) => {
        console.error('❌ WebSocket错误:', error)
        this.onError(error)
      }
      
      this.ws.onclose = (event) => {
        console.log('WebSocket 连接关闭:', event.code, event.reason)
        this.onClose(event)
        
        // 只有非正常关闭才重连，1000 是正常关闭
        if (event.code !== 1000 && event.code !== 1006) {
          this.handleReconnect(simulationId)
        } else if (event.code === 1006) {
          console.warn('WebSocket 异常关闭 (1006)，不自动重连')
        }
      }
      
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      this.handleReconnect(simulationId)
    }
  }

  // 处理重连
  private handleReconnect(simulationId: string): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`尝试重连... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      
      // 增加重连间隔时间
      const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1)
      
      setTimeout(() => {
        this.connect(simulationId)
      }, Math.min(delay, 30000)) // 最大重连间隔30秒
    } else {
      console.error('❌ WebSocket重连失败，达到最大重连次数')
      this.onError(new Event('max_reconnect_attempts'))
    }
  }

  // 发送消息
  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  // 断开连接
  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, '正常关闭')
      this.ws = null
    }
  }

  // 获取连接状态
  getConnectionState(): 'connecting' | 'open' | 'closing' | 'closed' {
    if (!this.ws) return 'closed'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'open'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'closed'
      default:
        return 'closed'
    }
  }
}

// 错误处理工具
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// 工具函数：处理API错误
export const handleApiError = (error: any): never => {
  if (error.response) {
    // 服务器响应错误
    throw new ApiError(
      error.response.data?.message || '服务器错误',
      error.response.status,
      error.response.data
    )
  } else if (error.request) {
    // 网络错误
    throw new ApiError('网络连接错误，请检查服务器状态')
  } else {
    // 其他错误
    throw new ApiError(error.message || '未知错误')
  }
}

// 工具函数：重试机制
export const retryApiCall = async <T>(
  apiCall: () => Promise<T>,
  maxRetries = 3,
  delay = 1000
): Promise<T> => {
  let lastError: Error
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await apiCall()
    } catch (error) {
      lastError = error as Error
      console.warn(`API调用失败，第${attempt}次重试:`, error)
      
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, delay * attempt))
      }
    }
  }
  
  throw lastError!
}

export default ApiService