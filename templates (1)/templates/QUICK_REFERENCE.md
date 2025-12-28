# BasicSR 网络移植快速参考指南

一页纸快速参考，帮助你30分钟内完成网络移植

---

## 📝 核心步骤（5步）

```
1. 网络架构 → 2. 配置文件 → 3. 测试 → 4. 训练 → 5. 评估
```

---

## 🚀 最小化示例（15分钟快速开始）

### 步骤 1: 创建网络 (5分钟)

```python
# basicsr/archs/mynet_arch.py
from basicsr.utils.registry import ARCH_REGISTRY
import torch.nn as nn

@ARCH_REGISTRY.register()
class MyNet(nn.Module):
    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, upscale=4):
        super().__init__()
        self.conv1 = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(
            nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.ReLU(),
        )
        self.upsampler = nn.Upsample(scale_factor=upscale, mode='bicubic')
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)

    def forward(self, x):
        feat = self.conv1(x)
        feat = self.body(feat)
        feat = self.upsampler(feat)
        return self.conv_last(feat)
```

### 步骤 2: 创建训练配置 (5分钟)

```yaml
# options/train/MyNet/train_MyNet_x4.yml
name: MyNet_x4_DIV2K
model_type: SRModel
scale: 4
num_gpu: 1
manual_seed: 0

datasets:
  train:
    name: DIV2K
    type: PairedImageDataset
    dataroot_gt: datasets/DIV2K/train_HR
    dataroot_lq: datasets/DIV2K/train_LR_x4
    io_backend: {type: disk}
    gt_size: 128
    use_hflip: true
    use_rot: true
    num_worker_per_gpu: 4
    batch_size_per_gpu: 8

  val:
    name: Set5
    type: PairedImageDataset
    dataroot_gt: datasets/Set5/GTmod12
    dataroot_lq: datasets/Set5/LRbicx4
    io_backend: {type: disk}

network_g:
  type: MyNet
  num_in_ch: 3
  num_out_ch: 3
  num_feat: 64
  upscale: 4

path:
  pretrain_network_g: ~
  strict_load_g: true

train:
  optim_g:
    type: Adam
    lr: !!float 1e-4
  scheduler:
    type: MultiStepLR
    milestones: [100000, 200000]
    gamma: 0.5
  total_iter: 300000
  pixel_opt:
    type: L1Loss
    loss_weight: 1.0

val:
  val_freq: !!float 5e3
  save_img: false
  metrics:
    psnr: {type: calculate_psnr, crop_border: 4}

logger:
  print_freq: 100
  save_checkpoint_freq: !!float 5e3
  use_tb_logger: true
```

### 步骤 3: 运行训练 (5分钟)

```bash
# 测试配置文件
python basicsr/train.py -opt options/train/MyNet/train_MyNet_x4.yml --debug

# 正式训练
python basicsr/train.py -opt options/train/MyNet/train_MyNet_x4.yml
```

---

## 📋 文件对应关系

| 模块 | 文件位置 | 配置键 | 必需性 |
|------|---------|--------|--------|
| 网络架构 | `basicsr/archs/mynet_arch.py` | `network_g: type: MyNet` | ✅ 必需 |
| 数据集 | `basicsr/data/mydata_dataset.py` | `datasets: type: MyData` | ⚠️ 可选 |
| 损失函数 | `basicsr/losses/myloss_loss.py` | `train: pixel_opt: type: MyLoss` | ⚠️ 可选 |
| 模型 | `basicsr/models/mymodel_model.py` | `model_type: MyModel` | ⚠️ 可选 |
| 训练配置 | `options/train/MyNet/train_*.yml` | - | ✅ 必需 |
| 测试配置 | `options/test/MyNet/test_*.yml` | - | ✅ 必需 |

**说明**:
- ✅ **必需**: 网络架构和配置文件是必需的
- ⚠️ **可选**: 数据集/损失/模型可以复用现有的（推荐）

---

## 🔄 Registry 注册机制

```python
# 所有模块都通过装饰器注册
@ARCH_REGISTRY.register()      # 网络架构
@DATASET_REGISTRY.register()   # 数据集
@LOSS_REGISTRY.register()      # 损失函数
@MODEL_REGISTRY.register()     # 模型

# 配置文件中通过 type 调用
network_g:
  type: MyNet  # → 调用 @ARCH_REGISTRY.register() 注册的 MyNet
```

---

## 🎯 常见场景

### 场景 1: 只有新网络架构（最常见）✅

```
需要创建:
  ✅ archs/mynet_arch.py
  ✅ options/train/MyNet/train_MyNet_x4.yml

复用现有:
  ✅ data: PairedImageDataset
  ✅ losses: L1Loss / CharbonnierLoss
  ✅ models: SRModel
```

### 场景 2: 新网络 + 新数据集

```
需要创建:
  ✅ archs/mynet_arch.py
  ✅ data/mydata_dataset.py
  ✅ options/train/MyNet/train_MyNet_x4.yml

复用现有:
  ✅ losses: L1Loss
  ✅ models: SRModel
```

### 场景 3: 完整新项目（GAN）

```
需要创建:
  ✅ archs/mygen_arch.py (生成器)
  ✅ archs/mydisc_arch.py (判别器)
  ✅ losses/myloss_loss.py (可选)
  ✅ models/mygan_model.py (自定义训练逻辑)
  ✅ options/train/MyGAN/train_MyGAN_x4.yml

复用现有:
  ✅ data: PairedImageDataset
```

---

## 🔧 调试检查清单

### 1. 网络测试

```python
from basicsr.archs import build_network
net = build_network({'type': 'MyNet', 'num_in_ch': 3, 'num_out_ch': 3, 'upscale': 4})
x = torch.randn(1, 3, 64, 64)
y = net(x)
print(y.shape)  # 应该是 (1, 3, 256, 256)
```

### 2. 数据集测试

```python
from basicsr.data import build_dataset
dataset = build_dataset({
    'type': 'PairedImageDataset',
    'dataroot_gt': '...',
    'dataroot_lq': '...',
    'io_backend': {'type': 'disk'}
})
sample = dataset[0]
print(sample['lq'].shape, sample['gt'].shape)
```

### 3. 配置文件测试

```bash
python basicsr/train.py -opt config.yml --debug
```

---

## ⚡ 性能优化

### 数据加载优化

```yaml
datasets:
  train:
    num_worker_per_gpu: 6      # 增加 worker
    prefetch_mode: cpu         # 使用预取
    pin_memory: true           # 锁定内存
```

### 训练优化

```yaml
train:
  use_amp: true               # 混合精度训练（降低显存）
```

### 多GPU训练

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 python -m torch.distributed.launch \
  --nproc_per_node=4 --master_port=4321 \
  basicsr/train.py -opt config.yml --launcher pytorch
```

---

## 📊 常用参数速查

### 网络参数

```python
num_in_ch: 3          # 输入通道 (RGB=3)
num_out_ch: 3         # 输出通道
num_feat: 64          # 特征通道 (常用: 32, 64, 128)
upscale: 4            # 超分倍数 (1, 2, 3, 4, 8)
```

### 训练参数

```yaml
batch_size_per_gpu: 16    # 批大小 (根据显存调整)
lr: 1e-4                  # 学习率 (常用: 1e-3 ~ 1e-5)
total_iter: 300000        # 总迭代次数
gt_size: 128              # GT patch 大小 (64, 96, 128, 192, 256)
```

### 损失权重

```yaml
pixel_opt:
  loss_weight: 1.0        # 像素损失权重
perceptual_opt:
  loss_weight: 0.1        # 感知损失权重（通常 << 1.0）
gan_opt:
  loss_weight: 0.1        # GAN 损失权重
```

---

## 🆘 常见错误

### 错误 1: `ModuleNotFoundError: No module named 'xxx'`

**原因**: 没有注册或导入模块

**解决**:
```python
# 确保使用了装饰器
@ARCH_REGISTRY.register()
class MyNet(...):

# 确保 __init__.py 中导入
# basicsr/archs/__init__.py 会自动导入
```

### 错误 2: `KeyError: 'No object named 'MyNet' found'`

**原因**: 配置文件中的 `type` 与注册名不匹配

**解决**:
```yaml
# 配置文件
network_g:
  type: MyNet  # 必须与 @ARCH_REGISTRY.register() 后的类名一致
```

### 错误 3: `RuntimeError: shape mismatch`

**原因**: 网络输出尺寸不对

**解决**: 检查上采样倍数是否正确

### 错误 4: `CUDA out of memory`

**解决**:
```yaml
# 减小 batch_size 或 gt_size
batch_size_per_gpu: 8  # 从 16 改为 8
gt_size: 96            # 从 128 改为 96
```

---

## 📚 模板文件索引

| 文件 | 用途 | 复制到 |
|------|------|--------|
| `arch_template.py` | 网络架构模板 | `basicsr/archs/` |
| `data_template.py` | 数据集模板 | `basicsr/data/` |
| `loss_template.py` | 损失函数模板 | `basicsr/losses/` |
| `model_template.py` | 模型模板 | `basicsr/models/` |
| `train_config_template.yml` | 训练配置模板 | `options/train/` |
| `test_config_template.yml` | 测试配置模板 | `options/test/` |

---

## 🎓 学习资源

- **完整指南**: `network_migration_guide.md`
- **官方文档**: https://github.com/XPixelGroup/BasicSR
- **示例代码**: `basicsr/archs/rrdbnet_arch.py`

---

## ✅ 移植检查清单

- [ ] 网络架构已创建并注册
- [ ] 训练配置文件已创建
- [ ] 测试配置文件已创建
- [ ] 网络前向传播测试通过
- [ ] 数据加载测试通过
- [ ] Debug 模式训练测试通过
- [ ] 正式训练启动成功
- [ ] TensorBoard 可视化正常

---

**快速帮助**: 遇到问题先检查这个列表，90%的问题都在这里！

**最后更新**: 2025-01-XX

