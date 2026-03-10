import React, { useRef, useEffect, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useStore } from '../stores/useStore'
import { Card, Radio, Space, Typography, Slider } from 'antd'
import { 
  EyeOutlined, 
  HeatMapOutlined, 
  ThunderboltOutlined,
  ExperimentOutlined 
} from '@ant-design/icons'

const { Text } = Typography

const ThreeDVisualization: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null)
  const { parameters, visualizationData } = useStore()
  const [viewMode, setViewMode] = useState<'geometry' | 'temperature' | 'velocity' | 'pressure'>('geometry')
  const [animationSpeed, setAnimationSpeed] = useState(1)

  useEffect(() => {
    if (!mountRef.current) return

    // 场景设置
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf0f0f0)

    // 相机设置
    const camera = new THREE.PerspectiveCamera(75, mountRef.current.clientWidth / mountRef.current.clientHeight, 0.1, 1000)
    camera.position.set(5, 5, 5)

    // 渲染器设置
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap

    // 控制器
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05

    // 光源
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(10, 10, 5)
    directionalLight.castShadow = true
    scene.add(directionalLight)

    // 坐标轴
    const axesHelper = new THREE.AxesHelper(2)
    scene.add(axesHelper)

    // 网格地面
    const gridHelper = new THREE.GridHelper(10, 10)
    scene.add(gridHelper)

    // 创建微通道几何体
    const createMicrochannelGeometry = () => {
      const { 
        channel_width, 
        channel_height, 
        channel_length, 
        channel_count,
        wall_thickness 
      } = parameters

      const group = new THREE.Group()

      // 计算总宽度
      const totalWidth = channel_count * (channel_width + wall_thickness)
      const startX = -totalWidth / 2

      // 创建通道和壁
      for (let i = 0; i < channel_count; i++) {
        const x = startX + i * (channel_width + wall_thickness)
        
        // 通道（流体区域）
        const channelGeometry = new THREE.BoxGeometry(channel_width, channel_height, channel_length)
        const channelMaterial = new THREE.MeshStandardMaterial({ 
          color: 0x2196f3,
          transparent: true,
          opacity: 0.7,
          metalness: 0.1,
          roughness: 0.5
        })
        const channel = new THREE.Mesh(channelGeometry, channelMaterial)
        channel.position.set(x + channel_width / 2, channel_height / 2, 0)
        channel.castShadow = true
        group.add(channel)

        // 壁（固体区域）
        if (i < channel_count - 1) {
          const wallGeometry = new THREE.BoxGeometry(wall_thickness, channel_height, channel_length)
          const wallMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x795548,
            metalness: 0.3,
            roughness: 0.4
          })
          const wall = new THREE.Mesh(wallGeometry, wallMaterial)
          wall.position.set(x + channel_width + wall_thickness / 2, channel_height / 2, 0)
          wall.castShadow = true
          wall.receiveShadow = true
          group.add(wall)
        }
      }

      // 基底
      const baseGeometry = new THREE.BoxGeometry(totalWidth, wall_thickness, channel_length)
      const baseMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x607d8b,
        metalness: 0.5,
        roughness: 0.3
      })
      const base = new THREE.Mesh(baseGeometry, baseMaterial)
      base.position.set(0, -wall_thickness / 2, 0)
      base.receiveShadow = true
      group.add(base)

      return group
    }

    // 创建温度场可视化
    const createTemperatureField = () => {
      const group = new THREE.Group()
      
      // 简化温度场可视化（实际应从仿真结果获取）
      const { channel_length, channel_count } = parameters
      const segmentCount = 20
      
      for (let i = 0; i < segmentCount; i++) {
        const z = (i / segmentCount - 0.5) * channel_length
        
        // 模拟温度梯度
        const temperature = 1 - i / segmentCount // 0-1范围
        const color = new THREE.Color().setHSL(0.7 * (1 - temperature), 0.8, 0.5)
        
        const geometry = new THREE.PlaneGeometry(2, 0.5)
        const material = new THREE.MeshBasicMaterial({ 
          color,
          transparent: true,
          opacity: 0.6,
          side: THREE.DoubleSide
        })
        
        const plane = new THREE.Mesh(geometry, material)
        plane.position.set(0, 1.5, z)
        plane.rotation.x = Math.PI / 2
        group.add(plane)
      }
      
      return group
    }

    // 创建速度场可视化
    const createVelocityField = () => {
      const group = new THREE.Group()
      
      // 简化速度场可视化
      const { channel_length } = parameters
      const arrowCount = 50
      
      for (let i = 0; i < arrowCount; i++) {
        const x = (Math.random() - 0.5) * 2
        const y = Math.random() * 1 + 0.5
        const z = (Math.random() - 0.5) * channel_length
        
        // 创建箭头表示速度
        const direction = new THREE.Vector3(0, 0, 1)
        const length = 0.3 + Math.random() * 0.2
        const hex = 0x00ff00
        
        const arrowHelper = new THREE.ArrowHelper(direction, new THREE.Vector3(x, y, z), length, hex, 0.1, 0.05)
        group.add(arrowHelper)
      }
      
      return group
    }

    // 创建压力场可视化
    const createPressureField = () => {
      const group = new THREE.Group()
      
      // 简化压力场可视化
      const { channel_length } = parameters
      const pointCount = 100
      
      for (let i = 0; i < pointCount; i++) {
        const x = (Math.random() - 0.5) * 2
        const y = Math.random() * 1 + 0.5
        const z = (Math.random() - 0.5) * channel_length
        
        // 压力大小用球体大小表示
        const pressure = 0.5 + Math.random() * 0.5
        const size = 0.02 + pressure * 0.03
        const color = new THREE.Color().setHSL(0.1, 0.8, 0.6)
        
        const geometry = new THREE.SphereGeometry(size, 8, 8)
        const material = new THREE.MeshBasicMaterial({ color })
        const sphere = new THREE.Mesh(geometry, material)
        sphere.position.set(x, y, z)
        group.add(sphere)
      }
      
      return group
    }

    let currentVisualization: THREE.Group | null = null

    const updateVisualization = () => {
      // 移除之前的可视化
      if (currentVisualization) {
        scene.remove(currentVisualization)
      }

      // 根据视图模式创建新的可视化
      switch (viewMode) {
        case 'geometry':
          currentVisualization = createMicrochannelGeometry()
          break
        case 'temperature':
          currentVisualization = createTemperatureField()
          break
        case 'velocity':
          currentVisualization = createVelocityField()
          break
        case 'pressure':
          currentVisualization = createPressureField()
          break
      }

      if (currentVisualization) {
        scene.add(currentVisualization)
      }
    }

    // 初始可视化
    updateVisualization()

    // 添加到DOM
    mountRef.current.appendChild(renderer.domElement)

    // 动画循环
    const animate = () => {
      requestAnimationFrame(animate)
      
      // 更新控制器
      controls.update()
      
      // 简单的动画效果
      if (currentVisualization && viewMode !== 'geometry') {
        currentVisualization.rotation.y += 0.001 * animationSpeed
      }
      
      renderer.render(scene, camera)
    }
    animate()

    // 响应式调整
    const handleResize = () => {
      if (!mountRef.current) return
      
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight)
    }

    window.addEventListener('resize', handleResize)

    // 清理函数
    return () => {
      window.removeEventListener('resize', handleResize)
      mountRef.current?.removeChild(renderer.domElement)
      renderer.dispose()
    }
  }, [parameters, viewMode, animationSpeed])

  return (
    <Card 
      title={
        <Space>
          <EyeOutlined />
          <Text strong>3D可视化</Text>
        </Space>
      }
      className="visualization-container"
      extra={
        <Space>
          <Text>动画速度:</Text>
          <Slider
            min={0}
            max={3}
            step={0.1}
            value={animationSpeed}
            onChange={setAnimationSpeed}
            style={{ width: 100 }}
            tooltip={{ formatter: (val) => `${val}x` }}
          />
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%', height: '100%' }}>
        {/* 视图模式选择 */}
        <Radio.Group 
          value={viewMode} 
          onChange={(e) => setViewMode(e.target.value)}
          buttonStyle="solid"
        >
          <Radio.Button value="geometry">
            <Space>
              <ExperimentOutlined />
              几何结构
            </Space>
          </Radio.Button>
          <Radio.Button value="temperature">
            <Space>
              <HeatMapOutlined />
              温度场
            </Space>
          </Radio.Button>
          <Radio.Button value="velocity">
            <Space>
              <ThunderboltOutlined />
              速度场
            </Space>
          </Radio.Button>
          <Radio.Button value="pressure">
            <Space>
              <ExperimentOutlined />
              压力场
            </Space>
          </Radio.Button>
        </Radio.Group>

        {/* 3D画布 */}
        <div 
          ref={mountRef} 
          className="three-canvas"
          style={{ 
            height: 'calc(100% - 50px)',
            border: '1px solid #d9d9d9',
            borderRadius: '6px'
          }}
        />

        {/* 图例说明 */}
        <Space direction="vertical" size="small" style={{ fontSize: '12px', color: '#666' }}>
          <Text>图例说明:</Text>
          <Space>
            <div style={{ width: 12, height: 12, backgroundColor: '#2196f3', opacity: 0.7 }} />
            <Text>流体通道</Text>
          </Space>
          <Space>
            <div style={{ width: 12, height: 12, backgroundColor: '#795548' }} />
            <Text>壁面</Text>
          </Space>
          <Space>
            <div style={{ width: 12, height: 12, backgroundColor: '#607d8b' }} />
            <Text>基底</Text>
          </Space>
        </Space>
      </Space>
    </Card>
  )
}

export default ThreeDVisualization