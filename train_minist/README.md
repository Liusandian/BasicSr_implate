# MNIST手写数字识别项目

这是一个使用PyTorch实现的MNIST手写数字识别项目，包含了深度学习的完整流程示例。

## 项目结构

```
train_mnist/
├── main.py                      # 主训练脚本
├── requirements.txt             # 依赖包列表
├── README.md                    # 项目说明（本文件）
├── MNIST深度学习完整教程.md      # 详细教程文档
└── runs/                        # TensorBoard日志目录（训练后生成）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行训练

**基础训练（默认参数）：**
```bash
python main.py
```

**启用TensorBoard并保存模型：**
```bash
python main.py --tensorboard --save-model
```

**自定义训练参数：**
```bash
python main.py --epochs 20 --batch-size 128 --lr 1.0 --tensorboard --save-model
```

### 3. 查看训练过程

在另一个终端运行：
```bash
tensorboard --logdir=runs
```

然后在浏览器中打开 http://localhost:6006

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--batch-size` | int | 64 | 训练批次大小 |
| `--test-batch-size` | int | 1000 | 测试批次大小 |
| `--epochs` | int | 14 | 训练轮数 |
| `--lr` | float | 1.0 | 学习率 |
| `--gamma` | float | 0.7 | 学习率衰减系数 |
| `--no-accel` | flag | - | 禁用加速器（GPU） |
| `--seed` | int | 1 | 随机种子 |
| `--log-interval` | int | 10 | 日志输出间隔 |
| `--save-model` | flag | - | 训练结束后保存模型 |
| `--tensorboard` | flag | - | 启用TensorBoard日志 |
| `--dry-run` | flag | - | 快速测试模式 |

## 项目特点

✅ **完整的训练流程**：从数据加载到模型保存  
✅ **详细的代码注释**：每行关键代码都有解释  
✅ **TensorBoard支持**：可视化训练过程  
✅ **灵活的配置**：支持命令行参数调整  
✅ **GPU加速支持**：自动检测并使用GPU  
✅ **模型检查点**：保存完整的训练状态  

## 模型架构

```
输入 [1, 28, 28]
    ↓
Conv2d(1→32) + ReLU
    ↓
Conv2d(32→64) + ReLU
    ↓
MaxPool2d(2x2)
    ↓
Dropout(0.25)
    ↓
Flatten [9216]
    ↓
Linear(9216→128) + ReLU
    ↓
Dropout(0.5)
    ↓
Linear(128→10)
    ↓
LogSoftmax
    ↓
输出 [10]
```

**总参数量**：约120万

## 预期结果

- **训练准确率**：~99%
- **测试准确率**：~98-99%
- **训练时间**：CPU约10-15分钟，GPU约2-3分钟（14个epochs）

## 学习资源

详细的深度学习概念讲解请查看：**[MNIST深度学习完整教程.md](MNIST深度学习完整教程.md)**

该文档包含：
- 神经网络结构详解
- 数据预处理原理
- 损失函数与优化器
- 梯度下降与反向传播
- 模型保存与加载
- TensorBoard使用指南

## 常见问题

**Q: 如何使用GPU训练？**  
A: 如果安装了CUDA版本的PyTorch，程序会自动使用GPU。可以用 `--no-accel` 强制使用CPU。

**Q: 模型文件保存在哪里？**  
A: 使用 `--save-model` 参数后，模型会保存在当前目录下：
- `mnist_cnn.pt`：模型参数
- `mnist_cnn_checkpoint.pt`：完整检查点

**Q: 如何修改网络结构？**  
A: 编辑 `main.py` 中的 `Net` 类，修改层的定义和 `forward` 方法。

**Q: 训练过程中断了怎么办？**  
A: 可以从检查点恢复训练（需要修改代码加载检查点）。

## 扩展建议

1. **数据增强**：添加随机旋转、平移等
2. **不同优化器**：尝试Adam、SGD+Momentum
3. **网络结构**：尝试更深的网络或残差连接
4. **正则化**：添加L2正则化、BatchNorm
5. **迁移学习**：将模型应用到其他数据集

## 依赖版本

- Python 3.8+
- PyTorch 2.0+
- torchvision 0.15+
- tensorboard 2.14+

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，请提交Issue。

---

**Happy Learning! 🎓🚀**

