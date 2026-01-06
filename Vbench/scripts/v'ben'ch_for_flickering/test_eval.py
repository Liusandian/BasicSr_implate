#!/usr/bin/env python3
"""
纹理抖动评测 - 快速示例

原始需求:
- 评测Insta360/Sony/Canon/Huawei P80 Ultra/iPhone 16手持或相机拍摄的纹理抖动性
- 主要场景: 背景绿植、夜景、玻璃幕墙、草地等强纹理区域
- 评测静态场景的纹理闪烁和夜景场景的纹理抖动性

解决方案已实现，请查看以下文件：

📚 完整文档和使用指南:
  1. 纹理抖动评测指标分析.md - 详细的理论文档和评测指标说明
  2. README.md - 快速开始指南和使用方法

🔧 实现工具:
  1. texture_jitter_eval.py - 主评测脚本（多维度综合评测）
  2. eval_flicker_penalty.py - Flicker Penalty专项评测
  3. analyze_results.py - 结果分析和报告生成

使用示例见下方。
"""

import os
import sys

# 添加VBench路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def quick_demo():
    """快速演示示例"""
    
    print("=" * 80)
    print("纹理抖动评测工具 - 快速演示")
    print("=" * 80)
    print()
    
    print("📚 完整文档:")
    print("  - 纹理抖动评测指标分析.md  (详细理论和评测指标)")
    print("  - README.md                 (快速开始指南)")
    print()
    
    print("🚀 快速使用:")
    print()
    
    print("1️⃣  评测单个视频 (使用Flicker Penalty):")
    print("   python eval_flicker_penalty.py --video test.mp4")
    print()
    
    print("2️⃣  对比多个相机:")
    print("   python eval_flicker_penalty.py --compare \\")
    print("     --camera 'Canon':videos/canon.mp4 \\")
    print("     --camera 'Sony':videos/sony.mp4 \\")
    print("     --camera 'iPhone 16':videos/iphone16.mp4")
    print()
    
    print("3️⃣  多维度综合评测:")
    print("   python texture_jitter_eval.py \\")
    print("     --video_dir test_videos/grass \\")
    print("     --mode standard")
    print()
    
    print("4️⃣  生成评测报告:")
    print("   python analyze_results.py \\")
    print("     --results_dir results \\")
    print("     --output report.md")
    print()
    
    print("=" * 80)
    print("📊 推荐的评测维度:")
    print("=" * 80)
    print()
    
    dimensions = [
        ("Flicker Penalty (FP)", "⭐⭐⭐⭐⭐", "运动场景纹理闪烁（含运动补偿）", "最推荐"),
        ("Temporal Flickering", "⭐⭐⭐⭐⭐", "静态场景纹理闪烁", "静态专用"),
        ("Motion Smoothness", "⭐⭐⭐⭐⭐", "运动平滑度（防抖性能）", "防抖评测"),
        ("Imaging Quality", "⭐⭐⭐⭐", "成像质量（清晰度、噪点）", "辅助参考"),
        ("Background Consistency", "⭐⭐⭐⭐", "背景一致性", "辅助参考"),
    ]
    
    for name, stars, desc, note in dimensions:
        print(f"  {name:25s} {stars} - {desc}")
        print(f"  {'':25s} 💡 {note}")
        print()
    
    print("=" * 80)
    print("🎯 场景推荐:")
    print("=" * 80)
    print()
    
    scenarios = [
        ("🌿 草地/绿植", "FP + Temporal Flickering + Imaging Quality"),
        ("🌃 夜景场景", "FP + Imaging Quality + Background Consistency"),
        ("🏢 玻璃幕墙", "FP + Temporal Flickering"),
        ("🚶 手持运动", "Motion Smoothness + FP"),
    ]
    
    for scene, dims in scenarios:
        print(f"  {scene:15s} → {dims}")
    
    print()
    print("=" * 80)
    print("详细使用说明请查阅 README.md")
    print("=" * 80)


if __name__ == '__main__':
    quick_demo()
    
    print("\n运行完整评测示例? (需要测试视频)")
    print("1. 准备测试视频")
    print("2. 运行: python texture_jitter_eval.py --video_dir test_videos --mode fast")
    print("3. 或直接使用FP评测: python eval_flicker_penalty.py --video test.mp4")