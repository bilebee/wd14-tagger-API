# WD14 Tagger API

Stable Diffusion WebUI 的 WD14 Tagger 扩展插件的独立版本，无需 WebUI 即可运行。

本项目为 Koakuma 项目提供后端支持，Koakuma 是一个图像检索网站项目。但此项目也可独立用于任何需要图像标签识别的场景。

## 功能特点

- 独立 API 服务器，无需依赖 Stable Diffusion WebUI
- 提供 Web 界面用于便捷地进行图像标签识别
- 支持多种标签识别模型
- 支持本地模型加载
- 提供 RESTful API 便于与其他应用集成

## 安装说明

### 前提条件

- Python 3.8 或更高版本
- pip 包管理器

### 自动安装

双击 `install.bat` 文件自动安装所有必需的依赖项。

### 手动安装

1. 克隆或下载本仓库
2. 安装所需依赖包：
   ```
   pip install -r requirements.txt
   ```

### 额外依赖

为获得完整功能，您可能还需要安装：

- DeepDanbooru 模型支持：
  ```
  pip install git+https://github.com/KichangKim/DeepDanbooru.git
  ```

- TensorFlow 模型支持：
  ```
  pip install tensorflow
  ```

- ONNX 模型支持：
  ```
  pip install onnxruntime
  ```
  
  # ONNX CUDA 支持（可选，但推荐用于提升性能）：
  # ```
  # pip install onnxruntime-gpu
  # ```

## 使用方法

### 启动服务器

双击 `run_server.bat` 文件以默认设置启动服务器。

### 命令行选项

您也可以使用自定义选项运行服务器：

```
python standalone.py [--host HOST] [--port PORT] [--reload]
                     [--deepdanbooru-path DEEPDANBOORU_PATH]
                     [--onnxtagger-path ONNXTAGGER_PATH]
                     [--hf-cache-dir HF_CACHE_DIR]
```

选项说明：
- `--host`: 运行 API 的主机地址 (默认: 127.0.0.1)
- `--port`: 运行 API 的端口 (默认: 8000)
- `--reload`: 启用开发模式下的自动重载功能
- `--deepdanbooru-path`: DeepDanbooru 模型路径
- `--onnxtagger-path`: ONNX 模型路径
- `--hf-cache-dir`: HuggingFace 缓存目录

### 访问界面

服务器启动后：

1. Web 界面: http://127.0.0.1:8000/ui
2. API 文档: http://127.0.0.1:8000/

## 本地模型支持

本独立版本支持加载本地模型。模型可以从 HuggingFace 自动下载，也可以手动放置在指定目录中。

### 目录结构

```
models/
├── deepdanbooru/
│   └── [model_name]/
│       ├── project.json
│       └── [其他模型文件]
└── TaggerOnnx/
    └── [model_name]/
        ├── [model_name].onnx
        └── selected_tags.csv
```

### 支持的模型类型

1. **DeepDanbooru 模型** - 放置于 `models/deepdanbooru/[model_name]/`
   - 必须包含 `project.json` 文件
   - 基于 TensorFlow 的模型

2. **ONNX 模型** - 放置于 `models/TaggerOnnx/[model_name]/`
   - 必须包含 `.onnx` 模型文件和 `selected_tags.csv` 文件
   - ONNX 格式模型，使用 ONNX Runtime 进行推理
   - 为提升性能，可考虑使用 GPU 加速版本 `onnxruntime-gpu`

### 模型放置说明

1. 按上述结构创建目录
2. 将模型文件放置在相应目录中：
   - DeepDanbooru 模型需确保模型目录中有 `project.json` 文件
   - ONNX模型需确保有 `.onnx` 模型文件以及 `selected_tags.csv` 文件
3. 重启服务器以检测新模型

### 支持自动下载的模型

以下模型将在首次使用时自动下载：
- WD14 ViT v1 和 v2
- WD14 ConvNeXT v1 和 v2
- WD14 ConvNeXTV2 v1
- WD14 SwinV2 v1
- WD14 moat tagger v2
- ML-Danbooru 模型

### 手动下载来源

如需手动下载模型，请访问以下仓库：
- [SmilingWolf HuggingFace 仓库](https://huggingface.co/SmilingWolf)
- [DeepDanbooru 模型](https://github.com/KichangKim/DeepDanbooru/releases)
- [ML-Danbooru ONNX 模型](https://huggingface.co/deepghs/ml-danbooru-onnx)

## API 端点

- `GET /` - API 文档和使用示例
- `GET /ui` - 图像标签识别 Web 界面
- `GET /tagger/v1/interrogators` - 列出可用模型
- `POST /tagger/v1/interrogate` - 图像标签识别
- `POST /tagger/v1/unload-interrogators` - 从内存中卸载模型

## 身份验证

设置 `API_AUTH` 环境变量以添加身份验证：

```
API_AUTH=username:password python standalone.py
```

## 使用示例

### 获取可用模型

```bash
curl -X GET "http://127.0.0.1:8000/tagger/v1/interrogators"
```

### 图像标签识别

```bash
curl -X POST "http://127.0.0.1:8000/tagger/v1/interrogate" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image",
    "model": "wd-v1-4-moat-tagger.v2",
    "threshold": 0.5
}'
```

## 文件忽略规则

本项目通过 `.gitignore` 文件忽略以下不应上传到仓库的文件和目录：
- `__pycache__/` - Python 缓存文件
- `.vscode/` - VS Code 配置文件
- `.venv/` - 虚拟环境目录
- `.env` - 环境变量配置文件
- `presets/` - 预设配置目录
- `models/` - 模型文件目录（包含所有模型文件，由于文件过大不应上传）
- 模型文件和其他大型二进制文件不会被提交到仓库中

## 许可证

本项目基于 Stable Diffusion WebUI 的 wd14-tagger 扩展开发，原项目采用 MIT 许可证。

本项目同样采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。