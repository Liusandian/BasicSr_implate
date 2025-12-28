"""
网络架构模板 - BasicSR

用于移植新的深度学习网络到 BasicSR 框架

使用说明:
1. 复制此文件到 basicsr/archs/ 目录
2. 重命名为 {yournet}_arch.py
3. 修改类名和注册名
4. 实现网络结构
5. 在配置文件中使用 type: YourNet
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from basicsr.utils.registry import ARCH_REGISTRY


# ============================================================================
# 示例 1: 简单的单网络架构
# ============================================================================

@ARCH_REGISTRY.register()
class SimpleNet(nn.Module):
    """
    简单网络架构模板

    适用于: 标准的图像超分、去噪、去模糊等任务

    Args:
        num_in_ch (int): 输入通道数，通常为 3 (RGB)
        num_out_ch (int): 输出通道数，通常为 3 (RGB)
        num_feat (int): 中间特征通道数，默认 64
        upscale (int): 上采样倍数，如 2, 3, 4

    配置文件示例:
        network_g:
          type: SimpleNet
          num_in_ch: 3
          num_out_ch: 3
          num_feat: 64
          upscale: 4
    """

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        upscale: int = 4
    ):
        super(SimpleNet, self).__init__()

        # 保存参数
        self.upscale = upscale

        # ====== 网络结构定义 ======

        # 1. 特征提取（浅层）
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)

        # 2. 特征处理（深层）- 在这里添加你的主干网络
        self.body = nn.Sequential(
            nn.Conv2d(num_feat, num_feat, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_feat, num_feat, 3, 1, 1),
            nn.ReLU(inplace=True),
            # 添加更多层...
        )

        # 3. 上采样（如果需要）
        if upscale == 2:
            self.upsampler = nn.Sequential(
                nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1),
                nn.PixelShuffle(2)
            )
        elif upscale == 3:
            self.upsampler = nn.Sequential(
                nn.Conv2d(num_feat, num_feat * 9, 3, 1, 1),
                nn.PixelShuffle(3)
            )
        elif upscale == 4:
            self.upsampler = nn.Sequential(
                nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1),
                nn.PixelShuffle(2),
                nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1),
                nn.PixelShuffle(2)
            )
        else:
            # 如果不需要上采样（如去噪任务）
            self.upsampler = nn.Identity()

        # 4. 输出层
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)

    def forward(self, x):
        """
        前向传播

        Args:
            x (Tensor): 输入图像，shape (B, C, H, W)

        Returns:
            Tensor: 输出图像，shape (B, C, H*upscale, W*upscale)
        """
        # 特征提取
        feat = self.conv_first(x)

        # 主干网络
        feat = self.body(feat)

        # 上采样
        feat = self.upsampler(feat)

        # 输出
        out = self.conv_last(feat)

        return out


# ============================================================================
# 示例 2: 带残差连接的网络
# ============================================================================

class ResidualBlock(nn.Module):
    """残差块"""

    def __init__(self, num_feat=64):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)

    def forward(self, x):
        identity = x
        out = self.conv1(x)
        out = self.relu(out)
        out = self.conv2(out)
        out = out + identity  # 残差连接
        return out


@ARCH_REGISTRY.register()
class ResidualNet(nn.Module):
    """
    带残差连接的网络架构

    适用于: 深层网络，需要残差连接缓解梯度消失

    Args:
        num_in_ch (int): 输入通道数
        num_out_ch (int): 输出通道数
        num_feat (int): 特征通道数
        num_block (int): 残差块数量
        upscale (int): 上采样倍数
    """

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_block: int = 16,
        upscale: int = 4
    ):
        super(ResidualNet, self).__init__()

        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)

        # 创建多个残差块
        self.body = nn.Sequential(
            *[ResidualBlock(num_feat) for _ in range(num_block)]
        )

        self.conv_after_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)

        # 上采样
        self.upsampler = self._make_upsampler(upscale, num_feat)

        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)

    def _make_upsampler(self, upscale, num_feat):
        """创建上采样层"""
        if upscale == 2:
            return nn.Sequential(
                nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1),
                nn.PixelShuffle(2)
            )
        elif upscale == 4:
            return nn.Sequential(
                nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1),
                nn.PixelShuffle(2),
                nn.Conv2d(num_feat, num_feat * 4, 3, 1, 1),
                nn.PixelShuffle(2)
            )
        else:
            return nn.Identity()

    def forward(self, x):
        feat = self.conv_first(x)

        # 主干网络 + 全局残差连接
        body_feat = self.conv_after_body(self.body(feat))
        feat = feat + body_feat

        feat = self.upsampler(feat)
        out = self.conv_last(feat)

        return out


# ============================================================================
# 示例 3: 多尺度网络
# ============================================================================

@ARCH_REGISTRY.register()
class MultiScaleNet(nn.Module):
    """
    多尺度网络架构

    适用于: 需要处理多尺度信息的任务

    Args:
        num_in_ch (int): 输入通道数
        num_out_ch (int): 输出通道数
        num_feat (int): 特征通道数
    """

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64
    ):
        super(MultiScaleNet, self).__init__()

        # 多尺度特征提取
        self.scale1 = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.scale2 = nn.Conv2d(num_in_ch, num_feat, 5, 1, 2)
        self.scale3 = nn.Conv2d(num_in_ch, num_feat, 7, 1, 3)

        # 特征融合
        self.fusion = nn.Conv2d(num_feat * 3, num_feat, 1, 1, 0)

        # 主干网络
        self.body = nn.Sequential(
            nn.Conv2d(num_feat, num_feat, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_feat, num_feat, 3, 1, 1),
        )

        # 输出
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)

    def forward(self, x):
        # 多尺度特征
        feat1 = self.scale1(x)
        feat2 = self.scale2(x)
        feat3 = self.scale3(x)

        # 融合
        feat = torch.cat([feat1, feat2, feat3], dim=1)
        feat = self.fusion(feat)

        # 处理
        feat = self.body(feat)

        # 输出
        out = self.conv_last(feat)

        return out


# ============================================================================
# 示例 4: 注意力机制网络
# ============================================================================

class ChannelAttention(nn.Module):
    """通道注意力模块"""

    def __init__(self, num_feat, reduction=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(num_feat, num_feat // reduction, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_feat // reduction, num_feat, 1, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        y = self.avg_pool(x)
        y = self.fc(y)
        return x * y


@ARCH_REGISTRY.register()
class AttentionNet(nn.Module):
    """
    带注意力机制的网络

    适用于: 需要关注重要特征的任务

    Args:
        num_in_ch (int): 输入通道数
        num_out_ch (int): 输出通道数
        num_feat (int): 特征通道数
        num_block (int): 注意力块数量
    """

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_block: int = 8
    ):
        super(AttentionNet, self).__init__()

        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)

        # 创建带注意力的模块
        blocks = []
        for _ in range(num_block):
            blocks.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
            blocks.append(nn.ReLU(inplace=True))
            blocks.append(ChannelAttention(num_feat))
        self.body = nn.Sequential(*blocks)

        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = self.body(feat)
        out = self.conv_last(feat)
        return out


# ============================================================================
# 工具函数
# ============================================================================

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


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == '__main__':
    """
    测试网络
    """
    # 创建网络
    net = SimpleNet(num_in_ch=3, num_out_ch=3, num_feat=64, upscale=4)

    # 测试前向传播
    x = torch.randn(1, 3, 64, 64)
    y = net(x)

    print(f"输入形状: {x.shape}")
    print(f"输出形状: {y.shape}")

    # 计算参数量
    num_params = sum(p.numel() for p in net.parameters())
    print(f"参数量: {num_params / 1e6:.2f}M")

    # 测试梯度
    loss = y.sum()
    loss.backward()
    print("✅ 梯度反向传播正常")

