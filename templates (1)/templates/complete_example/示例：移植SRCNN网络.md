# 完整示例：移植 SRCNN 网络到 BasicSR

手把手教你移植一个简单的超分网络（SRCNN）

---

## 📖 背景

**SRCNN (Super-Resolution Convolutional Neural Network)**
- 论文: "Image Super-Resolution Using Deep Convolutional Networks"
- 结构: 3 层卷积网络（超简单，适合学习）
- 任务: 图像超分辨率（2x/3x/4x）

**网络结构**:
```
Input (LR)
  → Conv(9x9, 64) + ReLU
  → Conv(1x1, 32) + ReLU
  → Conv(5x5, 3)
  → Output (SR)
```

---

## 🎯 移植步骤

### 步骤 1: 创建网络架构（10分钟）

**文件**: `basicsr/archs/srcnn_arch.py`

```python
"""
SRCNN 网络架构
论文: Image Super-Resolution Using Deep Convolutional Networks
"""

import torch
import torch.nn as nn
from basicsr.utils.registry import ARCH_REGISTRY


@ARCH_REGISTRY.register()
class SRCNN(nn.Module):
    """
    SRCNN 网络

    Args:
        num_in_ch (int): 输入通道数，默认 3 (RGB)
        num_out_ch (int): 输出通道数，默认 3
        num_feat (int): 中间特征数，默认 64
        upscale (int): 上采样倍数（通过预上采样实现）
    """

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        upscale: int = 4
    ):
        super(SRCNN, self).__init__()

        self.upscale = upscale

        # 预上采样（使用双三次插值）
        self.upsample = nn.Upsample(
            scale_factor=upscale,
            mode='bicubic',
            align_corners=False
        )

        # SRCNN 三层结构
        self.conv1 = nn.Conv2d(num_in_ch, num_feat, kernel_size=9, padding=4)
        self.conv2 = nn.Conv2d(num_feat, num_feat // 2, kernel_size=1, padding=0)
        self.conv3 = nn.Conv2d(num_feat // 2, num_out_ch, kernel_size=5, padding=2)

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        """
        前向传播

        Args:
            x (Tensor): 输入 LR 图像 (B, 3, H, W)

        Returns:
            Tensor: 输出 SR 图像 (B, 3, H*upscale, W*upscale)
        """
        # 预上采样
        x = self.upsample(x)

        # SRCNN 三层
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.conv3(x)

        return x


if __name__ == '__main__':
    # 测试网络
    model = SRCNN(num_in_ch=3, num_out_ch=3, num_feat=64, upscale=4)

    x = torch.randn(1, 3, 64, 64)
    y = model(x)

    print(f"输入: {x.shape}")
    print(f"输出: {y.shape}")
    print(f"参数量: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")
    print("✅ SRCNN 测试通过")
```

**测试**:

```bash
cd basicsr/archs
python srcnn_arch.py
# 应输出: 输入: torch.Size([1, 3, 64, 64])
#        输出: torch.Size([1, 3, 256, 256])
#        ✅ SRCNN 测试通过
```

---

### 步骤 2: 创建训练配置（15分钟）

**文件**: `options/train/SRCNN/train_SRCNN_x4.yml`

```yaml
# SRCNN x4 训练配置

# ====== 基本信息 ======
name: SRCNN_x4_DIV2K
model_type: SRModel           # 使用标准 SR 模型（不需要自定义）
scale: 4
num_gpu: 1
manual_seed: 0

# ====== 数据集 ======
datasets:
  train:
    name: DIV2K
    type: PairedImageDataset  # 使用现有数据集
    dataroot_gt: datasets/DIV2K/DIV2K_train_HR
    dataroot_lq: datasets/DIV2K/DIV2K_train_LR_bicubic/X4

    io_backend:
      type: disk

    # 数据增强
    gt_size: 96               # SRCNN 用较小的 patch
    use_hflip: true
    use_rot: true

    # DataLoader
    num_worker_per_gpu: 4
    batch_size_per_gpu: 16
    dataset_enlarge_ratio: 100
    prefetch_mode: ~

  val:
    name: Set5
    type: PairedImageDataset
    dataroot_gt: datasets/Set5/GTmod12
    dataroot_lq: datasets/Set5/LRbicx4
    io_backend:
      type: disk

# ====== 网络配置 ======
network_g:
  type: SRCNN              # 注册的网络名称
  num_in_ch: 3
  num_out_ch: 3
  num_feat: 64
  upscale: 4

# ====== 路径 ======
path:
  pretrain_network_g: ~
  strict_load_g: true
  resume_state: ~

# ====== 训练设置 ======
train:
  ema_decay: 0              # SRCNN 不使用 EMA

  # 优化器
  optim_g:
    type: Adam
    lr: !!float 1e-4
    weight_decay: 0
    betas: [0.9, 0.999]

  # 学习率调度
  scheduler:
    type: MultiStepLR
    milestones: [50000, 100000, 150000, 200000]
    gamma: 0.5

  # 训练迭代
  total_iter: 250000
  warmup_iter: -1

  # 损失函数（使用简单的 MSE）
  pixel_opt:
    type: MSELoss           # SRCNN 原论文用 MSE
    loss_weight: 1.0
    reduction: mean

# ====== 验证设置 ======
val:
  val_freq: !!float 5e3
  save_img: false

  metrics:
    psnr:
      type: calculate_psnr
      crop_border: 4
      test_y_channel: true  # SRCNN 通常在 Y 通道评估

# ====== 日志设置 ======
logger:
  print_freq: 100
  save_checkpoint_freq: !!float 5e3
  use_tb_logger: true
  wandb:
    project: ~

# ====== 分布式设置 ======
dist_params:
  backend: nccl
  port: 29500
```

---

### 步骤 3: 创建测试配置（5分钟）

**文件**: `options/test/SRCNN/test_SRCNN.yml`

```yaml
# SRCNN 测试配置

name: SRCNN_test_Set5
model_type: SRModel
scale: 4
num_gpu: 1
manual_seed: 0

# ====== 测试数据集 ======
datasets:
  test_1:
    name: Set5
    type: PairedImageDataset
    dataroot_gt: datasets/Set5/GTmod12
    dataroot_lq: datasets/Set5/LRbicx4
    io_backend:
      type: disk

  test_2:
    name: Set14
    type: PairedImageDataset
    dataroot_gt: datasets/Set14/GTmod12
    dataroot_lq: datasets/Set14/LRbicx4
    io_backend:
      type: disk

# ====== 网络配置（必须与训练时一致） ======
network_g:
  type: SRCNN
  num_in_ch: 3
  num_out_ch: 3
  num_feat: 64
  upscale: 4

# ====== 模型路径 ======
path:
  pretrain_network_g: experiments/SRCNN_x4_DIV2K/models/net_g_latest.pth
  strict_load_g: true

# ====== 评估设置 ======
val:
  save_img: true
  suffix: ~

  metrics:
    psnr:
      type: calculate_psnr
      crop_border: 4
      test_y_channel: true

    ssim:
      type: calculate_ssim
      crop_border: 4
      test_y_channel: true
```

---

### 步骤 4: 运行训练（实战）

```bash
# 1. 确保数据集已准备好
ls datasets/DIV2K/DIV2K_train_HR/
ls datasets/DIV2K/DIV2K_train_LR_bicubic/X4/

# 2. Debug 模式测试（跑几个 iter）
python basicsr/train.py \
  -opt options/train/SRCNN/train_SRCNN_x4.yml \
  --debug

# 3. 检查输出
# 应该看到:
#   - 网络创建成功
#   - 数据加载正常
#   - 损失正常下降
#   - 无报错

# 4. 正式训练
python basicsr/train.py \
  -opt options/train/SRCNN/train_SRCNN_x4.yml

# 5. 监控训练（另开终端）
tensorboard --logdir tb_logger/
```

---

### 步骤 5: 测试评估

```bash
# 等训练完成或中途测试

# 测试最新模型
python basicsr/test.py \
  -opt options/test/SRCNN/test_SRCNN.yml

# 测试特定 checkpoint
# 修改配置文件中的 pretrain_network_g 路径
# path:
#   pretrain_network_g: experiments/SRCNN_x4_DIV2K/models/net_g_100000.pth

# 查看结果
ls results/SRCNN_test_Set5/visualization/Set5/
```

---

## 📊 预期结果

### 训练日志示例

```
[SRCNN..][epoch:  0, iter:      100, lr:(1.000e-04,)] [eta: 2 days, 15:23:45, time (data): 0.234 (0.012)] l_pix: 1.2345e-02
[SRCNN..][epoch:  0, iter:      200, lr:(1.000e-04,)] [eta: 2 days, 14:52:31, time (data): 0.231 (0.011)] l_pix: 8.7654e-03
...

Validation Set5
	 # psnr: 28.4321	Best: 28.4321 @ 5000 iter
```

### 测试结果示例

```
Testing Set5...
Test baby	 psnr: 32.15	 ssim: 0.9145
Test bird	 psnr: 31.24	 ssim: 0.9234
Test butterfly	 psnr: 28.67	 ssim: 0.8956
...
Average: psnr: 30.52	 ssim: 0.9112
```

### 文件输出

```
experiments/SRCNN_x4_DIV2K/
├── models/
│   ├── net_g_5000.pth
│   ├── net_g_10000.pth
│   └── net_g_latest.pth
├── training_states/
│   └── 5000.state
├── visualization/          # 验证图像
└── train_SRCNN_x4_DIV2K_*.log

results/SRCNN_test_Set5/
├── visualization/
│   ├── Set5/
│   │   ├── baby.png
│   │   ├── bird.png
│   │   └── ...
│   └── Set14/
│       └── ...
└── test_SRCNN_test_Set5_*.log
```

---

## 🎓 学到的技巧

### 技巧 1: 最小化修改

SRCNN 示例中：
- ✅ **只创建了网络架构文件**（1 个文件）
- ✅ **复用现有数据集**（PairedImageDataset）
- ✅ **复用现有损失**（MSELoss）
- ✅ **复用现有模型**（SRModel）

**结论**: 大多数情况下只需要创建网络架构！

---

### 技巧 2: 配置文件调试

```yaml
# Debug 模式快速迭代
name: debug_SRCNN             # 添加 debug 前缀
datasets:
  train:
    batch_size_per_gpu: 4     # 减小 batch
    num_worker_per_gpu: 0     # 0 worker 方便调试
train:
  total_iter: 1000            # 减少迭代
val:
  val_freq: 100               # 频繁验证
logger:
  print_freq: 10              # 频繁打印
```

---

### 技巧 3: 渐进式训练

```bash
# 第 1 天: 小数据集，确保能跑通
# 修改配置: dataroot_gt: datasets/DIV2K_subset (只放10张图)
python basicsr/train.py -opt config.yml

# 第 2 天: 完整数据集，短时间训练
# total_iter: 10000
python basicsr/train.py -opt config.yml

# 第 3 天: 完整训练
# total_iter: 250000
python basicsr/train.py -opt config.yml
```

---

## 📈 性能对比

### SRCNN vs 其他网络

| 网络 | 参数量 | PSNR (Set5 x4) | 训练时间 |
|------|--------|----------------|---------|
| **SRCNN** | 57K | ~30.5 dB | 2-3 小时 |
| EDSR | 43M | ~32.5 dB | 2-3 天 |
| RCAN | 16M | ~32.6 dB | 3-4 天 |

**结论**: SRCNN 简单快速，适合学习和原型验证

---

## 🔧 常见问题

### Q1: 训练时显存不足？

**A**: SRCNN 很小，不应该显存不足。检查：

```yaml
# 减小 batch_size 或 gt_size
batch_size_per_gpu: 8   # 从 16 改为 8
gt_size: 64             # 从 96 改为 64
```

### Q2: 损失不收敛？

**A**: 检查学习率和数据

```yaml
# 降低学习率
lr: !!float 5e-5  # 从 1e-4 改为 5e-5

# 或增加预热
warmup_iter: 1000
```

### Q3: PSNR 太低？

**A**: SRCNN 是早期网络，性能有限。改进方向：

1. 增加网络层数
2. 增加特征通道数
3. 添加残差连接
4. 使用更好的上采样方法

---

## 🎉 成功！

恭喜你完成了第一个网络移植！

**下一步**:
- ✅ 尝试修改 SRCNN 结构提升性能
- ✅ 尝试移植更复杂的网络（EDSR、RCAN）
- ✅ 尝试添加自定义损失函数
- ✅ 尝试创建自定义数据集

---

**相关文件**:
- 网络代码: `basicsr/archs/srcnn_arch.py`
- 训练配置: `options/train/SRCNN/train_SRCNN_x4.yml`
- 测试配置: `options/test/SRCNN/test_SRCNN.yml`

