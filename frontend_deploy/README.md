# AI-Driven Heat Exchanger Design System - Frontend

基于 React + TypeScript + Three.js 的微通道散热器智能设计系统前端界面。

## 🚀 快速开始

### 本地开发

1. 安装依赖：
```bash
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

3. 访问 http://localhost:3000

### 部署到 Vercel

1. **上传到 GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/your-username/heat-exchanger-frontend.git
   git push -u origin main
   ```

2. **部署到 Vercel**
   - 访问 [Vercel](https://vercel.com)
   - 连接 GitHub 账户
   - 导入项目仓库
   - 配置环境变量：
     - `VITE_API_URL`: 后端 API 地址
     - `VITE_WS_HOST`: WebSocket 主机
     - `VITE_WS_PORT`: WebSocket 端口

3. **自动部署**
   - Vercel 会自动检测到项目并部署
   - 每次推送到 main 分支都会触发自动部署

## 📦 项目结构

```
src/
├── components/          # React 组件
│   ├── ParameterPanel.tsx    # 参数输入面板
│   ├── SimulationMonitor.tsx # 仿真监控界面
│   └── ThreeDVisualization.tsx # 3D 可视化
├── services/            # API 服务
│   └── api.ts          # API 和 WebSocket 服务
├── stores/             # 状态管理
│   └── useStore.ts     # Zustand 状态管理
├── types/              # TypeScript 类型定义
│   └── index.ts        # 类型定义
└── App.tsx             # 主应用组件
```

## 🔧 技术栈

- **前端框架**: React 18 + TypeScript
- **构建工具**: Vite
- **3D 可视化**: Three.js
- **UI 组件库**: Ant Design
- **状态管理**: Zustand
- **HTTP 客户端**: Axios
- **实时通信**: WebSocket

## 🌐 环境变量

创建 `.env` 文件（基于 `.env.example`）：

```env
# 开发环境
VITE_API_URL=http://localhost:8000/api
VITE_WS_HOST=localhost
VITE_WS_PORT=8000

# 生产环境
# VITE_API_URL=https://your-backend-domain.com/api
# VITE_WS_HOST=your-backend-domain.com
# VITE_WS_PORT=443
```

## 📱 功能特性

- ✅ 微通道几何参数配置
- ✅ 3D 实时可视化展示
- ✅ 仿真进度实时监控
- ✅ WebSocket 实时通信
- ✅ 响应式设计
- ✅ 多视图模式切换

## 🔗 后端 API

需要配合后端服务使用：
- API 地址：`VITE_API_URL`
- WebSocket 地址：自动根据协议生成

## 📄 许可证

MIT License