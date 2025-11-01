# WD14 Tagger 批量处理调用示例文档

本文档提供了使用 WD14 Tagger API 的批量处理功能的示例。

## 简介

WD14 Tagger API 的批量处理功能允许用户一次发送多个图像进行标签识别，相比逐个处理图像可以显著提高处理效率。API 会尽可能利用模型的批量处理能力来加速推理过程。

批量处理 API 返回分类格式的结果，将标签分为三类：
- `ratings`: 内容评分标签（general, sensitive, questionable, explicit）
- `characters`: 角色标签（category 4）
- `tags`: 常规标签（所有其他类别）

## API 端点

批量处理功能通过以下端点提供：

```
POST /tagger/v1/interrogate-batch
```

## 请求格式

批量处理请求需要以下参数：

- `images`: 字符串数组，包含多个 Base64 编码的图像
- `model`: 字符串，指定要使用的模型名称
- `threshold`: 浮点数，可选，标签置信度阈值（默认为 0.0）

## 示例

### Python 示例

```python
import base64
import requests
import json

# 准备图像文件
image_files = ["image1.jpg", "image2.jpg", "image3.jpg"]

# 将图像转换为 Base64 编码
encoded_images = []
for image_file in image_files:
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
        encoded_images.append(encoded)

# 构造请求数据
data = {
    "images": encoded_images,
    "model": "wd14-vit-v2",  # 使用 wd14 模型
    "threshold": 0.35
}

# 发送请求
response = requests.post(
    "http://127.0.0.1:8000/tagger/v1/interrogate-batch",
    headers={"Content-Type": "application/json"},
    data=json.dumps(data)
)

# 处理响应
if response.status_code == 200:
    result = response.json()
    captions = result["captions"]
    
    for i, caption in enumerate(captions):
        print(f"图像 {i+1} 的标签:")
        # 输出评分标签
        if "ratings" in caption and caption["ratings"]:
            print("  评分:")
            for rating, confidence in caption["ratings"].items():
                print(f"    {rating}: {confidence:.3f}")
        
        # 输出角色标签
        if "characters" in caption and caption["characters"]:
            print("  角色:")
            # 按置信度排序
            sorted_characters = sorted(caption["characters"].items(), key=lambda x: x[1], reverse=True)
            for character, confidence in sorted_characters:
                print(f"    {character}: {confidence:.3f}")
        
        # 输出常规标签
        if "tags" in caption and caption["tags"]:
            print("  标签:")
            # 按置信度排序
            sorted_tags = sorted(caption["tags"].items(), key=lambda x: x[1], reverse=True)
            for tag, confidence in sorted_tags[:10]:  # 只显示前10个标签
                print(f"    {tag}: {confidence:.3f}")
        print()
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(response.text)
```

### JavaScript 示例

```javascript
// 使用 fetch API 进行批量处理
async function batchInterrogate() {
    // 假设你已经有了图像文件
    const imageFiles = [file1, file2, file3]; // 这些应该是 File 对象
    
    // 将图像文件转换为 Base64
    const encodedImages = await Promise.all(
        imageFiles.map(file => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    // 移除 data URL 前缀，只保留 Base64 编码部分
                    const base64 = reader.result.split(',')[1];
                    resolve(base64);
                };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        })
    );
    
    // 构造请求数据
    const data = {
        images: encodedImages,
        model: "wd14-vit-v2",  # 使用 wd14 模型
        threshold: 0.35
    };
    
    try {
        # 发送请求
        const response = await fetch("http://127.0.0.1:8000/tagger/v1/interrogate-batch", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            const captions = result.captions;
            
            captions.forEach((caption, index) => {
                console.log(`图像 ${index+1} 的标签:`);
                
                # 输出评分标签
                if (caption.ratings) {
                    console.log("  评分:");
                    for (const [rating, confidence] of Object.entries(caption.ratings)) {
                        console.log(`    ${rating}: ${confidence.toFixed(3)}`);
                    }
                }
                
                # 输出角色标签
                if (caption.characters) {
                    console.log("  角色:");
                    # 按置信度排序
                    const sortedCharacters = Object.entries(caption.characters)
                        .sort((a, b) => b[1] - a[1]);
                    
                    sortedCharacters.forEach(([character, confidence]) => {
                        console.log(`    ${character}: ${confidence.toFixed(3)}`);
                    });
                }
                
                # 输出常规标签
                if (caption.tags) {
                    console.log("  标签:");
                    # 按置信度排序
                    const sortedTags = Object.entries(caption.tags)
                        .sort((a, b) => b[1] - a[1]);
                    
                    # 只显示前10个标签
                    sortedTags.slice(0, 10).forEach(([tag, confidence]) => {
                        console.log(`    ${tag}: ${confidence.toFixed(3)}`);
                    });
                }
                console.log();
            });
        } else {
            console.error("请求失败，状态码:", response.status);
        }
    } catch (error) {
        console.error("请求出错:", error);
    }
}

# 调用函数
batchInterrogate();
```

### cURL 示例

```bash
# 首先将图像转换为 Base64 编码
base64 -i image1.jpg | tr -d '\n' > image1.b64
base64 -i image2.jpg | tr -d '\n' > image2.b64

# 构造 JSON 请求数据
# 注意：这里需要手动将 Base64 数据放入 JSON 中
cat > batch_request.json <<EOF
{
    "images": [
        "$(cat image1.b64)",
        "$(cat image2.b64)"
    ],
    "model": "wd14-vit-v2",
    "threshold": 0.35
}
EOF

# 发送请求
curl -X POST "http://127.0.0.1:8000/tagger/v1/interrogate-batch" \
     -H "Content-Type: application/json" \
     -d @batch_request.json

# 清理临时文件
rm image1.b64 image2.b64 batch_request.json
```

### 使用 Python 脚本进行批量处理

```python
#!/usr/bin/env python3
"""
批量处理图像目录中的所有图像
"""

import base64
import requests
import json
import os
from pathlib import Path

def encode_image(image_path):
    """将图像文件编码为 Base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def batch_interrogate_images(image_dir, model="wd14-vit-v2", threshold=0.35, batch_size=10):
    """
    批量处理目录中的图像
    
    Args:
        image_dir: 包含图像的目录路径
        model: 使用的模型名称
        threshold: 标签置信度阈值
        batch_size: 每批次处理的图像数量
    """
    
    # 支持的图像扩展名
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    
    # 获取目录中的所有图像文件
    image_files = [
        f for f in Path(image_dir).iterdir() 
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"在目录 {image_dir} 中未找到图像文件")
        return
    
    print(f"找到 {len(image_files)} 个图像文件")
    
    # 分批处理
    for i in range(0, len(image_files), batch_size):
        batch = image_files[i:i+batch_size]
        print(f"处理批次 {i//batch_size + 1}: {len(batch)} 个图像")
        
        # 编码图像
        encoded_images = [encode_image(img) for img in batch]
        
        # 构造请求数据
        data = {
            "images": encoded_images,
            "model": model,
            "threshold": threshold
        }
        
        try:
            # 发送请求
            response = requests.post(
                "http://127.0.0.1:8000/tagger/v1/interrogate-batch",
                headers={"Content-Type": "application/json"},
                data=json.dumps(data)
            )
            
            if response.status_code == 200:
                result = response.json()
                captions = result["captions"]
                
                # 处理结果
                for j, (img_path, caption) in enumerate(zip(batch, captions)):
                    print(f"\n图像: {img_path.name}")
                    
                    # 保存标签到文本文件
                    tags_file = img_path.with_suffix('.txt')
                    tags = []
                    
                    # 收集评分标签
                    if "ratings" in caption and caption["ratings"]:
                        for rating, confidence in caption["ratings"].items():
                            tags.append(f"rating:{rating}:{confidence:.3f}")
                    
                    # 收集角色标签
                    if "characters" in caption and caption["characters"]:
                        for character, confidence in caption["characters"].items():
                            tags.append(f"character:{character}:{confidence:.3f}")
                    
                    # 收集常规标签
                    if "tags" in caption and caption["tags"]:
                        # 按置信度排序
                        sorted_tags = sorted(caption["tags"].items(), key=lambda x: x[1], reverse=True)
                        for tag, confidence in sorted_tags:
                            tags.append(f"{tag}:{confidence:.3f}")
                    
                    # 写入文件
                    with open(tags_file, 'w', encoding='utf-8') as f:
                        f.write(', '.join(tags))
                    
                    print(f"  标签已保存到: {tags_file.name}")
                    
                    # 打印前几个标签作为预览
                    if "tags" in caption and caption["tags"]:
                        sorted_tags = sorted(caption["tags"].items(), key=lambda x: x[1], reverse=True)
                        print("  前5个标签:")
                        for tag, confidence in sorted_tags[:5]:
                            print(f"    {tag}: {confidence:.3f}")
            else:
                print(f"  批次处理失败，状态码: {response.status_code}")
                print(f"  响应: {response.text}")
                
        except Exception as e:
            print(f"  处理批次时出错: {e}")

if __name__ == "__main__":
    # 示例用法
    image_directory = "./images"  # 替换为你的图像目录
    batch_interrogate_images(
        image_dir=image_directory,
        model="wd14-vit-v2",  # 使用 wd14 模型
        threshold=0.35,
        batch_size=5  # 每批次处理5个图像
    )
```

## 响应格式

批量处理的响应格式如下：

```json
{
  "captions": [
    {
      "ratings": {
        "general": 0.998,
        "sensitive": 0.001,
        "questionable": 0.000,
        "explicit": 0.000
      },
      "characters": {
        "1girl": 0.987
      },
      "tags": {
        "solo": 0.965,
        "long_hair": 0.876,
        // ... 更多标签
      }
    },
    // ... 更多图像的结果
  ]
}
```

每个图像的结果都包含三个部分：
- `ratings`: 内容评分标签及其置信度
- `characters`: 角色标签及其置信度
- `tags`: 常规标签及其置信度

## 注意事项

1. **模型选择**: 请确保指定的模型（如 "wd14-vit-v2"）已在服务器上可用
2. **批量大小**: 虽然 API 支持批量处理，但过大的批量可能导致内存不足，建议根据系统配置调整批量大小
3. **图像格式**: 支持常见的图像格式（JPEG, PNG, BMP, WebP 等）
4. **Base64 编码**: 图像需要以 Base64 格式编码，可以包含或不包含 `data:image/...;base64,` 前缀
5. **错误处理**: 请确保正确处理网络错误和 API 错误响应

## 性能提示

1. **使用支持批量处理的模型**: 选择支持批量推理的模型可以获得最佳性能
2. **合适的批量大小**: 根据系统内存和 GPU 显存调整批量大小，通常 8-32 张图像的批量大小是比较合理的
3. **复用连接**: 在处理大量图像时，复用 HTTP 连接可以减少开销