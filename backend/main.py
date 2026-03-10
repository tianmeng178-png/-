from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List
import os

from models.simulation import SimulationParameters, SimulationStatus, PerformanceMetrics
from services.simulation_manager import SimulationManager
from services.openfoam_service import OpenFOAMService
from services.llm_service import LLMService
from websocket.connection_manager import ConnectionManager

# 创建FastAPI应用
app = FastAPI(
    title="AI-Driven Heat Exchanger Design System",
    description="基于OpenFOAM的微通道散热器智能设计系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
simulation_manager = SimulationManager()
connection_manager = ConnectionManager()
openfoam_service = OpenFOAMService()
llm_service = LLMService()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "AI-Driven Heat Exchanger Design System API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """系统健康检查"""
    try:
        # 检查OpenFOAM服务
        openfoam_status = await openfoam_service.check_availability()
        
        # 检查LLM服务
        llm_status = await llm_service.check_availability()
        
        # 确定整体状态
        if openfoam_status and llm_status:
            status = "healthy"
        elif openfoam_status or llm_status:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "services": {
                "openfoam": openfoam_status,
                "llm": llm_status,
                "database": True  # 暂时硬编码
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")

@app.post("/api/parse-description")
async def parse_description(description: dict):
    """解析自然语言描述为仿真参数"""
    try:
        text = description.get("description", "")
        if not text:
            raise HTTPException(status_code=400, detail="描述不能为空")
        
        result = await llm_service.parse_parameters(text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@app.post("/api/validate-parameters")
async def validate_parameters(parameters: SimulationParameters):
    """验证仿真参数"""
    try:
        validation_result = await simulation_manager.validate_parameters(parameters)
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参数验证失败: {str(e)}")

@app.post("/api/simulation/start")
async def start_simulation(parameters: SimulationParameters):
    """开始新的仿真"""
    try:
        # 验证参数
        validation_result = await simulation_manager.validate_parameters(parameters)
        if not validation_result.is_valid:
            raise HTTPException(status_code=400, detail={
                "message": "参数验证失败",
                "errors": validation_result.errors
            })
        
        # 创建仿真ID
        simulation_id = str(uuid.uuid4())
        
        # 启动仿真
        await simulation_manager.start_simulation(simulation_id, parameters)
        
        return {
            "simulation_id": simulation_id,
            "message": "仿真已开始",
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"仿真启动失败: {str(e)}")

@app.get("/api/simulation/{simulation_id}/status")
async def get_simulation_status(simulation_id: str):
    """获取仿真状态"""
    try:
        status = await simulation_manager.get_simulation_status(simulation_id)
        if not status:
            raise HTTPException(status_code=404, detail="仿真不存在")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/pause")
async def pause_simulation(simulation_id: str):
    """暂停仿真"""
    try:
        await simulation_manager.pause_simulation(simulation_id)
        return {"message": "仿真已暂停"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/stop")
async def stop_simulation(simulation_id: str):
    """停止仿真"""
    try:
        await simulation_manager.stop_simulation(simulation_id)
        return {"message": "仿真已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")

@app.get("/api/simulation/{simulation_id}/results")
async def get_simulation_results(simulation_id: str):
    """获取仿真结果"""
    try:
        results = await simulation_manager.get_simulation_results(simulation_id)
        if not results:
            raise HTTPException(status_code=404, detail="仿真结果不存在")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/report")
async def generate_report(simulation_id: str, template: dict = None):
    """生成工程报告"""
    try:
        report_data = await simulation_manager.generate_report(
            simulation_id, 
            template.get("template") if template else None
        )
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")

@app.websocket("/ws/simulation/{simulation_id}")
async def websocket_endpoint(websocket: WebSocket, simulation_id: str):
    """WebSocket连接端点"""
    await connection_manager.connect(websocket, simulation_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            if message.get("type") == "subscribe":
                # 客户端订阅仿真更新
                await connection_manager.subscribe_to_simulation(websocket, simulation_id)
                
                # 发送当前状态
                status = await simulation_manager.get_simulation_status(simulation_id)
                if status:
                    await websocket.send_text(json.dumps({
                        "type": "status_update",
                        "status": status.dict()
                    }))
            
            elif message.get("type") == "control":
                # 处理控制命令
                command = message.get("command")
                if command == "pause":
                    await simulation_manager.pause_simulation(simulation_id)
                elif command == "resume":
                    await simulation_manager.resume_simulation(simulation_id)
                elif command == "stop":
                    await simulation_manager.stop_simulation(simulation_id)
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, simulation_id)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        connection_manager.disconnect(websocket, simulation_id)

# 启动服务器
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )