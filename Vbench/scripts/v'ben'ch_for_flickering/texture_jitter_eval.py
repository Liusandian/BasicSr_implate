#!/usr/bin/env python3
"""
纹理抖动性评测主脚本

用于评测不同相机设备在各种场景下的纹理抖动性能。
支持三种评测模式：快速、标准、专业。

使用示例:
    # 快速评测
    python texture_jitter_eval.py --video_dir test_videos/grass --mode fast
    
    # 标准评测（推荐）
    python texture_jitter_eval.py --video_dir test_videos --mode standard --output_dir results
    
    # 专业评测（全维度）
    python texture_jitter_eval.py --video_dir test_videos --mode professional

作者: VBench纹理抖动评测专项组
日期: 2026-01-06
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

import torch
import numpy as np
from tqdm import tqdm

# 添加VBench路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from vbench import VBench


class TextureJitterEvaluator:
    """纹理抖动评测器"""
    
    # 评测模式配置
    EVAL_MODES = {
        'fast': {
            'name': '快速评测',
            'dimensions': ['temporal_flickering', 'motion_smoothness'],
            'description': '仅评测核心维度，适合快速对比'
        },
        'standard': {
            'name': '标准评测',
            'dimensions': [
                'temporal_flickering',
                'motion_smoothness',
                'imaging_quality',
                'background_consistency',
                'overall_consistency'
            ],
            'description': '全面评测，推荐使用'
        },
        'professional': {
            'name': '专业评测',
            'dimensions': [
                'temporal_flickering',
                'motion_smoothness',
                'imaging_quality',
                'background_consistency',
                'subject_consistency',
                'overall_consistency',
                'dynamic_degree'
            ],
            'description': '最全面的评测，适合深度分析'
        }
    }
    
    def __init__(self, device='cuda', output_dir='results', mode='standard'):
        """
        初始化评测器
        
        Args:
            device: 计算设备 ('cuda' 或 'cpu')
            output_dir: 结果输出目录
            mode: 评测模式 ('fast', 'standard', 'professional')
        """
        self.device = device
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if mode not in self.EVAL_MODES:
            raise ValueError(f"无效的评测模式: {mode}. 可选: {list(self.EVAL_MODES.keys())}")
        
        self.mode = mode
        self.dimensions = self.EVAL_MODES[mode]['dimensions']
        
        # 初始化VBench
        print(f"初始化VBench评测器 (模式: {self.EVAL_MODES[mode]['name']})...")
        vbench_full_info = os.path.join(
            os.path.dirname(__file__), '..', '..', 'vbench', 'VBench_full_info.json'
        )
        
        self.vbench = VBench(
            device=self.device,
            full_info_dir=vbench_full_info,
            output_path=str(self.output_dir)
        )
        
        print(f"✓ 评测器初始化完成")
        print(f"  - 设备: {self.device}")
        print(f"  - 模式: {self.EVAL_MODES[mode]['name']}")
        print(f"  - 维度: {', '.join(self.dimensions)}")
        print(f"  - 输出: {self.output_dir}")
    
    def evaluate_videos(self, video_dir: str, recursive: bool = True) -> Dict:
        """
        评测视频目录
        
        Args:
            video_dir: 视频目录路径
            recursive: 是否递归搜索子目录
        
        Returns:
            评测结果字典
        """
        video_dir = Path(video_dir)
        
        if not video_dir.exists():
            raise FileNotFoundError(f"视频目录不存在: {video_dir}")
        
        # 查找所有视频文件
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.MP4', '.AVI', '.MOV', '.MKV']
        
        if recursive:
            video_files = []
            for ext in video_extensions:
                video_files.extend(video_dir.rglob(f"*{ext}"))
        else:
            video_files = []
            for ext in video_extensions:
                video_files.extend(video_dir.glob(f"*{ext}"))
        
        video_files = sorted(set(video_files))
        
        if not video_files:
            print(f"⚠️  在 {video_dir} 中未找到视频文件")
            return {}
        
        print(f"\n找到 {len(video_files)} 个视频文件")
        print("=" * 80)
        
        # 评测每个维度
        all_results = {}
        start_time = time.time()
        
        for dimension in self.dimensions:
            print(f"\n评测维度: {dimension}")
            print("-" * 80)
            
            dimension_start = time.time()
            
            try:
                # 使用VBench评测
                avg_score, video_results = self.vbench.evaluate(
                    videos_path=str(video_dir),
                    name=f"{dimension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    dimension_list=[dimension],
                    mode='custom_input'
                )
                
                all_results[dimension] = {
                    'average_score': float(avg_score) if not isinstance(avg_score, (int, float)) else avg_score,
                    'video_results': video_results
                }
                
                dimension_time = time.time() - dimension_start
                print(f"✓ {dimension}: {avg_score:.4f} (耗时: {dimension_time:.1f}秒)")
                
            except Exception as e:
                print(f"✗ {dimension} 评测失败: {str(e)}")
                all_results[dimension] = {
                    'average_score': None,
                    'error': str(e)
                }
        
        total_time = time.time() - start_time
        
        # 保存结果
        results_file = self.output_dir / f"results_{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        final_results = {
            'metadata': {
                'mode': self.mode,
                'video_dir': str(video_dir),
                'num_videos': len(video_files),
                'dimensions': self.dimensions,
                'evaluation_time': total_time,
                'timestamp': datetime.now().isoformat()
            },
            'results': all_results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print(f"✓ 评测完成！")
        print(f"  - 总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
        print(f"  - 结果文件: {results_file}")
        
        return final_results
    
    def evaluate_single_video(self, video_path: str) -> Dict:
        """
        评测单个视频
        
        Args:
            video_path: 视频文件路径
        
        Returns:
            评测结果字典
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        print(f"\n评测视频: {video_path.name}")
        print("=" * 80)
        
        results = {}
        start_time = time.time()
        
        for dimension in self.dimensions:
            print(f"\n维度: {dimension}")
            
            try:
                # 创建临时目录包含单个视频
                temp_dir = self.output_dir / 'temp'
                temp_dir.mkdir(exist_ok=True)
                
                avg_score, video_results = self.vbench.evaluate(
                    videos_path=str(video_path.parent),
                    name=f"{dimension}_{video_path.stem}",
                    dimension_list=[dimension],
                    mode='custom_input'
                )
                
                results[dimension] = float(avg_score) if not isinstance(avg_score, (int, float)) else avg_score
                print(f"  Score: {results[dimension]:.4f}")
                
            except Exception as e:
                print(f"  ✗ 失败: {str(e)}")
                results[dimension] = None
        
        total_time = time.time() - start_time
        
        print("\n" + "=" * 80)
        print(f"评测完成 (耗时: {total_time:.1f}秒)")
        
        return results
    
    def compare_cameras(self, camera_videos: Dict[str, str]) -> Dict:
        """
        对比多个相机的性能
        
        Args:
            camera_videos: 相机名称到视频路径的映射
                例如: {'Canon': 'videos/canon.mp4', 'Sony': 'videos/sony.mp4'}
        
        Returns:
            对比结果
        """
        print(f"\n对比 {len(camera_videos)} 款相机")
        print("=" * 80)
        
        comparison_results = {}
        
        for camera_name, video_path in camera_videos.items():
            print(f"\n评测相机: {camera_name}")
            print("-" * 80)
            
            try:
                results = self.evaluate_single_video(video_path)
                comparison_results[camera_name] = results
            except Exception as e:
                print(f"✗ {camera_name} 评测失败: {str(e)}")
                comparison_results[camera_name] = None
        
        # 生成对比报告
        print("\n" + "=" * 80)
        print("对比结果汇总")
        print("=" * 80)
        
        for dimension in self.dimensions:
            print(f"\n{dimension}:")
            scores = []
            for camera_name in camera_videos.keys():
                if comparison_results[camera_name] and comparison_results[camera_name].get(dimension):
                    score = comparison_results[camera_name][dimension]
                    scores.append((camera_name, score))
            
            # 按分数排序
            scores.sort(key=lambda x: x[1], reverse=True)
            
            for rank, (camera_name, score) in enumerate(scores, 1):
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                print(f"  {medal} {camera_name:20s}: {score:.4f}")
        
        # 保存对比结果
        comparison_file = self.output_dir / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump({
                'mode': self.mode,
                'cameras': list(camera_videos.keys()),
                'dimensions': self.dimensions,
                'results': comparison_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 对比结果已保存: {comparison_file}")
        
        return comparison_results


def main():
    parser = argparse.ArgumentParser(
        description='纹理抖动性评测工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
评测模式说明:
  fast        - 快速评测 (2个维度, ~10分钟)
  standard    - 标准评测 (5个维度, ~20分钟) [推荐]
  professional- 专业评测 (7个维度, ~30分钟)

使用示例:
  # 标准评测
  python texture_jitter_eval.py --video_dir test_videos --mode standard
  
  # 快速评测单个视频
  python texture_jitter_eval.py --video_path video.mp4 --mode fast
  
  # 对比多个相机
  python texture_jitter_eval.py --compare \
    --camera Canon:videos/canon.mp4 \
    --camera Sony:videos/sony.mp4 \
    --camera iPhone:videos/iphone.mp4
        """
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--video_dir', type=str, help='视频目录路径')
    input_group.add_argument('--video_path', type=str, help='单个视频文件路径')
    input_group.add_argument('--compare', action='store_true', help='对比模式')
    
    # 对比模式参数
    parser.add_argument('--camera', action='append', help='相机配置 (格式: 名称:视频路径)')
    
    # 通用参数
    parser.add_argument('--mode', type=str, default='standard',
                       choices=['fast', 'standard', 'professional'],
                       help='评测模式 (默认: standard)')
    parser.add_argument('--output_dir', type=str, default='results',
                       help='结果输出目录 (默认: results)')
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='计算设备 (默认: cuda)')
    parser.add_argument('--recursive', action='store_true',
                       help='递归搜索子目录中的视频')
    
    args = parser.parse_args()
    
    # 检查CUDA可用性
    if args.device == 'cuda' and not torch.cuda.is_available():
        print("⚠️  CUDA不可用，切换到CPU模式")
        args.device = 'cpu'
    
    # 初始化评测器
    evaluator = TextureJitterEvaluator(
        device=args.device,
        output_dir=args.output_dir,
        mode=args.mode
    )
    
    # 执行评测
    try:
        if args.compare:
            # 对比模式
            if not args.camera or len(args.camera) < 2:
                print("❌ 对比模式至少需要2个相机配置")
                print("   使用方法: --camera 名称:路径 --camera 名称:路径 ...")
                return 1
            
            camera_videos = {}
            for camera_config in args.camera:
                if ':' not in camera_config:
                    print(f"❌ 无效的相机配置: {camera_config}")
                    print("   格式应为: 名称:视频路径")
                    return 1
                
                name, path = camera_config.split(':', 1)
                camera_videos[name] = path
            
            evaluator.compare_cameras(camera_videos)
            
        elif args.video_path:
            # 单个视频评测
            evaluator.evaluate_single_video(args.video_path)
            
        else:
            # 目录评测
            evaluator.evaluate_videos(args.video_dir, recursive=args.recursive)
        
        print("\n✓ 所有任务完成！")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断评测")
        return 1
    except Exception as e:
        print(f"\n❌ 评测失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

