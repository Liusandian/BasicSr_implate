# 纹理抖动评测工具套件 - 文件索引

## 📑 快速导航

### 🚀 新手入门（按顺序阅读）

1. **[README.md](./README.md)** ⭐ 必读
   - 快速开始指南
   - 工具介绍和使用方法
   - 常见问题解答
   - **推荐阅读时间:** 15分钟

2. **[test_eval.py](./test_eval.py)** 📺 演示
   - 快速演示脚本
   - 查看工具概览和使用提示
   - **运行:** `python test_eval.py`

3. **[使用示例.md](./使用示例.md)** 📖 案例
   - 完整使用案例
   - 不同场景的评测方法
   - 高级用法示例
   - **推荐阅读时间:** 30分钟

---

### 📚 理论学习（深入理解）

4. **[纹理抖动评测指标分析.md](./纹理抖动评测指标分析.md)** 🎓 核心文档
   - 详细的评测指标说明
   - 技术原理和算法介绍
   - 适用场景和最佳实践
   - **推荐阅读时间:** 45-60分钟

---

### 🔧 实用工具（日常使用）

5. **[eval_flicker_penalty.py](./eval_flicker_penalty.py)** ⚡ 快速评测
   - Flicker Penalty专项评测
   - **适用:** 运动场景、手持拍摄
   - **推荐度:** ⭐⭐⭐⭐⭐ 最高
   ```bash
   # 快速使用
   python eval_flicker_penalty.py --video test.mp4
   
   # 对比多个相机
   python eval_flicker_penalty.py --compare \
       --camera "Canon":canon.mp4 \
       --camera "Sony":sony.mp4
   ```

6. **[texture_jitter_eval.py](./texture_jitter_eval.py)** 🎯 综合评测
   - 多维度综合评测主脚本
   - **适用:** 全面评测、正式报告
   - **模式:** fast / standard / professional
   ```bash
   # 标准评测
   python texture_jitter_eval.py \
       --video_dir test_videos/grass \
       --mode standard
   ```

7. **[analyze_results.py](./analyze_results.py)** 📊 结果分析
   - 生成评测报告
   - **输出:** Markdown格式报告
   ```bash
   # 生成报告
   python analyze_results.py \
       --results_dir results \
       --output report.md
   ```

---

### 🛠️ 批量处理（自动化）

8. **[batch_eval.sh](./batch_eval.sh)** 🐧 Linux/Mac批量脚本
   - 自动评测多个场景
   - **适用:** Linux / macOS
   ```bash
   chmod +x batch_eval.sh
   ./batch_eval.sh
   ```

9. **[batch_eval.bat](./batch_eval.bat)** 🪟 Windows批量脚本
   - 自动评测多个场景
   - **适用:** Windows
   ```cmd
   batch_eval.bat
   ```

---

### 📝 项目文档（了解项目）

10. **[实现总结.md](./实现总结.md)** 📋 项目总结
    - 项目完成概览
    - 技术实现细节
    - 使用场景映射
    - 性能基准数据

11. **[INDEX.md](./INDEX.md)** 📑 本文档
    - 文件索引和导航

---

## 🎯 场景导航（我该用什么工具？）

### 场景1: 我是新手，想快速上手

**推荐流程:**
1. 阅读 `README.md` (15分钟)
2. 运行 `python test_eval.py` (查看演示)
3. 准备一个测试视频
4. 运行 `python eval_flicker_penalty.py --video test.mp4`

**预计时间:** 30分钟

---

### 场景2: 我需要对比5款相机在草地场景的表现

**推荐工具:** `eval_flicker_penalty.py`

**操作步骤:**
```bash
# 1. 准备视频
# test_videos/grass/
#   ├── insta360.mp4
#   ├── sony.mp4
#   ├── canon.mp4
#   ├── huawei.mp4
#   └── iphone16.mp4

# 2. 运行对比评测
python eval_flicker_penalty.py --compare \
    --camera "Insta360":test_videos/grass/insta360.mp4 \
    --camera "Sony":test_videos/grass/sony.mp4 \
    --camera "Canon":test_videos/grass/canon.mp4 \
    --camera "Huawei":test_videos/grass/huawei.mp4 \
    --camera "iPhone16":test_videos/grass/iphone16.mp4
```

**预计时间:** 5-10分钟

---

### 场景3: 我需要全面评测并生成专业报告

**推荐工具:** `texture_jitter_eval.py` + `analyze_results.py`

**操作步骤:**
```bash
# 1. 多维度评测
python texture_jitter_eval.py \
    --video_dir test_videos/grass \
    --mode standard \
    --output_dir results/grass

# 2. 生成报告
python analyze_results.py \
    --results_dir results/grass \
    --output reports/grass_report.md
```

**预计时间:** 20-30分钟

---

### 场景4: 我需要评测多个场景（草地、夜景、玻璃等）

**推荐工具:** `batch_eval.sh` / `batch_eval.bat`

**操作步骤:**
```bash
# Linux/Mac
./batch_eval.sh

# Windows
batch_eval.bat
```

**预计时间:** 2-4小时

---

### 场景5: 我只关心防抖性能

**推荐工具:** `texture_jitter_eval.py` (fast模式)

**操作步骤:**
```bash
python texture_jitter_eval.py \
    --video_dir test_videos/walking \
    --mode fast \
    --output_dir results/walking
```

**重点维度:**
- Motion Smoothness (运动平滑度)
- Flicker Penalty (闪烁惩罚)

**预计时间:** 10分钟

---

## 📊 工具对比表

| 工具 | 适用场景 | 评测速度 | 结果详细度 | 易用性 | 推荐度 |
|-----|---------|---------|-----------|--------|--------|
| `eval_flicker_penalty.py` | 运动场景、快速对比 | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | ⚡⚡⚡⚡⚡ | 🔥🔥🔥🔥🔥 |
| `texture_jitter_eval.py` (fast) | 快速全面评测 | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 🔥🔥🔥🔥 |
| `texture_jitter_eval.py` (standard) | 正式评测报告 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 🔥🔥🔥🔥🔥 |
| `texture_jitter_eval.py` (professional) | 深度研究分析 | ⚡⚡ | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | 🔥🔥🔥 |
| `batch_eval.sh/.bat` | 批量自动化 | ⚡ | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡⚡ | 🔥🔥🔥🔥 |

---

## 🎓 学习路径

### 路径A: 快速实战派（1小时）

```
README.md (15分钟)
    ↓
运行 test_eval.py (5分钟)
    ↓
准备测试视频 (10分钟)
    ↓
使用 eval_flicker_penalty.py (10分钟)
    ↓
查看结果 (5分钟)
    ↓
阅读 使用示例.md 相关部分 (15分钟)
```

### 路径B: 理论实践派（3小时）

```
README.md (15分钟)
    ↓
纹理抖动评测指标分析.md (60分钟)
    ↓
使用示例.md (30分钟)
    ↓
实践评测 (45分钟)
    ↓
分析结果 (30分钟)
```

### 路径C: 完整掌握派（1天）

```
所有文档通读 (3小时)
    ↓
准备完整测试集 (2小时)
    ↓
运行所有工具 (2小时)
    ↓
批量评测实践 (2小时)
    ↓
高级功能探索 (1小时)
```

---

## 💡 快速决策树

```
开始
  │
  ├─ 只有一个视频？
  │   └─ YES → 使用 eval_flicker_penalty.py
  │   └─ NO → 继续
  │
  ├─ 需要对比多个相机？
  │   └─ YES → 使用 eval_flicker_penalty.py --compare
  │   └─ NO → 继续
  │
  ├─ 需要详细多维度评测？
  │   └─ YES → 使用 texture_jitter_eval.py --mode standard
  │   └─ NO → 继续
  │
  ├─ 需要评测多个场景？
  │   └─ YES → 使用 batch_eval.sh/.bat
  │   └─ NO → 继续
  │
  └─ 已有评测结果，需要生成报告？
      └─ YES → 使用 analyze_results.py
```

---

## 📞 获取帮助

### 问题1: 我不知道从哪里开始

**答:** 先阅读 `README.md`，然后运行 `python test_eval.py`

### 问题2: 评测太慢了怎么办

**答:** 
1. 使用 `eval_flicker_penalty.py` (最快)
2. 降低视频分辨率到1080p
3. 使用更强的GPU

### 问题3: 结果怎么解读

**答:** 阅读 `纹理抖动评测指标分析.md` 的"输出解读"部分

### 问题4: 我的场景不在示例中

**答:** 
1. 查看 `使用示例.md` 的高级用法部分
2. 参考类似场景，自行调整维度配置

### 问题5: 遇到错误怎么办

**答:**
1. 检查 `README.md` 的常见问题部分
2. 查看错误日志
3. 确认环境和依赖是否正确安装

---

## 🔗 外部资源

### VBench相关

- [VBench GitHub](https://github.com/Vchitect/VBench)
- [VBench论文](https://arxiv.org/abs/2311.17982)
- [VBench文档](../../README.md)
- [VBench FAQ](../../README-FAQ.md)

### 算法相关

- [RAFT光流算法](https://github.com/princeton-vl/RAFT)
- [AMT插帧算法](https://github.com/MCG-NKU/AMT)
- [Flicker Penalty详解](../../vbench/worldscore/README_FlickerPenalty.md)

---

## 📈 版本信息

- **当前版本:** v1.0
- **发布日期:** 2026-01-06
- **开发团队:** VBench纹理抖动评测专项组
- **最后更新:** 2026-01-06

---

## 🎉 快速启动命令

```bash
# 1. 查看演示
python test_eval.py

# 2. 快速评测单个视频
python eval_flicker_penalty.py --video test.mp4

# 3. 对比多个相机
python eval_flicker_penalty.py --compare \
    --camera "Camera1":video1.mp4 \
    --camera "Camera2":video2.mp4

# 4. 标准评测
python texture_jitter_eval.py \
    --video_dir test_videos \
    --mode standard

# 5. 生成报告
python analyze_results.py \
    --results_dir results \
    --output report.md

# 6. 批量评测
./batch_eval.sh    # Linux/Mac
batch_eval.bat     # Windows
```

---

**开始你的评测之旅！** 🚀

有任何问题，先查阅 `README.md` 和 `纹理抖动评测指标分析.md`

