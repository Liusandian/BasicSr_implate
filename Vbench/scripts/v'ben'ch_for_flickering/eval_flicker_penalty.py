#!/usr/bin/env python3
"""
Flicker Penalty (FP) 专项评测脚本

用于评测视频的纹理闪烁程度，支持运动补偿。
这是评测运动场景纹理稳定性的最佳工具。

使用示例:
    # 评测单个视频
    python eval_flicker_penalty.py --video video.mp4
    
    # 批量评测目录
    python eval_flicker_penalty.py --video_dir test_videos/grass
    
    # 对比多个相机
    python eval_flicker_penalty.py --compare \
        --camera Canon:videos/canon.mp4 \
        --camera Sony:videos/sony.mp4

作者: VBench纹理抖动评测专项组
日期: 2026-01-06
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

import torch

# 添加VBench路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from vbench.worldscore.flicker_penalty import FlickerPenalty, evaluate_video
except ImportError:
    print("❌ 无法导入Flicker Penalty模块")
    print("   请确保已安装VBench并下载RAFT模型")
    print("   运行: cd pretrained/raft_model && bash download.sh")
    sys.exit(1)


class FlickerPenaltyEvaluator:
    """Flicker Penalty评测器"""
    
    # 评分等级
    SCORE_GRADES = [
        (0.95, '优秀', '⭐⭐⭐⭐⭐', '专业级稳定，无可见闪烁'),
        (0.90, '良好', '⭐⭐⭐⭐', '稳定，轻微闪烁'),
        (0.85, '中等', '⭐⭐⭐', '可见轻微闪烁'),
        (0.80, '一般', '⭐⭐', '明显闪烁和抖动'),
        (0.00, '较差', '⭐', '严重闪烁')
    ]
    
    def __init__(self, device='cuda', raft_model_path=None):
        """
        初始化评测器
        
        Args:
            device: 计算设备 ('cuda' 或 'cpu')
            raft_model_path: RAFT模型路径 (默认自动检测)
        """
        self.device = device
        
        print("初始化Flicker Penalty评测器...")
        print(f"  - 设备: {device}")
        
        if raft_model_path is None:
            # 自动查找RAFT模型
            raft_model_path = os.path.expanduser(
                "~/.cache/vbench/raft_model/models/raft-things.pth"
            )
        
        if not os.path.exists(raft_model_path):
            print(f"❌ RAFT模型未找到: {raft_model_path}")
            print("   请运行: cd pretrained/raft_model && bash download.sh")
            raise FileNotFoundError(f"RAFT模型不存在: {raft_model_path}")
        
        print(f"  - RAFT模型: {raft_model_path}")
        
        self.raft_model_path = raft_model_path
        self.fp_evaluator = FlickerPenalty(device=device, raft_model_path=raft_model_path)
        
        print("✓ 评测器初始化完成")
    
    def get_grade(self, score: float):
        """获取分数对应的等级"""
        for threshold, grade, stars, desc in self.SCORE_GRADES:
            if score >= threshold:
                return grade, stars, desc
        return '较差', '⭐', '严重闪烁'
    
    def evaluate_single(self, video_path: str) -> float:
        """评测单个视频"""
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        print(f"\n评测视频: {video_path.name}")
        print("-" * 80)
        
        try:
            score = self.fp_evaluator.evaluate(str(video_path))
            grade, stars, desc = self.get_grade(score)
            
            print(f"  FP Score: {score:.4f}")
            print(f"  评级: {grade} {stars}")
            print(f"  描述: {desc}")
            
            return score
            
        except Exception as e:
            print(f"  ✗ 评测失败: {str(e)}")
            raise
    
    def evaluate_directory(self, video_dir: str, recursive: bool = False) -> Dict:
        """批量评测目录中的视频"""
        video_dir = Path(video_dir)
        
        if not video_dir.exists():
            raise FileNotFoundError(f"目录不存在: {video_dir}")
        
        # 查找视频文件
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
        
        results = {}
        
        for video_file in video_files:
            try:
                score = self.evaluate_single(video_file)
                results[video_file.name] = score
            except Exception as e:
                print(f"✗ {video_file.name} 失败: {str(e)}")
                results[video_file.name] = None
        
        # 统计
        valid_scores = [s for s in results.values() if s is not None]
        
        if valid_scores:
            print("\n" + "=" * 80)
            print("批量评测统计")
            print("=" * 80)
            print(f"  - 成功: {len(valid_scores)}/{len(video_files)}")
            print(f"  - 平均分数: {sum(valid_scores)/len(valid_scores):.4f}")
            print(f"  - 最高分数: {max(valid_scores):.4f}")
            print(f"  - 最低分数: {min(valid_scores):.4f}")
        
        return results
    
    def compare_cameras(self, camera_videos: Dict[str, str]) -> Dict:
        """对比多个相机"""
        print(f"\n对比 {len(camera_videos)} 款相机")
        print("=" * 80)
        
        results = {}
        
        for camera_name, video_path in camera_videos.items():
            print(f"\n【{camera_name}】")
            
            try:
                score = self.evaluate_single(video_path)
                results[camera_name] = score
            except Exception as e:
                print(f"✗ 失败: {str(e)}")
                results[camera_name] = None
        
        # 生成排名
        print("\n" + "=" * 80)
        print("对比结果 - Flicker Penalty (FP) 排名")
        print("=" * 80)
        
        valid_results = [(name, score) for name, score in results.items() if score is not None]
        valid_results.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (camera_name, score) in enumerate(valid_results, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            grade, stars, desc = self.get_grade(score)
            
            print(f"{medal} {camera_name:20s}: {score:.4f} | {grade} {stars}")
            print(f"   {desc}")
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description='Flicker Penalty (FP) 专项评测工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
评测说明:
  Flicker Penalty (FP) 是评测纹理闪烁的高级指标，使用RAFT光流进行运动补偿。
  
  适用场景:
    - ✓ 手持相机拍摄 (有运动补偿)
    - ✓ 运动场景 (走路、摇镜头等)
    - ✓ 静态场景
    - ✓ 夜景、草地、玻璃幕墙等强纹理场景
  
  分数范围: 0.0 - 1.0 (越高越好)
    0.95-1.0  : 优秀 ⭐⭐⭐⭐⭐
    0.90-0.95 : 良好 ⭐⭐⭐⭐
    0.85-0.90 : 中等 ⭐⭐⭐
    0.80-0.85 : 一般 ⭐⭐
    < 0.80    : 较差 ⭐

使用示例:
  # 评测单个视频
  python eval_flicker_penalty.py --video test.mp4
  
  # 批量评测
  python eval_flicker_penalty.py --video_dir videos/grass
  
  # 对比相机
  python eval_flicker_penalty.py --compare \
    --camera "Canon R6":videos/canon.mp4 \
    --camera "Sony A7":videos/sony.mp4 \
    --camera "iPhone 16":videos/iphone.mp4
  
  # 保存结果
  python eval_flicker_penalty.py --video_dir videos \
    --output results/fp_results.json
        """
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--video', type=str, help='单个视频文件')
    input_group.add_argument('--video_dir', type=str, help='视频目录')
    input_group.add_argument('--compare', action='store_true', help='对比模式')
    
    # 对比模式参数
    parser.add_argument('--camera', action='append', help='相机配置 (格式: 名称:视频路径)')
    
    # 通用参数
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='计算设备 (默认: cuda)')
    parser.add_argument('--raft_model', type=str, help='RAFT模型路径 (可选)')
    parser.add_argument('--output', type=str, help='结果输出文件 (JSON格式)')
    parser.add_argument('--recursive', action='store_true', help='递归搜索子目录')
    
    args = parser.parse_args()
    
    # 检查CUDA
    if args.device == 'cuda' and not torch.cuda.is_available():
        print("⚠️  CUDA不可用，切换到CPU模式")
        args.device = 'cpu'
    
    try:
        # 初始化评测器
        evaluator = FlickerPenaltyEvaluator(
            device=args.device,
            raft_model_path=args.raft_model
        )
        
        # 执行评测
        if args.compare:
            # 对比模式
            if not args.camera or len(args.camera) < 2:
                print("❌ 对比模式至少需要2个相机配置")
                print("   使用: --camera 名称:路径 --camera 名称:路径")
                return 1
            
            camera_videos = {}
            for camera_config in args.camera:
                if ':' not in camera_config:
                    print(f"❌ 无效配置: {camera_config}")
                    print("   格式: 名称:视频路径")
                    return 1
                
                name, path = camera_config.split(':', 1)
                camera_videos[name] = path
            
            results = evaluator.compare_cameras(camera_videos)
            
            # 保存结果
            if args.output:
                output_data = {
                    'mode': 'comparison',
                    'cameras': list(camera_videos.keys()),
                    'results': results,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n✓ 结果已保存: {args.output}")
        
        elif args.video:
            # 单个视频
            score = evaluator.evaluate_single(args.video)
            
            if args.output:
                output_data = {
                    'mode': 'single',
                    'video': args.video,
                    'fp_score': score,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n✓ 结果已保存: {args.output}")
        
        else:
            # 目录批量评测
            results = evaluator.evaluate_directory(args.video_dir, args.recursive)
            
            if args.output:
                output_data = {
                    'mode': 'batch',
                    'video_dir': args.video_dir,
                    'results': results,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n✓ 结果已保存: {args.output}")
        
        print("\n✓ 所有任务完成！")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

