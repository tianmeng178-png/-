# ParaViewWeb 实时流场 + 残差可视化设计

## 目标
- 真实模式下，实时展示 OpenFOAM 求解残差曲线。
- 真实模式下，提供可交互 3D 流场（ParaViewWeb / Trame）。
- 全流程工业级可追踪：仿真会话、端口、日志、异常清晰可定位。

## 非目标
- 不改动求解器物理模型（不“调参”去追求好看的数值）。
- 不在前端做伪 3D 或纯图片流替代真实渲染。

## 架构概览
1. 仿真执行层（WSL）：OpenFOAM 作为唯一真值源，输出时间步与场文件。
2. ParaViewWeb 服务层（WSL）：通过 `pvpython` 启动 Trame/ParaViewWeb，读取同一 case 目录。
3. 编排层（FastAPI）：负责仿真生命周期管理、ParaViewWeb 进程管理、残差解析与推送。
4. 实时通信层（WebSocket）：推送残差、求解日志、ParaViewWeb 访问地址。
5. 前端可视化层：残差曲线、求解器日志、3D 实时流场面板。

## 数据流
1. 前端启动仿真 → 后端生成 case → 启动 OpenFOAM 求解。
2. 求解过程中实时解析 stdout → 抽取残差信息 → WebSocket 推送。
3. 并行启动 ParaViewWeb，指向同一 case 目录 → 推送访问 URL 给前端。
4. 前端订阅 WebSocket → 实时更新残差曲线，并嵌入 3D 流场。

## 关键模块设计
### ParaViewWebService（后端）
- 负责选择端口、启动/停止进程、保存会话状态。
- 启动命令：优先使用 `pvpython -m paraview.web.serve`；若缺少模块则提示安装 Trame/ParaViewWeb。
- 对外返回：`url`、`port`、`status`。

### OpenFOAM 残差解析
- 解析 `Time = ...`、`Solving for ... Initial residual = ...` 行。
- 每条残差以 `{time, field, initial, final, iterations, region?}` 推送。
- 异常行统一归为 `solver_log`，便于排查。

### 前端展示
- 残差曲线（多曲线、可隐藏/显示）。
- 3D 实时流场视图（iframe 方式嵌入 ParaViewWeb）。
- 求解器日志面板（实时滚动）。

## 错误处理
- ParaViewWeb 启动失败 → WebSocket 发送 `paraview_web` 错误状态。
- 求解器异常/超时 → 前端显示错误提示并保留日志。
- WebSocket 断线 → 前端降级为轮询状态信息。

## 测试与验证
- 单次仿真：残差曲线持续更新，3D 画面可交互。
- 断线恢复：WebSocket 重连后继续订阅残差。
- 并行仿真：端口分配正确，互不干扰。
- 异常复现：异常时日志完整、可追踪到具体 case 目录。
