# AI驱动的换热器智能设计系统

基于OpenFOAM和LLM的换热器智能设计系统 V1.0

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config/system_config.json`，配置LLM网关：

```json
{
  "llm": {
    "gateway_url": "http://localhost:8000/v1",
    "api_key": "your-api-key",
    "model": "deepseek-chat"
  }
}
```

### 3. 运行测试

```bash
# 命令行模式
python main.py -i "设计一个CPU微通道散热器，入口温度30℃，流速2m/s"

# 交互模式
python main.py --interactive
```

## 项目架构

```
heat_exchanger_ai/
├── config/              # 配置文件
├── cases/              # OpenFOAM案例
│   └── microchannel_template/  # 微通道换热器模板
├── src/                # 源代码
│   ├── llm_gateway.py      # LLM网关
│   ├── foam_controller.py # 仿真控制器
│   └── result_processor.py # 结果处理
├── main.py             # 主入口
└── requirements.txt    # Python依赖
```

## 技术栈

- **foamlib**: 开源OpenFOAM Python接口
- **LLM**: 通过API网关调用（DeepSeek/Qwen）
- **可视化**: Matplotlib
