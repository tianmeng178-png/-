# NVIDIA GPU 加速配置指南

## 系统要求

- 显卡：NVIDIA RTX 4060 或更高版本
- 驱动程序：NVIDIA CUDA Toolkit 11.8 或更高版本
- 操作系统：Windows 10/11 或 Linux

## OpenFOAM GPU 加速方案

### 方案一：使用 OpenFOAM-GPU 版本（推荐）

OpenFOAM 官方从 v2106 开始提供对 GPU 的支持，主要通过以下方式：

#### 1. OpenFOAM-AMGX
- 使用 NVIDIA AMGX 库加速线性求解器
- 支持共轭梯度（CG）和 GMRES 求解器
- 适用于压力和速度方程求解

#### 2. OpenFOAM-Kokkos
- 使用 Kokkos 编程模型实现异构计算
- 支持 CPU 和 GPU 混合执行
- 更灵活的编程接口

### 方案二：使用第三方 GPU 加速求解器

#### 1. PyTorch 或 TensorFlow 代理模型
- 使用机器学习加速设计优化
- 训练代理模型替代部分 CFD 计算
- 适用于参数扫描和优化

#### 2. CUDA 自定义求解器
- 开发专用的 CUDA 内核
- 针对微通道换热器优化
- 最大性能潜力

## Windows 环境配置步骤

### 1. 安装 NVIDIA CUDA Toolkit

```powershell
# 下载并安装 CUDA Toolkit 11.8 或更高版本
# 访问：https://developer.nvidia.com/cuda-toolkit
```

### 2. 验证 CUDA 安装

```powershell
nvidia-smi
nvcc --version
```

### 3. 设置 WSL2 环境（推荐）

```powershell
# 安装 WSL2
wsl --install

# 安装 Ubuntu 24.04
wsl --install -d Ubuntu-24.04
```

### 4. 在 WSL2 中配置 GPU 支持

```bash
# 在 WSL2 Ubuntu 中执行
sudo apt update
sudo apt install nvidia-cuda-toolkit

# 验证 GPU 可用性
nvidia-smi
```

### 5. 安装 OpenFOAM-GPU 版本

```bash
# 在 WSL2 中安装 OpenFOAM v11
curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
sudo apt install openfoam11

# 或者从源码编译支持 GPU 的版本
git clone https://develop.openfoam.com/Development/openfoam.git
cd openfoam
git checkout OpenFOAM-11
./Allwmake -j
```

## 使用代理模型加速（快速方案）

对于当前系统，可以使用以下方法实现 GPU 加速：

### 1. 参数优化阶段
- 使用 GPU 训练代理模型
- 快速参数扫描
- 找到最优设计点

### 2. 验证阶段
- 使用完整 OpenFOAM 仿真
- 在 CPU 上运行高精度验证
- 确保结果准确性

## 当前系统实现

### 模拟模式（已实现）
- 使用工程经验公式
- 快速计算（15-20秒）
- 适用于设计迭代

### OpenFOAM 模式（已实现）
- 完整 CFD 仿真
- 高精度结果
- 支持真实 OpenFOAM 调用

### GPU 加速选项
- 当前显示为可选功能
- 需要配置后启用
- 提供提示信息

## 性能对比

| 模式 | 计算时间 | 精度 | GPU 支持 |
|------|----------|------|----------|
| 模拟模式 | 15-20秒 | 工程级 | 不适用 |
| OpenFOAM CPU | 30-90分钟 | 高精度 | 否 |
| OpenFOAM GPU | 10-30分钟 | 高精度 | 是 |

## 下一步建议

1. **短期**：配置 WSL2 + OpenFOAM 环境
2. **中期**：实现代理模型 GPU 加速
3. **长期**：集成 OpenFOAM-GPU 求解器

## 参考资源

- [OpenFOAM 官方文档](https://openfoam.org/)
- [NVIDIA CUDA 文档](https://docs.nvidia.com/cuda/)
- [WSL2 GPU 加速](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
