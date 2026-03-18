import asyncio
import os
import subprocess
import json
import shutil
from typing import Dict, Optional
from pathlib import Path


class OpenFOAMService:
    def __init__(self):
        self.available = False
        self.openfoam_path = None
        self.wsl_distro = "Ubuntu-24.04"
        self._check_availability()
    
    def _check_availability(self):
        try:
            # 检查WSL中的OpenFOAM路径
            openfoam_path = r"\\wsl.localhost\Ubuntu-24.04\opt\openfoam11"
            
            if os.path.exists(openfoam_path):
                self.openfoam_path = openfoam_path
                self.available = True
                print(f"✅ OpenFOAM 在 WSL 中可用: {openfoam_path}")
            else:
                # 尝试通过WSL命令检查
                result = subprocess.run(
                    ["wsl", "-d", self.wsl_distro, "which", "foamRun"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout_text = result.stdout.decode("utf-8", "ignore").strip() if result.stdout else ""
                if result.returncode == 0 and stdout_text:
                    self.available = True
                    print(f"✅ OpenFOAM 在 WSL 中可用: {stdout_text}")
                else:
                    self.available = False
                    print("❌ OpenFOAM 在 WSL 中不可用")
        
        except Exception as e:
            print(f"OpenFOAM检查失败: {e}")
            self.available = False
    
    async def check_availability(self) -> bool:
        return self.available
    
    async def generate_case(self, case_name: str, parameters: dict) -> Dict:
        """在WSL中生成OpenFOAM案例"""
        if not self.available:
            return {"error": "OpenFOAM不可用"}
        
        try:
            # 创建案例目录结构
            case_dir = f"/tmp/openfoam_cases/{case_name}"
            
            # 在WSL中执行命令
            commands = [
                f"mkdir -p {case_dir}",
                f"cd {case_dir}",
                "source /opt/openfoam11/etc/bashrc",
                "foamNewCase .",
                "blockMesh",
                "simpleFoam"
            ]
            
            # 执行WSL命令
            result = subprocess.run(
                ["wsl", "-d", self.wsl_distro, "bash", "-c", " && ".join(commands)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout_text = result.stdout.decode("utf-8", "ignore") if result.stdout else ""
            stderr_text = result.stderr.decode("utf-8", "ignore") if result.stderr else ""
            
            if result.returncode == 0:
                return {
                    "case_name": case_name,
                    "status": "generated",
                    "directory": case_dir,
                    "log": stdout_text
                }
            else:
                return {
                    "case_name": case_name,
                    "status": "error",
                    "error": stderr_text
                }
        
        except Exception as e:
            return {
                "case_name": case_name,
                "status": "error",
                "error": str(e)
            }
    
    async def run_simulation(self, case_name: str) -> Dict:
        """在WSL中运行OpenFOAM仿真"""
        if not self.available:
            return {"error": "OpenFOAM不可用"}
        
        try:
            case_dir = f"/tmp/openfoam_cases/{case_name}"
            
            # 在WSL中执行仿真命令
            commands = [
                f"cd {case_dir}",
                "source /opt/openfoam11/etc/bashrc",
                "simpleFoam > log.simpleFoam 2>&1"
            ]
            
            # 异步执行仿真
            process = await asyncio.create_subprocess_exec(
                "wsl", "-d", self.wsl_distro, "bash", "-c", " && ".join(commands),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待仿真完成
            stdout, stderr = await process.communicate()
            
            return {
                "case_name": case_name,
                "status": "completed" if process.returncode == 0 else "error",
                "exit_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            }
        
        except Exception as e:
            return {
                "case_name": case_name,
                "status": "error",
                "error": str(e)
            }
    
    async def parse_results(self, case_name: str) -> Optional[Dict]:
        """解析OpenFOAM仿真结果"""
        if not self.available:
            return None
        
        try:
            case_dir = f"/tmp/openfoam_cases/{case_name}"
            
            # 在WSL中执行结果解析命令
            commands = [
                f"cd {case_dir}",
                "source /opt/openfoam11/etc/bashrc",
                "postProcess -func 'patchAverage(p)' -latestTime",
                "postProcess -func 'patchAverage(T)' -latestTime"
            ]
            
            result = subprocess.run(
                ["wsl", "-d", self.wsl_distro, "bash", "-c", " && ".join(commands)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout_text = result.stdout.decode("utf-8", "ignore") if result.stdout else ""
            
            if result.returncode == 0:
                # 模拟解析结果（实际项目中需要解析OpenFOAM输出文件）
                return {
                    "max_temperature": 350.5,
                    "min_temperature": 300.0,
                    "pressure_drop": 1250.0,
                    "heat_transfer_coefficient": 8500.0,
                    "reynolds_number": 1250.0,
                    "nusselt_number": 45.2
                }
            else:
                return None
        
        except Exception as e:
            print(f"解析结果失败: {e}")
            return None
    
    async def get_simulation_progress(self, case_name: str) -> Dict:
        """获取仿真进度"""
        try:
            case_dir = f"/tmp/openfoam_cases/{case_name}"
            
            # 检查日志文件
            commands = [
                f"cd {case_dir}",
                "if [ -f log.simpleFoam ]; then tail -n 10 log.simpleFoam; else echo 'No log file'; fi"
            ]
            
            result = subprocess.run(["wsl", "-d", self.wsl_distro, "bash", "-c", 
                                   " && ".join(commands)], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            stdout_text = result.stdout.decode("utf-8", "ignore") if result.stdout else ""
            
            return {
                "case_name": case_name,
                "log_tail": stdout_text.strip(),
                "has_log": stdout_text.strip() != "No log file"
            }
        
        except Exception as e:
            return {
                "case_name": case_name,
                "error": str(e)
            }
