# Depth Anything V2 - Raw深度图保存和查看指南

## 功能概述

本脚本已增强，支持保存raw/bin格式的深度图，方便使用YUVPlayer查看每个像素的具体深度值。

## 新增参数

### `--save-raw`
- 保存8位归一化深度图为`.raw`格式
- 深度值范围：0-255（uint8）
- 用途：在YUVPlayer中可视化查看每个像素的深度值

### `--save-float`
- 保存原始浮点深度值为`_float.bin`格式
- 数据类型：32位浮点（float32）
- 用途：用于精确的深度值分析和后处理

## 使用方法

### 基础用法

```bash
# 仅保存raw格式深度图
python run.py --img-path your_image.jpg --save-raw

# 同时保存raw和float格式
python run.py --img-path your_image.jpg --save-raw --save-float

# 处理整个文件夹
python run.py --img-path ./images --save-raw --encoder vitl

# 只保存深度预测（不拼接原图）
python run.py --img-path ./images --save-raw --pred-only
```

### 完整示例

```bash
# 使用vitl编码器，保存raw格式，只输出深度图
python run.py \
    --img-path ./test_images \
    --encoder vitl \
    --input-size 518 \
    --outdir ./output \
    --save-raw \
    --pred-only
```

## YUVPlayer配置方法

### 步骤1：打开文件
1. 启动YUVPlayer
2. 选择 `File` → `Open` 或直接拖拽`.raw`文件到YUVPlayer窗口

### 步骤2：配置参数

脚本运行时会在控制台输出配置信息，例如：
```
Saved raw depth to: ./output/image.raw
YUVPlayer config: 1920x1080, Y800 (8-bit grayscale)
```

在YUVPlayer中设置：

| 参数 | 值 | 说明 |
|------|-----|------|
| **Width（宽度）** | 例如：1920 | 图像宽度（从控制台输出获取） |
| **Height（高度）** | 例如：1080 | 图像高度（从控制台输出获取） |
| **Color Format** | Y800 / GRAY8 / Y8 | 8位灰度格式 |
| **Bits per sample** | 8 | 每个采样点8位 |
| **Byte Order** | Little Endian | 字节序（通常默认） |

### 步骤3：查看像素值

- **鼠标悬停**：将鼠标悬停在图像上，YUVPlayer会显示当前像素的具体数值（0-255）
- **深度含义**：
  - **数值越大（接近255，白色）**：物体距离越远
  - **数值越小（接近0，黑色）**：物体距离越近

### YUVPlayer界面示例

```
┌─────────────────────────────────────┐
│ File: image.raw                     │
│ Size: 1920x1080                     │
│ Format: Y800                        │
│                                     │
│ [深度图显示区域]                    │
│                                     │
│ Pixel Info:                         │
│ Position: (960, 540)                │
│ Y Value: 128                        │  ← 当前像素深度值
└─────────────────────────────────────┘
```

## 读取Float格式深度数据

如果需要进行精确的深度值分析，可以使用Python读取`_float.bin`文件：

### 方法1：使用NumPy读取

```python
import numpy as np

# 读取float深度图
depth = np.fromfile('output_float.bin', dtype=np.float32)

# 重塑为二维数组（需要知道原始尺寸）
height, width = 1080, 1920  # 替换为实际尺寸
depth = depth.reshape(height, width)

# 查看统计信息
print(f"Shape: {depth.shape}")
print(f"Min depth: {depth.min():.4f}")
print(f"Max depth: {depth.max():.4f}")
print(f"Mean depth: {depth.mean():.4f}")
print(f"Std depth: {depth.std():.4f}")
```

### 方法2：可视化float深度图

```python
import numpy as np
import matplotlib.pyplot as plt

# 读取数据
depth = np.fromfile('output_float.bin', dtype=np.float32)
depth = depth.reshape(height, width)

# 可视化
plt.figure(figsize=(12, 6))

plt.subplot(1, 2, 1)
plt.imshow(depth, cmap='Spectral_r')
plt.colorbar(label='Depth Value')
plt.title('Depth Map')

plt.subplot(1, 2, 2)
plt.hist(depth.flatten(), bins=100)
plt.xlabel('Depth Value')
plt.ylabel('Frequency')
plt.title('Depth Distribution')

plt.tight_layout()
plt.savefig('depth_analysis.png')
plt.show()
```

### 方法3：提取特定区域的深度信息

```python
import numpy as np

# 读取深度图
depth = np.fromfile('output_float.bin', dtype=np.float32)
depth = depth.reshape(height, width)

# 提取特定区域（例如中心100x100区域）
center_y, center_x = height // 2, width // 2
region = depth[center_y-50:center_y+50, center_x-50:center_x+50]

print(f"Center region depth:")
print(f"  Min: {region.min():.4f}")
print(f"  Max: {region.max():.4f}")
print(f"  Mean: {region.mean():.4f}")

# 查看特定像素的深度值
pixel_depth = depth[540, 960]  # (y, x)坐标
print(f"Depth at (960, 540): {pixel_depth:.4f}")
```

## 输出文件说明

运行脚本后，会在输出目录生成以下文件：

```
output/
├── image.png              # PNG可视化结果（彩色深度图或拼接图）
├── image.raw              # 8位raw深度图（使用--save-raw）
└── image_float.bin        # 32位浮点深度图（使用--save-float）
```

### 文件大小计算

- **`.raw`文件**: `width × height × 1 byte`
  - 例如 1920×1080 = 2,073,600 bytes ≈ 2MB
  
- **`_float.bin`文件**: `width × height × 4 bytes`
  - 例如 1920×1080 × 4 = 8,294,400 bytes ≈ 8MB

## 常见问题

### Q1: YUVPlayer显示的图像不正确？
**A**: 检查Width和Height设置是否与控制台输出一致，确保Color Format选择Y800/GRAY8。

### Q2: 如何确定图像的宽度和高度？
**A**: 运行脚本时，控制台会输出配置信息，或者使用以下Python代码：
```python
import os
file_size = os.path.getsize('image.raw')
# 对于正方形图像
side_length = int(file_size ** 0.5)
print(f"Possible size: {side_length}x{side_length}")
```

### Q3: 深度值的单位是什么？
**A**: Depth Anything V2输出的是相对深度（无单位），表示场景中的深度顺序关系，不是绝对距离（米）。

### Q4: 如何转换为绝对深度？
**A**: 需要额外的标定信息或深度后处理。相对深度可用于深度排序、3D重建等任务。

## 技术细节

### 深度值归一化

raw格式深度图使用以下公式归一化：

```
depth_normalized = (depth - depth_min) / (depth_max - depth_min) × 255
```

### 数据存储格式

- **Raw格式**: 按行优先（row-major）顺序存储，无文件头
- **Float格式**: 32位IEEE 754浮点数，按行优先顺序存储

## 参考资料

- [Depth Anything V2 官方仓库](https://github.com/DepthAnything/Depth-Anything-V2)
- [YUVPlayer 官方网站](http://www.yuvplayer.com/)
- [YUV格式说明](https://en.wikipedia.org/wiki/YUV)

## 更新日志

- **2026-01-06**: 添加`--save-raw`和`--save-float`参数支持

---

如有问题或建议，欢迎提出Issue。

