#!/usr/bin/env python3
"""
自动创建新网络脚本

用法:
    python create_new_network.py --name MyNet --scale 4 --task sr

功能:
    自动创建网络移植所需的所有文件（架构、配置等）
"""

import argparse
import os
from pathlib import Path
import shutil


TEMPLATES = {
    'arch': 'arch_template.py',
    'train_config': 'train_config_template.yml',
    'test_config': 'test_config_template.yml',
}


def create_network_arch(name, output_dir):
    """创建网络架构文件"""
    template_path = Path('templates') / 'arch_template.py'
    output_path = output_dir / 'archs' / f'{name.lower()}_arch.py'

    # 读取模板
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换占位符（保留示例代码）
    content = f'''"""
{name} 网络架构

自动生成自模板，请根据需求修改
"""

{content}

# ============================================================================
# {name} 网络实现
# ============================================================================

@ARCH_REGISTRY.register()
class {name}(nn.Module):
    """
    {name} 网络

    TODO: 添加网络说明

    Args:
        num_in_ch (int): 输入通道数
        num_out_ch (int): 输出通道数
        num_feat (int): 特征通道数
        upscale (int): 上采样倍数
    """

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        upscale: int = 4
    ):
        super({name}, self).__init__()

        # TODO: 实现网络结构
        self.conv1 = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(
            nn.Conv2d(num_feat, num_feat, 3, 1, 1),
            nn.ReLU(inplace=True),
        )
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)

    def forward(self, x):
        """
        TODO: 实现前向传播
        """
        feat = self.conv1(x)
        feat = self.body(feat)
        out = self.conv_last(feat)
        return out
'''

    # 创建目录
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 创建网络架构: {output_path}")
    return output_path


def create_train_config(name, scale, dataset, output_dir):
    """创建训练配置文件"""
    output_path = output_dir / 'options' / 'train' / name / f'train_{name}_x{scale}.yml'

    content = f'''# {name} x{scale} 训练配置

name: {name}_x{scale}_{dataset}
model_type: SRModel
scale: {scale}
num_gpu: auto
manual_seed: 0

# ====== 数据集 ======
datasets:
  train:
    name: {dataset}
    type: PairedImageDataset
    dataroot_gt: datasets/{dataset}/{dataset}_train_HR
    dataroot_lq: datasets/{dataset}/{dataset}_train_LR_bicubic/X{scale}

    io_backend:
      type: disk

    gt_size: 128
    use_hflip: true
    use_rot: true

    num_worker_per_gpu: 6
    batch_size_per_gpu: 16
    dataset_enlarge_ratio: 100
    prefetch_mode: ~

  val:
    name: Set5
    type: PairedImageDataset
    dataroot_gt: datasets/Set5/GTmod12
    dataroot_lq: datasets/Set5/LRbicx{scale}
    io_backend:
      type: disk

# ====== 网络配置 ======
network_g:
  type: {name}
  num_in_ch: 3
  num_out_ch: 3
  num_feat: 64
  upscale: {scale}

# ====== 路径 ======
path:
  pretrain_network_g: ~
  strict_load_g: true
  resume_state: ~

# ====== 训练设置 ======
train:
  ema_decay: 0.999

  optim_g:
    type: Adam
    lr: !!float 1e-4
    weight_decay: 0
    betas: [0.9, 0.99]

  scheduler:
    type: MultiStepLR
    milestones: [200000, 400000, 600000, 800000]
    gamma: 0.5

  total_iter: 1000000
  warmup_iter: -1

  # 损失函数
  pixel_opt:
    type: L1Loss
    loss_weight: 1.0
    reduction: mean

# ====== 验证设置 ======
val:
  val_freq: !!float 5e3
  save_img: false

  metrics:
    psnr:
      type: calculate_psnr
      crop_border: {scale}
      test_y_channel: false

# ====== 日志设置 ======
logger:
  print_freq: 100
  save_checkpoint_freq: !!float 5e3
  use_tb_logger: true
  wandb:
    project: ~

dist_params:
  backend: nccl
  port: 29500
'''

    # 创建目录
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 创建训练配置: {output_path}")
    return output_path


def create_test_config(name, scale, output_dir):
    """创建测试配置文件"""
    output_path = output_dir / 'options' / 'test' / name / f'test_{name}.yml'

    content = f'''# {name} 测试配置

name: {name}_test
model_type: SRModel
scale: {scale}
num_gpu: 1
manual_seed: 0

# ====== 测试数据集 ======
datasets:
  test_1:
    name: Set5
    type: PairedImageDataset
    dataroot_gt: datasets/Set5/GTmod12
    dataroot_lq: datasets/Set5/LRbicx{scale}
    io_backend:
      type: disk

  test_2:
    name: Set14
    type: PairedImageDataset
    dataroot_gt: datasets/Set14/GTmod12
    dataroot_lq: datasets/Set14/LRbicx{scale}
    io_backend:
      type: disk

# ====== 网络配置 ======
network_g:
  type: {name}
  num_in_ch: 3
  num_out_ch: 3
  num_feat: 64
  upscale: {scale}

# ====== 模型路径 ======
path:
  pretrain_network_g: experiments/{name}_x{scale}_DIV2K/models/net_g_latest.pth
  strict_load_g: true

# ====== 评估设置 ======
val:
  save_img: true
  suffix: ~

  metrics:
    psnr:
      type: calculate_psnr
      crop_border: {scale}
      test_y_channel: false

    ssim:
      type: calculate_ssim
      crop_border: {scale}
      test_y_channel: false
'''

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 创建测试配置: {output_path}")
    return output_path


def create_readme(name, files, output_dir):
    """创建 README 文件"""
    output_path = output_dir / f'README_{name}.md'

    content = f'''# {name} 网络移植说明

自动生成的网络移植文件

---

## 📁 已创建的文件

'''

    for desc, path in files.items():
        content += f"- **{desc}**: `{path}`\n"

    content += f'''

---

## 🚀 快速开始

### 1. 实现网络架构

编辑 `{files['网络架构']}`，实现你的网络结构。

### 2. 测试网络

```bash
cd basicsr/archs
python {name.lower()}_arch.py
```

### 3. 修改训练配置

编辑 `{files['训练配置']}`，调整超参数。

### 4. Debug 训练

```bash
python basicsr/train.py -opt {files['训练配置']} --debug
```

### 5. 正式训练

```bash
python basicsr/train.py -opt {files['训练配置']}
```

### 6. 测试评估

```bash
python basicsr/test.py -opt {files['测试配置']}
```

---

## 📝 下一步

- [ ] 实现 {name} 网络结构
- [ ] 测试网络前向传播
- [ ] 准备训练数据集
- [ ] 运行 Debug 训练
- [ ] 检查 TensorBoard
- [ ] 运行完整训练
- [ ] 评估测试结果

---

**创建时间**: {import datetime; datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**模板版本**: v1.0
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 创建说明文档: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='自动创建 BasicSR 网络移植文件')

    parser.add_argument('--name', type=str, required=True, help='网络名称（如 SRCNN）')
    parser.add_argument('--scale', type=int, default=4, help='超分倍数')
    parser.add_argument('--dataset', type=str, default='DIV2K', help='数据集名称')
    parser.add_argument('--task', type=str, default='sr', choices=['sr', 'denoise', 'deblur'],
                       help='任务类型')
    parser.add_argument('--output_dir', type=str, default='..', help='BasicSR 根目录')

    args = parser.parse_args()

    print("\n" + "="*70)
    print(f"🚀 创建 {args.name} 网络移植文件")
    print("="*70 + "\n")

    output_dir = Path(args.output_dir)

    # 创建文件
    files = {}

    # 1. 网络架构
    arch_path = create_network_arch(args.name, output_dir)
    files['网络架构'] = str(arch_path.relative_to(output_dir))

    # 2. 训练配置
    train_config = create_train_config(args.name, args.scale, args.dataset, output_dir)
    files['训练配置'] = str(train_config.relative_to(output_dir))

    # 3. 测试配置
    test_config = create_test_config(args.name, args.scale, output_dir)
    files['测试配置'] = str(test_config.relative_to(output_dir))

    # 4. README
    create_readme(args.name, files, output_dir)

    # 总结
    print("\n" + "="*70)
    print("✅ 所有文件创建完成！")
    print("="*70 + "\n")

    print("下一步:")
    print(f"  1. 编辑 {files['网络架构']}")
    print(f"  2. 运行测试: cd basicsr/archs && python {args.name.lower()}_arch.py")
    print(f"  3. Debug 训练: python basicsr/train.py -opt {files['训练配置']} --debug")
    print(f"\n详细说明请查看: README_{args.name}.md\n")


if __name__ == '__main__':
    main()

