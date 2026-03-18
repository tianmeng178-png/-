"""
统一配置管理器
优化配置文件结构，解决重复和冲突问题
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """加载所有配置文件"""
        config_files = [
            "llm_config.json",
            "system_config.json", 
            "project.json"
        ]
        
        for config_file in config_files:
            file_path = self.config_dir / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.configs[config_file] = json.load(f)
                except Exception as e:
                    print(f"⚠️ 加载配置文件 {config_file} 失败: {e}")
    
    def get_config(self, config_type: str, key: str, default: Any = None) -> Any:
        """获取配置值，支持环境变量覆盖"""
        # 优先使用环境变量
        env_key = f"HEAT_EXCHANGER_{config_type.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._parse_env_value(env_value)
        
        # 从配置文件中获取
        config_file = f"{config_type}_config.json"
        if config_file in self.configs:
            return self.configs[config_file].get(key, default)
        
        # 从project.json中获取
        if config_type == "project" and "project.json" in self.configs:
            return self.configs["project.json"].get(key, default)
        
        return default
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试解析为JSON
        try:
            return json.loads(value)
        except:
            pass
        
        # 尝试解析为布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 尝试解析为数字
        try:
            return float(value) if '.' in value else int(value)
        except:
            pass
        
        return value
    
    def validate_configs(self) -> Dict[str, Any]:
        """验证配置完整性"""
        validation_results = {}
        
        # 检查必需配置
        required_configs = {
            "llm": ["gateway_url", "model"],
            "openfoam": ["use_wsl", "openfoam_path"],
            "simulation": ["template_dir", "solver"]
        }
        
        for config_type, required_keys in required_configs.items():
            validation_results[config_type] = {}
            for key in required_keys:
                value = self.get_config(config_type, key)
                if value is None:
                    validation_results[config_type][key] = "缺失"
                else:
                    validation_results[config_type][key] = "正常"
        
        # 检查配置冲突
        validation_results["conflicts"] = self._check_config_conflicts()
        
        return validation_results
    
    def _check_config_conflicts(self) -> Dict[str, Any]:
        """检查配置冲突"""
        conflicts = {}
        
        # 检查LLM配置冲突
        if "llm_config.json" in self.configs and "system_config.json" in self.configs:
            llm_config1 = self.configs["llm_config.json"].get("gateway_url")
            llm_config2 = self.configs["system_config.json"].get("llm", {}).get("gateway_url")
            
            if llm_config1 and llm_config2 and llm_config1 != llm_config2:
                conflicts["llm_gateway_url"] = {
                    "llm_config.json": llm_config1,
                    "system_config.json": llm_config2
                }
        
        return conflicts
    
    def generate_unified_config(self) -> Dict[str, Any]:
        """生成统一配置文件"""
        unified_config = {
            "version": "2.0",
            "description": "AI-Driven Heat Exchanger Design System - Unified Configuration",
            "configs": {}
        }
        
        # 合并LLM配置
        llm_config = {}
        if "llm_config.json" in self.configs:
            llm_config.update(self.configs["llm_config.json"])
        if "system_config.json" in self.configs:
            llm_config.update(self.configs["system_config.json"].get("llm", {}))
        
        unified_config["configs"]["llm"] = llm_config
        
        # 合并OpenFOAM配置
        openfoam_config = {}
        if "system_config.json" in self.configs:
            openfoam_config.update(self.configs["system_config.json"].get("openfoam", {}))
        
        unified_config["configs"]["openfoam"] = openfoam_config
        
        # 合并仿真配置
        simulation_config = {}
        if "system_config.json" in self.configs:
            simulation_config.update(self.configs["system_config.json"].get("simulation", {}))
        
        unified_config["configs"]["simulation"] = simulation_config
        
        # 项目信息
        if "project.json" in self.configs:
            unified_config["project"] = self.configs["project.json"]
        
        return unified_config
    
    def save_unified_config(self, output_file: str = "unified_config.json"):
        """保存统一配置文件"""
        unified_config = self.generate_unified_config()
        
        output_path = self.config_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unified_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 统一配置文件已保存: {output_path}")
    
    def create_env_template(self) -> str:
        """创建环境变量模板"""
        env_template = """# AI-Driven Heat Exchanger Design System 环境变量配置
# 复制此文件为 .env 并填写实际值

# LLM配置
HEAT_EXCHANGER_LLM_GATEWAY_URL=http://localhost:8000/v1
HEAT_EXCHANGER_LLM_API_KEY=your_api_key_here
HEAT_EXCHANGER_LLM_MODEL=deepseek-chat
HEAT_EXCHANGER_LLM_TIMEOUT=60
HEAT_EXCHANGER_LLM_TEMPERATURE=0.7

# OpenFOAM配置
HEAT_EXCHANGER_OPENFOAM_USE_WSL=true
HEAT_EXCHANGER_OPENFOAM_WSL_DISTRO=Ubuntu-24.04
HEAT_EXCHANGER_OPENFOAM_OPENFOAM_PATH=/opt/openfoam11

# 仿真配置
HEAT_EXCHANGER_SIMULATION_TEMPLATE_DIR=cases/test_final2
HEAT_EXCHANGER_SIMULATION_SOLVER=foamRun -solver incompressibleFluid
HEAT_EXCHANGER_SIMULATION_MESH_METHOD=blockMesh

# 安全配置
HEAT_EXCHANGER_SECURITY_ENCRYPT_API_KEYS=false
HEAT_EXCHANGER_SECURITY_LOG_SENSITIVE_DATA=false
"""
        return env_template


def analyze_current_configs():
    """分析当前配置文件状态"""
    print("🔍 分析当前配置文件状态...")
    
    config_manager = ConfigManager()
    
    # 显示当前配置
    print("\n📊 当前配置文件内容:")
    for config_file, config_data in config_manager.configs.items():
        print(f"\n📁 {config_file}:")
        print(json.dumps(config_data, indent=2, ensure_ascii=False))
    
    # 验证配置
    print("\n🔍 配置验证结果:")
    validation_results = config_manager.validate_configs()
    
    for config_type, results in validation_results.items():
        if config_type == "conflicts":
            if results:
                print(f"\n⚠️ 配置冲突:")
                for conflict_key, conflict_info in results.items():
                    print(f"  {conflict_key}:")
                    for file_name, value in conflict_info.items():
                        print(f"    {file_name}: {value}")
            else:
                print("✅ 无配置冲突")
        else:
            print(f"\n📋 {config_type}配置验证:")
            for key, status in results.items():
                print(f"  {key}: {status}")
    
    # 生成统一配置预览
    print("\n🔄 统一配置预览:")
    unified_config = config_manager.generate_unified_config()
    print(json.dumps(unified_config, indent=2, ensure_ascii=False))
    
    # 保存统一配置
    config_manager.save_unified_config()
    
    # 生成环境变量模板
    env_template = config_manager.create_env_template()
    env_file_path = config_manager.config_dir / ".env.template"
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.write(env_template)
    
    print(f"✅ 环境变量模板已保存: {env_file_path}")
    
    return config_manager


if __name__ == "__main__":
    analyze_current_configs()