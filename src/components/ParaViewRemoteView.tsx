import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Empty, Spin, Typography } from 'antd'
import vtkWSLinkClient from 'vtk.js/Sources/IO/Core/WSLinkClient'
import vtkRemoteView, { connectImageStream, disconnectImageStream } from 'vtk.js/Sources/Rendering/Misc/RemoteView'
import SmartConnect from 'wslink/src/SmartConnect'

const { Text } = Typography

vtkWSLinkClient.setSmartConnectClass(SmartConnect)

type ViewStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'closed'

interface ParaViewRemoteViewProps {
  url?: string | null
  height?: number | string
  onStatusChange?: (status: ViewStatus) => void
}

const buildWsUrl = (rawUrl?: string | null): string | null => {
  if (!rawUrl) return null
  if (rawUrl.startsWith('ws://') || rawUrl.startsWith('wss://')) {
    const trimmed = rawUrl.replace(/\/+$/, '')
    return trimmed.endsWith('/ws') ? trimmed : `${trimmed}/ws`
  }
  try {
    const parsed = new URL(rawUrl)
    const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
    const basePath = parsed.pathname.replace(/\/+$/, '')
    const path = basePath ? `${basePath}/ws` : '/ws'
    return `${wsProtocol}//${parsed.host}${path}`
  } catch {
    return null
  }
}

const ParaViewRemoteView: React.FC<ParaViewRemoteViewProps> = ({
  url,
  height = 480,
  onStatusChange
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const clientRef = useRef<any>(null)
  const viewRef = useRef<any>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)

  const [status, setStatus] = useState<ViewStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [retryToken, setRetryToken] = useState(0)

  const wsUrl = useMemo(() => buildWsUrl(url), [url])

  useEffect(() => {
    if (onStatusChange) onStatusChange(status)
  }, [status, onStatusChange])

  useEffect(() => {
    if (!wsUrl || !containerRef.current) {
      setStatus('idle')
      setErrorMessage(null)
      return
    }

    let canceled = false
    setStatus('connecting')
    setErrorMessage(null)

    const client = vtkWSLinkClient.newInstance()
    clientRef.current = client

    const cleanup = () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
        resizeObserverRef.current = null
      }
      if (viewRef.current) {
        viewRef.current.delete()
        viewRef.current = null
      }
      disconnectImageStream()
      if (clientRef.current) {
        clientRef.current.disconnect()
        if (clientRef.current.delete) {
          clientRef.current.delete()
        }
        clientRef.current = null
      }
    }

    client.onConnectionReady(() => {
      if (canceled || !containerRef.current) return
      const connection = client.getConnection()
      const session = connection?.getSession()
      if (!session) {
        setStatus('error')
        setErrorMessage('ParaViewWeb session unavailable')
        return
      }

      const originalCall = session.call?.bind(session)
      if (typeof originalCall === 'function') {
        session.call = function (method: string, args?: unknown[], kwargs?: Record<string, unknown>) {
          return (originalCall as (m: string, a?: unknown[], k?: Record<string, unknown>) => Promise<unknown>)(method, args, kwargs).catch((err: { code?: number; message?: string; data?: unknown }) => {
            if (!canceled && err && (err.code === -32001 || err.code === -32601)) {
              const detail = err.data != null ? (typeof err.data === 'object' && 'message' in (err.data as object) ? String((err.data as { message?: string }).message) : JSON.stringify(err.data)) : err.message
              setErrorMessage(`${err.message || 'RPC 错误'}${detail ? ` — ${detail}` : ''}`)
              setStatus('error')
            }
            throw err
          })
        }
      }

      connectImageStream(session)
      const view = vtkRemoteView.newInstance()
      viewRef.current = view
      view.setSession(session)
      view.setContainer(containerRef.current)
      view.setViewId('-1')
      view.render()

      setStatus('connected')

      resizeObserverRef.current = new ResizeObserver(() => {
        if (viewRef.current) {
          viewRef.current.resize()
        }
      })
      resizeObserverRef.current.observe(containerRef.current)

      setTimeout(() => {
        if (viewRef.current) {
          viewRef.current.resetCamera()
          viewRef.current.render()
        }
      }, 250)
    })

    client.onConnectionError((error) => {
      if (canceled) return
      setStatus('error')
      setErrorMessage(error?.message || 'ParaViewWeb connection error')
    })

    client.onConnectionClose(() => {
      if (canceled) return
      setStatus('closed')
    })

    client.connect({ sessionURL: wsUrl })

    return () => {
      canceled = true
      cleanup()
    }
  }, [wsUrl, retryToken])

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          minHeight: typeof height === 'number' ? `${height}px` : undefined,
          background: '#0f0f0f'
        }}
      />

      {status !== 'connected' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: '8px',
            background: 'rgba(15, 15, 15, 0.78)'
          }}
        >
          {status === 'connecting' && (
            <>
              <Spin />
              <Text type="secondary">Connecting to ParaViewWeb...</Text>
            </>
          )}
          {status === 'idle' && <Empty description="ParaViewWeb 未就绪" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          {status === 'error' && (
            <>
              <Text type="danger">连接失败</Text>
              <Text type="secondary" style={{ maxWidth: 360, textAlign: 'center' }}>
                {errorMessage || '请确认 ParaViewWeb 服务已启动'}
              </Text>
              <Text type="secondary" style={{ fontSize: '12px', maxWidth: 360, textAlign: 'center' }}>
                若为「Exception raised」或 RPC 错误，请查看 WSL 中 pvweb 进程的终端输出以定位服务端异常
              </Text>
            </>
          )}
          {status === 'closed' && <Text type="secondary">连接已关闭</Text>}
          {(status === 'error' || status === 'closed') && (
            <Button size="small" onClick={() => setRetryToken(Date.now())}>
              重试连接
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

export default ParaViewRemoteView
