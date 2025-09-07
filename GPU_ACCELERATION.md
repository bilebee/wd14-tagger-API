# GPU 加速问题诊断与解决方案

## 问题概述

当前项目无法使用 GPU 加速进行模型推理，这会导致图像标签识别速度较慢。

## 问题分析

通过检查代码和环境，我们发现以下问题：

1. 系统已安装 NVIDIA GPU 驱动并支持 CUDA (CUDA Version: 12.9)
2. 系统中安装了 `onnxruntime` (版本 1.22.1) 但没有安装 `onnxruntime-gpu`
3. 当前可用的 ONNX Runtime 提供程序只有: `['AzureExecutionProvider', 'CPUExecutionProvider']`
4. 缺少 CUDA Execution Provider，因此无法使用 GPU 进行推理

## 解决方案

### 方案一：安装 onnxruntime-gpu（推荐）

```bash
# 卸载 CPU 版本
pip uninstall onnxruntime

# 安装 GPU 版本
pip install onnxruntime-gpu
```

安装完成后，可用的提供程序应该包括 `['CUDAExecutionProvider', 'CPUExecutionProvider']`。

### 方案二：如果 onnxruntime-gpu 安装失败

如果由于 CUDA 版本或其他原因无法安装 onnxruntime-gpu，可以尝试以下替代方案：

1. 安装与 CUDA 版本兼容的 onnxruntime-gpu 版本
2. 确保系统安装了正确的 CUDA 和 cuDNN 版本

## CUDA 和 cuDNN 版本兼容性问题解决方案

根据您遇到的错误信息：
```
Failed to create CUDAExecutionProvider. Require cuDNN 9.* and CUDA 12.*, and the latest MSVC runtime.
```

这表明您的系统虽然有CUDA 12.9，但可能缺少正确的cuDNN版本或MSVC运行时库。

### 解决步骤：

1. **检查CUDA版本**：
   ```bash
   nvcc --version
   ```
   或
   ```bash
   nvidia-smi
   ```

2. **安装正确的cuDNN版本**：
   - 访问NVIDIA cuDNN下载页面：https://developer.nvidia.com/cudnn
   - 下载与您的CUDA 12.*版本兼容的cuDNN 9.*版本
   - 按照NVIDIA官方指南安装cuDNN

3. **安装MSVC运行时库**：
   - 访问Microsoft Visual C++ Redistributable下载页面
   - 安装最新的x64版本运行时库

4. **设置环境变量**：
   确保CUDA和cuDNN路径已添加到系统PATH环境变量中：
   ```
   C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin
   C:\tools\cuda\bin (如果cuDNN安装在此路径)
   ```

## 代码改进

我们已经在 [interrogator.py](tagger/interrogator.py) 文件中添加了对 GPU 支持的检测逻辑：

```python
def get_onnxrt():
    """Get ONNX runtime module with error handling for standalone mode"""
    try:
        import onnxruntime as ort
        
        # Check if CUDA is available and onnxruntime-gpu is installed
        # If CUDA is available but only onnxruntime (CPU version) is installed,
        # try to install onnxruntime-gpu
        try:
            # Check if CUDA provider is available
            available_providers = ort.get_available_providers()
            if 'CUDAExecutionProvider' not in available_providers:
                # CUDA provider not available, check if CUDA is available on system
                import subprocess
                try:
                    result = subprocess.run(['nvidia-smi'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # NVIDIA GPU is available but CUDAExecutionProvider is not in providers
                        # This means onnxruntime-gpu is not installed
                        print("CUDA is available but onnxruntime-gpu is not installed.")
                        print("For better performance, please install onnxruntime-gpu:")
                        print("pip install onnxruntime-gpu")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # nvidia-smi not found or timeout, skip CUDA check
                    pass
            return ort
        except Exception:
            pass
            
        return ort
    except ImportError:
        raise ImportError(
            "Please install onnxruntime to use ONNX models: "
            "pip install onnxruntime"
        )
```

这段代码会检测系统是否支持 CUDA，如果支持但未安装 onnxruntime-gpu，会提示用户安装。

## 验证解决方案

安装 onnxruntime-gpu 后，可以通过以下命令验证：

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

预期输出应该包含 `CUDAExecutionProvider`：

```
['CUDAExecutionProvider', 'CPUExecutionProvider']
```

## 性能提升预期

使用 GPU 加速后，图像标签识别的性能应该有显著提升，特别是在处理大批量图像时。

## 注意事项

1. 确保 CUDA 驱动版本与 onnxruntime-gpu 版本兼容
2. 如果遇到版本兼容性问题，可以查看 ONNX Runtime 的官方文档获取版本对应关系
3. 在某些情况下，可能需要重启 Python 环境才能使新安装的包生效
4. 确保安装了正确的 cuDNN 版本 (9.*) 和 MSVC 运行时库
5. 检查环境变量是否正确配置，确保 CUDA 和 cuDNN 路径在系统 PATH 中

## 常见问题及解决方案

### 1. CUDA依赖库缺失错误

如果遇到如下错误：
```
Error loading "...onnxruntime_providers_cuda.dll" which depends on "cublas64_12.dll" which is missing.
```

这表明CUDA库文件缺失，请确保：

1. 安装了完整版本的CUDA Toolkit (不仅仅是驱动)
2. CUDA的bin目录已添加到系统PATH环境变量中
3. 安装了与CUDA版本匹配的cuDNN库

### 2. cuDNN版本不兼容

如果遇到如下错误：
```
Failed to create CUDAExecutionProvider. Require cuDNN 9.* and CUDA 12.*
```

请确保：

1. 下载并安装了正确的cuDNN版本 (9.*)
2. cuDNN文件已正确复制到CUDA安装目录
3. 重启系统使环境变量生效

### 3. MSVC运行时库缺失

如果遇到如下错误：
```
Failed to create CUDAExecutionProvider. ... and the latest MSVC runtime.
```

请确保：

1. 安装了最新版本的Microsoft Visual C++ Redistributable
2. 可能需要安装x64和x86两个版本
3. 重启系统使更改生效

## 测试CUDA功能

我们提供了一个简单的测试脚本[test_cuda.py](test_cuda.py)来验证CUDA功能是否正常工作。运行该脚本可以检查：

1. ONNX Runtime是否支持CUDA执行提供程序
2. CUDA执行提供程序是否能正常加载和运行模型
3. 是否存在依赖库缺失问题

运行测试脚本：
```bash
python test_cuda.py
```

如果一切正常，您应该看到类似以下输出：
```
Available providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
CUDA Execution Provider works!
Inference successful with CUDA!
```

如果有任何错误，脚本会显示详细的错误信息，帮助您诊断问题。