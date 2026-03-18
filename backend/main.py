from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import os

from models.simulation import SimulationParameters, SimulationStatus, PerformanceMetrics
from services.simulation_manager import SimulationManager
from services.openfoam_service import OpenFOAMService
from services.llm_service import LLMService
from services.data_storage import SimulationHistory, ParameterPresets
from websocket.connection_manager import ConnectionManager

simulation_manager = SimulationManager()
connection_manager = ConnectionManager()
openfoam_service = OpenFOAMService()
llm_service = LLMService()
simulation_history = SimulationHistory()
parameter_presets = ParameterPresets()


def load_system_config() -> Dict[str, Any]:
    config_path = Path(__file__).resolve().parents[1] / "config" / "system_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

async def progress_callback(simulation_id: str, message: dict):
    await connection_manager.send_message(simulation_id, message)
    
    if message.get("type") == "completed":
        sim_data = simulation_manager.simulations.get(simulation_id)
        if sim_data:
            simulation_history.update_simulation_status(
                simulation_id,
                "completed",
                sim_data.get("performance_metrics").dict() if sim_data.get("performance_metrics") else None
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    simulation_manager.set_progress_callback(progress_callback)
    os.makedirs("static", exist_ok=True)
    os.makedirs("data/simulations", exist_ok=True)
    os.makedirs("data/presets", exist_ok=True)
    print("🚀 AI-Driven Heat Exchanger Design System 启动中...")
    print("📊 数据持久化服务已初始化")
    yield
    await connection_manager.close_all_connections()
    print("👋 系统关闭，所有连接已清理")

app = FastAPI(
    title="AI-Driven Heat Exchanger Design System",
    description="基于OpenFOAM的微通道散热器智能设计系统API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {
        "message": "AI-Driven Heat Exchanger Design System API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "websocket_stats": "/api/websocket/stats",
        "endpoints": {
            "simulation": "/api/simulation",
            "history": "/api/history",
            "presets": "/api/presets"
        }
    }

@app.get("/api/health")
async def health_check():
    try:
        openfoam_status = await openfoam_service.check_availability()
        llm_status = await llm_service.check_availability()
        
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
                "database": True,
                "websocket": connection_manager.get_connection_count()
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")

@app.get("/api/websocket/stats")
async def websocket_stats():
    return connection_manager.get_connection_stats()


@app.post("/api/tools/paraview/launch")
async def launch_paraview(payload: Dict[str, Optional[str]] = None):
    config = load_system_config()
    tools_config = config.get("tools", {})
    paraview_link = tools_config.get("paraview_link")

    if not paraview_link or not Path(paraview_link).exists():
        raise HTTPException(status_code=404, detail="ParaView 启动路径未配置或不存在")

    target = paraview_link
    if payload:
        case_file = payload.get("case_file")
        if case_file and Path(case_file).exists():
            target = case_file

    try:
        subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        return {"status": "launched", "target": target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 ParaView 失败: {str(e)}")


@app.post("/api/tools/open-path")
async def open_path(payload: Dict[str, str]):
    target_path = payload.get("path")
    if not target_path or not Path(target_path).exists():
        raise HTTPException(status_code=404, detail="路径不存在")

    try:
        subprocess.Popen(["cmd", "/c", "start", "", target_path], shell=False)
        return {"status": "opened", "path": target_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开路径失败: {str(e)}")

@app.post("/api/parse-description")
async def parse_description(description: dict):
    try:
        text = description.get("description", "")
        if not text:
            raise HTTPException(status_code=400, detail="描述不能为空")
        
        result = await llm_service.parse_parameters(text)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@app.post("/api/validate-parameters")
async def validate_parameters(parameters: SimulationParameters):
    try:
        validation_result = await simulation_manager.validate_parameters(parameters)
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参数验证失败: {str(e)}")

@app.post("/api/debug/simulation-data")
async def debug_simulation_data(request: Request):
    try:
        raw_data = await request.json()
        print(f"🔍 原始请求数据: {raw_data}")
        return {"status": "success", "data": raw_data}
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.post("/api/simulation/start")
async def start_simulation(parameters: SimulationParameters):
    try:
        print(f"📥 接收到参数: {parameters.dict()}")
        validation_result = await simulation_manager.validate_parameters(parameters)
        if not validation_result.is_valid:
            print(f"❌ 验证失败: errors={validation_result.errors}, warnings={validation_result.warnings}")
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "参数验证失败",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }
            )
        
        simulation_id = str(uuid.uuid4())
        
        simulation_history.save_simulation(
            simulation_id,
            parameters.dict(),
            "running"
        )
        
        await simulation_manager.start_simulation(simulation_id, parameters)
        
        return {
            "simulation_id": simulation_id,
            "message": "仿真已开始",
            "status": "running",
            "websocket_url": f"/ws/simulation/{simulation_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"仿真启动失败: {str(e)}")

@app.get("/api/simulation/{simulation_id}/status")
async def get_simulation_status(simulation_id: str):
    try:
        status = await simulation_manager.get_simulation_status(simulation_id)
        if not status:
            history_record = simulation_history.get_simulation(simulation_id)
            if history_record:
                return {
                    "simulation_id": simulation_id,
                    "status": history_record.get("status"),
                    "progress": 100 if history_record.get("status") == "completed" else 0,
                    "current_step": "历史记录",
                    "log_messages": []
                }
            raise HTTPException(status_code=404, detail="仿真不存在")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/pause")
async def pause_simulation(simulation_id: str):
    try:
        await simulation_manager.pause_simulation(simulation_id)
        simulation_history.update_simulation_status(simulation_id, "paused")
        return {"message": "仿真已暂停", "simulation_id": simulation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/resume")
async def resume_simulation(simulation_id: str):
    try:
        await simulation_manager.resume_simulation(simulation_id)
        simulation_history.update_simulation_status(simulation_id, "running")
        return {"message": "仿真已恢复", "simulation_id": simulation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/stop")
async def stop_simulation(simulation_id: str):
    try:
        await simulation_manager.stop_simulation(simulation_id)
        simulation_history.update_simulation_status(simulation_id, "stopped")
        return {"message": "仿真已停止", "simulation_id": simulation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")

@app.get("/api/simulation/{simulation_id}/results")
async def get_simulation_results(simulation_id: str):
    try:
        results = await simulation_manager.get_simulation_results(simulation_id)
        if not results:
            history_record = simulation_history.get_simulation(simulation_id)
            if history_record and history_record.get("status") == "completed":
                return {
                    "simulation_id": simulation_id,
                    "parameters": history_record.get("parameters"),
                    "performance_metrics": history_record.get("performance_metrics"),
                    "visualization_data": {},
                    "created_at": history_record.get("created_at")
                }
            raise HTTPException(status_code=404, detail="仿真结果不存在或仿真未完成")
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")

@app.get("/api/simulation/{simulation_id}/paraview-web")
async def get_paraview_web(simulation_id: str):
    try:
        return simulation_manager.get_paraview_info(simulation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 ParaViewWeb 信息失败: {str(e)}")

@app.post("/api/simulation/{simulation_id}/report")
async def generate_report(simulation_id: str, template: dict = None):
    try:
        report_data = await simulation_manager.generate_report(
            simulation_id, 
            template.get("template") if template else None
        )
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")

@app.get("/api/history")
async def get_history(limit: int = 50, status: Optional[str] = None):
    try:
        history = simulation_history.get_history(limit=limit, status=status)
        return {
            "total": len(history),
            "simulations": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")

@app.get("/api/history/{simulation_id}")
async def get_history_detail(simulation_id: str):
    try:
        record = simulation_history.get_simulation(simulation_id)
        if not record:
            raise HTTPException(status_code=404, detail="仿真记录不存在")
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记录详情失败: {str(e)}")

@app.delete("/api/history/{simulation_id}")
async def delete_history(simulation_id: str):
    try:
        success = simulation_history.delete_simulation(simulation_id)
        if not success:
            raise HTTPException(status_code=404, detail="仿真记录不存在")
        return {"message": "记录已删除", "simulation_id": simulation_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记录失败: {str(e)}")

@app.get("/api/history/statistics")
async def get_statistics():
    try:
        stats = simulation_history.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.post("/api/history/search")
async def search_history(query: dict):
    try:
        results = simulation_history.search_simulations(query)
        return {
            "total": len(results),
            "simulations": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/presets")
async def get_presets():
    try:
        presets = parameter_presets.get_all_presets()
        return {
            "total": len(presets),
            "presets": presets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预设失败: {str(e)}")

@app.get("/api/presets/{preset_id}")
async def get_preset(preset_id: str):
    try:
        preset = parameter_presets.get_preset(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="预设不存在")
        return preset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预设失败: {str(e)}")

@app.post("/api/presets")
async def create_preset(preset_data: dict):
    try:
        name = preset_data.get("name")
        parameters = preset_data.get("parameters")
        description = preset_data.get("description", "")
        
        if not name or not parameters:
            raise HTTPException(status_code=400, detail="名称和参数不能为空")
        
        new_preset = parameter_presets.save_preset(name, parameters, description)
        return new_preset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建预设失败: {str(e)}")

@app.delete("/api/presets/{preset_id}")
async def delete_preset(preset_id: str):
    try:
        success = parameter_presets.delete_preset(preset_id)
        if not success:
            raise HTTPException(status_code=404, detail="预设不存在或为默认预设")
        return {"message": "预设已删除", "preset_id": preset_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除预设失败: {str(e)}")

@app.websocket("/ws/simulation/{simulation_id}")
async def websocket_endpoint(websocket: WebSocket, simulation_id: str):
    await connection_manager.connect(websocket, simulation_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            connection_manager.handle_pong(websocket)
            
            if msg_type == "pong":
                pass
            
            elif msg_type == "subscribe":
                await connection_manager.subscribe_to_simulation(websocket, simulation_id)
                
                status = await simulation_manager.get_simulation_status(simulation_id)
                if status:
                    await websocket.send_json({
                        "type": "status_update",
                        "data": jsonable_encoder(status)
                    })
                else:
                    history_record = simulation_history.get_simulation(simulation_id)
                    if history_record:
                        await websocket.send_json({
                            "type": "status_update",
                            "data": {
                                "simulation_id": simulation_id,
                                "status": history_record.get("status"),
                                "progress": 100 if history_record.get("status") == "completed" else 0
                            }
                        })
                    else:
                        await websocket.send_json({
                            "type": "info",
                            "data": {"message": "等待仿真启动..."}
                        })
            
            elif msg_type == "control":
                command = message.get("command")
                if command == "pause":
                    await simulation_manager.pause_simulation(simulation_id)
                    simulation_history.update_simulation_status(simulation_id, "paused")
                    await websocket.send_json({
                        "type": "control_response",
                        "data": {"command": "pause", "status": "success"}
                    })
                elif command == "resume":
                    await simulation_manager.resume_simulation(simulation_id)
                    simulation_history.update_simulation_status(simulation_id, "running")
                    await websocket.send_json({
                        "type": "control_response",
                        "data": {"command": "resume", "status": "success"}
                    })
                elif command == "stop":
                    await simulation_manager.stop_simulation(simulation_id)
                    simulation_history.update_simulation_status(simulation_id, "stopped")
                    await websocket.send_json({
                        "type": "control_response",
                        "data": {"command": "stop", "status": "success"}
                    })
            
            elif msg_type == "get_status":
                status = await simulation_manager.get_simulation_status(simulation_id)
                if status:
                    await websocket.send_json({
                        "type": "status_update",
                        "data": status.dict()
                    })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, simulation_id)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        await websocket.send_json({
            "type": "error",
            "data": {"message": "消息格式错误"}
        })
    except Exception as e:
        print(f"WebSocket错误: {e}")
        connection_manager.disconnect(websocket, simulation_id)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
