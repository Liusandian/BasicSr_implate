"""
损失函数模板 - BasicSR

用于创建自定义损失函数

使用说明:
1. 复制此文件到 basicsr/losses/ 目录
2. 重命名为 {yourloss}_loss.py
3. 修改类名和注册名
4. 实现损失计算逻辑
5. 在配置文件中使用 type: YourLoss
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from basicsr.utils.registry import LOSS_REGISTRY


# ============================================================================
# 示例 1: 简单的像素级损失
# ============================================================================

@LOSS_REGISTRY.register()
class SimpleLossTemplate(nn.Module):
    """
    简单损失函数模板

    适用于: 基础的像素级损失计算

    配置文件示例:
        train:
          pixel_opt:
            type: SimpleLossTemplate
            loss_weight: 1.0
            reduction: mean

    Args:
        loss_weight (float): 损失权重，默认 1.0
        reduction (str): 归约方式，'mean' | 'sum' | 'none'
    """

    def __init__(self, loss_weight=1.0, reduction='mean'):
        super(SimpleLossTemplate, self).__init__()

        if reduction not in ['none', 'mean', 'sum']:
            raise ValueError(f'Unsupported reduction mode: {reduction}')

        self.loss_weight = loss_weight
        self.reduction = reduction

    def forward(self, pred, target, weight=None):
        """
        前向传播计算损失

        Args:
            pred (Tensor): 预测图像，shape (N, C, H, W)
            target (Tensor): 目标图像，shape (N, C, H, W)
            weight (Tensor, optional): 像素权重，shape (N, C, H, W) 或 (N, 1, H, W)

        Returns:
            Tensor: 损失值（标量或张量，取决于 reduction）
        """
        # 计算损失（这里用 L1 作为示例）
        loss = F.l1_loss(pred, target, reduction='none')

        # 应用权重（如果提供）
        if weight is not None:
            loss = loss * weight

        # 归约
        if self.reduction == 'mean':
            loss = loss.mean()
        elif self.reduction == 'sum':
            loss = loss.sum()
        # 'none' 时保持原样

        return loss * self.loss_weight


# ============================================================================
# 示例 2: Charbonnier 损失（鲁棒 L1）
# ============================================================================

@LOSS_REGISTRY.register()
class CharbonnierLossTemplate(nn.Module):
    """
    Charbonnier 损失（平滑 L1 损失）

    公式: sqrt((x - y)^2 + eps^2)

    适用于: 对异常值更鲁棒的像素损失

    Args:
        loss_weight (float): 损失权重
        reduction (str): 归约方式
        eps (float): 平滑参数，默认 1e-3
    """

    def __init__(self, loss_weight=1.0, reduction='mean', eps=1e-3):
        super(CharbonnierLossTemplate, self).__init__()
        self.loss_weight = loss_weight
        self.reduction = reduction
        self.eps = eps

    def forward(self, pred, target):
        """计算 Charbonnier 损失"""
        diff = pred - target
        loss = torch.sqrt(diff * diff + self.eps * self.eps)

        if self.reduction == 'mean':
            loss = loss.mean()
        elif self.reduction == 'sum':
            loss = loss.sum()

        return loss * self.loss_weight


# ============================================================================
# 示例 3: 感知损失（基于 VGG 特征）
# ============================================================================

from basicsr.archs.vgg_arch import VGGFeatureExtractor


@LOSS_REGISTRY.register()
class PerceptualLossTemplate(nn.Module):
    """
    感知损失模板（基于 VGG 特征）

    适用于: 需要保持感知相似性的任务（如 SRGAN）

    配置文件示例:
        train:
          perceptual_opt:
            type: PerceptualLossTemplate
            layer_weights:
              conv3_4: 1.0
              conv4_4: 1.0
              conv5_4: 1.0
            vgg_type: vgg19
            perceptual_weight: 1.0
            style_weight: 0

    Args:
        layer_weights (dict): VGG 层权重，如 {'conv5_4': 1.0}
        vgg_type (str): VGG 类型，'vgg16' | 'vgg19'
        use_input_norm (bool): 是否对输入归一化
        perceptual_weight (float): 感知损失权重
        style_weight (float): 风格损失权重
        criterion (str): 损失类型，'l1' | 'l2' | 'fro'
    """

    def __init__(
        self,
        layer_weights,
        vgg_type='vgg19',
        use_input_norm=True,
        range_norm=False,
        perceptual_weight=1.0,
        style_weight=0.0,
        criterion='l1'
    ):
        super(PerceptualLossTemplate, self).__init__()

        self.perceptual_weight = perceptual_weight
        self.style_weight = style_weight
        self.layer_weights = layer_weights

        # 创建 VGG 特征提取器
        self.vgg = VGGFeatureExtractor(
            layer_name_list=list(layer_weights.keys()),
            vgg_type=vgg_type,
            use_input_norm=use_input_norm,
            range_norm=range_norm
        )

        # 损失函数
        self.criterion_type = criterion
        if criterion == 'l1':
            self.criterion = nn.L1Loss()
        elif criterion == 'l2':
            self.criterion = nn.MSELoss()
        elif criterion == 'fro':
            self.criterion = None  # 使用 Frobenius 范数
        else:
            raise NotImplementedError(f'{criterion} criterion is not supported.')

    def forward(self, x, gt):
        """
        计算感知损失

        Args:
            x (Tensor): 预测图像 (N, C, H, W)
            gt (Tensor): 目标图像 (N, C, H, W)

        Returns:
            Tensor: 感知损失
            Tensor: 风格损失（如果 style_weight > 0）
        """
        # 提取 VGG 特征
        x_features = self.vgg(x)
        gt_features = self.vgg(gt.detach())

        # 计算感知损失
        percep_loss = 0
        if self.perceptual_weight > 0:
            for k in x_features.keys():
                if self.criterion_type == 'fro':
                    percep_loss += torch.norm(
                        x_features[k] - gt_features[k],
                        p='fro'
                    ) * self.layer_weights[k]
                else:
                    percep_loss += self.criterion(
                        x_features[k],
                        gt_features[k]
                    ) * self.layer_weights[k]
            percep_loss *= self.perceptual_weight
        else:
            percep_loss = None

        # 计算风格损失（Gram 矩阵）
        style_loss = 0
        if self.style_weight > 0:
            for k in x_features.keys():
                x_gram = self._gram_mat(x_features[k])
                gt_gram = self._gram_mat(gt_features[k])

                if self.criterion_type == 'fro':
                    style_loss += torch.norm(
                        x_gram - gt_gram,
                        p='fro'
                    ) * self.layer_weights[k]
                else:
                    style_loss += self.criterion(
                        x_gram, gt_gram
                    ) * self.layer_weights[k]
            style_loss *= self.style_weight
        else:
            style_loss = None

        return percep_loss, style_loss

    def _gram_mat(self, x):
        """计算 Gram 矩阵"""
        n, c, h, w = x.size()
        features = x.view(n, c, h * w)
        features_t = features.transpose(1, 2)
        gram = features.bmm(features_t) / (c * h * w)
        return gram


# ============================================================================
# 示例 4: 频域损失（FFT）
# ============================================================================

@LOSS_REGISTRY.register()
class FrequencyLossTemplate(nn.Module):
    """
    频域损失模板

    适用于: 需要保持频域信息的任务

    Args:
        loss_weight (float): 损失权重
        criterion (str): 损失类型
    """

    def __init__(self, loss_weight=1.0, criterion='l1'):
        super(FrequencyLossTemplate, self).__init__()
        self.loss_weight = loss_weight

        if criterion == 'l1':
            self.criterion = nn.L1Loss()
        elif criterion == 'l2':
            self.criterion = nn.MSELoss()
        else:
            raise NotImplementedError(f'{criterion} not supported')

    def forward(self, pred, target):
        """计算频域损失"""
        # 转换到频域
        pred_fft = torch.fft.rfft2(pred, norm='ortho')
        target_fft = torch.fft.rfft2(target, norm='ortho')

        # 计算幅度谱损失
        pred_amp = torch.abs(pred_fft)
        target_amp = torch.abs(target_fft)

        loss = self.criterion(pred_amp, target_amp)

        return loss * self.loss_weight


# ============================================================================
# 示例 5: 多尺度损失
# ============================================================================

@LOSS_REGISTRY.register()
class MultiScaleLossTemplate(nn.Module):
    """
    多尺度损失模板

    适用于: 需要在多个尺度计算损失的任务

    Args:
        loss_weight (float): 损失权重
        scales (list): 尺度列表，如 [1, 0.5, 0.25]
        criterion (str): 基础损失类型
    """

    def __init__(self, loss_weight=1.0, scales=None, criterion='l1'):
        super(MultiScaleLossTemplate, self).__init__()
        self.loss_weight = loss_weight
        self.scales = scales or [1, 0.5, 0.25]

        if criterion == 'l1':
            self.criterion = nn.L1Loss()
        elif criterion == 'l2':
            self.criterion = nn.MSELoss()
        else:
            raise NotImplementedError()

    def forward(self, pred, target):
        """计算多尺度损失"""
        total_loss = 0

        for scale in self.scales:
            if scale != 1:
                # 下采样
                h, w = pred.shape[2:]
                new_h, new_w = int(h * scale), int(w * scale)

                pred_scaled = F.interpolate(
                    pred, size=(new_h, new_w),
                    mode='bilinear', align_corners=False
                )
                target_scaled = F.interpolate(
                    target, size=(new_h, new_w),
                    mode='bilinear', align_corners=False
                )
            else:
                pred_scaled = pred
                target_scaled = target

            # 计算损失
            loss = self.criterion(pred_scaled, target_scaled)
            total_loss += loss

        return total_loss * self.loss_weight / len(self.scales)


# ============================================================================
# 示例 6: 组合损失
# ============================================================================

@LOSS_REGISTRY.register()
class CombinedLossTemplate(nn.Module):
    """
    组合损失模板（多个损失的加权和）

    适用于: 需要多种损失组合的任务

    配置文件示例:
        train:
          combined_opt:
            type: CombinedLossTemplate
            l1_weight: 1.0
            perceptual_weight: 0.1
            frequency_weight: 0.5

    Args:
        l1_weight (float): L1 损失权重
        perceptual_weight (float): 感知损失权重
        frequency_weight (float): 频域损失权重
    """

    def __init__(
        self,
        l1_weight=1.0,
        perceptual_weight=0.0,
        frequency_weight=0.0
    ):
        super(CombinedLossTemplate, self).__init__()

        self.l1_weight = l1_weight
        self.perceptual_weight = perceptual_weight
        self.frequency_weight = frequency_weight

        # 创建子损失
        if l1_weight > 0:
            self.l1_loss = nn.L1Loss()

        if perceptual_weight > 0:
            # 这里简化，实际应使用 PerceptualLoss
            pass

        if frequency_weight > 0:
            # 这里简化，实际应使用 FrequencyLoss
            pass

    def forward(self, pred, target):
        """计算组合损失"""
        total_loss = 0
        loss_dict = {}

        # L1 损失
        if self.l1_weight > 0:
            l1_loss = self.l1_loss(pred, target) * self.l1_weight
            total_loss += l1_loss
            loss_dict['l1'] = l1_loss

        # 感知损失
        if self.perceptual_weight > 0:
            # percep_loss = self.perceptual_loss(pred, target) * self.perceptual_weight
            # total_loss += percep_loss
            # loss_dict['perceptual'] = percep_loss
            pass

        # 频域损失
        if self.frequency_weight > 0:
            # freq_loss = self.frequency_loss(pred, target) * self.frequency_weight
            # total_loss += freq_loss
            # loss_dict['frequency'] = freq_loss
            pass

        return total_loss


# ============================================================================
# 工具函数
# ============================================================================

def weighted_loss(loss_func):
    """
    装饰器：为损失函数添加权重支持

    用法:
        @weighted_loss
        def my_loss(pred, target):
            return (pred - target).abs()
    """
    def wrapper(pred, target, weight=None, **kwargs):
        loss = loss_func(pred, target, **kwargs)
        if weight is not None:
            loss = loss * weight
        return loss
    return wrapper


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == '__main__':
    """测试损失函数"""
    # 创建损失
    loss_fn = SimpleLossTemplate(loss_weight=1.0, reduction='mean')

    # 测试数据
    pred = torch.randn(2, 3, 64, 64)
    target = torch.randn(2, 3, 64, 64)

    # 计算损失
    loss = loss_fn(pred, target)

    print(f"损失值: {loss.item():.6f}")

    # 测试梯度
    loss.backward()
    print("✅ 损失函数测试通过")

