"""
工具函数模板 - BasicSR

用于创建自定义工具函数

使用说明:
1. 复制此文件到 basicsr/utils/ 目录
2. 重命名为 {yourutil}.py
3. 实现工具函数
4. 在需要的地方导入使用
"""

import torch
import torch.nn as nn
import numpy as np
import cv2


# ============================================================================
# 示例 1: 图像处理工具
# ============================================================================

def preprocess_image(img, mean=None, std=None):
    """
    图像预处理

    Args:
        img (np.ndarray): 输入图像 (H, W, C)，范围 [0, 1]
        mean (tuple): 均值，如 (0.485, 0.456, 0.406)
        std (tuple): 标准差，如 (0.229, 0.224, 0.225)

    Returns:
        torch.Tensor: 预处理后的图像 (C, H, W)
    """
    # 转换为 Tensor
    img_tensor = torch.from_numpy(img.transpose(2, 0, 1)).float()

    # 归一化
    if mean is not None and std is not None:
        mean = torch.tensor(mean).view(-1, 1, 1)
        std = torch.tensor(std).view(-1, 1, 1)
        img_tensor = (img_tensor - mean) / std

    return img_tensor


def postprocess_image(tensor, mean=None, std=None):
    """
    图像后处理

    Args:
        tensor (torch.Tensor): 图像 Tensor (C, H, W)
        mean (tuple): 均值
        std (tuple): 标准差

    Returns:
        np.ndarray: 图像数组 (H, W, C)，范围 [0, 255]
    """
    # 反归一化
    if mean is not None and std is not None:
        mean = torch.tensor(mean).view(-1, 1, 1)
        std = torch.tensor(std).view(-1, 1, 1)
        tensor = tensor * std + mean

    # 转换为 numpy
    img = tensor.cpu().numpy().transpose(1, 2, 0)
    img = np.clip(img * 255, 0, 255).astype(np.uint8)

    return img


# ============================================================================
# 示例 2: 网络层工具
# ============================================================================

def pixel_unshuffle(x, scale):
    """
    像素反洗牌（PixelShuffle 的逆操作）

    Args:
        x (Tensor): 输入 (B, C, H, W)
        scale (int): 下采样倍数

    Returns:
        Tensor: 输出 (B, C*scale^2, H/scale, W/scale)
    """
    b, c, h, w = x.size()
    out_h, out_w = h // scale, w // scale

    x = x.view(b, c, out_h, scale, out_w, scale)
    x = x.permute(0, 1, 3, 5, 2, 4).contiguous()
    x = x.view(b, c * scale * scale, out_h, out_w)

    return x


def make_layer(basic_block, num_blocks, **kwargs):
    """
    创建重复的层

    Args:
        basic_block: 基础模块类
        num_blocks: 重复次数
        **kwargs: 传递给 basic_block 的参数

    Returns:
        nn.Sequential: 组合的层
    """
    layers = []
    for _ in range(num_blocks):
        layers.append(basic_block(**kwargs))
    return nn.Sequential(*layers)


class ResidualBlockNoBN(nn.Module):
    """无 BN 的残差块（BasicSR 常用）"""

    def __init__(self, num_feat=64, res_scale=1.0):
        super(ResidualBlockNoBN, self).__init__()
        self.res_scale = res_scale
        self.conv1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1, bias=True)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        identity = x
        out = self.conv2(self.relu(self.conv1(x)))
        return identity + out * self.res_scale


# ============================================================================
# 示例 3: 上采样工具
# ============================================================================

class Upsample(nn.Sequential):
    """
    上采样模块（支持多种倍数）

    Args:
        scale (int): 上采样倍数
        num_feat (int): 特征通道数
    """

    def __init__(self, scale, num_feat):
        m = []
        if (scale & (scale - 1)) == 0:  # 2^n
            for _ in range(int(np.log2(scale))):
                m.append(nn.Conv2d(num_feat, 4 * num_feat, 3, 1, 1))
                m.append(nn.PixelShuffle(2))
        elif scale == 3:
            m.append(nn.Conv2d(num_feat, 9 * num_feat, 3, 1, 1))
            m.append(nn.PixelShuffle(3))
        else:
            raise ValueError(f'scale {scale} is not supported. Supported scales: 2^n and 3.')

        super(Upsample, self).__init__(*m)


# ============================================================================
# 示例 4: 数据增强工具
# ============================================================================

def random_crop_pair(img_gt, img_lq, gt_size, scale):
    """
    配对随机裁剪

    Args:
        img_gt (np.ndarray): GT 图像 (H, W, C)
        img_lq (np.ndarray): LQ 图像 (H/scale, W/scale, C)
        gt_size (int): GT patch 大小
        scale (int): 超分倍数

    Returns:
        tuple: (gt_patch, lq_patch)
    """
    h_gt, w_gt = img_gt.shape[:2]
    h_lq, w_lq = img_lq.shape[:2]

    # 检查尺寸
    assert h_gt == h_lq * scale and w_gt == w_lq * scale, \
        f'GT and LQ size mismatch: {h_gt}x{w_gt} vs {h_lq}x{w_lq}'

    # GT 随机裁剪
    top = np.random.randint(0, h_gt - gt_size + 1)
    left = np.random.randint(0, w_gt - gt_size + 1)
    img_gt = img_gt[top:top+gt_size, left:left+gt_size, :]

    # LQ 对应裁剪
    top_lq = top // scale
    left_lq = left // scale
    lq_size = gt_size // scale
    img_lq = img_lq[top_lq:top_lq+lq_size, left_lq:left_lq+lq_size, :]

    return img_gt, img_lq


def augment_flip_rot(imgs, hflip=True, rot=True):
    """
    随机翻转和旋转

    Args:
        imgs (list): 图像列表
        hflip (bool): 是否水平翻转
        rot (bool): 是否旋转

    Returns:
        list: 增强后的图像列表
    """
    # 水平翻转
    if hflip and np.random.rand() < 0.5:
        imgs = [cv2.flip(img, 1) for img in imgs]

    # 旋转 (90, 180, 270 度)
    if rot:
        rot_code = np.random.choice([0, 1, 2, 3])
        if rot_code == 1:  # 90 度
            imgs = [cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE) for img in imgs]
        elif rot_code == 2:  # 180 度
            imgs = [cv2.rotate(img, cv2.ROTATE_180) for img in imgs]
        elif rot_code == 3:  # 270 度
            imgs = [cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE) for img in imgs]

    return imgs


# ============================================================================
# 示例 5: 指标计算工具
# ============================================================================

def calculate_psnr_simple(img1, img2, crop_border=0, test_y_channel=False):
    """
    简化的 PSNR 计算

    Args:
        img1 (np.ndarray): 第一张图像 (H, W, C)，范围 [0, 255]
        img2 (np.ndarray): 第二张图像
        crop_border (int): 裁剪边界像素
        test_y_channel (bool): 是否只在 Y 通道计算

    Returns:
        float: PSNR 值（dB）
    """
    assert img1.shape == img2.shape, 'Image shapes must match'

    # 裁剪边界
    if crop_border > 0:
        img1 = img1[crop_border:-crop_border, crop_border:-crop_border, :]
        img2 = img2[crop_border:-crop_border, crop_border:-crop_border, :]

    # 转换为 Y 通道
    if test_y_channel:
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # 计算 MSE
    mse = np.mean((img1.astype(np.float64) - img2.astype(np.float64)) ** 2)

    if mse == 0:
        return float('inf')

    # 计算 PSNR
    psnr = 20 * np.log10(255.0 / np.sqrt(mse))

    return psnr


# ============================================================================
# 示例 6: 模型权重处理
# ============================================================================

def load_pretrained_weights(model, pretrained_path, strict=True):
    """
    加载预训练权重

    Args:
        model (nn.Module): 模型
        pretrained_path (str): 权重文件路径
        strict (bool): 是否严格匹配

    Returns:
        nn.Module: 加载权重后的模型
    """
    print(f"加载预训练权重: {pretrained_path}")

    # 加载 checkpoint
    checkpoint = torch.load(pretrained_path, map_location='cpu')

    # 提取参数字典
    if 'params' in checkpoint:
        state_dict = checkpoint['params']
    elif 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint

    # 加载到模型
    model.load_state_dict(state_dict, strict=strict)

    print("✅ 权重加载成功")
    return model


def count_parameters(model):
    """
    统计模型参数量

    Args:
        model (nn.Module): 模型

    Returns:
        dict: 参数统计信息
    """
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    return {
        'total': total_params,
        'trainable': trainable_params,
        'total_M': total_params / 1e6,
        'trainable_M': trainable_params / 1e6
    }


# ============================================================================
# 示例 7: 可视化工具
# ============================================================================

def visualize_feature_maps(features, save_path='features.png', max_channels=16):
    """
    可视化特征图

    Args:
        features (Tensor): 特征图 (B, C, H, W)
        save_path (str): 保存路径
        max_channels (int): 最多可视化的通道数
    """
    import matplotlib.pyplot as plt

    features = features.detach().cpu()
    b, c, h, w = features.shape

    num_show = min(c, max_channels)

    fig, axes = plt.subplots(4, 4, figsize=(12, 12))
    axes = axes.flatten()

    for i in range(num_show):
        feat = features[0, i].numpy()
        axes[i].imshow(feat, cmap='viridis')
        axes[i].axis('off')
        axes[i].set_title(f'Ch {i}')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"✅ 特征图已保存: {save_path}")


def save_comparison_grid(lq, sr, gt, save_path='comparison.png'):
    """
    保存 LQ-SR-GT 对比图

    Args:
        lq (np.ndarray): LQ 图像 (H, W, 3)
        sr (np.ndarray): SR 图像 (H*scale, W*scale, 3)
        gt (np.ndarray): GT 图像 (H*scale, W*scale, 3)
        save_path (str): 保存路径
    """
    # 上采样 LQ 到相同尺寸
    h, w = sr.shape[:2]
    lq_up = cv2.resize(lq, (w, h), interpolation=cv2.INTER_CUBIC)

    # 横向拼接
    comparison = np.hstack([lq_up, sr, gt])

    # 添加标签
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, 'LQ', (10, 30), font, 1, (255, 255, 255), 2)
    cv2.putText(comparison, 'SR', (w + 10, 30), font, 1, (255, 255, 255), 2)
    cv2.putText(comparison, 'GT', (2*w + 10, 30), font, 1, (255, 255, 255), 2)

    cv2.imwrite(save_path, comparison)
    print(f"✅ 对比图已保存: {save_path}")


# ============================================================================
# 示例 8: 训练辅助工具
# ============================================================================

class EMA:
    """
    Exponential Moving Average (指数移动平均)

    用于稳定训练，提升测试性能

    使用:
        ema = EMA(model, decay=0.999)

        # 训练循环中
        for data in loader:
            loss = ...
            loss.backward()
            optimizer.step()

            # 更新 EMA
            ema.update(model)

        # 测试时使用 EMA 模型
        ema.apply_shadow(model)
        with torch.no_grad():
            output = model(input)
        ema.restore(model)
    """

    def __init__(self, model, decay=0.999):
        self.model = model
        self.decay = decay
        self.shadow = {}
        self.backup = {}

        # 注册参数
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self, model):
        """更新 EMA 参数"""
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                new_average = (1.0 - self.decay) * param.data + self.decay * self.shadow[name]
                self.shadow[name] = new_average.clone()

    def apply_shadow(self, model):
        """应用 EMA 参数（用于测试）"""
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                self.backup[name] = param.data
                param.data = self.shadow[name]

    def restore(self, model):
        """恢复原始参数"""
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.backup
                param.data = self.backup[name]
        self.backup = {}


# ============================================================================
# 示例 9: 退化模拟工具
# ============================================================================

def apply_gaussian_blur(img, kernel_size=21, sigma=1.5):
    """应用高斯模糊"""
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)


def add_gaussian_noise(img, sigma=10):
    """
    添加高斯噪声

    Args:
        img (np.ndarray): 输入图像，范围 [0, 1]
        sigma (float): 噪声标准差（0-255 scale）

    Returns:
        np.ndarray: 加噪图像
    """
    noise = np.random.randn(*img.shape) * (sigma / 255.0)
    noisy_img = img + noise
    return np.clip(noisy_img, 0, 1)


def bicubic_downsample(img, scale):
    """双三次下采样"""
    h, w = img.shape[:2]
    return cv2.resize(img, (w // scale, h // scale), interpolation=cv2.INTER_CUBIC)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == '__main__':
    """测试工具函数"""
    print("="*70)
    print("工具函数测试")
    print("="*70)

    # 测试图像处理
    img = np.random.rand(256, 256, 3)
    tensor = preprocess_image(img, mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
    print(f"✅ 图像预处理: {img.shape} -> {tensor.shape}")

    # 测试网络层
    x = torch.randn(1, 64, 32, 32)
    y = pixel_unshuffle(x, scale=2)
    print(f"✅ Pixel Unshuffle: {x.shape} -> {y.shape}")

    # 测试上采样
    upsampler = Upsample(scale=4, num_feat=64)
    x = torch.randn(1, 64, 32, 32)
    y = upsampler(x)
    print(f"✅ Upsample: {x.shape} -> {y.shape}")

    # 测试参数统计
    model = nn.Conv2d(3, 64, 3, 1, 1)
    stats = count_parameters(model)
    print(f"✅ 参数统计: {stats['total_M']:.2f}M")

    print("\n所有测试通过！")

