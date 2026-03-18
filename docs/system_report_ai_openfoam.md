# AI + OpenFOAM 微通道换热器设计系统技术报告（导师版）

> 版本日期：2026-03-12  
> 项目目录：`D:\openfoam闭环生态\heat_exchanger_ai`

## 1. 项目概述
本系统面向微通道换热器的智能设计与真实 CFD 验证，采用“AI 参数理解/校验 + OpenFOAM 真实仿真 + 可视化分析”的闭环流程。核心目标是：
1. 用自然语言或参数面板快速定义几何与工况；
2. 通过工程约束与参数校验保证可制造性与数值稳定性；
3. 在 **真实 OpenFOAM 11** 环境中完成网格、求解与结果提取；
4. 以 3D/2D 可视化与 ParaView 联动展示结果；
5. 明确区分快速模式（工程经验公式）与真实模式（OpenFOAM）。

## 2. 系统架构与模块
### 2.1 前端（React + Ant Design + Three.js）
- **主要目录**：`frontend/src`
- **参数面板**：`components/ParameterPanel.tsx`  
  - 支持模板参数、自然语言解析、参数验证、真实/快速模式切换；
  - 真实模式下 `mesh_resolution` 语义为“单元尺寸（m）”；快速模式为“单元数量”。
- **仿真监控**：`components/SimulationMonitor.tsx`  
  - WebSocket 实时进度 + 轮询兜底（避免断连导致卡住）；
  - 按钮状态与仿真状态强绑定：暂停/继续仅模拟模式可用，真实 OpenFOAM 模式提示不支持；
  - 新增“刷新状态”“打开 ParaView”“打开结果目录”。
- **3D 可视化**：`components/ThreeDVisualization.tsx`  
  - 基于 Three.js 的温度/速度/压力/几何视图；
  - 增加尺寸标注、坐标轴缩放、自适应视角；
  - 动画仅在速度场启用，避免“按钮无效”的错觉。
- **2D 可视化**：`components/ResultsPanel.tsx`  
  - Recharts 曲线 + Canvas 剖面热力图（示意）；真实场建议 ParaView。

### 2.2 后端（FastAPI）
- **主要目录**：`backend`
- **接口层**：`backend/main.py`
  - REST API + WebSocket；
  - 新增工具接口：
    - `POST /api/tools/paraview/launch`（启动 ParaView）
    - `POST /api/tools/open-path`（打开结果目录）
- **仿真管理**：`backend/services/simulation_manager.py`
  - 支持模拟模式与 OpenFOAM 模式；
  - 真模式严格依赖 WSL + OpenFOAM 11，不允许静默降级；
  - 结果完成后自动保存 OpenFOAM 案例目录；
  - 生成 `.foam` 文件供 ParaView 直接打开。
- **参数模型与验证**：`backend/models/simulation.py`
  - Pydantic 数据模型（几何/流动/热参数等）。
- **AI 参数解析**：`backend/services/llm_service.py`
  - 若存在 `nlp_parameter_parser` 则启用解析，否则使用可运行的模拟解析；
  - 可扩展接入真实 LLM 服务。

### 2.3 OpenFOAM 控制层（WSL）
- **核心控制器**：`src/foam_controller.py`
  - 通过 `wsl -d Ubuntu-24.04` 调用 OpenFOAM 11；
  - 网格生成：`blockMesh`
  - 求解：`foamRun -solver incompressibleFluid` + `scalarTransport` 温度场函数；
  - 结果读取：解析 OpenFOAM `T/p/U` 场文件，支持 `nonuniform List<scalar>`。
- **模板案例**：`openfoam_templates/microchannel`
  - `system/blockMeshDict`：参数化几何与网格；
  - `constant/physicalProperties`：粘性系数；
  - `system/controlDict`：`foamRun` + `scalarTransport`；
  - `system/fvSchemes/fvSolution`：基础设置。

### 2.4 数据与持久化
- **历史记录**：`backend/data/simulations/`
- **真实 OpenFOAM 案例**：`data/openfoam_cases/<simulation_id>/`
  - 自动生成 `.foam` 文件供 ParaView 打开。

## 3. 核心技术：AI + OpenFOAM
### 3.1 AI 侧能力
1. **自然语言参数解析**  
   - 解析通道宽高、流速、热流密度、材料类型等；
   - 输出缺失参数与建议，便于补齐输入。
2. **约束与安全校验**  
   - 对参数范围进行工程合理性检查（尺寸、速度、热流等）；
   - 提示潜在的压降风险或热安全风险。
3. **参数辅助优化**  
   - 基于规则给出尺寸/工况优化建议（例如避免过大压降、维持层流）。

### 3.2 OpenFOAM 侧能力
1. **真实 CFD 流程**  
   - `blockMesh` 生成网格；  
   - `foamRun` 驱动求解；  
   - `scalarTransport(T)` 温度场求解。  
2. **真实场结果提取**  
   - 从 OpenFOAM 输出目录解析 `T/p/U`；
   - 解析支持 `nonuniform List<scalar>`，避免把“单元数量”误读为温度。  
3. **性能适配**  
   - 动态超时估计：网格大时自动放宽超时；  
   - 保留真实模式精准性，不做自动降级。  

### 3.3 AI + OpenFOAM 协同流程（闭环）
1. AI 解析输入并校验；
2. 真实模式调用 OpenFOAM；
3. 输出数值结果 + 可视化；
4. 结果可用于再次优化参数（闭环迭代）。

## 4. 系统运行逻辑（真实模式）
1. 前端提交参数 `POST /api/simulation/start`；
2. 后端创建仿真实例并通过 WebSocket 推送状态；
3. 复制模板案例并写入几何/边界/物性参数；
4. 调用 `blockMesh` 生成网格；
5. 调用 `foamRun` 求解并输出场结果；
6. 提取 `T/p/U` 并计算性能指标；
7. 保存 `.foam` 供 ParaView 打开；
8. 前端展示曲线、剖面和 3D 视图。

## 5. 可视化体系
### 5.1 3D 可视化（Three.js）
- 直接展示几何体；
- 温度/速度/压力场以色彩映射渲染；
- 显示模型尺寸、坐标轴比例；
- 自适应视角和截图功能。

### 5.2 2D 可视化
- 参数驱动曲线（温度、压力、速度沿程变化）；
- 2D 剖面热力图（示意）；  
  - 真实场建议使用 ParaView 打开 `.foam`。

### 5.3 ParaView 联动
系统自动生成 `.foam` 文件，并提供一键启动 ParaView 入口。  
配置位置：`config/system_config.json` → `tools.paraview_link`。

## 6. 技术配置与关键文件
### 6.1 关键配置
`config/system_config.json`（示例）
```json
{
  "openfoam": {
    "use_wsl": true,
    "wsl_distro": "Ubuntu-24.04",
    "openfoam_path": "/opt/openfoam11",
    "keep_case_dir": true,
    "case_storage_dir": "data/openfoam_cases"
  },
  "tools": {
    "paraview_link": "C:\\Users\\16659\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Ubuntu-24.04\\ParaView (Ubuntu-24.04).lnk"
  }
}
```

### 6.2 端口与访问
- 前端默认：`http://localhost:5173`
- 后端默认：`http://localhost:8000`
- WebSocket：`ws://localhost:8000/ws/simulation/<simulation_id>`

## 7. 发展前景与潜力
1. **智能化设计迭代**  
   - 可引入强化学习或贝叶斯优化，基于真实 CFD 结果进行自动搜索与多目标优化。
2. **多物理场扩展**  
   - 由标量温度传输扩展到固-液耦合、多区域换热、相变。
3. **工程数据闭环**  
   - 结合实验数据校准模型，提升可信度；
   - 建立数据驱动的参数推荐与设计规则库。
4. **工业落地**  
   - 适配电子散热、微反应器、能量回收等工程应用场景；
   - 对接 CAD/CAE 流程，实现更完整的工程链路。

## 8. 新手搭建教程（完整步骤）
### 8.1 环境准备
1. Windows 10/11；
2. WSL2 + Ubuntu 24.04；
3. OpenFOAM 11（安装在 `/opt/openfoam11`）；
4. Node.js 18+；
5. Python 3.11+（建议使用 conda 或 venv）。

### 8.2 配置 WSL + OpenFOAM
在 WSL 中验证：
```bash
source /opt/openfoam11/etc/bashrc
foamRun -help
```

### 8.3 配置项目
编辑：
`D:\openfoam闭环生态\heat_exchanger_ai\config\system_config.json`  
确保 WSL 发行版与 OpenFOAM 路径正确。

### 8.4 安装依赖
```powershell
# 后端
cd D:\openfoam闭环生态\heat_exchanger_ai\backend
pip install -r requirements.txt

# 前端
cd D:\openfoam闭环生态\heat_exchanger_ai\frontend
npm install
```

### 8.5 启动服务
```powershell
# 后端
cd D:\openfoam闭环生态\heat_exchanger_ai\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd D:\openfoam闭环生态\heat_exchanger_ai\frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

### 8.6 运行真实仿真
1. 打开前端界面；
2. 在参数面板选择 `真实 OpenFOAM 模式`；
3. 设置几何参数与工况；
4. 设置 `单元尺寸`（建议 5-20 um）；
5. 点击“开始仿真”，完成后获取结果；
6. 点击“打开 ParaView”查看真实场。

## 9. 常见问题与建议
1. **仿真步骤卡住**  
   - 前端已加入轮询兜底；可点击“刷新状态”强制更新。
2. **温度异常高**  
   - 已修复 OpenFOAM 结果解析逻辑，避免把单元数误读为温度。
3. **真实模式耗时长**  
   - 调大单元尺寸或减少通道数量；
   - 真实模式不做自动降级，保证准确性。
4. **ParaView 无法打开**  
   - 检查 `tools.paraview_link` 是否正确；
   - 手动打开 `data/openfoam_cases/<id>/<id>.foam`。

---
**结论**：本系统实现了 AI 与 OpenFOAM 的深度融合，具备真实 CFD 求解能力与可扩展的智能化设计能力，可作为科研与工程验证平台持续演化。
