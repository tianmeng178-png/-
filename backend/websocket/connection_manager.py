from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional
import json
import asyncio
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ConnectionInfo:
    websocket: WebSocket
    simulation_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    is_alive: bool = True


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[ConnectionInfo]] = {}
        self.subscribers: Dict[str, Set[WebSocket]] = {}
        self.connection_by_ws: Dict[WebSocket, ConnectionInfo] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30
        self._heartbeat_timeout = 180
    
    async def start_heartbeat_monitor(self):
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            print("💓 WebSocket心跳监控已启动")
    
    async def stop_heartbeat_monitor(self):
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            print("💔 WebSocket心跳监控已停止")
    
    async def _heartbeat_loop(self):
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self._check_connections_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"心跳检测错误: {e}")
    
    async def _check_connections_health(self):
        now = datetime.now()
        dead_connections = []
        
        for ws, conn_info in self.connection_by_ws.items():
            if not conn_info.is_alive:
                continue
            
            time_since_ping = (now - conn_info.last_ping).total_seconds()
            
            if time_since_ping > self._heartbeat_timeout:
                print(f"⚠️ 连接超时，准备断开: {conn_info.simulation_id}")
                dead_connections.append((ws, conn_info))
            else:
                try:
                    await ws.send_json({"type": "ping", "timestamp": now.isoformat()})
                except Exception as e:
                    print(f"发送心跳失败: {e}")
                    dead_connections.append((ws, conn_info))
        
        for ws, conn_info in dead_connections:
            await self._close_connection(ws, conn_info, "心跳超时")
    
    async def _close_connection(self, websocket: WebSocket, conn_info: ConnectionInfo, reason: str = ""):
        try:
            conn_info.is_alive = False
            await websocket.close(code=1000, reason=reason)
        except Exception:
            pass
        
        self.disconnect(websocket, conn_info.simulation_id)
    
    async def connect(self, websocket: WebSocket, simulation_id: str):
        await websocket.accept()
        
        conn_info = ConnectionInfo(
            websocket=websocket,
            simulation_id=simulation_id
        )
        
        if simulation_id not in self.active_connections:
            self.active_connections[simulation_id] = []
        self.active_connections[simulation_id].append(conn_info)
        
        self.connection_by_ws[websocket] = conn_info
        
        print(f"✅ WebSocket 连接成功: {simulation_id} (当前连接数: {len(self.connection_by_ws)})")
        
        # 发送连接成功消息给客户端
        try:
            await websocket.send_json({
                "type": "connected",
                "simulation_id": simulation_id,
                "message": "WebSocket连接成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"发送连接确认消息失败: {e}")
        
        await self.start_heartbeat_monitor()
    
    def disconnect(self, websocket: WebSocket, simulation_id: str):
        if websocket in self.connection_by_ws:
            del self.connection_by_ws[websocket]
        
        if simulation_id in self.active_connections:
            self.active_connections[simulation_id] = [
                conn for conn in self.active_connections[simulation_id]
                if conn.websocket != websocket
            ]
            if not self.active_connections[simulation_id]:
                del self.active_connections[simulation_id]
        
        if simulation_id in self.subscribers:
            self.subscribers[simulation_id].discard(websocket)
            if not self.subscribers[simulation_id]:
                del self.subscribers[simulation_id]
        
        print(f"❌ WebSocket 断开连接: {simulation_id} (剩余连接数: {len(self.connection_by_ws)})")
    
    def handle_pong(self, websocket: WebSocket):
        if websocket in self.connection_by_ws:
            self.connection_by_ws[websocket].last_ping = datetime.now()
            self.connection_by_ws[websocket].is_alive = True
    
    async def subscribe_to_simulation(self, websocket: WebSocket, simulation_id: str):
        if simulation_id not in self.subscribers:
            self.subscribers[simulation_id] = set()
        self.subscribers[simulation_id].add(websocket)
        print(f"📡 客户端订阅仿真更新: {simulation_id}")
        
        # 发送订阅确认消息
        try:
            await websocket.send_json({
                "type": "subscribed",
                "simulation_id": simulation_id,
                "message": "已成功订阅仿真更新",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"发送订阅确认消息失败: {e}")
    
    async def send_message(self, simulation_id: str, message: dict):
        if simulation_id not in self.subscribers:
            return
        
        disconnected = []
        for connection in self.subscribers[simulation_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"发送消息失败: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn, simulation_id)
    
    async def send_to_all_connections(self, simulation_id: str, message: dict):
        if simulation_id not in self.active_connections:
            return
        
        disconnected = []
        for conn_info in self.active_connections[simulation_id]:
            if not conn_info.is_alive:
                continue
            try:
                await conn_info.websocket.send_json(message)
            except Exception as e:
                print(f"发送消息失败: {e}")
                disconnected.append(conn_info.websocket)
        
        for ws in disconnected:
            self.disconnect(ws, simulation_id)
    
    async def broadcast(self, message: dict):
        for simulation_id in list(self.subscribers.keys()):
            await self.send_message(simulation_id, message)
    
    def get_connection_count(self) -> int:
        return len(self.connection_by_ws)
    
    def get_simulation_connection_count(self, simulation_id: str) -> int:
        return len(self.active_connections.get(simulation_id, []))
    
    def get_subscriber_count(self, simulation_id: str) -> int:
        return len(self.subscribers.get(simulation_id, set()))
    
    def get_connection_stats(self) -> dict:
        return {
            "total_connections": len(self.connection_by_ws),
            "simulations_with_connections": len(self.active_connections),
            "simulations_with_subscribers": len(self.subscribers),
            "connection_details": {
                sim_id: len(conns) 
                for sim_id, conns in self.active_connections.items()
            }
        }
    
    async def close_all_connections(self):
        for ws, conn_info in list(self.connection_by_ws.items()):
            try:
                await ws.close(code=1000, reason="服务器关闭")
            except Exception:
                pass
        
        self.active_connections.clear()
        self.subscribers.clear()
        self.connection_by_ws.clear()
        
        await self.stop_heartbeat_monitor()
        print("🔒 所有WebSocket连接已关闭")
