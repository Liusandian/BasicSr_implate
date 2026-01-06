#!/usr/bin/env python3
"""
评测结果分析脚本

用于分析和可视化纹理抖动评测结果，生成对比报告。

使用示例:
    python analyze_results.py --results_dir results --output report.md
    python analyze_results.py --json results/comparison_*.json --format markdown

作者: VBench纹理抖动评测专项组
日期: 2026-01-06
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict

import numpy as np


class ResultsAnalyzer:
    """评测结果分析器"""
    
    # 维度中文名称映射
    DIMENSION_NAMES_CN = {
        'temporal_flickering': '时序闪烁',
        'motion_smoothness': '运动平滑度',
        'imaging_quality': '成像质量',
        'background_consistency': '背景一致性',
        'subject_consistency': '主体一致性',
        'overall_consistency': '整体一致性',
        'dynamic_degree': '动态程度',
        'flicker_penalty': '闪烁惩罚(FP)'
    }
    
    # 评分等级标准
    SCORE_GRADES = [
        (0.95, '优秀', '⭐⭐⭐⭐⭐'),
        (0.90, '良好', '⭐⭐⭐⭐'),
        (0.85, '中等', '⭐⭐⭐'),
        (0.80, '一般', '⭐⭐'),
        (0.00, '较差', '⭐')
    ]
    
    def __init__(self):
        pass
    
    def load_results(self, results_path: str) -> Dict:
        """加载评测结果JSON文件"""
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_results_dir(self, results_dir: str) -> List[Dict]:
        """加载目录中的所有结果文件"""
        results_dir = Path(results_dir)
        results_files = list(results_dir.glob('*.json'))
        
        results = []
        for file in results_files:
            try:
                data = self.load_results(file)
                data['_source_file'] = file.name
                results.append(data)
            except Exception as e:
                print(f"⚠️  无法加载 {file.name}: {str(e)}")
        
        return results
    
    def get_grade(self, score: float) -> Tuple[str, str]:
        """获取分数对应的等级和星级"""
        if score is None:
            return '无效', '-'
        
        for threshold, grade, stars in self.SCORE_GRADES:
            if score >= threshold:
                return grade, stars
        
        return '较差', '⭐'
    
    def generate_markdown_report(self, results: Dict, output_file: str = None) -> str:
        """生成Markdown格式的评测报告"""
        
        report_lines = []
        
        # 标题
        report_lines.append("# 纹理抖动评测报告\n")
        report_lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append("---\n")
        
        # 元数据
        if 'metadata' in results:
            meta = results['metadata']
            report_lines.append("## 📋 评测信息\n")
            report_lines.append(f"- **评测模式:** {meta.get('mode', 'unknown')}")
            report_lines.append(f"- **视频目录:** `{meta.get('video_dir', 'N/A')}`")
            report_lines.append(f"- **视频数量:** {meta.get('num_videos', 'N/A')}")
            report_lines.append(f"- **评测维度:** {', '.join(meta.get('dimensions', []))}")
            eval_time = meta.get('evaluation_time', 0)
            report_lines.append(f"- **评测耗时:** {eval_time:.1f}秒 ({eval_time/60:.1f}分钟)")
            report_lines.append(f"- **评测时间:** {meta.get('timestamp', 'N/A')}\n")
            report_lines.append("---\n")
        
        # 汇总结果
        if 'results' in results:
            report_lines.append("## 📊 评测结果汇总\n")
            
            # 创建表格
            report_lines.append("| 评测维度 | 平均分数 | 评级 | 星级 |")
            report_lines.append("|---------|---------|------|------|")
            
            dimension_scores = []
            
            for dimension, data in results['results'].items():
                dim_name = self.DIMENSION_NAMES_CN.get(dimension, dimension)
                
                if isinstance(data, dict):
                    score = data.get('average_score')
                else:
                    score = data
                
                if score is not None:
                    grade, stars = self.get_grade(score)
                    dimension_scores.append((dim_name, score))
                    report_lines.append(f"| {dim_name} | {score:.4f} | {grade} | {stars} |")
                else:
                    report_lines.append(f"| {dim_name} | N/A | 无效 | - |")
            
            report_lines.append("")
            
            # 计算综合得分
            if dimension_scores:
                avg_score = np.mean([s for _, s in dimension_scores])
                grade, stars = self.get_grade(avg_score)
                
                report_lines.append("### 综合评分\n")
                report_lines.append(f"**综合得分:** {avg_score:.4f} | **评级:** {grade} {stars}\n")
            
            report_lines.append("---\n")
        
        # 对比模式特殊处理
        if 'cameras' in results:
            report_lines.append("## 🎯 相机对比结果\n")
            
            cameras = results['cameras']
            dimensions = results.get('dimensions', [])
            comparison_results = results['results']
            
            # 为每个维度创建对比表格
            for dimension in dimensions:
                dim_name = self.DIMENSION_NAMES_CN.get(dimension, dimension)
                report_lines.append(f"### {dim_name}\n")
                
                # 收集所有相机的分数
                camera_scores = []
                for camera in cameras:
                    camera_result = comparison_results.get(camera)
                    if camera_result and dimension in camera_result:
                        score = camera_result[dimension]
                        if score is not None:
                            camera_scores.append((camera, score))
                
                # 排序
                camera_scores.sort(key=lambda x: x[1], reverse=True)
                
                # 生成表格
                report_lines.append("| 排名 | 相机型号 | 分数 | 评级 | 星级 |")
                report_lines.append("|-----|---------|------|------|------|")
                
                for rank, (camera, score) in enumerate(camera_scores, 1):
                    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}"
                    grade, stars = self.get_grade(score)
                    report_lines.append(f"| {medal} | {camera} | {score:.4f} | {grade} | {stars} |")
                
                report_lines.append("")
            
            # 综合排名
            report_lines.append("### 🏆 综合排名\n")
            
            camera_avg_scores = []
            for camera in cameras:
                camera_result = comparison_results.get(camera)
                if camera_result:
                    scores = [camera_result[d] for d in dimensions if camera_result.get(d) is not None]
                    if scores:
                        avg = np.mean(scores)
                        camera_avg_scores.append((camera, avg))
            
            camera_avg_scores.sort(key=lambda x: x[1], reverse=True)
            
            report_lines.append("| 排名 | 相机型号 | 综合得分 | 评级 | 星级 |")
            report_lines.append("|-----|---------|---------|------|------|")
            
            for rank, (camera, score) in enumerate(camera_avg_scores, 1):
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}"
                grade, stars = self.get_grade(score)
                report_lines.append(f"| {medal} | {camera} | {score:.4f} | {grade} | {stars} |")
            
            report_lines.append("")
            report_lines.append("---\n")
        
        # 详细结果
        if 'results' in results and any(isinstance(v, dict) and 'video_results' in v for v in results['results'].values()):
            report_lines.append("## 📹 各视频详细结果\n")
            
            for dimension, data in results['results'].items():
                if isinstance(data, dict) and 'video_results' in data:
                    dim_name = self.DIMENSION_NAMES_CN.get(dimension, dimension)
                    video_results = data['video_results']
                    
                    report_lines.append(f"### {dim_name}\n")
                    report_lines.append("| 视频文件 | 分数 | 评级 |")
                    report_lines.append("|---------|------|------|")
                    
                    for video_result in video_results:
                        video_path = video_result.get('video_path', 'N/A')
                        video_name = Path(video_path).name if video_path != 'N/A' else 'N/A'
                        score = video_result.get('video_results')
                        
                        if score is not None:
                            grade, _ = self.get_grade(score)
                            report_lines.append(f"| `{video_name}` | {score:.4f} | {grade} |")
                        else:
                            report_lines.append(f"| `{video_name}` | N/A | 无效 |")
                    
                    report_lines.append("")
            
            report_lines.append("---\n")
        
        # 评分说明
        report_lines.append("## 📝 评分说明\n")
        report_lines.append("### 分数范围: 0.0 - 1.0 (越高越好)\n")
        report_lines.append("| 分数范围 | 评级 | 星级 | 说明 |")
        report_lines.append("|---------|------|------|------|")
        report_lines.append("| 0.95 - 1.0 | 优秀 | ⭐⭐⭐⭐⭐ | 纹理极其稳定，无可见闪烁 |")
        report_lines.append("| 0.90 - 0.95 | 良好 | ⭐⭐⭐⭐ | 纹理稳定，轻微闪烁 |")
        report_lines.append("| 0.85 - 0.90 | 中等 | ⭐⭐⭐ | 可见闪烁，但可接受 |")
        report_lines.append("| 0.80 - 0.85 | 一般 | ⭐⭐ | 明显闪烁 |")
        report_lines.append("| < 0.80 | 较差 | ⭐ | 严重闪烁，需改进 |")
        report_lines.append("")
        
        # 维度说明
        report_lines.append("### 维度说明\n")
        report_lines.append("- **时序闪烁**: 静态场景下的纹理稳定性（不含运动补偿）")
        report_lines.append("- **闪烁惩罚(FP)**: 运动场景下的纹理稳定性（含运动补偿）")
        report_lines.append("- **运动平滑度**: 防抖性能，运动连续性")
        report_lines.append("- **成像质量**: 清晰度、噪点、色彩等综合质量")
        report_lines.append("- **背景一致性**: 背景区域的时序一致性")
        report_lines.append("- **主体一致性**: 主体对象的时序一致性")
        report_lines.append("- **整体一致性**: 全局时序一致性")
        report_lines.append("- **动态程度**: 视频的运动幅度\n")
        
        report_lines.append("---\n")
        report_lines.append(f"*报告生成工具: VBench纹理抖动评测分析器 v1.0*\n")
        
        report = "\n".join(report_lines)
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✓ 报告已保存: {output_file}")
        
        return report
    
    def generate_comparison_chart(self, results: Dict) -> str:
        """生成ASCII对比图表"""
        
        if 'cameras' not in results:
            return ""
        
        cameras = results['cameras']
        dimensions = results.get('dimensions', [])
        comparison_results = results['results']
        
        chart_lines = []
        chart_lines.append("\n" + "=" * 100)
        chart_lines.append("相机性能对比图表")
        chart_lines.append("=" * 100)
        
        for dimension in dimensions:
            dim_name = self.DIMENSION_NAMES_CN.get(dimension, dimension)
            chart_lines.append(f"\n{dim_name}:")
            
            # 收集分数
            camera_scores = []
            for camera in cameras:
                camera_result = comparison_results.get(camera)
                if camera_result and dimension in camera_result:
                    score = camera_result[dimension]
                    if score is not None:
                        camera_scores.append((camera, score))
            
            # 找出最大分数用于归一化
            if camera_scores:
                max_score = max(s for _, s in camera_scores)
                
                # 按分数排序
                camera_scores.sort(key=lambda x: x[1], reverse=True)
                
                for camera, score in camera_scores:
                    bar_length = int((score / max_score) * 50) if max_score > 0 else 0
                    bar = "█" * bar_length
                    chart_lines.append(f"  {camera:15s} {score:.4f} |{bar}")
        
        chart_lines.append("=" * 100)
        
        return "\n".join(chart_lines)


def main():
    parser = argparse.ArgumentParser(
        description='评测结果分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--results_dir', type=str, help='结果目录路径')
    input_group.add_argument('--json', type=str, help='单个JSON结果文件')
    
    # 输出参数
    parser.add_argument('--output', type=str, help='输出报告文件路径 (默认: report.md)')
    parser.add_argument('--format', type=str, default='markdown',
                       choices=['markdown', 'text'],
                       help='输出格式 (默认: markdown)')
    parser.add_argument('--show_chart', action='store_true',
                       help='显示ASCII对比图表')
    
    args = parser.parse_args()
    
    analyzer = ResultsAnalyzer()
    
    try:
        # 加载结果
        if args.json:
            results = analyzer.load_results(args.json)
            default_output = Path(args.json).stem + '_report.md'
        else:
            # 加载目录中最新的结果
            all_results = analyzer.load_results_dir(args.results_dir)
            if not all_results:
                print(f"❌ 在 {args.results_dir} 中未找到结果文件")
                return 1
            
            # 使用最新的结果
            results = max(all_results, key=lambda x: x.get('metadata', {}).get('timestamp', ''))
            default_output = 'report.md'
            print(f"✓ 找到 {len(all_results)} 个结果文件，使用最新的结果")
        
        # 设置输出文件
        output_file = args.output or default_output
        
        # 生成报告
        if args.format == 'markdown':
            report = analyzer.generate_markdown_report(results, output_file)
            print(f"\n预览:\n")
            print(report[:1000] + "..." if len(report) > 1000 else report)
        
        # 显示对比图表
        if args.show_chart:
            chart = analyzer.generate_comparison_chart(results)
            print(chart)
        
        print(f"\n✓ 分析完成！")
        return 0
        
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

