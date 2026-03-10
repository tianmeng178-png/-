"""
案例生成模板系统
根据自然语言解析结果自动生成OpenFOAM案例文件
"""

import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from nlp_parameter_parser import NaturalLanguageParser, MicrochannelParameters


class CaseGenerator:
    """OpenFOAM案例生成器"""
    
    def __init__(self, base_case_dir: str = "cases/templates"):
        self.base_case_dir = Path(base_case_dir)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """加载案例模板"""
        templates = {}
        
        # 基础模板文件
        template_files = [
            "system/controlDict",
            "system/fvSchemes", 
            "system/fvSolution",
            "constant/transportProperties",
            "0/U",
            "0/p",
            "0/T"
        ]
        
        for template_file in template_files:
            template_path = self.base_case_dir / template_file
            if template_path.exists():
                templates[template_file] = template_path.read_text(encoding="utf-8")
        
        return templates
    
    def generate_case(self, parameters: Dict[str, Any], case_name: str) -> str:
        """
        生成完整的OpenFOAM案例
        
        Args:
            parameters: 自然语言解析结果
            case_name: 案例名称
            
        Returns:
            生成的案例目录路径
        """
        print(f"开始生成案例: {case_name}")
        
        # 创建案例目录
        case_dir = Path("cases") / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成案例文件
        self._generate_system_files(case_dir, parameters["parameters"])
        self._generate_constant_files(case_dir, parameters["parameters"])
        self._generate_initial_files(case_dir, parameters["parameters"])
        self._generate_geometry_files(case_dir, parameters["parameters"])
        
        print(f"案例生成完成: {case_dir}")
        return str(case_dir)
    
    def _generate_system_files(self, case_dir: Path, parameters: Dict[str, Any]):
        """生成system目录下的文件"""
        system_dir = case_dir / "system"
        system_dir.mkdir(exist_ok=True)
        
        # controlDict
        control_content = self._render_control_dict(parameters)
        (system_dir / "controlDict").write_text(control_content, encoding="utf-8")
        
        # fvSchemes
        schemes_content = self._render_fv_schemes(parameters)
        (system_dir / "fvSchemes").write_text(schemes_content, encoding="utf-8")
        
        # fvSolution
        solution_content = self._render_fv_solution(parameters)
        (system_dir / "fvSolution").write_text(solution_content, encoding="utf-8")
    
    def _generate_constant_files(self, case_dir: Path, parameters: Dict[str, Any]):
        """生成constant目录下的文件"""
        constant_dir = case_dir / "constant"
        constant_dir.mkdir(exist_ok=True)
        
        # transportProperties
        transport_content = self._render_transport_properties(parameters)
        (constant_dir / "transportProperties").write_text(transport_content, encoding="utf-8")
        
        # 生成polyMesh目录（网格文件）
        poly_mesh_dir = constant_dir / "polyMesh"
        poly_mesh_dir.mkdir(exist_ok=True)
        
        # 生成基本的网格文件
        self._generate_mesh_files(poly_mesh_dir, parameters)
    
    def _generate_initial_files(self, case_dir: Path, parameters: Dict[str, Any]):
        """生成0目录下的初始条件文件"""
        zero_dir = case_dir / "0"
        zero_dir.mkdir(exist_ok=True)
        
        # 速度场文件
        u_content = self._render_velocity_field(parameters)
        (zero_dir / "U").write_text(u_content, encoding="utf-8")
        
        # 压力场文件
        p_content = self._render_pressure_field(parameters)
        (zero_dir / "p").write_text(p_content, encoding="utf-8")
        
        # 温度场文件
        t_content = self._render_temperature_field(parameters)
        (zero_dir / "T").write_text(t_content, encoding="utf-8")
    
    def _generate_geometry_files(self, case_dir: Path, parameters: Dict[str, Any]):
        """生成几何相关文件"""
        # 生成blockMeshDict
        block_mesh_content = self._render_block_mesh_dict(parameters)
        (case_dir / "system" / "blockMeshDict").write_text(block_mesh_content, encoding="utf-8")
    
    def _render_control_dict(self, parameters: Dict[str, Any]) -> str:
        """生成controlDict文件内容"""
        geo_params = parameters["geometry"]
        flow_params = parameters["flow"]
        
        # 根据通道长度计算合适的计算时间
        channel_length = geo_params["channel_length"]
        inlet_velocity = flow_params["inlet_velocity"]
        residence_time = channel_length / inlet_velocity if inlet_velocity > 0 else 1.0
        
        end_time = max(100, int(residence_time * 10))
        
        return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         {end_time};

deltaT          1;

writeControl    timeStep;

writeInterval   50;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

// ************************************************************************* //
"""
    
    def _render_fv_schemes(self, parameters: Dict[str, Any]) -> str:
        """生成fvSchemes文件内容"""
        return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{{
    default         steadyState;
}}

gradSchemes
{{
    default         Gauss linear;
    grad(U)         Gauss linear;
    grad(p)         Gauss linear;
    grad(T)         Gauss linear;
}}

divSchemes
{{
    default         none;
    div(phi,U)      Gauss linearUpwindV grad(U);
    div(phi,T)      Gauss linearUpwind default;
    div((nuEff*dev2(grad(U).T()))) Gauss linear;
}}

laplacianSchemes
{{
    default         Gauss linear corrected;
}}

interpolationSchemes
{{
    default         linear;
}}

snGradSchemes
{{
    default         corrected;
}}

// ************************************************************************* //
"""
    
    def _render_fv_solution(self, parameters: Dict[str, Any]) -> str:
        """生成fvSolution文件内容"""
        return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{{
    p
    {{
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0.01;
    }}

    pFinal
    {{
        $p;
        relTol          0;
    }}

    "(U|T)"
    {{
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-08;
        relTol          0.01;
    }}
    
    "(U|T)Final"
    {{
        $U;
        relTol          0;
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      yes;

    residualControl
    {{
        p               1e-6;
        U               1e-6;
        T               1e-6;
    }}
}}

relaxationFactors
{{
    equations
    {{
        U               0.7;
        T               0.7;
    }}
}}

// ************************************************************************* //
"""
    
    def _render_transport_properties(self, parameters: Dict[str, Any]) -> str:
        """生成transportProperties文件内容"""
        fluid_type = parameters["materials"]["fluid_type"]
        
        # 流体粘度参数
        viscosity_map = {
            "water": 0.001,
            "air": 1.8e-5
        }
        viscosity = viscosity_map.get(fluid_type, 0.001)
        
        return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       dictionary;
    location    "constant";
    object      transportProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              nu [0 2 -1 0 0 0 0] {viscosity};

// ************************************************************************* //
"""
    
    def _render_velocity_field(self, parameters: Dict[str, Any]) -> str:
        """生成速度场文件内容"""
        flow_params = parameters["flow"]
        inlet_velocity = flow_params["inlet_velocity"]
        
        return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({inlet_velocity} 0 0);
    }}
    
    outlet
    {{
        type            zeroGradient;
    }}
    
    walls
    {{
        type            noSlip;
    }}
}}

// ************************************************************************* //
"""
    
    def _render_pressure_field(self, parameters: Dict[str, Any]) -> str:
        """生成压力场文件内容"""
        flow_params = parameters["flow"]
        outlet_pressure = flow_params["outlet_pressure"]
        
        return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    inlet
    {{
        type            zeroGradient;
    }}
    
    outlet
    {{
        type            fixedValue;
        value           uniform {outlet_pressure};
    }}
    
    walls
    {{
        type            zeroGradient;
    }}
}}

// ************************************************************************* //
"""
    
    def _render_temperature_field(self, parameters: Dict[str, Any]) -> str:
        """生成温度场文件内容"""
        flow_params = parameters["flow"]
        thermal_params = parameters["thermal"]
        
        inlet_temperature = flow_params["inlet_temperature"]
        base_temperature = thermal_params["base_temperature"]
        
        return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       volScalarField;
    location    "0";
    object      T;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 0 1 0 0 0];

internalField   uniform {inlet_temperature};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {inlet_temperature};
    }}
    
    outlet
    {{
        type            zeroGradient;
    }}
    
    walls
    {{
        type            fixedValue;
        value           uniform {base_temperature};
    }}
}}

// ************************************************************************* //
"""
    
    def _render_block_mesh_dict(self, parameters: Dict[str, Any]) -> str:
        """生成blockMeshDict文件内容"""
        geo_params = parameters["geometry"]
        
        channel_width = geo_params["channel_width"]
        channel_height = geo_params["channel_height"]
        channel_length = geo_params["channel_length"]
        channel_count = geo_params["channel_count"]
        wall_thickness = geo_params["wall_thickness"]
        
        # 计算总宽度
        total_width = channel_count * channel_width + (channel_count - 1) * wall_thickness
        
        return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v11                                   |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    (0 0 0)                    // 0
    ({total_width} 0 0)        // 1
    ({total_width} {channel_height} 0)  // 2
    (0 {channel_height} 0)              // 3
    (0 0 {channel_length})             // 4
    ({total_width} 0 {channel_length})  // 5
    ({total_width} {channel_height} {channel_length})  // 6
    (0 {channel_height} {channel_length})              // 7
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (20 10 50) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    
    outlet
    {{
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }}
    
    walls
    {{
        type wall;
        faces
        (
            (0 3 2 1)
            (0 1 5 4)
            (3 7 6 2)
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""
    
    def _generate_mesh_files(self, poly_mesh_dir: Path, parameters: Dict[str, Any]):
        """生成基本的网格文件（占位符）"""
        # 这里简化处理，实际应用中应该使用blockMesh生成网格
        for file_name in ["points", "faces", "owner", "neighbour", "boundary"]:
            (poly_mesh_dir / file_name).write_text("# Placeholder for mesh file\n", encoding="utf-8")


def test_case_generator():
    """测试案例生成器"""
    # 创建自然语言解析器
    parser = NaturalLanguageParser()
    
    # 测试用例
    test_description = "设计一个微通道散热器，通道宽度100微米，高度500微米，数量20个，入口速度0.2m/s，入口温度25°C，热通量50W/cm²，使用水冷却，铜材料"
    
    print("=== 测试案例生成器 ===")
    
    # 解析用户描述
    parameters = parser.parse_user_description(test_description)
    
    # 生成案例
    generator = CaseGenerator()
    case_dir = generator.generate_case(parameters, "test_generated_case")
    
    print(f"生成的案例目录: {case_dir}")
    print("案例文件结构:")
    
    # 显示生成的文件结构
    case_path = Path(case_dir)
    for root, dirs, files in os.walk(case_path):
        level = root.replace(str(case_path), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{sub_indent}{file}")


if __name__ == "__main__":
    test_case_generator()