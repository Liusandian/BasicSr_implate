# 纹理抖动评测工具套件

用于评测真实相机拍摄视频的纹理抖动性能，基于VBench框架。

## 📁 文件说明

| 文件名 | 说明 | 用途 |
|-------|------|------|
| `纹理抖动评测指标分析.md` | 📚 完整评测指标文档 | 理论指导和详细说明 |
| `texture_jitter_eval.py` | 🎯 主评测脚本 | 多维度综合评测 |
| `eval_flicker_penalty.py` | ⭐ FP专项评测 | 运动场景闪烁评测 |
| `analyze_results.py` | 📊 结果分析工具 | 生成评测报告 |
| `README.md` | 📖 本文件 | 快速开始指南 |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保已安装VBench
cd VBench-master
pip install -r requirements.txt

# 下载必要的预训练模型
cd pretrained/raft_model && bash download.sh && cd ../..
cd pretrained/amt_model && bash download.sh && cd ../..
```

### 2. 准备测试视频

**推荐的文件组织结构:**

```
test_videos/
├── grass/              # 草地场景
│   ├── insta360.mp4
│   ├── sony.mp4
│   ├── canon.mp4
│   ├── huawei.mp4
│   └── iphone16.mp4
├── night/              # 夜景场景
│   └── ...
├── glass/              # 玻璃幕墙
│   └── ...
└── motion/             # 运动场景
    └── ...
```

**视频要求:**
- 格式: MP4 (推荐)
- 分辨率: 1080p 或 4K
- 帧率: ≥30fps
- 时长: 10-15秒

---

## 📊 使用方法

### 方法A: 快速评测 (推荐新手)

使用Flicker Penalty进行快速评测，适合大部分场景。

```bash
# 评测单个视频
python scripts/v'ben'ch_for_flickering/eval_flicker_penalty.py \
    --video test_videos/grass/canon.mp4

# 批量评测一个目录
python scripts/v'ben'ch_for_flickering/eval_flicker_penalty.py \
    --video_dir test_videos/grass

# 对比多个相机
python scripts/v'ben'ch_for_flickering/eval_flicker_penalty.py \
    --compare \
    --camera "Canon R6":test_videos/grass/canon.mp4 \
    --camera "Sony A7":test_videos/grass/sony.mp4 \
    --camera "iPhone 16":test_videos/grass/iphone16.mp4
```

**输出示例:**

```
对比结果 - Flicker Penalty (FP) 排名
================================================================================
🥇 Canon R6            : 0.9523 | 优秀 ⭐⭐⭐⭐⭐
   专业级稳定，无可见闪烁
🥈 Sony A7             : 0.9401 | 良好 ⭐⭐⭐⭐
   稳定，轻微闪烁
🥉 iPhone 16           : 0.9187 | 良好 ⭐⭐⭐⭐
   稳定，轻微闪烁
```

---

### 方法B: 多维度综合评测

使用主评测脚本进行全面评测。

```bash
# 标准评测模式 (5个维度，约20分钟)
python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
    --video_dir test_videos/grass \
    --mode standard \
    --output_dir results

# 快速评测模式 (2个维度，约10分钟)
python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
    --video_dir test_videos \
    --mode fast

# 专业评测模式 (7个维度，约30分钟)
python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
    --video_dir test_videos \
    --mode professional
```

**评测模式对比:**

| 模式 | 维度数量 | 评测时长 | 适用场景 |
|-----|---------|---------|----------|
| `fast` | 2个 | ~10分钟 | 快速对比 |
| `standard` ⭐ | 5个 | ~20分钟 | 正式评测（推荐） |
| `professional` | 7个 | ~30分钟 | 深度分析 |

---

### 方法C: 相机对比评测

对比多个相机在相同场景下的表现。

```bash
# 使用综合评测对比
python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
    --compare \
    --camera "Canon":test_videos/grass/canon.mp4 \
    --camera "Sony":test_videos/grass/sony.mp4 \
    --camera "Huawei":test_videos/grass/huawei.mp4 \
    --camera "iPhone16":test_videos/grass/iphone16.mp4 \
    --mode standard \
    --output_dir results
```

---

### 方法D: 生成评测报告

评测完成后，生成可读性强的Markdown报告。

```bash
# 分析最新的评测结果
python scripts/v'ben'ch_for_flickering/analyze_results.py \
    --results_dir results \
    --output report.md \
    --show_chart

# 分析特定的JSON结果文件
python scripts/v'ben'ch_for_flickering/analyze_results.py \
    --json results/comparison_20260106_143052.json \
    --output detailed_report.md
```

**生成的报告包含:**
- 📊 评测结果汇总表格
- 🏆 相机排名对比
- ⭐ 评分等级和星级
- 📹 各视频详细结果
- 📝 评分标准说明

---

## 🎯 典型应用场景

### 场景1: 草地纹理抖动评测

**目标:** 评测不同相机拍摄草地时的纹理稳定性

```bash
# Step 1: 录制视频
# 使用不同相机在同一草地场景拍摄10-15秒视频

# Step 2: 评测
python scripts/v'ben'ch_for_flickering/eval_flicker_penalty.py \
    --compare \
    --camera "Insta360":grass/insta360.mp4 \
    --camera "Sony":grass/sony.mp4 \
    --camera "Canon":grass/canon.mp4 \
    --camera "Huawei P80":grass/huawei.mp4 \
    --camera "iPhone 16":grass/iphone16.mp4 \
    --output results/grass_comparison.json

# Step 3: 生成报告
python scripts/v'ben'ch_for_flickering/analyze_results.py \
    --json results/grass_comparison.json \
    --output reports/grass_report.md
```

---

### 场景2: 夜景纹理闪烁评测

**目标:** 评测夜景模式下的噪点控制和纹理稳定性

```bash
# 使用多维度评测（包含成像质量）
python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
    --video_dir test_videos/night \
    --mode standard \
    --output_dir results/night

# 分析结果
python scripts/v'ben'ch_for_flickering/analyze_results.py \
    --results_dir results/night \
    --output reports/night_report.md
```

**重点关注维度:**
- Flicker Penalty: 纹理闪烁
- Imaging Quality: 噪点控制
- Background Consistency: 背景稳定性

---

### 场景3: 玻璃幕墙反射闪烁

**目标:** 评测玻璃幕墙高频反射的稳定性

```bash
# 使用FP评测（最适合高频闪烁）
python scripts/v'ben'ch_for_flickering/eval_flicker_penalty.py \
    --video_dir test_videos/glass \
    --output results/glass_fp.json
```

---

### 场景4: 手持防抖性能测试

**目标:** 评测不同相机的防抖效果

```bash
# 使用标准评测，重点关注运动平滑度
python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
    --video_dir test_videos/handheld_walking \
    --mode standard \
    --output_dir results/stabilization
```

**重点关注维度:**
- Motion Smoothness: 防抖性能
- Flicker Penalty: 运动中的纹理稳定性

---

## 📊 评分标准参考

### Flicker Penalty (FP) 分数对照表

| 分数范围 | 评级 | 星级 | 典型表现 |
|---------|------|------|----------|
| 0.95 - 1.0 | 优秀 | ⭐⭐⭐⭐⭐ | 专业级稳定，无可见闪烁 |
| 0.90 - 0.95 | 良好 | ⭐⭐⭐⭐ | 稳定，轻微闪烁 |
| 0.85 - 0.90 | 中等 | ⭐⭐⭐ | 可见轻微闪烁 |
| 0.80 - 0.85 | 一般 | ⭐⭐ | 明显闪烁和抖动 |
| < 0.80 | 较差 | ⭐ | 严重闪烁 |

### 综合评分权重建议

```python
# 不同场景的权重配置示例
weights = {
    "草地/绿植场景": {
        "flicker_penalty": 0.50,
        "temporal_flickering": 0.30,
        "imaging_quality": 0.20
    },
    "夜景场景": {
        "flicker_penalty": 0.40,
        "imaging_quality": 0.40,
        "background_consistency": 0.20
    },
    "运动场景": {
        "motion_smoothness": 0.50,
        "flicker_penalty": 0.30,
        "overall_consistency": 0.20
    }
}
```

---

## 🔧 高级用法

### 1. 批量处理多个场景

```bash
#!/bin/bash
# batch_eval.sh - 批量评测脚本

scenes=("grass" "night" "glass" "motion")

for scene in "${scenes[@]}"; do
    echo "Evaluating scene: $scene"
    
    python scripts/v'ben'ch_for_flickering/texture_jitter_eval.py \
        --video_dir "test_videos/$scene" \
        --mode standard \
        --output_dir "results/$scene"
    
    python scripts/v'ben'ch_for_flickering/analyze_results.py \
        --results_dir "results/$scene" \
        --output "reports/${scene}_report.md"
done

echo "All scenes evaluated!"
```

### 2. 自动场景分类评测

```python
# auto_eval.py - 根据场景自动选择评测维度
from texture_jitter_eval import TextureJitterEvaluator

# 先评估动态程度
evaluator = TextureJitterEvaluator(mode='fast')
results = evaluator.evaluate_videos('test_videos')

# 根据dynamic_degree选择合适的维度
if results['dynamic_degree']['average_score'] < 0.3:
    # 静态场景
    evaluator = TextureJitterEvaluator(mode='standard')
    # 重点评测: temporal_flickering, imaging_quality
else:
    # 运动场景
    # 重点评测: motion_smoothness, flicker_penalty
    pass
```

### 3. 结果可视化

```python
# visualize_results.py
import json
import matplotlib.pyplot as plt

# 读取结果
with open('results/comparison.json') as f:
    data = json.load(f)

# 绘制雷达图
# ... (代码略)
```

---

## ⚠️ 注意事项

### 1. GPU显存要求

| 评测工具 | 最小显存 | 推荐显存 | 分辨率 |
|---------|---------|---------|--------|
| Flicker Penalty | 4GB | 8GB | 1080p |
| Motion Smoothness | 4GB | 6GB | 1080p |
| 综合评测 (Standard) | 6GB | 8GB | 1080p |

**显存不足解决方案:**
- 降低视频分辨率
- 使用CPU模式 (非常慢)
- 分维度单独评测

### 2. 视频拍摄建议

✅ **推荐做法:**
- 统一分辨率和帧率
- 统一拍摄时长 (10-15秒)
- 统一光线条件
- 避免自动曝光剧烈变化

❌ **避免事项:**
- 视频时长过短 (<5秒)
- 分辨率混乱
- 场景中物体快速移动
- 测试者手持技巧差异过大

### 3. 评测模式选择

| 你的需求 | 推荐评测方式 | 预计时长 |
|---------|-------------|---------|
| 只想快速对比 | FP评测 | 5-10分钟 |
| 需要全面报告 | 标准模式 | 20分钟 |
| 专业深度分析 | 专业模式 | 30分钟 |
| 只关心静态纹理 | Temporal Flickering + Imaging Quality | 8分钟 |
| 只关心防抖 | Motion Smoothness + FP | 15分钟 |

---

## 🐛 常见问题

### Q1: RAFT模型下载失败

**A:** 手动下载RAFT模型

```bash
cd pretrained/raft_model
wget https://github.com/princeton-vl/RAFT/releases/download/v1.0/raft-things.pth
mkdir -p ~/.cache/vbench/raft_model/models
mv raft-things.pth ~/.cache/vbench/raft_model/models/
```

### Q2: CUDA out of memory

**A:** 降低分辨率或使用CPU

```bash
# 使用CPU模式（非常慢）
python eval_flicker_penalty.py --video test.mp4 --device cpu

# 或预先降低视频分辨率
ffmpeg -i input.mp4 -vf scale=1280:720 output_720p.mp4
```

### Q3: 评测速度太慢

**A:** 优化建议

1. 确保使用GPU模式
2. 降低视频分辨率到1080p
3. 缩短测试视频时长到10秒
4. 使用fast模式而非professional模式

### Q4: Temporal Flickering分数异常低

**A:** 可能原因

- 视频包含相机运动（应使用Flicker Penalty）
- 场景本身包含运动物体
- 自动曝光变化剧烈

**解决方案:** 使用Flicker Penalty代替Temporal Flickering

---

## 📚 延伸阅读

- [完整评测指标文档](./纹理抖动评测指标分析.md) - 理论原理和详细说明
- [VBench官方文档](../../README.md) - VBench框架介绍
- [Flicker Penalty详细说明](../../vbench/worldscore/README_FlickerPenalty.md) - FP算法原理

---

## 📞 技术支持

如有问题，请查阅:

1. [VBench FAQ](../../README-FAQ.md)
2. [VBench Issues](https://github.com/Vchitect/VBench/issues)
3. 本目录下的详细文档

---

## 📝 更新日志

- **v1.0** (2026-01-06)
  - 初始版本
  - 实现多维度评测
  - 实现FP专项评测
  - 实现结果分析工具

---

**开发团队:** VBench纹理抖动评测专项组  
**最后更新:** 2026-01-06

