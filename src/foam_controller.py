# -*- coding: utf-8 -*-
"""
OpenFOAM仿真控制器 - 使用开源foamlib库
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

FOAMLIB_AVAILABLE = False

try:
    from foamlib import foam

    FOAMLIB_AVAILABLE = True
except ImportError:
    pass


def load_openfoam_config() -> Dict[str, Any]:
    """加载OpenFOAM配置"""
    config_path = Path("config/system_config.json")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("openfoam", {})
    return {}


OPENFOAM_CONFIG = load_openfoam_config()
USE_WSL = OPENFOAM_CONFIG.get("use_wsl", True)
WSL_DISTRO = OPENFOAM_CONFIG.get("wsl_distro", "Ubuntu-24.04")
OPENFOAM_PATH = OPENFOAM_CONFIG.get("openfoam_path", "/opt/openfoam11")
TEMPLATE_CASE = OPENFOAM_CONFIG.get(
    "template_case", "/opt/openfoam11/tutorials/incompressibleFluid/cavity"
)


def get_wsl_command(command: str, case_dir: str) -> str:
    """获取在WSL中运行的命令"""
    wsl_case_path = case_dir.replace("\\", "/")
    if len(wsl_case_path) >= 2 and wsl_case_path[1] == ":":
        wsl_case_path = f"/mnt/{wsl_case_path[0].lower()}" + wsl_case_path[2:]

    return f"wsl -d {WSL_DISTRO} -e {command}"


@dataclass
class SimulationConfig:
    """仿真配置"""

    case_dir: str
    solver: str = "simpleFoam"
    mesh_method: str = "blockMesh"
    start_time: float = 0
    end_time: float = 1000
    write_interval: float = 100


class OpenFOAMController:
    """OpenFOAM仿真控制器"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.case_dir = Path(config.case_dir)
        self._foam_case = None

        if FOAMLIB_AVAILABLE:
            try:
                self._foam_case = foam.FoamCase(self.case_dir)
            except Exception as e:
                print(f"警告: 无法加载foam case: {e}")

    @staticmethod
    def _to_wsl_path(windows_path: str) -> str:
        """将Windows路径转换为WSL路径"""
        path = windows_path.replace("\\", "/")
        if len(path) >= 2 and path[1] == ":":
            return f"/mnt/{path[0].lower()}" + path[2:]
        return path

    @staticmethod
    def from_template(
        template_dir: str, target_dir: str, params: Dict[str, Any]
    ) -> "OpenFOAMController":
        """从模板创建案例"""
        import shutil
        import subprocess

        target_path = Path(target_dir)

        if target_path.exists():
            shutil.rmtree(target_path)

        if USE_WSL:
            wsl_target = OpenFOAMController._to_wsl_path(str(target_path))
            wsl_template = OpenFOAMController._to_wsl_path(
                str(Path(template_dir).resolve())
            )
            cmd = f'wsl -d {WSL_DISTRO} -e bash -c "mkdir -p {wsl_target} && cp -r {wsl_template}/* {wsl_target}/"'
            subprocess.run(cmd, shell=True, capture_output=True)
        else:
            shutil.copytree(template_dir, target_dir)

        config = SimulationConfig(case_dir=target_dir)
        controller = OpenFOAMController(config)

        controller.update_parameters(params)

        return controller

    def update_parameters(self, params: Dict[str, Any]) -> None:
        """更新案例参数"""
        self._update_boundary_conditions(params)
        self._update_mesh_params(params)
        self._update_solver_params(params)

    def _update_boundary_conditions(self, params: Dict[str, Any]) -> None:
        """更新边界条件"""
        velocity = params.get("velocity", 2.0)
        inlet_temp = params.get("inlet_temperature", 30.0)
        wall_temp = params.get("wall_temperature", 80.0)

        u_file = self.case_dir / "0" / "U"
        if u_file.exists():
            content = u_file.read_text(encoding="utf-8")
            content = content.replace("uniform (10 0 0)", f"uniform ({velocity} 0 0)")
            content = content.replace("uniform (1 0 0)", f"uniform ({velocity} 0 0)")
            u_file.write_text(content, encoding="utf-8")

        t_file = self.case_dir / "0" / "T"
        if t_file.exists():
            content = t_file.read_text(encoding="utf-8")
            internal_temp = inlet_temp + 273.15
            content = content.replace("uniform 300", f"uniform {internal_temp}")
            wall_temp_k = wall_temp + 273.15
            content = content.replace("uniform 350", f"uniform {wall_temp_k}")
            t_file.write_text(content, encoding="utf-8")

    def _update_mesh_params(self, params: Dict[str, Any]) -> None:
        """更新网格参数"""
        block_mesh_dict = self.case_dir / "system" / "blockMeshDict"

        if block_mesh_dict.exists():
            content = block_mesh_dict.read_text(encoding="utf-8")

            channel_width = params.get("channel_width", 50)
            channel_height = params.get("channel_height", 2)

            content = content.replace("50 0 0", f"{channel_width} 0 0")
            content = content.replace("50 2 0", f"{channel_width} {channel_height} 0")
            content = content.replace(
                "(50 2 1)", f"({channel_width} {channel_height} 1)"
            )

            block_mesh_dict.write_text(content, encoding="utf-8")

    def _update_solver_params(self, params: Dict[str, Any]) -> None:
        """更新求解器参数"""
        pass

    def _get_openfoam_command(self, command: str) -> str:
        """获取OpenFOAM命令（通过WSL运行）"""
        if USE_WSL:
            wsl_case = self._to_wsl_path(str(self.case_dir))
            source_cmd = (
                f"cd {wsl_case} && source {OPENFOAM_PATH}/etc/bashrc && {command}"
            )
            return f'wsl -d {WSL_DISTRO} -e bash -c "{source_cmd}"'
        return command

    def run_mesh(self) -> bool:
        """运行网格生成"""
        cmd = self._get_openfoam_command("blockMesh")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                shell=True,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode != 0:
                print(
                    f"网格生成错误: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                )
            return result.returncode == 0
        except FileNotFoundError:
            print("错误: WSL未找到或OpenFOAM未安装")
            return False
        except Exception as e:
            print(f"网格生成异常: {e}")
            return False

    def run_simulation(self) -> bool:
        """运行流体求解"""
        cmd = self._get_openfoam_command(self.config.solver)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                shell=True,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode != 0:
                print(
                    f"流体求解错误: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                )
            return result.returncode == 0
        except Exception as e:
            print(f"流体求解异常: {e}")
            return False

    def run_temperature_solve(self) -> bool:
        """运行温度场求解"""
        # 检查是否配置了温度场求解器
        control_dict = self.case_dir / "system" / "controlDict"
        if control_dict.exists():
            content = control_dict.read_text(encoding="utf-8")
            if "buoyantFoam" in content:
                # 使用buoyantFoam求解器
                cmd = self._get_openfoam_command("buoyantFoam")
            elif "chtMultiRegionFoam" in content:
                # 使用chtMultiRegionFoam求解器
                cmd = self._get_openfoam_command("chtMultiRegionFoam")
            elif "rhoSimpleFoam" in content:
                # 使用rhoSimpleFoam求解器
                cmd = self._get_openfoam_command("rhoSimpleFoam")
            else:
                # 默认使用buoyantFoam
                cmd = self._get_openfoam_command("buoyantFoam")
        else:
            cmd = self._get_openfoam_command("buoyantFoam")
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                shell=True,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode != 0:
                print(
                    f"温度求解错误: {result.stderr[:500] if result.stderr else 'Unknown error'}"
                )
            return result.returncode == 0
        except Exception as e:
            print(f"温度求解异常: {e}")
            return False

    def run(self) -> bool:
        """运行完整仿真流程"""
        print(f"开始仿真案例: {self.case_dir}")

        print("步骤1: 生成网格...")
        if not self.run_mesh():
            print("网格生成失败")
            return False

        # 检查是否配置了温度场求解器
        control_dict = self.case_dir / "system" / "controlDict"
        if control_dict.exists():
            content = control_dict.read_text(encoding="utf-8")
            if "buoyantFoam" in content or "chtMultiRegionFoam" in content or "rhoSimpleFoam" in content:
                print("步骤2: 运行温度场耦合求解...")
                if not self.run_temperature_solve():
                    print("温度场耦合求解失败")
                    return False
            else:
                print("步骤2: 运行流体求解...")
                if not self.run_simulation():
                    print("流体求解失败")
                    return False
        else:
            print("步骤2: 运行流体求解...")
            if not self.run_simulation():
                print("流体求解失败")
                return False

        print("仿真完成!")
        return True

    def get_results(self) -> Dict[str, Any]:
        """获取仿真结果"""
        results = {}

        last_time = self._get_last_time_directory()
        if not last_time:
            return results

        if USE_WSL:
            wsl_case = self._to_wsl_path(str(self.case_dir))
            results = self._get_results_from_wsl(wsl_case, last_time)
        else:
            time_dir = self.case_dir / last_time
            t_file = time_dir / "T"
            if t_file.exists():
                try:
                    results["temperature"] = self._parse_scalar_field(t_file)
                except Exception as e:
                    print(f"读取温度结果失败: {e}")

            p_file = time_dir / "p"
            if p_file.exists():
                try:
                    results["pressure"] = self._parse_scalar_field(p_file)
                except Exception as e:
                    print(f"读取压力结果失败: {e}")

            u_file = time_dir / "U"
            if u_file.exists():
                try:
                    results["velocity"] = self._parse_vector_field(u_file)
                except Exception as e:
                    print(f"读取速度结果失败: {e}")

        return results

    def _get_results_from_wsl(self, wsl_case: str, time_dir: str) -> Dict[str, Any]:
        """从WSL获取结果"""
        import subprocess

        results = {}

        for field, filename in [
            ("velocity", "U"),
            ("pressure", "p"),
            ("temperature", "T"),
        ]:
            cmd = (
                f'wsl -d {WSL_DISTRO} -e bash -c "cat {wsl_case}/{time_dir}/{filename}"'
            )
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=30,
                )
                if result.returncode == 0:
                    if field == "velocity":
                        results[field] = self._parse_vector_field_text(result.stdout)
                    else:
                        results[field] = self._parse_scalar_field_text(result.stdout)
            except Exception as e:
                print(f"读取{field}失败: {e}")

        return results

    def _parse_scalar_field_text(self, content: str) -> Dict[str, float]:
        """解析标量场文本"""
        values = []
        in_internal = False

        for line in content.split("\n"):
            line = line.strip()
            if "internalField" in line:
                if "uniform" in line:
                    try:
                        val = float(line.split("uniform")[1].strip().rstrip(";"))
                        return {"min": val, "max": val, "average": val}
                    except:
                        pass
                in_internal = True
                continue

            if in_internal and line == ")":
                break

            if in_internal and line and line[0].isdigit():
                try:
                    values.append(float(line.split()[0]))
                except:
                    pass

        if values:
            return {
                "min": min(values),
                "max": max(values),
                "average": sum(values) / len(values),
            }

        return {"min": 0, "max": 0, "average": 0}

    def _parse_vector_field_text(self, content: str) -> Dict[str, float]:
        """解析向量场文本"""
        max_mag = 0.0

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("(") and line.endswith(")"):
                parts = line[1:-1].split()
                if len(parts) >= 3:
                    try:
                        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                        mag = (x**2 + y**2 + z**2) ** 0.5
                        max_mag = max(max_mag, mag)
                    except:
                        pass

        return {"max": max_mag}

    def _parse_scalar_field(self, filepath: Path) -> Dict[str, float]:
        """解析标量场"""
        content = filepath.read_text(encoding="utf-8")

        values = []
        in_internal_field = False

        for line in content.split("\n"):
            line = line.strip()
            if "internalField" in line:
                if "uniform" in line:
                    try:
                        val = float(line.split("uniform")[1].strip().rstrip(";"))
                        return {"min": val, "max": val, "average": val}
                    except:
                        pass
                in_internal_field = True
                continue

            if in_internal_field and line == ")":
                break

            if in_internal_field and line and line[0].isdigit():
                try:
                    values.append(float(line.split()[0]))
                except:
                    pass

        if values:
            return {
                "min": min(values),
                "max": max(values),
                "average": sum(values) / len(values),
            }

        return {"min": 0, "max": 0, "average": 0}

    def _parse_vector_field(self, filepath: Path) -> Dict[str, float]:
        """解析向量场"""
        content = filepath.read_text(encoding="utf-8")

        max_mag = 0.0

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("(") and line.endswith(")"):
                parts = line[1:-1].split()
                if len(parts) >= 3:
                    try:
                        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                        mag = (x**2 + y**2 + z**2) ** 0.5
                        max_mag = max(max_mag, mag)
                    except:
                        pass

        return {"max": max_mag}

    def _get_last_time_directory(self) -> Optional[str]:
        """获取最后一个时间目录"""
        if USE_WSL:
            wsl_case = self._to_wsl_path(str(self.case_dir))
            import subprocess

            cmd = f"wsl -d {WSL_DISTRO} -e bash -c \"ls {wsl_case}/ | grep -E '^[0-9]+\\.?[0-9]*$' | sort -n | tail -1\""
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
            return None

        if not self.case_dir.exists():
            return None

        times = []
        for item in self.case_dir.iterdir():
            if item.is_dir():
                try:
                    t = float(item.name)
                    times.append(t)
                except ValueError:
                    continue

        if times:
            return str(max(times))

        return None


def create_simulation_case(
    params: Dict[str, Any], template_dir: str, output_dir: str
) -> Dict[str, Any]:
    """创建并运行仿真案例"""
    controller = OpenFOAMController.from_template(
        template_dir=template_dir, target_dir=output_dir, params=params
    )

    success = controller.run()

    if not success:
        return {"status": "failed", "error": "Simulation failed"}

    results = controller.get_results()
    results["status"] = "success"

    return results


if __name__ == "__main__":
    params = {"velocity": 2.0, "inlet_temperature": 30.0, "fluid": "water"}
    controller = OpenFOAMController(config=SimulationConfig(case_dir="./test_case"))
    print("OpenFOAM控制器初始化完成")
