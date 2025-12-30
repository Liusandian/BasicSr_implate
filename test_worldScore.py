"""
Flicker Penalty (FP) 计算模块

基于Li Feifei WorldScore框架的思想，实现视频纹理闪烁程度的评估。
使用RAFT光流进行运动补偿，通过计算预测误差来量化闪烁程度。

主要步骤：
1. 光流估计 - 使用RAFT计算相邻帧间光流
2. 运动补偿生成预测帧 - 基于光流进行帧间预测
3. 帧间误差计算 - 计算预测帧与实际帧的误差
4. 全局FP聚合 - 计算视频级别的闪烁惩罚分数
"""

import os
import cv2
import torch
import numpy as np
from tqdm import tqdm
import torch.nn.functional as F
from pathlib import Path

from vbench.third_party.RAFT.core.raft import RAFT
from vbench.third_party.RAFT.core.utils_core.utils import InputPadder


class FlickerPenaltyCalculator:
    """Flicker Penalty 计算器"""

    def __init__(self, model_path=None, device='cuda'):
        """
        初始化FP计算器

        Args:
            model_path (str): RAFT模型路径，如果为None则使用默认路径
            device (str): 计算设备
        """
        self.device = device
        self.model = None
        self.model_path = model_path or self._get_default_model_path()
        self.load_model()

    def _get_default_model_path(self):
        """获取默认RAFT模型路径"""
        cache_dir = os.path.join(os.path.dirname(__file__), '../../pretrained/raft_model')
        return os.path.join(cache_dir, 'models/raft-things.pth')

    def load_model(self):
        """加载RAFT模型"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"RAFT model not found at {self.model_path}")

        # 初始化RAFT参数
        args = type('Args', (), {})()
        args.small = False
        args.mixed_precision = False
        args.alternate_corr = False

        self.model = torch.nn.DataParallel(RAFT(args))
        self.model.load_state_dict(torch.load(self.model_path))
        self.model = self.model.module
        self.model.to(self.device)
        self.model.eval()
        print(f"RAFT model loaded from {self.model_path}")

    def load_video_frames(self, video_path, max_frames=None):
        """
        加载视频帧

        Args:
            video_path (str): 视频路径
            max_frames (int): 最大帧数限制，None表示加载全部

        Returns:
            list: RGB帧列表，形状为[H, W, 3]
        """
        frames = []
        video = cv2.VideoCapture(video_path)

        if not video.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        frame_count = 0
        while video.isOpened():
            success, frame = video.read()
            if not success:
                break

            # 转换为RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

        video.release()

        if len(frames) < 2:
            raise ValueError(f"Video must have at least 2 frames, got {len(frames)}")

        print(f"Loaded {len(frames)} frames from {video_path}")
        return frames

    def frames_to_tensor(self, frames):
        """
        将帧转换为PyTorch张量

        Args:
            frames (list): RGB帧列表

        Returns:
            torch.Tensor: 形状为[N, 3, H, W]的张量
        """
        tensor_frames = []
        for frame in frames:
            # 转换为float32并归一化到[0,1]
            frame_tensor = torch.from_numpy(frame.astype(np.float32)).permute(2, 0, 1)
            frame_tensor = frame_tensor / 255.0
            tensor_frames.append(frame_tensor)

        return torch.stack(tensor_frames).to(self.device)

    def compute_optical_flow(self, frame1, frame2):
        """
        计算两帧间的光流

        Args:
            frame1 (torch.Tensor): 第一帧 [3, H, W]
            frame2 (torch.Tensor): 第二帧 [3, H, W]

        Returns:
            torch.Tensor: 光流 [2, H, W]
        """
        with torch.no_grad():
            padder = InputPadder(frame1.shape)
            frame1_padded, frame2_padded = padder.pad(frame1.unsqueeze(0), frame2.unsqueeze(0))

            _, flow_up = self.model(frame1_padded, frame2_padded, iters=20, test_mode=True)
            flow_up = padder.unpad(flow_up)

        return flow_up.squeeze(0)

    def motion_compensation(self, frame, flow):
        """
        运动补偿生成预测帧

        Args:
            frame (torch.Tensor): 参考帧 [3, H, W]
            flow (torch.Tensor): 光流 [2, H, W]

        Returns:
            torch.Tensor: 预测帧 [3, H, W]
        """
        # 创建坐标网格
        h, w = frame.shape[1:3]
        coords = torch.meshgrid(torch.arange(h, device=self.device),
                               torch.arange(w, device=self.device),
                               indexing='ij')
        coords = torch.stack(coords[::-1], dim=-1).float()  # [H, W, 2]

        # 应用光流变换
        warped_coords = coords + flow.permute(1, 2, 0)  # [H, W, 2]

        # 归一化坐标到[-1, 1]
        warped_coords[..., 0] = 2.0 * warped_coords[..., 0] / (w - 1) - 1.0
        warped_coords[..., 1] = 2.0 * warped_coords[..., 1] / (h - 1) - 1.0

        # 进行双线性采样
        warped_coords = warped_coords.unsqueeze(0)  # [1, H, W, 2]
        predicted_frame = F.grid_sample(frame.unsqueeze(0),
                                       warped_coords,
                                       mode='bilinear',
                                       padding_mode='border',
                                       align_corners=True)

        return predicted_frame.squeeze(0)

    def compute_frame_error(self, predicted_frame, actual_frame):
        """
        计算帧间误差

        Args:
            predicted_frame (torch.Tensor): 预测帧 [3, H, W]
            actual_frame (torch.Tensor): 实际帧 [3, H, W]

        Returns:
            float: 帧间误差（MAE）
        """
        # 计算MAE
        error = torch.abs(predicted_frame - actual_frame).mean()
        return error.item()

    def compute_flicker_penalty(self, video_path, max_frames=None):
        """
        计算视频的Flicker Penalty

        Args:
            video_path (str): 视频路径
            max_frames (int): 最大帧数限制

        Returns:
            dict: 包含FP分数和详细结果的字典
        """
        # 1. 加载视频帧
        frames = self.load_video_frames(video_path, max_frames)
        tensor_frames = self.frames_to_tensor(frames)

        frame_errors = []
        flow_magnitudes = []

        print("Computing optical flow and frame errors...")

        # 2. 对每一对相邻帧计算光流和误差
        for i in tqdm(range(len(tensor_frames) - 1)):
            frame1 = tensor_frames[i]  # 当前帧
            frame2 = tensor_frames[i + 1]  # 下一帧

            # 计算光流 (frame1 -> frame2)
            flow = self.compute_optical_flow(frame1, frame2)

            # 计算光流幅度（用于分析）
            flow_magnitude = torch.sqrt(flow[0]**2 + flow[1]**2).mean().item()
            flow_magnitudes.append(flow_magnitude)

            # 使用frame1的光流预测frame2
            predicted_frame2 = self.motion_compensation(frame1, flow)

            # 计算预测误差
            error = self.compute_frame_error(predicted_frame2, frame2)
            frame_errors.append(error)

        # 3. 计算全局FP分数
        if len(frame_errors) == 0:
            return {'fp_score': 0.0, 'details': {}}

        # FP分数定义：平均帧间误差，归一化到[0,1]范围
        # 更高的误差表示更多的闪烁，FP分数越高
        avg_error = np.mean(frame_errors)
        max_possible_error = 1.0  # RGB归一化到[0,1]的最大可能误差
        fp_score = min(avg_error / max_possible_error, 1.0)

        # 4. 返回结果
        result = {
            'fp_score': fp_score,
            'avg_frame_error': avg_error,
            'max_frame_error': np.max(frame_errors),
            'min_frame_error': np.min(frame_errors),
            'frame_errors': frame_errors,
            'avg_flow_magnitude': np.mean(flow_magnitudes),
            'frame_count': len(frames),
            'video_path': video_path
        }

        return result

    def analyze_flicker_patterns(self, result):
        """
        分析闪烁模式

        Args:
            result (dict): FP计算结果

        Returns:
            dict: 闪烁模式分析结果
        """
        frame_errors = np.array(result['frame_errors'])

        # 计算误差的统计特征
        error_std = np.std(frame_errors)
        error_variance = np.var(frame_errors)

        # 检测闪烁峰值
        threshold = np.mean(frame_errors) + 2 * np.std(frame_errors)
        flicker_peaks = np.sum(frame_errors > threshold)

        # 计算闪烁频率（高误差帧的比例）
        flicker_frequency = flicker_peaks / len(frame_errors)

        analysis = {
            'error_std': error_std,
            'error_variance': error_variance,
            'flicker_peaks': flicker_peaks,
            'flicker_frequency': flicker_frequency,
            'temporal_consistency': 1.0 / (1.0 + error_variance),  # 时间一致性分数
        }

        return analysis


def compute_fp_score(video_path, model_path=None, device='cuda', max_frames=None):
    """
    计算单个视频的Flicker Penalty分数

    Args:
        video_path (str): 视频路径
        model_path (str): RAFT模型路径
        device (str): 计算设备
        max_frames (int): 最大帧数限制

    Returns:
        dict: FP计算结果
    """
    calculator = FlickerPenaltyCalculator(model_path, device)
    result = calculator.compute_flicker_penalty(video_path, max_frames)

    # 添加闪烁模式分析
    analysis = calculator.analyze_flicker_patterns(result)
    result['analysis'] = analysis

    return result


def batch_compute_fp_scores(video_paths, model_path=None, device='cuda', max_frames=None):
    """
    批量计算多个视频的FP分数

    Args:
        video_paths (list): 视频路径列表
        model_path (str): RAFT模型路径
        device (str): 计算设备
        max_frames (int): 最大帧数限制

    Returns:
        dict: 批量计算结果
    """
    calculator = FlickerPenaltyCalculator(model_path, device)

    results = []
    fp_scores = []

    for video_path in tqdm(video_paths, desc="Computing FP scores"):
        try:
            result = calculator.compute_flicker_penalty(video_path, max_frames)
            analysis = calculator.analyze_flicker_patterns(result)
            result['analysis'] = analysis

            results.append(result)
            fp_scores.append(result['fp_score'])

        except Exception as e:
            print(f"Error processing {video_path}: {e}")
            continue

    if len(fp_scores) == 0:
        return {'avg_fp_score': 0.0, 'results': []}

    batch_result = {
        'avg_fp_score': np.mean(fp_scores),
        'std_fp_score': np.std(fp_scores),
        'max_fp_score': np.max(fp_scores),
        'min_fp_score': np.min(fp_scores),
        'results': results,
        'processed_count': len(results),
        'total_count': len(video_paths)
    }

    return batch_result


if __name__ == "__main__":
    # 示例用法
    import argparse

    parser = argparse.ArgumentParser(description="Compute Flicker Penalty for videos")
    parser.add_argument("--video_path", type=str, help="Path to video file")
    parser.add_argument("--video_dir", type=str, help="Path to directory containing videos")
    parser.add_argument("--model_path", type=str, default=None, help="Path to RAFT model")
    parser.add_argument("--device", type=str, default="cuda", help="Computation device")
    parser.add_argument("--max_frames", type=int, default=None, help="Maximum number of frames to process")

    args = parser.parse_args()

    if args.video_path:
        # 处理单个视频
        result = compute_fp_score(args.video_path, args.model_path, args.device, args.max_frames)
        print("Flicker Penalty Results:")
        print(f"Video: {result['video_path']}")
        print(".4f")
        print(".4f")
        print(".4f")
        print(".4f")
        print(f"Analysis - Temporal Consistency: {result['analysis']['temporal_consistency']:.4f}")

    elif args.video_dir:
        # 处理目录中的所有视频
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        video_paths = []

        for ext in video_extensions:
            video_paths.extend(Path(args.video_dir).glob(f"**/*{ext}"))

        if len(video_paths) == 0:
            print(f"No video files found in {args.video_dir}")
            exit(1)

        video_paths = [str(p) for p in video_paths]
        print(f"Found {len(video_paths)} video files")

        batch_result = batch_compute_fp_scores(video_paths, args.model_path, args.device, args.max_frames)

        print("Batch Flicker Penalty Results:")
        print(f"Processed {batch_result['processed_count']}/{batch_result['total_count']} videos")
        print(".4f")
        print(".4f")
        print(".4f")

    else:
        print("Please specify either --video_path or --video_dir")
