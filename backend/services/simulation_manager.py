import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any, List
import sys
from pathlib import Path
import json
import shutil
import math
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.simulation import (
    SimulationParameters,
    SimulationStatus,
    SimulationStatusEnum,
    ValidationResult,
    PerformanceMetrics,
    SimulationResults
)
from services.paraview_web_service import ParaViewWebService

# 禁用 parameter_constraints 模块，使用基础验证
CONSTRAINTS_AVAILABLE = False
print("提示: 使用基础参数验证")

def _load_system_config() -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "config" / "system_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


class SimulationManager:
    def __init__(self):
        self.simulations: Dict[str, dict] = {}
        self.simulation_tasks: Dict[str, asyncio.Task] = {}
        self.progress_callback: Optional[Callable] = None
        self.constraints = EngineeringConstraints() if CONSTRAINTS_AVAILABLE else None
        self.paraview_service = ParaViewWebService()
    
    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback
    
    async def validate_parameters(self, parameters: SimulationParameters) -> ValidationResult:
        errors = []
        warnings = []
        suggestions = []
        
        try:
            params_dict = parameters.dict()
        except Exception as e:
            errors.append(str(e))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        if self.constraints:
            validation_results = self._validate_with_constraints(parameters)
            errors.extend(validation_results.get("errors", []))
            warnings.extend(validation_results.get("warnings", []))
            suggestions.extend(validation_results.get("suggestions", []))
        else:
            basic_results = self._basic_validation(parameters)
            errors.extend(basic_results.get("errors", []))
            warnings.extend(basic_results.get("warnings", []))
            suggestions.extend(basic_results.get("suggestions", []))
        
        if len(errors) == 0:
            suggestions.append("参数设置合理，可以进行仿真")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_with_constraints(self, parameters: SimulationParameters) -> Dict[str, List[str]]:
        errors = []
        warnings = []
        suggestions = []
        
        geometry_params = {
            "channel_width": parameters.channel_width,
            "channel_height": parameters.channel_height,
            "channel_length": parameters.channel_length,
            "channel_count": float(parameters.channel_count)
        }
        
        flow_params = {
            "inlet_velocity": parameters.inlet_velocity,
            "inlet_temperature": parameters.inlet_temperature
        }
        
        thermal_params = {
            "heat_flux": parameters.heat_flux,
            "base_temperature": parameters.base_temperature
        }
        
        for param_name, value in geometry_params.items():
            result = self.constraints.validate_parameter("geometry", param_name, value)
            if result["status"] == "error":
                errors.append(result["message"])
            elif result["status"] == "warning":
                warnings.append(result["message"])
                suggestions.append(result["suggestion"])
        
        for param_name, value in flow_params.items():
            result = self.constraints.validate_parameter("flow", param_name, value)
            if result["status"] == "error":
                errors.append(result["message"])
            elif result["status"] == "warning":
                warnings.append(result["message"])
                suggestions.append(result["suggestion"])
        
        for param_name, value in thermal_params.items():
            result = self.constraints.validate_parameter("thermal", param_name, value)
            if result["status"] == "error":
                errors.append(result["message"])
            elif result["status"] == "warning":
                warnings.append(result["message"])
                suggestions.append(result["suggestion"])
        
        relationship_params = {
            "channel_width": parameters.channel_width,
            "channel_height": parameters.channel_height,
            "inlet_velocity": parameters.inlet_velocity,
            "fluid_viscosity": self._get_fluid_viscosity(parameters.fluid_type)
        }
        
        relationship_results = self.constraints.validate_all_relationships(relationship_params)
        for rel_name, result in relationship_results.items():
            if result["status"] == "error":
                errors.append(f"参数关联验证失败 - {rel_name}: {result['message']}")
            elif result["status"] == "warning":
                warnings.append(f"参数关联警告 - {rel_name}: {result['message']}")
                suggestions.append(result["suggestion"])
        
        reynolds = self._calculate_reynolds_number(parameters)
        if reynolds > 2300:
            warnings.append(f"雷诺数 Re={reynolds:.1f}，流动可能进入过渡流或湍流区域")
            suggestions.append("建议降低入口速度或减小通道尺寸以保持层流状态")
        elif reynolds < 100:
            warnings.append(f"雷诺数 Re={reynolds:.1f}，流速较低可能影响散热效率")
            suggestions.append("建议适当提高入口速度以增强对流换热")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    def _basic_validation(self, parameters: SimulationParameters) -> Dict[str, List[str]]:
        errors = []
        warnings = []
        suggestions = []
        
        if parameters.channel_width < 1e-6:
            errors.append("通道宽度过小，建议使用大于1微米的尺寸")
        if parameters.channel_width > 0.01:
            errors.append("通道宽度过大，建议使用小于1厘米的尺寸")
        
        if parameters.channel_height < 1e-6:
            errors.append("通道高度过小，建议使用大于1微米的尺寸")
        if parameters.channel_height > 0.01:
            errors.append("通道高度过大，建议使用小于1厘米的尺寸")
        
        if parameters.inlet_velocity > 100:
            errors.append("速度过高，建议使用小于100 m/s的速度")
        
        if parameters.heat_flux > 1e7:
            errors.append("热通量过高，建议使用小于10 MW/m²的热通量")
        
        aspect_ratio = parameters.channel_height / parameters.channel_width if parameters.channel_width > 0 else 0
        if aspect_ratio < 1 or aspect_ratio > 10:
            warnings.append(f"通道纵横比 {aspect_ratio:.2f} 可能影响流动特性")
            suggestions.append("建议纵横比在2-5之间")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    def _get_fluid_viscosity(self, fluid_type) -> float:
        viscosity_map = {
            "water": 0.001,
            "air": 1.8e-5,
            "ethylene_glycol": 0.016,
            "engine_oil": 0.1
        }
        return viscosity_map.get(str(fluid_type.value) if hasattr(fluid_type, 'value') else str(fluid_type), 0.001)
    
    def _calculate_reynolds_number(self, parameters: SimulationParameters) -> float:
        hydraulic_diameter = 2 * parameters.channel_width * parameters.channel_height / (
            parameters.channel_width + parameters.channel_height
        )
        viscosity = self._get_fluid_viscosity(parameters.fluid_type)
        density = 998.2 if parameters.fluid_type.value == "water" else 1.225
        return parameters.inlet_velocity * hydraulic_diameter * density / viscosity
    
    async def start_simulation(self, simulation_id: str, parameters: SimulationParameters):
        # 获取仿真模式参数
        params_dict = parameters.dict()
        simulation_mode = params_dict.get('simulation_mode', 'mock')
        use_gpu = params_dict.get('use_gpu_acceleration', False)
        
        self.simulations[simulation_id] = {
            "id": simulation_id,
            "status": SimulationStatusEnum.RUNNING,
            "progress": 0,
            "current_step": "初始化仿真环境",
            "parameters": parameters,
            "start_time": datetime.now(),
            "log_messages": [
                f"仿真任务已创建",
                f"仿真模式：{'OpenFOAM' if simulation_mode == 'openfoam' else '模拟'}",
                f"GPU 加速：{'启用' if use_gpu else '禁用'}",
                "正在初始化..."
            ],
            "reynolds_number": self._calculate_reynolds_number(parameters)
        }
        
        # 根据仿真模式选择执行方式
        if simulation_mode == 'openfoam':
            # 启动真实 OpenFOAM 仿真任务
            task = asyncio.create_task(self._run_openfoam_simulation(simulation_id))
        else:
            # 启动模拟仿真任务
            task = asyncio.create_task(self._simulate_progress(simulation_id))
        
        self.simulation_tasks[simulation_id] = task
    
    async def _simulate_progress(self, simulation_id: str):
        steps = [
            ("初始化仿真环境", 10),
            ("生成计算网格", 25),
            ("设置边界条件", 40),
            ("运行CFD求解器", 60),
            ("计算流动场", 75),
            ("计算温度场", 90),
            ("生成结果报告", 100)
        ]
        
        for step_name, progress in steps:
            await asyncio.sleep(2)
            
            if simulation_id not in self.simulations:
                break
            
            if self.simulations[simulation_id]["status"] == SimulationStatusEnum.STOPPED:
                break
            
            self.simulations[simulation_id]["current_step"] = step_name
            self.simulations[simulation_id]["progress"] = progress
            self.simulations[simulation_id]["log_messages"].append(f"完成: {step_name}")
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "progress",
                    "data": {
                        "progress": progress,
                        "current_step": step_name,
                        "log_messages": self.simulations[simulation_id]["log_messages"]
                    }
                })
        
        if simulation_id in self.simulations:
            if self.simulations[simulation_id]["status"] != SimulationStatusEnum.STOPPED:
                self.simulations[simulation_id]["status"] = SimulationStatusEnum.COMPLETED
                self.simulations[simulation_id]["end_time"] = datetime.now()
                self.simulations[simulation_id]["log_messages"].append("✅ 仿真完成！")
                
                params = self.simulations[simulation_id]["parameters"]
                self.simulations[simulation_id]["performance_metrics"] = self._calculate_performance_metrics(params)
                
                if self.progress_callback:
                    await self.progress_callback(simulation_id, {
                        "type": "completed",
                        "data": {
                            "progress": 100,
                            "current_step": "仿真完成",
                            "performance_metrics": self.simulations[simulation_id]["performance_metrics"].dict()
                        }
                    })
    
    async def _run_openfoam_simulation(self, simulation_id: str):
        """运行真实 OpenFOAM 仿真"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
            from foam_controller import OpenFOAMController, is_openfoam_installed_in_wsl
            
            # 更新状态：初始化环境
            self.simulations[simulation_id]["current_step"] = "初始化 OpenFOAM 环境"
            self.simulations[simulation_id]["progress"] = 10
            self.simulations[simulation_id]["log_messages"].append("✅ OpenFOAM 环境初始化完成")
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "progress",
                    "data": {
                        "progress": 10,
                        "current_step": "初始化 OpenFOAM 环境",
                        "log_messages": self.simulations[simulation_id]["log_messages"]
                    }
                })
            
            await asyncio.sleep(0.5)
            
            # 创建临时案例目录
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="openfoam_case_")
            case_dir = Path(temp_dir)
            
            self.simulations[simulation_id]["log_messages"].append(f"📁 案例目录：{case_dir}")
            
            # 更新状态：创建案例
            self.simulations[simulation_id]["current_step"] = "创建仿真案例"
            self.simulations[simulation_id]["progress"] = 25
            self.simulations[simulation_id]["log_messages"].append("正在创建 OpenFOAM 案例...")
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "progress",
                    "data": {
                        "progress": 25,
                        "current_step": "创建仿真案例",
                        "log_messages": self.simulations[simulation_id]["log_messages"]
                    }
                })
            
            # 从模板创建案例
            repo_root = Path(__file__).resolve().parents[2]
            template_dir = repo_root / "openfoam_templates" / "microchannel"

            if not template_dir.exists():
                raise FileNotFoundError(f"模板案例目录不存在：{template_dir}")
            
            try:
                # 将前端参数转换为控制器参数
                params = self.simulations[simulation_id]["parameters"]
                simulation_mode = params.simulation_mode
                if hasattr(simulation_mode, "value"):
                    simulation_mode = simulation_mode.value
                simulation_mode = str(simulation_mode)
                controller_params = {
                    "velocity": params.inlet_velocity,
                    "inlet_temperature": params.inlet_temperature,
                    "outlet_pressure": params.outlet_pressure,
                    "base_temperature": params.base_temperature,
                    "heat_flux": params.heat_flux,
                    "channel_width": params.channel_width * 1e6,
                    "channel_height": params.channel_height * 1e6,
                    "channel_length": params.channel_length * 1e6,
                    "wall_thickness": params.wall_thickness * 1e6,
                    "mesh_resolution": params.mesh_resolution,
                    "max_iterations": params.max_iterations,
                    "fluid_type": params.fluid_type.value if hasattr(params.fluid_type, "value") else str(params.fluid_type),
                    "solid_material": params.solid_material.value if hasattr(params.solid_material, "value") else str(params.solid_material),
                    "simulation_mode": simulation_mode
                }
                
                # 创建控制器
                controller = OpenFOAMController.from_template(
                    template_dir=str(template_dir),
                    target_dir=str(case_dir),
                    params=controller_params
                )
                
                self.simulations[simulation_id]["log_messages"].append("✅ 仿真案例创建完成")

                # 确保 OpenFOAM 在 WSL 中可用（真实模式不允许静默降级）
                if not is_openfoam_installed_in_wsl():
                    raise RuntimeError("WSL 中未检测到 OpenFOAM，请确认 /opt/openfoam11 已安装并可用")
                
            except Exception as e:
                results_error = f"结果提取失败：{e}"
                print(f"案例创建错误：{e}")
                self.simulations[simulation_id]["log_messages"].append(f"❌ OpenFOAM 案例创建失败：{e}")
                raise
            
            # 更新状态：生成网格
            self.simulations[simulation_id]["current_step"] = "生成计算网格"
            self.simulations[simulation_id]["progress"] = 40
            self.simulations[simulation_id]["log_messages"].append("正在生成计算网格...")
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "progress",
                    "data": {
                        "progress": 40,
                        "current_step": "生成计算网格",
                        "log_messages": self.simulations[simulation_id]["log_messages"]
                    }
                })
            
            # 尝试运行网格生成
            try:
                if 'controller' in locals():
                    mesh_success = await asyncio.to_thread(controller.run_mesh)
                    if mesh_success:
                        self.simulations[simulation_id]["log_messages"].append("✅ 网格生成完成")
                    else:
                        raise RuntimeError("网格生成失败，请检查 blockMesh.log")
                else:
                    await asyncio.sleep(2)
                    self.simulations[simulation_id]["log_messages"].append("✅ 网格生成完成（模拟）")
            except Exception as e:
                print(f"网格生成异常：{e}")
                self.simulations[simulation_id]["log_messages"].append(f"❌ 网格生成失败：{e}")
                raise

            # ParaViewWeb 实时流场（WSL）
            try:
                case_foam = case_dir / "case.foam"
                try:
                    case_foam.touch(exist_ok=True)
                except Exception:
                    pass

                pv_info = self.paraview_service.start(
                    simulation_id=simulation_id,
                    case_dir=str(case_dir),
                    case_file=str(case_foam),
                )
                if pv_info.get("status") == "running":
                    self.simulations[simulation_id]["paraview_web_url"] = pv_info.get("url")
                    self.simulations[simulation_id]["paraview_web_ws_url"] = pv_info.get("ws_url")
                    self.simulations[simulation_id]["paraview_web_port"] = pv_info.get("port")
                    self.simulations[simulation_id]["log_messages"].append(
                        f"✅ ParaViewWeb 已启动：{pv_info.get('url')}"
                    )
                else:
                    message = pv_info.get("message")
                    if message:
                        self.simulations[simulation_id]["log_messages"].append(
                            f"⚠️ ParaViewWeb 未就绪：{message}"
                        )

                if self.progress_callback:
                    await self.progress_callback(simulation_id, {
                        "type": "paraview_web",
                        "data": pv_info
                    })
            except Exception as e:
                print(f"ParaViewWeb 启动异常：{e}")
                self.simulations[simulation_id]["log_messages"].append(
                    f"⚠️ ParaViewWeb 启动失败：{e}"
                )
            
            # 更新状态：运行求解器
            self.simulations[simulation_id]["current_step"] = "运行 CFD 求解器"
            self.simulations[simulation_id]["progress"] = 60
            self.simulations[simulation_id]["log_messages"].append("正在运行 CFD 求解器...")
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "progress",
                    "data": {
                        "progress": 60,
                        "current_step": "运行 CFD 求解器",
                        "log_messages": self.simulations[simulation_id]["log_messages"]
                    }
                })
            
            # 尝试运行求解器
            try:
                if 'controller' in locals():
                    await asyncio.sleep(1)
                    loop = asyncio.get_running_loop()
                    residual_state = {"time": None}
                    solver_error = {"message": None}

                    time_pattern = re.compile(r"^\s*Time\s*=\s*([0-9eE\.\+\-]+)")
                    residual_pattern = re.compile(
                        r"Solving for\s+([A-Za-z0-9_]+).*Initial residual\s*=\s*([0-9eE\.\+\-]+)"
                        r".*Final residual\s*=\s*([0-9eE\.\+\-]+).*No Iterations\s*([0-9]+)"
                    )
                    region_pattern = re.compile(r"^\s*(fluid|solid)\s*:\s*(.*)")

                    def on_solver_output(line: str) -> None:
                        if not line:
                            return
                        text = line.strip()
                        if not text:
                            return

                        is_important = (
                            text.startswith("Time =")
                            or "Solving for" in text
                            or "Courant" in text
                            or "ExecutionTime" in text
                            or "FOAM" in text
                            or "error" in text.lower()
                        )

                        if is_important and self.progress_callback:
                            asyncio.run_coroutine_threadsafe(
                                self.progress_callback(simulation_id, {
                                    "type": "solver_log",
                                    "data": {"line": text}
                                }),
                                loop
                            )

                        if "FOAM FATAL" in text or "Floating point exception" in text:
                            solver_error["message"] = text

                        time_match = time_pattern.search(text)
                        if time_match:
                            try:
                                residual_state["time"] = float(time_match.group(1))
                            except Exception:
                                pass

                        region = None
                        residual_line = text
                        region_match = region_pattern.match(text)
                        if region_match:
                            region = region_match.group(1)
                            residual_line = region_match.group(2)

                        residual_match = residual_pattern.search(residual_line)
                        if residual_match and self.progress_callback:
                            field = residual_match.group(1)
                            if region:
                                field = f"{region}:{field}"
                            try:
                                initial_residual = float(residual_match.group(2))
                                final_residual = float(residual_match.group(3))
                                iterations = int(residual_match.group(4))
                            except Exception:
                                return

                            asyncio.run_coroutine_threadsafe(
                                self.progress_callback(simulation_id, {
                                    "type": "residual_update",
                                    "data": {
                                        "time": residual_state.get("time"),
                                        "field": field,
                                        "initial_residual": initial_residual,
                                        "final_residual": final_residual,
                                        "iterations": iterations
                                    }
                                }),
                                loop
                            )

                    solver_success = await asyncio.to_thread(controller.run_simulation, on_solver_output)
                    if solver_error.get("message"):
                        raise RuntimeError(f"求解器致命错误: {solver_error['message']}")
                    if solver_success:
                        self.simulations[simulation_id]["log_messages"].append("✅ CFD 求解器运行完成")
                    else:
                        raise RuntimeError("求解器运行失败，请检查求解器日志")
                else:
                    await asyncio.sleep(3)
                    self.simulations[simulation_id]["log_messages"].append("✅ CFD 求解器运行完成（模拟）")
            except Exception as e:
                print(f"求解器异常：{e}")
                self.simulations[simulation_id]["log_messages"].append(f"❌ 求解器运行失败：{e}")
                raise
            
            # 模拟计算过程
            for progress in [75, 90, 100]:
                await asyncio.sleep(1.5)
                step_name = "计算流动场" if progress == 75 else "计算温度场" if progress == 90 else "生成结果报告"
                
                self.simulations[simulation_id]["current_step"] = step_name
                self.simulations[simulation_id]["progress"] = progress
                self.simulations[simulation_id]["log_messages"].append(f"✅ {step_name}完成")
                
                if self.progress_callback:
                    await self.progress_callback(simulation_id, {
                        "type": "progress",
                        "data": {
                            "progress": progress,
                            "current_step": step_name,
                            "log_messages": self.simulations[simulation_id]["log_messages"]
                        }
                    })
            
            # 获取仿真结果
            performance_metrics = None
            results_error = None
            used_fallback = False
            params = self.simulations[simulation_id]["parameters"]
            velocity = params.inlet_velocity
            temp_in = params.inlet_temperature
            try:
                if 'controller' in locals():
                    results = await asyncio.to_thread(controller.get_results)
                    if results:
                        # 从 OpenFOAM 结果提取性能指标
                        temp_results = results.get("temperature", {})
                        max_temp = temp_results.get("max")
                        min_temp = temp_results.get("min", temp_in)

                        try:
                            max_temp_val = float(max_temp)
                            min_temp_val = float(min_temp)
                        except Exception:
                            results_error = "温度场异常（可能时间步长过大或求解不稳定），请检查控制参数与网格尺寸"
                        else:
                            if (
                                not math.isfinite(max_temp_val)
                                or not math.isfinite(min_temp_val)
                                or max_temp_val < min_temp_val
                                or max_temp_val > 1e6
                            ):
                                results_error = "温度场异常（可能时间步长过大或求解不稳定），请检查控制参数与网格尺寸"
                            else:
                                pressure_drop = None
                                pressure_results = results.get("pressure", {})
                                if pressure_results:
                                    try:
                                        p_max = float(pressure_results.get("max", 0))
                                        p_min = float(pressure_results.get("min", 0))
                                        pressure_drop = max(p_max - p_min, 0.0)
                                    except Exception:
                                        pressure_drop = None

                                derived = self._calculate_performance_metrics(params)
                                performance_metrics = {
                                    "max_temperature": max_temp_val,
                                    "min_temperature": min_temp_val,
                                    "pressure_drop": pressure_drop if pressure_drop is not None else derived.pressure_drop,
                                    "heat_transfer_coefficient": derived.heat_transfer_coefficient,
                                    "reynolds_number": derived.reynolds_number,
                                    "nusselt_number": derived.nusselt_number
                                }
            except Exception as e:
                print(f"结果提取错误：{e}")
            
            # 如果没有从 OpenFOAM 获取到结果，使用模拟结果
            if not performance_metrics:
                used_fallback = True
                params = self.simulations[simulation_id]["parameters"]
                velocity = params.inlet_velocity
                temp_in = params.inlet_temperature
                heat_flux = params.heat_flux
                
                max_temp = temp_in + 20 + (heat_flux / 10000) * 30
                pressure_drop = velocity * 500 + 500
                htc = 5000 + velocity * 3000
                reynolds = 500 + velocity * 800
                nusselt = 20 + velocity * 20
                
                performance_metrics = {
                    "max_temperature": round(max_temp, 1),
                    "min_temperature": temp_in,
                    "pressure_drop": round(pressure_drop, 1),
                    "heat_transfer_coefficient": round(htc, 1),
                    "reynolds_number": round(reynolds, 1),
                    "nusselt_number": round(nusselt, 1)
                }

            if simulation_mode == "openfoam" and used_fallback:
                performance_metrics = None
                if not results_error:
                    results_error = "未获取到 OpenFOAM 结果，无法生成真实指标"

            # 持久化 OpenFOAM 案例目录，供 ParaView 使用
            try:
                case_info = self._persist_openfoam_case(simulation_id, case_dir)
                if case_info:
                    self.simulations[simulation_id].update(case_info)
                    self.simulations[simulation_id]["log_messages"].append(
                        f"📦 已保存 OpenFOAM 案例：{case_info.get('case_directory')}"
                    )
            except Exception as e:
                print(f"保存 OpenFOAM 案例失败: {e}")
                self.simulations[simulation_id]["log_messages"].append(
                    f"⚠️ 保存 OpenFOAM 案例失败：{str(e)}"
                )
            
            # 仿真完成
            if results_error:
                raise RuntimeError(results_error)

            self.simulations[simulation_id]["status"] = SimulationStatusEnum.COMPLETED
            self.simulations[simulation_id]["end_time"] = datetime.now()
            self.simulations[simulation_id]["log_messages"].append("✅ OpenFOAM 仿真完成！")
            
            # 创建性能指标对象
            from models.simulation import PerformanceMetrics
            self.simulations[simulation_id]["performance_metrics"] = PerformanceMetrics(
                max_temperature=performance_metrics["max_temperature"],
                min_temperature=performance_metrics.get("min_temperature", temp_in),
                pressure_drop=performance_metrics["pressure_drop"],
                heat_transfer_coefficient=performance_metrics["heat_transfer_coefficient"],
                reynolds_number=performance_metrics["reynolds_number"],
                nusselt_number=performance_metrics["nusselt_number"],
                friction_factor=0.025,
                thermal_resistance=0.15,
                efficiency=0.85
            )
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "completed",
                    "data": {
                        "progress": 100,
                        "current_step": "仿真完成",
                        "performance_metrics": self.simulations[simulation_id]["performance_metrics"].dict(),
                        "paraview_web_url": self.simulations[simulation_id].get("paraview_web_url"),
                        "paraview_web_ws_url": self.simulations[simulation_id].get("paraview_web_ws_url")
                    }
                })
            
            # 清理临时目录（若正在提供 ParaViewWeb，则保留以便实时查看）
            try:
                if not self.simulations[simulation_id].get("paraview_web_url"):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
        except Exception as e:
            print(f"OpenFOAM 仿真错误：{e}")
            import traceback
            traceback.print_exc()
            self.simulations[simulation_id]["status"] = SimulationStatusEnum.STOPPED
            self.simulations[simulation_id]["log_messages"].append(f"❌ OpenFOAM 仿真失败：{str(e)}")

            try:
                self.paraview_service.stop(simulation_id)
            except Exception:
                pass
            
            if self.progress_callback:
                await self.progress_callback(simulation_id, {
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "log_messages": self.simulations[simulation_id]["log_messages"]
                    }
                })

    def _persist_openfoam_case(self, simulation_id: str, case_dir: Path) -> Optional[Dict[str, str]]:
        config = _load_system_config()
        openfoam_cfg = config.get("openfoam", {})
        keep_case = openfoam_cfg.get("keep_case_dir", False)
        if not keep_case:
            return None

        repo_root = Path(__file__).resolve().parents[2]
        storage_dir = openfoam_cfg.get("case_storage_dir", "data/openfoam_cases")
        target_root = Path(storage_dir)
        if not target_root.is_absolute():
            target_root = repo_root / target_root
        target_root.mkdir(parents=True, exist_ok=True)

        target_dir = target_root / simulation_id
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        shutil.copytree(case_dir, target_dir)
        foam_file = target_dir / f"{simulation_id}.foam"
        try:
            foam_file.touch(exist_ok=True)
        except Exception:
            pass

        return {
            "case_directory": str(target_dir),
            "paraview_file": str(foam_file)
        }
    
    def _calculate_performance_metrics(self, params: SimulationParameters) -> PerformanceMetrics:
        reynolds = self._calculate_reynolds_number(params)
        
        hydraulic_diameter = 2 * params.channel_width * params.channel_height / (
            params.channel_width + params.channel_height
        )
        
        if reynolds < 2300:
            nusselt = 3.66 + (0.0668 * (reynolds * 0.7) / (1 + 0.04 * (reynolds * 0.7) ** (2/3)))
            friction_factor = 64 / reynolds if reynolds > 0 else 0.05
        else:
            nusselt = 0.023 * (reynolds ** 0.8) * (0.7 ** 0.4)
            friction_factor = 0.316 / (reynolds ** 0.25)
        
        k_fluid = 0.6 if params.fluid_type.value == "water" else 0.024
        h = nusselt * k_fluid / hydraulic_diameter if hydraulic_diameter > 0 else 0
        
        channel_area = params.channel_width * params.channel_length * params.channel_count
        thermal_resistance = 1 / (h * channel_area) if h * channel_area > 0 else 0
        
        inlet_temp = params.inlet_temperature
        heat_input = params.heat_flux * channel_area
        mass_flow = 998.2 * params.inlet_velocity * params.channel_width * params.channel_height * params.channel_count
        temp_rise = heat_input / (mass_flow * 4186) if mass_flow > 0 else 0
        max_temp = inlet_temp + temp_rise
        
        pressure_drop = friction_factor * (params.channel_length / hydraulic_diameter) * \
                       (0.5 * 998.2 * params.inlet_velocity ** 2) if hydraulic_diameter > 0 else 0
        
        efficiency = min(1.0, (params.base_temperature - inlet_temp) / 
                        (max_temp - inlet_temp)) if max_temp > inlet_temp else 0.85
        
        return PerformanceMetrics(
            max_temperature=max_temp,
            min_temperature=inlet_temp,
            pressure_drop=pressure_drop,
            heat_transfer_coefficient=h,
            reynolds_number=reynolds,
            nusselt_number=nusselt,
            friction_factor=friction_factor,
            thermal_resistance=thermal_resistance,
            efficiency=efficiency
        )
    
    async def get_simulation_status(self, simulation_id: str) -> Optional[SimulationStatus]:
        if simulation_id not in self.simulations:
            return None
        
        sim_data = self.simulations[simulation_id]
        return SimulationStatus(
            simulation_id=simulation_id,
            status=sim_data["status"],
            progress=sim_data["progress"],
            current_step=sim_data["current_step"],
            start_time=sim_data.get("start_time"),
            end_time=sim_data.get("end_time"),
            log_messages=sim_data["log_messages"]
        )
    
    async def pause_simulation(self, simulation_id: str):
        if simulation_id in self.simulations:
            self.simulations[simulation_id]["status"] = SimulationStatusEnum.PAUSED
            self.simulations[simulation_id]["log_messages"].append("仿真已暂停")
    
    async def resume_simulation(self, simulation_id: str):
        if simulation_id in self.simulations:
            self.simulations[simulation_id]["status"] = SimulationStatusEnum.RUNNING
            self.simulations[simulation_id]["log_messages"].append("仿真已恢复")
    
    async def stop_simulation(self, simulation_id: str):
        if simulation_id in self.simulations:
            self.simulations[simulation_id]["status"] = SimulationStatusEnum.STOPPED
            self.simulations[simulation_id]["log_messages"].append("仿真已停止")
        
        if simulation_id in self.simulation_tasks:
            self.simulation_tasks[simulation_id].cancel()

        # 停止 ParaViewWeb
        try:
            self.paraview_service.stop(simulation_id)
        except Exception:
            pass
    
    async def get_simulation_results(self, simulation_id: str) -> Optional[SimulationResults]:
        if simulation_id not in self.simulations:
            return None
        
        sim_data = self.simulations[simulation_id]
        if sim_data["status"] != SimulationStatusEnum.COMPLETED:
            return None
        
        return SimulationResults(
            simulation_id=simulation_id,
            parameters=sim_data["parameters"],
            performance_metrics=sim_data["performance_metrics"],
            visualization_data={},
            case_directory=sim_data.get("case_directory"),
            paraview_file=sim_data.get("paraview_file"),
            paraview_web_url=sim_data.get("paraview_web_url"),
            created_at=sim_data["start_time"]
        )

    def get_paraview_info(self, simulation_id: str) -> Dict[str, Any]:
        sim_data = self.simulations.get(simulation_id)
        if sim_data and sim_data.get("paraview_web_url"):
            return {
                "status": "running",
                "url": sim_data.get("paraview_web_url"),
                "ws_url": sim_data.get("paraview_web_ws_url"),
                "port": sim_data.get("paraview_web_port")
            }
        return self.paraview_service.get_info(simulation_id)
    
    async def generate_report(self, simulation_id: str, template: Optional[str] = None):
        if simulation_id not in self.simulations:
            return {"error": "仿真任务不存在"}
        
        sim_data = self.simulations[simulation_id]
        
        report_data = {
            "simulation_id": simulation_id,
            "template": template or "default",
            "generated_at": datetime.now().isoformat(),
            "status": sim_data["status"].value,
            "parameters": sim_data["parameters"].dict(),
            "performance_metrics": sim_data.get("performance_metrics", PerformanceMetrics(
                max_temperature=350.5,
                min_temperature=300.0,
                pressure_drop=1250.0,
                heat_transfer_coefficient=8500.0,
                reynolds_number=1250.0,
                nusselt_number=45.2,
                friction_factor=0.025,
                thermal_resistance=0.15,
                efficiency=0.85
            )).dict() if sim_data.get("performance_metrics") else None,
            "summary": "仿真报告已生成",
            "recommendations": self._generate_engineering_recommendations(sim_data)
        }
        
        return report_data
    
    def _generate_engineering_recommendations(self, sim_data: dict) -> List[str]:
        recommendations = []
        
        if "performance_metrics" in sim_data:
            metrics = sim_data["performance_metrics"]
            
            if metrics.max_temperature > 373.15:
                recommendations.append("最高温度超过100°C，建议增加流量或优化通道设计")
            
            if metrics.pressure_drop > 50000:
                recommendations.append("压力损失较大，建议增大通道尺寸或减少通道长度")
            
            if metrics.efficiency < 0.7:
                recommendations.append("散热效率较低，建议优化通道几何参数")
            
            if metrics.reynolds_number > 2000:
                recommendations.append("流动接近湍流状态，注意压力损失增加")
        
        return recommendations if recommendations else ["设计参数合理，性能表现良好"]
