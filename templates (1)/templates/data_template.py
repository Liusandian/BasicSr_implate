"""
数据集模板 - BasicSR

用于创建自定义数据集

使用说明:
1. 复制此文件到 basicsr/data/ 目录
2. 重命名为 {yourdata}_dataset.py
3. 修改类名和注册名
4. 实现数据加载逻辑
5. 在配置文件中使用 type: YourDataset
"""

import os
import cv2
import numpy as np
import torch
from torch.utils import data as data
from torchvision.transforms import functional as TF

from basicsr.data.data_util import (
    paired_paths_from_folder,
    paired_paths_from_lmdb,
    paired_paths_from_meta_info_file
)
from basicsr.data.transforms import augment, paired_random_crop
from basicsr.utils import FileClient, get_root_logger, imfrombytes, img2tensor
from basicsr.utils.registry import DATASET_REGISTRY


# ============================================================================
# 示例 1: 配对图像数据集（LQ-GT 对）
# ============================================================================

@DATASET_REGISTRY.register()
class PairedDatasetTemplate(data.Dataset):
    """
    配对图像数据集模板（低质量-高质量图像对）

    适用于: 图像超分、去噪、去模糊等需要配对数据的任务

    配置文件示例:
        datasets:
          train:
            name: MyData
            type: PairedDatasetTemplate
            dataroot_gt: datasets/MyData/train_HR
            dataroot_lq: datasets/MyData/train_LR
            io_backend:
              type: disk  # disk | lmdb
            gt_size: 128
            use_hflip: true
            use_rot: true

    Args:
        opt (dict): 数据集配置字典，包含以下键：
            - dataroot_gt (str): GT 图像根目录
            - dataroot_lq (str): LQ 图像根目录
            - io_backend (dict): IO 后端类型
            - gt_size (int): GT patch 大小
            - use_hflip (bool): 是否使用水平翻转
            - use_rot (bool): 是否使用旋转
    """

    def __init__(self, opt):
        super(PairedDatasetTemplate, self).__init__()
        self.opt = opt

        # 文件客户端（支持 disk 和 lmdb）
        self.file_client = None
        self.io_backend_opt = opt['io_backend']

        # GT 和 LQ 路径
        self.gt_folder = opt['dataroot_gt']
        self.lq_folder = opt['dataroot_lq']

        # ====== 获取图像路径列表 ======
        if 'meta_info' in opt and opt['meta_info'] is not None:
            # 从 meta_info 文件读取
            self.paths = paired_paths_from_meta_info_file(
                [self.lq_folder, self.gt_folder],
                ['lq', 'gt'],
                opt['meta_info'],
                opt.get('filename_tmpl', '{}')
            )
        elif self.io_backend_opt['type'] == 'lmdb':
            # 从 LMDB 读取
            self.paths = paired_paths_from_lmdb(
                [self.lq_folder, self.gt_folder],
                ['lq', 'gt']
            )
        else:
            # 从文件夹读取
            self.paths = paired_paths_from_folder(
                [self.lq_folder, self.gt_folder],
                ['lq', 'gt'],
                opt.get('filename_tmpl', '{}')
            )

    def __getitem__(self, index):
        """
        获取一个数据样本

        Returns:
            dict: 包含以下键的字典:
                - 'lq': LQ 图像 Tensor (C, H, W)
                - 'gt': GT 图像 Tensor (C, H, W)
                - 'lq_path': LQ 图像路径
                - 'gt_path': GT 图像路径
        """
        if self.file_client is None:
            self.file_client = FileClient(
                self.io_backend_opt.pop('type'),
                **self.io_backend_opt
            )

        # ====== 1. 加载图像 ======
        gt_path = self.paths[index]['gt_path']
        lq_path = self.paths[index]['lq_path']

        # 读取 GT 图像
        img_bytes = self.file_client.get(gt_path, 'gt')
        img_gt = imfrombytes(img_bytes, float32=True)

        # 读取 LQ 图像
        img_bytes = self.file_client.get(lq_path, 'lq')
        img_lq = imfrombytes(img_bytes, float32=True)

        # ====== 2. 数据增强（训练时） ======
        if self.opt.get('phase') == 'train':
            gt_size = self.opt.get('gt_size', 128)

            # 随机裁剪（配对裁剪）
            img_gt, img_lq = paired_random_crop(
                img_gt, img_lq, gt_size,
                scale=self.opt.get('scale', 1),
                gt_path=gt_path
            )

            # 随机翻转和旋转
            img_gt, img_lq = augment(
                [img_gt, img_lq],
                self.opt.get('use_hflip', True),
                self.opt.get('use_rot', True)
            )

        # ====== 3. 转换为 Tensor ======
        # BGR to RGB, HWC to CHW, numpy to tensor
        img_gt, img_lq = img2tensor(
            [img_gt, img_lq],
            bgr2rgb=True,
            float32=True
        )

        # ====== 4. 归一化（可选） ======
        # if self.opt.get('normalize', False):
        #     img_gt = (img_gt - 0.5) / 0.5
        #     img_lq = (img_lq - 0.5) / 0.5

        return {
            'lq': img_lq,
            'gt': img_gt,
            'lq_path': lq_path,
            'gt_path': gt_path
        }

    def __len__(self):
        return len(self.paths)


# ============================================================================
# 示例 2: 单图像数据集（仅 GT）
# ============================================================================

@DATASET_REGISTRY.register()
class SingleDatasetTemplate(data.Dataset):
    """
    单图像数据集模板（仅高质量图像）

    适用于: GAN 训练、自监督学习等不需要配对数据的任务

    配置文件示例:
        datasets:
          train:
            name: MyData
            type: SingleDatasetTemplate
            dataroot_gt: datasets/MyData/train
            gt_size: 128
    """

    def __init__(self, opt):
        super(SingleDatasetTemplate, self).__init__()
        self.opt = opt

        self.file_client = None
        self.io_backend_opt = opt['io_backend']
        self.gt_folder = opt['dataroot_gt']

        # 获取图像路径
        self.paths = []
        for root, _, files in os.walk(self.gt_folder):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    self.paths.append(os.path.join(root, file))

    def __getitem__(self, index):
        if self.file_client is None:
            self.file_client = FileClient(
                self.io_backend_opt.pop('type'),
                **self.io_backend_opt
            )

        # 加载图像
        gt_path = self.paths[index]
        img_bytes = self.file_client.get(gt_path, 'gt')
        img_gt = imfrombytes(img_bytes, float32=True)

        # 数据增强
        if self.opt.get('phase') == 'train':
            gt_size = self.opt.get('gt_size', 128)

            # 随机裁剪
            h, w = img_gt.shape[:2]
            if h >= gt_size and w >= gt_size:
                top = np.random.randint(0, h - gt_size + 1)
                left = np.random.randint(0, w - gt_size + 1)
                img_gt = img_gt[top:top+gt_size, left:left+gt_size, :]

            # 随机翻转
            if self.opt.get('use_hflip', True) and np.random.rand() < 0.5:
                img_gt = cv2.flip(img_gt, 1)

        # 转换为 Tensor
        img_gt = img2tensor([img_gt], bgr2rgb=True, float32=True)[0]

        return {
            'gt': img_gt,
            'gt_path': gt_path
        }

    def __len__(self):
        return len(self.paths)


# ============================================================================
# 示例 3: 自定义退化数据集（在线生成 LQ）
# ============================================================================

@DATASET_REGISTRY.register()
class DegradationDatasetTemplate(data.Dataset):
    """
    自定义退化数据集（在线生成低质量图像）

    适用于: 需要特定退化模型的任务（如 Real-ESRGAN）

    配置文件示例:
        datasets:
          train:
            name: MyData
            type: DegradationDatasetTemplate
            dataroot_gt: datasets/MyData/train
            blur_kernel_size: 21
            blur_sigma: [0.2, 3]
            downsample_range: [0.5, 8]
            noise_range: [0, 20]
    """

    def __init__(self, opt):
        super(DegradationDatasetTemplate, self).__init__()
        self.opt = opt

        self.file_client = None
        self.io_backend_opt = opt['io_backend']
        self.gt_folder = opt['dataroot_gt']

        # 退化参数
        self.blur_kernel_size = opt.get('blur_kernel_size', 21)
        self.blur_sigma = opt.get('blur_sigma', [0.2, 3])
        self.downsample_range = opt.get('downsample_range', [0.5, 8])
        self.noise_range = opt.get('noise_range', [0, 20])

        # 获取图像路径
        self.paths = []
        for root, _, files in os.walk(self.gt_folder):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.paths.append(os.path.join(root, file))

    def __getitem__(self, index):
        if self.file_client is None:
            self.file_client = FileClient(
                self.io_backend_opt.pop('type'),
                **self.io_backend_opt
            )

        # 加载 GT 图像
        gt_path = self.paths[index]
        img_bytes = self.file_client.get(gt_path, 'gt')
        img_gt = imfrombytes(img_bytes, float32=True)

        # ====== 在线生成 LQ 图像 ======
        img_lq = img_gt.copy()

        # 1. 模糊
        if np.random.rand() < 0.5:
            kernel_size = np.random.choice([7, 9, 11, 13, 15, 17, 19, 21])
            sigma = np.random.uniform(self.blur_sigma[0], self.blur_sigma[1])
            img_lq = cv2.GaussianBlur(img_lq, (kernel_size, kernel_size), sigma)

        # 2. 下采样
        scale = np.random.uniform(self.downsample_range[0], self.downsample_range[1])
        h, w = img_lq.shape[:2]
        img_lq = cv2.resize(img_lq, (int(w/scale), int(h/scale)), interpolation=cv2.INTER_CUBIC)
        img_lq = cv2.resize(img_lq, (w, h), interpolation=cv2.INTER_CUBIC)

        # 3. 添加噪声
        if np.random.rand() < 0.5:
            noise_level = np.random.uniform(self.noise_range[0], self.noise_range[1])
            noise = np.random.randn(*img_lq.shape) * (noise_level / 255.0)
            img_lq = np.clip(img_lq + noise, 0, 1)

        # ====== 数据增强 ======
        if self.opt.get('phase') == 'train':
            gt_size = self.opt.get('gt_size', 128)
            img_gt, img_lq = paired_random_crop(img_gt, img_lq, gt_size, 1, gt_path)
            img_gt, img_lq = augment([img_gt, img_lq], True, True)

        # 转换为 Tensor
        img_gt, img_lq = img2tensor([img_gt, img_lq], bgr2rgb=True, float32=True)

        return {
            'lq': img_lq,
            'gt': img_gt,
            'lq_path': gt_path,  # LQ 是在线生成的
            'gt_path': gt_path
        }

    def __len__(self):
        return len(self.paths)


# ============================================================================
# 示例 4: 视频数据集
# ============================================================================

@DATASET_REGISTRY.register()
class VideoDatasetTemplate(data.Dataset):
    """
    视频数据集模板

    适用于: 视频超分、视频去噪等任务

    配置文件示例:
        datasets:
          train:
            name: MyVideoData
            type: VideoDatasetTemplate
            dataroot_gt: datasets/MyVideo/train_GT
            dataroot_lq: datasets/MyVideo/train_LQ
            num_frame: 5  # 输入帧数
            center_frame_idx: 2  # 中心帧索引
    """

    def __init__(self, opt):
        super(VideoDatasetTemplate, self).__init__()
        self.opt = opt

        self.gt_root = opt['dataroot_gt']
        self.lq_root = opt['dataroot_lq']
        self.num_frame = opt.get('num_frame', 5)
        self.center_frame_idx = opt.get('center_frame_idx', self.num_frame // 2)

        # 获取视频文件夹列表
        self.video_folders = sorted(os.listdir(self.gt_root))

    def __getitem__(self, index):
        # 获取视频文件夹
        video_name = self.video_folders[index]
        gt_video_path = os.path.join(self.gt_root, video_name)
        lq_video_path = os.path.join(self.lq_root, video_name)

        # 获取帧列表
        gt_frames = sorted(os.listdir(gt_video_path))
        num_frames_total = len(gt_frames)

        # 随机选择中心帧
        if self.opt.get('phase') == 'train':
            center_idx = np.random.randint(
                self.center_frame_idx,
                num_frames_total - (self.num_frame - self.center_frame_idx - 1)
            )
        else:
            center_idx = num_frames_total // 2

        # 获取相邻帧索引
        start_idx = center_idx - self.center_frame_idx
        end_idx = start_idx + self.num_frame

        # 加载帧
        img_gts = []
        img_lqs = []

        for i in range(start_idx, end_idx):
            # GT 帧
            gt_frame_path = os.path.join(gt_video_path, gt_frames[i])
            img_gt = cv2.imread(gt_frame_path, cv2.IMREAD_COLOR).astype(np.float32) / 255.0
            img_gts.append(img_gt)

            # LQ 帧
            lq_frame_path = os.path.join(lq_video_path, gt_frames[i])
            img_lq = cv2.imread(lq_frame_path, cv2.IMREAD_COLOR).astype(np.float32) / 255.0
            img_lqs.append(img_lq)

        # 转换为 Tensor
        img_gts = img2tensor(img_gts, bgr2rgb=True, float32=True)
        img_lqs = img2tensor(img_lqs, bgr2rgb=True, float32=True)

        # Stack: (T, C, H, W)
        img_gts = torch.stack(img_gts, dim=0)
        img_lqs = torch.stack(img_lqs, dim=0)

        return {
            'lq': img_lqs,
            'gt': img_gts,
            'folder': video_name,
            'idx': center_idx
        }

    def __len__(self):
        return len(self.video_folders)


# ============================================================================
# 工具函数
# ============================================================================

def get_image_paths(folder, extensions=('.png', '.jpg', '.jpeg', '.bmp')):
    """递归获取文件夹下所有图像路径"""
    paths = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(extensions):
                paths.append(os.path.join(root, file))
    return sorted(paths)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == '__main__':
    """
    测试数据集
    """
    # 配置
    opt = {
        'name': 'test',
        'type': 'PairedDatasetTemplate',
        'dataroot_gt': 'datasets/DIV2K/train_HR',
        'dataroot_lq': 'datasets/DIV2K/train_LR_bicubic/X4',
        'io_backend': {'type': 'disk'},
        'phase': 'train',
        'gt_size': 128,
        'use_hflip': True,
        'use_rot': True,
        'scale': 4
    }

    # 创建数据集
    dataset = PairedDatasetTemplate(opt)

    # 测试
    print(f"数据集大小: {len(dataset)}")

    sample = dataset[0]
    print(f"LQ shape: {sample['lq'].shape}")
    print(f"GT shape: {sample['gt'].shape}")
    print(f"LQ path: {sample['lq_path']}")
    print(f"GT path: {sample['gt_path']}")

    # 创建 DataLoader
    from torch.utils.data import DataLoader

    loader = DataLoader(dataset, batch_size=4, shuffle=True, num_workers=0)

    for batch in loader:
        print(f"Batch LQ: {batch['lq'].shape}")
        print(f"Batch GT: {batch['gt'].shape}")
        break

    print("✅ 数据集测试通过")

