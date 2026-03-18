import asyncio
import sys
import os
from typing import Dict, Optional, Any, List
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from nlp_parameter_parser import NaturalLanguageParser
    NLP_PARSER_AVAILABLE = True
except ImportError:
    NLP_PARSER_AVAILABLE = False
    print("警告: nlp_parameter_parser 模块导入失败，将使用模拟数据")


class LLMService:
    def __init__(self):
        self.available = True
        self.parser = NaturalLanguageParser() if NLP_PARSER_AVAILABLE else None
    
    async def check_availability(self) -> bool:
        return self.available
    
    async def parse_parameters(self, description: str) -> Dict[str, Any]:
        if self.parser:
            try:
                result = self.parser.parse_user_description(description)
                return self._format_response(result, description)
            except Exception as e:
                print(f"解析错误: {e}")
                return self._mock_parse(description)
        else:
            return self._mock_parse(description)
    
    def _format_response(self, parsed_result: Dict[str, Any], description: str) -> Dict[str, Any]:
        params = parsed_result.get("parameters", {})
        geometry = params.get("geometry", {})
        flow = params.get("flow", {})
        thermal = params.get("thermal", {})
        materials = params.get("materials", {})
        
        extracted = {}
        confidence_scores = []
        
        if geometry.get("channel_width"):
            extracted["channel_width"] = {
                "value": geometry["channel_width"],
                "confidence": 0.9,
                "unit": "m"
            }
            confidence_scores.append(0.9)
        
        if geometry.get("channel_height"):
            extracted["channel_height"] = {
                "value": geometry["channel_height"],
                "confidence": 0.85,
                "unit": "m"
            }
            confidence_scores.append(0.85)
        
        if geometry.get("channel_count"):
            extracted["channel_count"] = {
                "value": geometry["channel_count"],
                "confidence": 0.95,
                "unit": "个"
            }
            confidence_scores.append(0.95)
        
        if flow.get("inlet_velocity"):
            extracted["inlet_velocity"] = {
                "value": flow["inlet_velocity"],
                "confidence": 0.88,
                "unit": "m/s"
            }
            confidence_scores.append(0.88)
        
        if flow.get("inlet_temperature"):
            extracted["inlet_temperature"] = {
                "value": flow["inlet_temperature"],
                "confidence": 0.85,
                "unit": "K"
            }
            confidence_scores.append(0.85)
        
        if thermal.get("heat_flux"):
            extracted["heat_flux"] = {
                "value": thermal["heat_flux"],
                "confidence": 0.87,
                "unit": "W/m²"
            }
            confidence_scores.append(0.87)
        
        if materials.get("fluid_type"):
            extracted["fluid_type"] = {
                "value": materials["fluid_type"],
                "confidence": 0.92,
                "unit": ""
            }
            confidence_scores.append(0.92)
        
        if materials.get("solid_material"):
            extracted["material_type"] = {
                "value": materials["solid_material"],
                "confidence": 0.90,
                "unit": ""
            }
            confidence_scores.append(0.90)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        missing_params = self._identify_missing_parameters(extracted)
        
        suggestions = self._generate_suggestions(extracted, missing_params)
        
        return {
            "description": description,
            "extracted_parameters": extracted,
            "missing_parameters": missing_params,
            "warnings": self._generate_warnings(extracted),
            "recommendations": suggestions,
            "parsing_confidence": round(avg_confidence, 2),
            "fluid_properties": parsed_result.get("fluid_properties", {}),
            "solid_properties": parsed_result.get("solid_properties", {}),
            "formatted_parameters": {
                "channel_width": geometry.get("channel_width", 0.0001),
                "channel_height": geometry.get("channel_height", 0.0005),
                "channel_length": geometry.get("channel_length", 0.01),
                "channel_count": geometry.get("channel_count", 10),
                "wall_thickness": geometry.get("wall_thickness", 0.00005),
                "inlet_velocity": flow.get("inlet_velocity", 0.1),
                "inlet_temperature": flow.get("inlet_temperature", 293.15),
                "outlet_pressure": flow.get("outlet_pressure", 0),
                "heat_flux": thermal.get("heat_flux", 10000),
                "base_temperature": thermal.get("base_temperature", 353.15),
                "fluid_type": materials.get("fluid_type", "water"),
                "material_type": materials.get("solid_material", "copper"),
                "mesh_resolution": params.get("solver", {}).get("mesh_resolution", 20),
                "convergence_criteria": params.get("solver", {}).get("convergence_criteria", 1e-6)
            }
        }
    
    def _identify_missing_parameters(self, extracted: Dict[str, Any]) -> List[str]:
        required_params = [
            "channel_width", "channel_height", "channel_count",
            "inlet_velocity", "inlet_temperature", "heat_flux",
            "fluid_type", "material_type"
        ]
        return [p for p in required_params if p not in extracted]
    
    def _generate_warnings(self, extracted: Dict[str, Any]) -> List[str]:
        warnings = []
        
        if "channel_width" in extracted:
            width = extracted["channel_width"]["value"]
            if width < 50e-6:
                warnings.append("通道宽度小于50微米，可能存在制造困难")
            elif width > 1000e-6:
                warnings.append("通道宽度大于1毫米，可能影响散热效率")
        
        if "inlet_velocity" in extracted:
            velocity = extracted["inlet_velocity"]["value"]
            if velocity > 2.0:
                warnings.append("入口速度较高，可能导致较大的压力损失")
        
        if "heat_flux" in extracted:
            flux = extracted["heat_flux"]["value"]
            if flux > 500000:
                warnings.append("热通量较高，建议验证散热器材料耐温性能")
        
        return warnings
    
    def _generate_suggestions(self, extracted: Dict[str, Any], missing: List[str]) -> List[str]:
        suggestions = []
        
        if missing:
            suggestions.append(f"建议补充以下参数: {', '.join(missing)}")
        
        if "fluid_type" not in extracted:
            suggestions.append("建议使用水作为冷却介质以获得更好的散热效果")
        
        if "material_type" not in extracted:
            suggestions.append("建议使用铜材料以获得更好的导热性能")
        
        if "channel_count" in extracted:
            count = extracted["channel_count"]["value"]
            if count < 5:
                suggestions.append("通道数量较少，考虑增加通道数量以提高散热面积")
            elif count > 30:
                suggestions.append("通道数量较多，注意制造复杂性和压力分布均匀性")
        
        return suggestions
    
    def _mock_parse(self, description: str) -> Dict[str, Any]:
        return {
            "description": description,
            "extracted_parameters": {
                "channel_width": {"value": 0.0001, "confidence": 0.9, "unit": "m"},
                "channel_height": {"value": 0.0005, "confidence": 0.85, "unit": "m"},
                "channel_count": {"value": 10, "confidence": 0.95, "unit": "个"},
                "inlet_velocity": {"value": 0.2, "confidence": 0.88, "unit": "m/s"},
                "inlet_temperature": {"value": 298.15, "confidence": 0.85, "unit": "K"},
                "heat_flux": {"value": 500000, "confidence": 0.87, "unit": "W/m²"},
                "fluid_type": {"value": "water", "confidence": 0.92, "unit": ""},
                "material_type": {"value": "copper", "confidence": 0.90, "unit": ""}
            },
            "missing_parameters": [],
            "warnings": [],
            "recommendations": ["建议使用水作为冷却介质以获得更好的散热效果"],
            "parsing_confidence": 0.87,
            "fluid_properties": {
                "density": 998.2,
                "viscosity": 0.001,
                "specific_heat": 4186,
                "thermal_conductivity": 0.6
            },
            "solid_properties": {
                "density": 8960,
                "thermal_conductivity": 401,
                "specific_heat": 385
            },
            "formatted_parameters": {
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
                "material_type": "copper",
                "mesh_resolution": 20,
                "convergence_criteria": 1e-6
            }
        }
