# VBench真实手持相机视频评测适用维度分析

## 背景与目标

本文档旨在分析VBench评测框架中哪些维度适用于评测**真实拍摄的手持相机视频**，特别是用于评估不同竞品手持相机的视频效果质量。

VBench原本是为AI视频生成模型设计的评测基准，但其中许多维度基于通用的视频质量评估方法，完全可以应用于真实视频的客观评测。

---

## 适用维度总览

### ✅ 高度适用（推荐使用）

| 维度名称 | 适用性 | 应用场景 |
|---------|--------|----------|
| Temporal Flickering | ⭐⭐⭐⭐⭐ | 纹理闪烁评测（玻璃幕墙、草地、夜景） |
| Motion Smoothness | ⭐⭐⭐⭐⭐ | 运动平滑度评测（防抖性能） |
| Dynamic Degree | ⭐⭐⭐⭐⭐ | 运动幅度检测 |
| Aesthetic Quality | ⭐⭐⭐⭐⭐ | 美学质量评估 |
| Imaging Quality | ⭐⭐⭐⭐⭐ | 成像质量评估（清晰度、色彩） |
| Subject Consistency | ⭐⭐⭐⭐ | 主体跟踪稳定性 |
| Background Consistency | ⭐⭐⭐⭐ | 背景稳定性 |
| Overall Consistency | ⭐⭐⭐⭐ | 整体时间一致性 |

### ⚠️ 部分适用（需谨慎使用）

| 维度名称 | 适用性 | 限制条件 |
|---------|--------|----------|
| Color | ⭐⭐⭐ | 需要已知正确的颜色标签 |
| Scene | ⭐⭐⭐ | 需要场景标签 |
| Camera Motion | ⭐⭐⭐ | VBench 2.0提供，适用于分析相机运动 |

### ❌ 不适用（针对AI生成）

| 维度名称 | 原因 |
|---------|------|
| Object Class | 需要文本prompt进行对比 |
| Multiple Objects | 需要文本prompt中的对象列表 |
| Human Action | 需要文本prompt中的动作描述 |
| Spatial Relationship | 需要文本prompt中的空间关系 |
| Appearance/Temporal Style | 针对AI生成风格控制 |

---

## 详细分析：适用维度

### 1. ⭐ Temporal Flickering（时间闪烁）

**适用性：★★★★★**

#### 功能说明
评估视频在时间维度上的纹理闪烁和抖动程度，特别适合检测：
- 玻璃幕墙的反射闪烁
- 草地、绿植的纹理抖动
- 夜景场景的噪点闪烁
- 水面、金属表面的高频闪烁

#### 评测原理
计算相邻帧之间的平均绝对误差(MAE)，假设视频内容是静态的。对于手持相机，建议结合运动补偿使用（见Flicker Penalty）。

#### 使用方法

```python
from vbench import VBench

my_VBench = VBench("cuda", "vbench/VBench_full_info.json", "results")
my_VBench.evaluate(
    videos_path="path/to/handheld_videos",
    name="camera_test",
    dimension_list=["temporal_flickering"],
    mode="custom_input"  # 使用自定义视频
)
```

#### 输出解读
- **分数范围：** 0-1（归一化后的分数，1为最好）
- **高分（>0.8）：** 纹理稳定，无明显闪烁
- **中分（0.6-0.8）：** 轻微闪烁
- **低分（<0.6）：** 明显闪烁，需要改进防抖或降噪

#### 应用场景示例
```bash
# 评测不同相机在夜景模式下的纹理稳定性
vbench evaluate --videos_path ./night_scene_videos \
    --dimension temporal_flickering \
    --mode custom_input
```

#### 局限性
- 对于运动场景，原始实现假设视频静态，可能产生误判
- 建议结合 **Flicker Penalty（FP）** 指标进行运动补偿

---

### 2. ⭐ Motion Smoothness（运动平滑度）

**适用性：★★★★★**

#### 功能说明
评估视频中运动的平滑程度，检测运动抖动、卡顿、不自然的加速度变化。对手持相机尤为重要，可以评估：
- 电子防抖效果
- 光学防抖性能
- 云台稳定性
- 手持抖动程度

#### 评测原理
基于RAFT光流估计，计算运动场的时间一致性。通过分析光流的平滑度和连续性来评分。

#### 使用方法

```python
from vbench import VBench

my_VBench = VBench("cuda", "vbench/VBench_full_info.json", "results")
my_VBench.evaluate(
    videos_path="path/to/handheld_videos",
    name="motion_test",
    dimension_list=["motion_smoothness"],
    mode="custom_input"
)
```

#### 输出解读
- **高分：** 运动流畅，防抖效果好
- **低分：** 运动抖动明显，防抖性能差

#### 应用场景示例
```python
# 比较不同相机的防抖性能
results_camera_a = evaluate_motion_smoothness("camera_a_walking.mp4")
results_camera_b = evaluate_motion_smoothness("camera_b_walking.mp4")

print(f"相机A防抖分数: {results_camera_a}")
print(f"相机B防抖分数: {results_camera_b}")
```

#### 推荐测试场景
1. **步行拍摄**：测试基础防抖
2. **跑步拍摄**：测试强力防抖
3. **摇镜头**：测试运动跟踪平滑度
4. **推拉镜头**：测试深度运动稳定性

---

### 3. ⭐ Dynamic Degree（动态程度）

**适用性：★★★★★**

#### 功能说明
量化视频的动态程度，区分静态场景和运动场景。可用于：
- 检测相机是否成功捕捉运动
- 分析不同场景下的运动幅度
- 作为其他指标的前置条件判断

#### 评测原理
基于RAFT光流计算运动幅度，统计显著运动的像素比例。

#### 使用方法

```python
my_VBench.evaluate(
    videos_path="path/to/videos",
    name="dynamic_test",
    dimension_list=["dynamic_degree"],
    mode="custom_input"
)
```

#### 输出解读
- **高分（>0.7）：** 动态场景，有明显运动
- **中分（0.3-0.7）：** 中等运动
- **低分（<0.3）：** 静态或微动场景

#### 应用策略
结合动态程度，可以为不同场景选择合适的评测维度：

```python
# 伪代码示例
if dynamic_degree > 0.5:
    # 运动场景，评测防抖和运动平滑度
    evaluate(["motion_smoothness", "subject_consistency"])
else:
    # 静态场景，评测纹理闪烁和成像质量
    evaluate(["temporal_flickering", "imaging_quality"])
```

---

### 4. ⭐ Aesthetic Quality（美学质量）

**适用性：★★★★★**

#### 功能说明
使用深度学习模型评估视频的美学质量，包括：
- 构图美感
- 色彩协调性
- 光线运用
- 整体视觉吸引力

#### 评测原理
基于预训练的美学评分模型（如LAION Aesthetic Predictor），对视频帧进行美学评分并平均。

#### 使用方法

```python
my_VBench.evaluate(
    videos_path="path/to/videos",
    name="aesthetic_test",
    dimension_list=["aesthetic_quality"],
    mode="custom_input"
)
```

#### 输出解读
- **高分（>6.0）：** 美学质量优秀
- **中分（5.0-6.0）：** 美学质量良好
- **低分（<5.0）：** 美学质量一般

#### 应用场景
- 评估自动构图算法效果
- 比较不同相机的色彩科学
- 评估HDR、夜景模式的美学表现

#### 注意事项
- 美学是主观的，该指标基于训练数据的偏好
- 更适合作为参考，而非绝对标准

---

### 5. ⭐ Imaging Quality（成像质量）

**适用性：★★★★★**

#### 功能说明
评估视频的成像质量，包括：
- **清晰度**：图像锐利程度
- **色彩**：色彩饱和度、对比度
- **噪声**：图像噪点水平
- **失真**：畸变、色差等

#### 评测原理
使用PYIQA（Python Image Quality Assessment）库中的多个无参考质量评估指标（如NIQE, BRISQUE等）。

#### 使用方法

```python
my_VBench.evaluate(
    videos_path="path/to/videos",
    name="imaging_test",
    dimension_list=["imaging_quality"],
    mode="custom_input"
)
```

#### 输出解读
分数越高表示成像质量越好。

#### 推荐测试场景
1. **夜景低光**：测试降噪和细节保留
2. **高对比度**：测试动态范围
3. **高速运动**：测试运动模糊控制
4. **微距**：测试焦外效果和锐度

#### 扩展评测
结合不同拍摄模式：
```python
# 评测不同模式的成像质量
modes = ["normal", "night", "portrait", "sport"]
for mode in modes:
    evaluate(f"camera_{mode}_videos", dimension_list=["imaging_quality"])
```

---

### 6. ⭐ Subject Consistency（主体一致性）

**适用性：★★★★**

#### 功能说明
评估视频中主体在时间维度上的视觉一致性，可用于：
- 评估跟踪拍摄时主体的稳定性
- 检测主体在帧间的抖动
- 评估自动对焦的稳定性

#### 评测原理
使用CLIP模型提取主体的特征向量，计算帧间特征的余弦相似度。

#### 使用方法

```python
my_VBench.evaluate(
    videos_path="path/to/videos",
    name="subject_test",
    dimension_list=["subject_consistency"],
    mode="custom_input"
)
```

#### 输出解读
- **高分：** 主体稳定，跟踪效果好
- **低分：** 主体抖动或丢失

#### 应用场景
- 评估人像追焦性能
- 评估运动主体跟踪
- 评估稳定器锁定主体能力

---

### 7. ⭐ Background Consistency（背景一致性）

**适用性：★★★★**

#### 功能说明
评估视频背景的时间稳定性，检测：
- 背景抖动
- 虚焦稳定性
- 散景效果的时间一致性

#### 评测原理
使用深度估计或分割模型提取背景区域，计算背景特征的帧间一致性。

#### 使用方法

```python
my_VBench.evaluate(
    videos_path="path/to/videos",
    name="background_test",
    dimension_list=["background_consistency"],
    mode="custom_input"
)
```

#### 应用场景
- 评估人像模式的背景虚化稳定性
- 评估手持拍摄时背景的稳定度
- 评估电影模式的散景效果

---

### 8. ⭐ Overall Consistency（整体一致性）

**适用性：★★★★**

#### 功能说明
评估视频整体画面的时间一致性，综合考虑：
- 亮度一致性
- 色调一致性
- 整体风格稳定性

#### 评测原理
使用视频级别的特征提取（如ViCLIP），计算全局特征的帧间相似度。

#### 使用方法

```python
my_VBench.evaluate(
    videos_path="path/to/videos",
    name="overall_test",
    dimension_list=["overall_consistency"],
    mode="custom_input"
)
```

#### 应用场景
- 评估自动曝光的稳定性
- 评估自动白平衡的一致性
- 评估整体视频质量稳定性

---

## 部分适用维度

### 9. ⚠️ Camera Motion（相机运动）- VBench 2.0

**适用性：★★★**

#### 功能说明
VBench 2.0新增维度，专门分析相机运动类型，包括：
- Push In / Pull Out（推进/拉远）
- Pan Left / Right（左右摇移）
- Tilt Up / Down（上下俯仰）
- Zoom In / Out（变焦）
- Static（静止）

#### 评测原理
基于光流分析和相机运动模型，分类相机运动类型。

#### 适用场景
- 分析手持拍摄的运动模式
- 评估稳定器的运动控制
- 统计不同相机运动的使用频率

#### 局限性
需要VBench 2.0环境，且主要用于分类而非质量评分。

#### 使用方法

```python
# VBench 2.0
from vbench2 import VBench2

my_VBench2 = VBench2("cuda", "vbench2/VBench2_full_info.json", "results")
my_VBench2.evaluate(
    videos_path="path/to/videos",
    name="camera_motion_test",
    dimension_list=["Camera_Motion"]
)
```

---

### 10. ⚠️ Color（颜色）

**适用性：★★★**

#### 功能说明
评估视频是否正确呈现了特定颜色。

#### 局限性
VBench的Color维度需要文本prompt中的颜色标签（如"a red car"），对于真实视频：
- 需要预先标注物体颜色
- 或者使用参考色卡进行对比

#### 适用场景（需改造）
- **色彩准确性测试**：拍摄标准色卡，评估色彩还原
- **白平衡测试**：在不同光源下拍摄，评估色彩偏移

#### 改造建议
```python
# 伪代码：使用参考色卡
reference_colors = extract_colors_from_color_card("reference.jpg")
video_colors = extract_colors_from_video("test_video.mp4")
color_accuracy = compare_colors(reference_colors, video_colors)
```

---

## 不适用维度说明

以下维度专门为AI文本到视频生成设计，需要文本prompt作为输入，**不适用于真实视频评测**：

| 维度 | 原因 |
|------|------|
| Object Class | 需要prompt中的物体类别进行对比 |
| Multiple Objects | 需要prompt中列出的多个物体 |
| Human Action | 需要prompt中描述的人类动作 |
| Spatial Relationship | 需要prompt中的空间关系描述 |
| Scene | 需要prompt中的场景类型 |
| Appearance Style | 评估AI生成的艺术风格控制 |
| Temporal Style | 评估AI生成的时间风格一致性 |

---

## 推荐评测流程

### 完整评测流程

```python
from vbench import VBench

# 初始化VBench
vbench = VBench(
    device="cuda",
    full_info_path="vbench/VBench_full_info.json",
    output_path="evaluation_results"
)

# 定义评测维度（高度适用的）
dimensions = [
    "temporal_flickering",    # 纹理闪烁
    "motion_smoothness",      # 运动平滑度
    "dynamic_degree",         # 动态程度
    "aesthetic_quality",      # 美学质量
    "imaging_quality",        # 成像质量
    "subject_consistency",    # 主体一致性
    "background_consistency", # 背景一致性
    "overall_consistency"     # 整体一致性
]

# 批量评测
vbench.evaluate(
    videos_path="path/to/camera_videos",
    name="handheld_camera_evaluation",
    dimension_list=dimensions,
    mode="custom_input"
)
```

### 分场景评测策略

#### 1. 静态场景评测
```python
static_dimensions = [
    "temporal_flickering",
    "imaging_quality",
    "aesthetic_quality"
]
```

**适用场景：** 风景、建筑、静物拍摄

#### 2. 运动场景评测
```python
motion_dimensions = [
    "motion_smoothness",
    "subject_consistency",
    "background_consistency",
    "dynamic_degree"
]
```

**适用场景：** 运动、街拍、Vlog

#### 3. 夜景/低光评测
```python
lowlight_dimensions = [
    "temporal_flickering",  # 重点：噪点闪烁
    "imaging_quality",      # 重点：噪声控制
    "aesthetic_quality"
]
```

**适用场景：** 夜景、室内低光

#### 4. 人像/跟踪评测
```python
portrait_dimensions = [
    "subject_consistency",
    "background_consistency",
    "motion_smoothness",
    "aesthetic_quality"
]
```

**适用场景：** 人像、宠物跟踪拍摄

---

## 命令行快速评测

### 单维度评测
```bash
# 评测纹理闪烁
vbench evaluate \
    --videos_path ./test_videos \
    --dimension temporal_flickering \
    --mode custom_input

# 评测运动平滑度
vbench evaluate \
    --videos_path ./test_videos \
    --dimension motion_smoothness \
    --mode custom_input
```

### 多维度批量评测
```bash
# 创建评测脚本
cat > eval_camera.sh << 'EOF'
#!/bin/bash

VIDEO_PATH="./camera_test_videos"
DIMENSIONS=(
    "temporal_flickering"
    "motion_smoothness"
    "dynamic_degree"
    "aesthetic_quality"
    "imaging_quality"
    "subject_consistency"
    "background_consistency"
    "overall_consistency"
)

for dim in "${DIMENSIONS[@]}"; do
    echo "Evaluating $dim..."
    vbench evaluate \
        --videos_path $VIDEO_PATH \
        --dimension $dim \
        --mode custom_input
done
EOF

chmod +x eval_camera.sh
./eval_camera.sh
```

---

## 结果分析与可视化

### 结果汇总
```python
import json
import pandas as pd

# 读取评测结果
results = {}
dimensions = ["temporal_flickering", "motion_smoothness", "imaging_quality"]

for dim in dimensions:
    with open(f"evaluation_results/{dim}_results.json") as f:
        results[dim] = json.load(f)

# 创建DataFrame
df = pd.DataFrame(results).T
df.columns = ["Score"]
print(df)

# 可视化
import matplotlib.pyplot as plt

df.plot(kind='bar', title='Camera Video Quality Assessment')
plt.ylabel('Score')
plt.xlabel('Dimension')
plt.tight_layout()
plt.savefig('camera_evaluation_results.png')
```

### 雷达图可视化
```python
import numpy as np
import matplotlib.pyplot as plt

# 归一化分数到0-1
dimensions = list(results.keys())
scores = [results[dim]['score'] for dim in dimensions]

# 创建雷达图
angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
scores += scores[:1]  # 闭合图形
angles += angles[:1]

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
ax.plot(angles, scores, 'o-', linewidth=2)
ax.fill(angles, scores, alpha=0.25)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(dimensions)
ax.set_ylim(0, 1)
ax.set_title('Camera Video Quality Radar Chart')
plt.savefig('radar_chart.png')
```

---

## 对比评测示例

### 多相机对比
```python
cameras = ["Camera_A", "Camera_B", "Camera_C"]
dimensions = ["temporal_flickering", "motion_smoothness", "imaging_quality"]

results_matrix = {}
for camera in cameras:
    results_matrix[camera] = {}
    for dim in dimensions:
        result = vbench.evaluate(
            videos_path=f"./videos/{camera}",
            name=f"{camera}_{dim}",
            dimension_list=[dim],
            mode="custom_input"
        )
        results_matrix[camera][dim] = result[dim]

# 生成对比表格
df = pd.DataFrame(results_matrix).T
print(df)

# 可视化对比
df.plot(kind='bar', figsize=(12, 6))
plt.title('Multi-Camera Comparison')
plt.ylabel('Score')
plt.legend(title='Dimensions')
plt.tight_layout()
plt.savefig('camera_comparison.png')
```

---

## 高级应用：自定义评测场景

### 1. 特定纹理闪烁评测

针对玻璃幕墙、草地等场景，使用增强版FP指标：

```python
from vbench.worldscore.flicker_penalty import compute_fp_score

# 评测玻璃幕墙场景
glass_result = compute_fp_score(
    video_path="glass_building.mp4",
    device="cuda"
)

print(f"玻璃幕墙FP分数: {glass_result['fp_score']:.4f}")
print(f"闪烁峰值数量: {glass_result['analysis']['flicker_peaks']}")
print(f"时间一致性: {glass_result['analysis']['temporal_consistency']:.4f}")

# 评测草地场景
grass_result = compute_fp_score(
    video_path="grass_field.mp4",
    device="cuda"
)

print(f"草地FP分数: {grass_result['fp_score']:.4f}")
```

### 2. 防抖性能专项测试

```python
# 测试不同运动强度下的防抖性能
test_scenarios = {
    "static": "static_shot.mp4",
    "slow_walk": "slow_walking.mp4",
    "fast_walk": "fast_walking.mp4",
    "running": "running.mp4",
    "shake": "intentional_shake.mp4"
}

for scenario, video_path in test_scenarios.items():
    result = vbench.evaluate(
        videos_path=video_path,
        name=f"stabilization_{scenario}",
        dimension_list=["motion_smoothness"],
        mode="custom_input"
    )
    print(f"{scenario}: {result['motion_smoothness']:.4f}")
```

### 3. 夜景模式质量评测

```python
night_dimensions = [
    "temporal_flickering",  # 噪点闪烁
    "imaging_quality",      # 噪声水平
    "aesthetic_quality",    # 整体美感
    "overall_consistency"   # 曝光稳定性
]

night_result = vbench.evaluate(
    videos_path="night_mode_videos",
    name="night_mode_test",
    dimension_list=night_dimensions,
    mode="custom_input"
)

# 生成夜景模式质量报告
print("=== 夜景模式质量报告 ===")
for dim in night_dimensions:
    print(f"{dim}: {night_result[dim]:.4f}")
```

---

## 常见问题 (FAQ)

### Q1: VBench能直接评测真实视频吗？

**A:** 是的，通过设置 `mode="custom_input"`，VBench可以评测任何视频文件，不需要文本prompt。但只有部分维度适用于真实视频（见本文档"适用维度"部分）。

### Q2: 哪些维度最适合评测手持相机防抖？

**A:** 推荐使用：
1. **Motion Smoothness**：直接评估运动平滑度
2. **Temporal Flickering** 或 **Flicker Penalty**：评估画面稳定性
3. **Subject Consistency**：评估跟踪拍摄时主体的稳定性

### Q3: 如何评测夜景模式的效果？

**A:** 夜景评测重点关注：
- **Temporal Flickering**：噪点闪烁
- **Imaging Quality**：图像质量（包含噪声评估）
- **Overall Consistency**：曝光和色彩稳定性

### Q4: Temporal Flickering 和 Flicker Penalty 有什么区别？

**A:** 
- **Temporal Flickering**：简单帧差法，适合静态或微动场景，计算快
- **Flicker Penalty**：基于光流运动补偿，适合运动场景，计算慢但更准确

建议：运动场景使用FP，静态场景使用TF。

### Q5: 评测结果如何解读？

**A:** VBench的大多数维度分数在0-1范围内（部分如aesthetic_quality在0-10）：
- **0.8-1.0**：优秀
- **0.6-0.8**：良好
- **0.4-0.6**：一般
- **<0.4**：较差

具体阈值因维度而异，建议通过对比测试建立基线。

### Q6: 需要GPU吗？

**A:** 
- **必须GPU**：Motion Smoothness, Flicker Penalty（基于RAFT光流）
- **推荐GPU**：Aesthetic Quality, Imaging Quality（深度学习模型）
- **可用CPU**：Temporal Flickering（简单帧差）

### Q7: 如何批量评测大量视频？

**A:** 使用循环或并行处理：

```python
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

video_paths = list(Path("./videos").glob("**/*.mp4"))

def evaluate_single(video_path):
    return vbench.evaluate(
        videos_path=str(video_path),
        name=video_path.stem,
        dimension_list=["temporal_flickering", "imaging_quality"],
        mode="custom_input"
    )

# 并行评测（注意GPU内存）
with ThreadPoolExecutor(max_workers=2) as executor:
    results = list(executor.map(evaluate_single, video_paths))
```

### Q8: 评测结果保存在哪里？

**A:** 结果默认保存在初始化时指定的 `output_path` 目录，每个维度一个JSON文件：
```
evaluation_results/
├── temporal_flickering_results.json
├── motion_smoothness_results.json
└── ...
```

---

## 总结与建议

### 推荐评测套装

#### 基础套装（必测）
```python
basic_dimensions = [
    "temporal_flickering",  # 纹理稳定性
    "motion_smoothness",    # 运动平滑度
    "imaging_quality"       # 成像质量
]
```

#### 完整套装（推荐）
```python
full_dimensions = [
    "temporal_flickering",
    "motion_smoothness",
    "dynamic_degree",
    "aesthetic_quality",
    "imaging_quality",
    "subject_consistency",
    "background_consistency",
    "overall_consistency"
]
```

#### 高级套装（专业测试）
```python
# 基于Flicker Penalty的纹理闪烁
from vbench.worldscore.flicker_penalty import compute_fp_score

fp_result = compute_fp_score(video_path)

# 结合VBench标准维度
vbench_result = vbench.evaluate(
    videos_path=video_path,
    dimension_list=full_dimensions,
    mode="custom_input"
)
```

### 评测最佳实践

1. **场景标准化**：
   - 使用统一的测试场景（如固定路线、固定光照）
   - 确保不同相机测试条件一致

2. **多次重复**：
   - 每个场景至少拍摄3次取平均
   - 减少偶然因素影响

3. **分类评测**：
   - 按场景类型分组（静态、运动、夜景等）
   - 使用对应的维度组合

4. **建立基线**：
   - 选择标杆相机作为参考
   - 所有结果与基线对比

5. **结合主观评价**：
   - 客观指标 + 人眼观察
   - 关注数值无法反映的细节

### 局限性说明

1. **依赖GPU**：部分维度需要高性能GPU
2. **计算时间**：完整评测可能需要较长时间
3. **场景依赖**：不同场景的分数可比性有限
4. **绝对值意义**：分数更适合用于相对比较而非绝对判断

---

## 参考资源

### VBench相关
- [VBench GitHub](https://github.com/Vchitect/VBench)
- [VBench Paper (CVPR 2024)](https://arxiv.org/abs/2311.17982)
- [VBench 2.0 Paper](https://arxiv.org/abs/2503.21755)
- [VBench Leaderboard](https://huggingface.co/spaces/Vchitect/VBench_Leaderboard)

### 技术文档
- [RAFT: Optical Flow Estimation](https://arxiv.org/abs/2003.12039)
- [CLIP: Vision-Language Models](https://arxiv.org/abs/2103.00020)
- [PYIQA: Image Quality Assessment](https://github.com/chaofengc/IQA-PyTorch)

### 本项目文档
- [Flicker Penalty计算模块文档](./vbench/worldscore/README_FlickerPenalty.md)

---

## 联系与支持

如有问题或建议，请通过以下方式联系：
- **GitHub Issues**: https://github.com/Vchitect/VBench/issues
- **Email**: ZIQI002@e.ntu.edu.sg

---

**文档版本**: 1.0  
**最后更新**: 2025年1月  
**适用VBench版本**: v0.1.5+, VBench 2.0+

