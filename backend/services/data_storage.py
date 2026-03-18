import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid


class SimulationHistory:
    def __init__(self, storage_dir: str = "data/simulations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "history.json"
        self._ensure_history_file()
    
    def _ensure_history_file(self):
        if not self.history_file.exists():
            self._write_history([])
    
    def _read_history(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _write_history(self, history: List[Dict[str, Any]]):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2, default=str)
    
    def save_simulation(self, simulation_id: str, parameters: Dict[str, Any], 
                       status: str, performance_metrics: Optional[Dict] = None) -> Dict[str, Any]:
        history = self._read_history()
        
        simulation_record = {
            "simulation_id": simulation_id,
            "parameters": parameters,
            "status": status,
            "performance_metrics": performance_metrics,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        existing_index = None
        for i, record in enumerate(history):
            if record.get("simulation_id") == simulation_id:
                existing_index = i
                break
        
        if existing_index is not None:
            simulation_record["created_at"] = history[existing_index].get("created_at", datetime.now().isoformat())
            history[existing_index] = simulation_record
        else:
            history.insert(0, simulation_record)
        
        self._write_history(history)
        
        self._save_simulation_detail(simulation_id, simulation_record)
        
        return simulation_record
    
    def _save_simulation_detail(self, simulation_id: str, record: Dict[str, Any]):
        detail_file = self.storage_dir / f"{simulation_id}.json"
        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    
    def get_simulation(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        detail_file = self.storage_dir / f"{simulation_id}.json"
        
        if detail_file.exists():
            with open(detail_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        history = self._read_history()
        for record in history:
            if record.get("simulation_id") == simulation_id:
                return record
        
        return None
    
    def get_history(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        history = self._read_history()
        
        if status:
            history = [r for r in history if r.get("status") == status]
        
        return history[:limit]
    
    def update_simulation_status(self, simulation_id: str, status: str, 
                                 performance_metrics: Optional[Dict] = None):
        record = self.get_simulation(simulation_id)
        
        if record:
            record["status"] = status
            record["updated_at"] = datetime.now().isoformat()
            
            if performance_metrics:
                record["performance_metrics"] = performance_metrics
            
            self.save_simulation(
                simulation_id,
                record.get("parameters", {}),
                status,
                performance_metrics
            )
            
            return record
        
        return None
    
    def delete_simulation(self, simulation_id: str) -> bool:
        history = self._read_history()
        original_length = len(history)
        
        history = [r for r in history if r.get("simulation_id") != simulation_id]
        
        if len(history) < original_length:
            self._write_history(history)
            
            detail_file = self.storage_dir / f"{simulation_id}.json"
            if detail_file.exists():
                detail_file.unlink()
            
            return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        history = self._read_history()
        
        total_count = len(history)
        
        status_counts = {}
        for record in history:
            status = record.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        avg_metrics = {}
        completed = [r for r in history if r.get("status") == "completed" and r.get("performance_metrics")]
        
        if completed:
            metrics_keys = ["max_temperature", "pressure_drop", "heat_transfer_coefficient", "efficiency"]
            for key in metrics_keys:
                values = [r["performance_metrics"].get(key) for r in completed if r["performance_metrics"].get(key)]
                if values:
                    avg_metrics[f"avg_{key}"] = sum(values) / len(values)
        
        return {
            "total_simulations": total_count,
            "status_distribution": status_counts,
            "average_metrics": avg_metrics,
            "last_updated": datetime.now().isoformat()
        }
    
    def search_simulations(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        history = self._read_history()
        results = []
        
        for record in history:
            match = True
            
            if "fluid_type" in query:
                params = record.get("parameters", {})
                if params.get("fluid_type") != query["fluid_type"]:
                    match = False
            
            if "solid_material" in query:
                params = record.get("parameters", {})
                if params.get("solid_material") != query["solid_material"]:
                    match = False
            
            if "status" in query:
                if record.get("status") != query["status"]:
                    match = False
            
            if "min_efficiency" in query:
                metrics = record.get("performance_metrics", {})
                if metrics.get("efficiency", 0) < query["min_efficiency"]:
                    match = False
            
            if match:
                results.append(record)
        
        return results


class ParameterPresets:
    def __init__(self, storage_dir: str = "data/presets"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.presets_file = self.storage_dir / "presets.json"
        self._ensure_presets_file()
    
    def _ensure_presets_file(self):
        if not self.presets_file.exists():
            default_presets = self._get_default_presets()
            self._write_presets(default_presets)
    
    def _get_default_presets(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "default_water_copper",
                "name": "水冷铜基板标准配置",
                "description": "适用于大多数电子设备散热的标准配置",
                "parameters": {
                    "channel_width": 0.0001,
                    "channel_height": 0.0005,
                    "channel_length": 0.01,
                    "channel_count": 10,
                    "wall_thickness": 0.00005,
                    "inlet_velocity": 0.2,
                    "inlet_temperature": 298.15,
                    "outlet_pressure": 0,
                    "heat_flux": 500000,
                    "base_temperature": 353.15,
                    "fluid_type": "water",
                    "solid_material": "copper"
                },
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            {
                "id": "high_power",
                "name": "高功率散热配置",
                "description": "适用于高功率密度电子设备",
                "parameters": {
                    "channel_width": 0.00015,
                    "channel_height": 0.0008,
                    "channel_length": 0.02,
                    "channel_count": 20,
                    "wall_thickness": 0.00005,
                    "inlet_velocity": 0.5,
                    "inlet_temperature": 293.15,
                    "outlet_pressure": 0,
                    "heat_flux": 800000,
                    "base_temperature": 373.15,
                    "fluid_type": "water",
                    "solid_material": "copper"
                },
                "created_at": datetime.now().isoformat(),
                "is_default": False
            },
            {
                "id": "air_cooling",
                "name": "风冷配置",
                "description": "适用于低功率或空气冷却场景",
                "parameters": {
                    "channel_width": 0.0002,
                    "channel_height": 0.001,
                    "channel_length": 0.015,
                    "channel_count": 15,
                    "wall_thickness": 0.0001,
                    "inlet_velocity": 1.0,
                    "inlet_temperature": 300.15,
                    "outlet_pressure": 0,
                    "heat_flux": 100000,
                    "base_temperature": 343.15,
                    "fluid_type": "air",
                    "solid_material": "aluminum"
                },
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        ]
    
    def _read_presets(self) -> List[Dict[str, Any]]:
        try:
            with open(self.presets_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._get_default_presets()
    
    def _write_presets(self, presets: List[Dict[str, Any]]):
        with open(self.presets_file, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=2, default=str)
    
    def get_all_presets(self) -> List[Dict[str, Any]]:
        return self._read_presets()
    
    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        presets = self._read_presets()
        for preset in presets:
            if preset.get("id") == preset_id:
                return preset
        return None
    
    def save_preset(self, name: str, parameters: Dict[str, Any], 
                   description: str = "") -> Dict[str, Any]:
        presets = self._read_presets()
        
        new_preset = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "parameters": parameters,
            "created_at": datetime.now().isoformat(),
            "is_default": False
        }
        
        presets.append(new_preset)
        self._write_presets(presets)
        
        return new_preset
    
    def delete_preset(self, preset_id: str) -> bool:
        presets = self._read_presets()
        original_length = len(presets)
        
        presets = [p for p in presets if p.get("id") != preset_id or p.get("is_default")]
        
        if len(presets) < original_length:
            self._write_presets(presets)
            return True
        
        return False
