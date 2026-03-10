import React from 'react'
import { Layout, Tabs, Space, Typography, Button } from 'antd'
import { 
  ExperimentOutlined, 
  PlayCircleOutlined, 
  BarChartOutlined,
  SettingOutlined 
} from '@ant-design/icons'
import ParameterPanel from './components/ParameterPanel'
import ThreeDVisualization from './components/ThreeDVisualization'
import SimulationMonitor from './components/SimulationMonitor'
import { useStore } from './stores/useStore'

const { Header, Content, Sider } = Layout
const { Title } = Typography

const App: React.FC = () => {
  const { activeTab, setActiveTab, is3DView, toggle3DView } = useStore()

  const tabItems = [
    {
      key: 'design',
      label: (
        <Space>
          <ExperimentOutlined />
          设计参数
        </Space>
      ),
      children: <ParameterPanel />
    },
    {
      key: 'simulation',
      label: (
        <Space>
          <PlayCircleOutlined />
          仿真监控
        </Space>
      ),
      children: <SimulationMonitor />
    },
    {
      key: 'results',
      label: (
        <Space>
          <BarChartOutlined />
          结果分析
        </Space>
      ),
      children: (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <Title level={3}>结果分析界面</Title>
          <p>仿真完成后将显示详细的分析结果和性能指标</p>
        </div>
      )
    }
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 顶部导航栏 */}
      <Header style={{ 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Space>
          <ExperimentOutlined style={{ fontSize: '24px', color: 'white' }} />
          <Title level={3} style={{ color: 'white', margin: 0 }}>
            AI-Driven Heat Exchanger Design System
          </Title>
        </Space>
        
        <Space>
          <Button 
            type={is3DView ? 'primary' : 'default'} 
            icon={<SettingOutlined />}
            onClick={toggle3DView}
          >
            {is3DView ? '3D视图' : '2D视图'}
          </Button>
          <Button type="dashed">帮助</Button>
        </Space>
      </Header>

      <Layout>
        {/* 左侧边栏 - 参数面板 */}
        <Sider 
          width={350} 
          style={{ 
            background: '#fff',
            padding: '16px',
            overflow: 'auto'
          }}
          breakpoint="lg"
          collapsedWidth="0"
        >
          <Tabs
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as any)}
            tabPosition="top"
            items={tabItems}
            style={{ height: '100%' }}
          />
        </Sider>

        {/* 主内容区域 - 可视化 */}
        <Content style={{ 
          padding: '16px',
          background: '#f0f2f5',
          overflow: 'auto'
        }}>
          {is3DView ? (
            <ThreeDVisualization />
          ) : (
            <div style={{ 
              background: '#fff', 
              padding: '20px', 
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <Title level={3}>2D可视化界面</Title>
              <p>2D视图功能正在开发中...</p>
              <Button type="primary" onClick={toggle3DView}>
                切换到3D视图
              </Button>
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  )
}

export default App