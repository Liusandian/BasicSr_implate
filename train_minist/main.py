import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.optim.lr_scheduler import StepLR
from torch.utils.tensorboard import SummaryWriter
import os
from datetime import datetime


class Net(nn.Module):
    """
    简单的卷积神经网络（CNN）用于MNIST手写数字识别
    网络结构：
    - 两个卷积层 (conv1, conv2) 用于特征提取
    - 两个全连接层 (fc1, fc2) 用于分类
    - Dropout层用于防止过拟合
    """
    def __init__(self):
        super(Net, self).__init__()
        # 第一个卷积层：输入通道1(灰度图)，输出通道32，卷积核大小3x3，步长1
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        # 第二个卷积层：输入通道32，输出通道64，卷积核大小3x3，步长1
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        # Dropout层：在训练时随机丢弃25%的神经元
        self.dropout1 = nn.Dropout(0.25)
        # Dropout层：在训练时随机丢弃50%的神经元
        self.dropout2 = nn.Dropout(0.5)
        # 第一个全连接层：9216 = 64 * 12 * 12 (经过两次卷积和一次池化后的特征图大小)
        self.fc1 = nn.Linear(9216, 128)
        # 第二个全连接层：输出10个类别（0-9的数字）
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        """
        前向传播过程
        x: 输入图像 [batch_size, 1, 28, 28]
        """
        # 卷积层1 + ReLU激活函数
        x = self.conv1(x)  # [batch, 32, 26, 26]
        x = F.relu(x)
        # 卷积层2 + ReLU激活函数
        x = self.conv2(x)  # [batch, 64, 24, 24]
        x = F.relu(x)
        # 最大池化层：2x2窗口，步长2
        x = F.max_pool2d(x, 2)  # [batch, 64, 12, 12]
        # Dropout正则化
        x = self.dropout1(x)
        # 展平：将多维特征转换为一维向量
        x = torch.flatten(x, 1)  # [batch, 9216]
        # 全连接层1 + ReLU激活函数
        x = self.fc1(x)  # [batch, 128]
        x = F.relu(x)
        # Dropout正则化
        x = self.dropout2(x)
        # 全连接层2（输出层）
        x = self.fc2(x)  # [batch, 10]
        # Log-Softmax：将输出转换为对数概率
        output = F.log_softmax(x, dim=1)
        return output


def train(args, model, device, train_loader, optimizer, epoch, writer=None):
    """
    训练函数
    
    参数:
        args: 命令行参数
        model: 神经网络模型
        device: 运行设备（CPU或GPU）
        train_loader: 训练数据加载器
        optimizer: 优化器
        epoch: 当前epoch
        writer: TensorBoard写入器
    """
    model.train()  # 设置模型为训练模式（启用Dropout等）
    
    for batch_idx, (data, target) in enumerate(train_loader):
        # 将数据和标签移到对应设备上（CPU或GPU）
        data, target = data.to(device), target.to(device)
        
        # === 梯度下降的关键步骤 ===
        
        # 1. 清零梯度（防止梯度累积）
        optimizer.zero_grad()
        
        # 2. 前向传播：计算模型输出
        output = model(data)
        
        # 3. 计算损失函数：负对数似然损失（Negative Log Likelihood Loss）
        # 这是分类问题常用的损失函数
        loss = F.nll_loss(output, target)
        
        # 4. 反向传播：计算梯度
        # PyTorch自动计算所有参数相对于损失的梯度
        loss.backward()
        
        # 5. 参数更新：使用优化器更新模型参数
        # 根据梯度和学习率更新权重：θ = θ - lr * ∇θ
        optimizer.step()
        
        # 记录和可视化
        if batch_idx % args.log_interval == 0:
            # 打印训练信息
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))
            
            # 使用TensorBoard记录训练损失
            if writer is not None:
                global_step = (epoch - 1) * len(train_loader) + batch_idx
                writer.add_scalar('Loss/train', loss.item(), global_step)
            
            if args.dry_run:
                break


def test(model, device, test_loader, epoch=0, writer=None):
    """
    测试/验证函数
    
    参数:
        model: 神经网络模型
        device: 运行设备（CPU或GPU）
        test_loader: 测试数据加载器
        epoch: 当前epoch
        writer: TensorBoard写入器
    """
    model.eval()  # 设置模型为评估模式（关闭Dropout等）
    test_loss = 0
    correct = 0
    
    # 使用torch.no_grad()禁用梯度计算，节省内存并加速
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            # 前向传播
            output = model(data)
            # 累加批次损失
            test_loss += F.nll_loss(output, target, reduction='sum').item()
            # 获取预测结果：取概率最大的类别作为预测
            pred = output.argmax(dim=1, keepdim=True)
            # 统计正确预测的数量
            correct += pred.eq(target.view_as(pred)).sum().item()

    # 计算平均损失和准确率
    test_loss /= len(test_loader.dataset)
    accuracy = 100. * correct / len(test_loader.dataset)

    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset), accuracy))
    
    # 使用TensorBoard记录测试指标
    if writer is not None:
        writer.add_scalar('Loss/test', test_loss, epoch)
        writer.add_scalar('Accuracy/test', accuracy, epoch)
    
    return test_loss, accuracy


def main():
    """
    主函数：整个训练流程的入口
    """
    # === 1. 训练参数设置 ===
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                        help='input batch size for training (default: 64)')
    parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--epochs', type=int, default=14, metavar='N',
                        help='number of epochs to train (default: 14)')
    parser.add_argument('--lr', type=float, default=1.0, metavar='LR',
                        help='learning rate (default: 1.0)')
    parser.add_argument('--gamma', type=float, default=0.7, metavar='M',
                        help='Learning rate step gamma (default: 0.7)')
    parser.add_argument('--no-accel', action='store_true',
                        help='disables accelerator')
    parser.add_argument('--dry-run', action='store_true',
                        help='quickly check a single pass')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='how many batches to wait before logging training status')
    parser.add_argument('--save-model', action='store_true', 
                        help='For Saving the current Model')
    parser.add_argument('--tensorboard', action='store_true',
                        help='Enable TensorBoard logging')
    args = parser.parse_args()

    # === 2. 设备配置 ===
    use_accel = not args.no_accel and torch.accelerator.is_available()
    
    # 设置随机种子以确保结果可复现
    torch.manual_seed(args.seed)

    # 选择运行设备（GPU/CPU）
    if use_accel:
        device = torch.accelerator.current_accelerator()
        print(f'Using accelerator: {device}')
    else:
        device = torch.device("cpu")
        print('Using CPU')

    # === 3. 数据加载器配置 ===
    train_kwargs = {'batch_size': args.batch_size}
    test_kwargs = {'batch_size': args.test_batch_size}
    if use_accel:
        accel_kwargs = {'num_workers': 1,
                        'persistent_workers': True,
                       'pin_memory': True,
                       'shuffle': True}
        train_kwargs.update(accel_kwargs)
        test_kwargs.update(accel_kwargs)

    # === 4. 数据预处理和加载 ===
    # 数据变换：将图像转换为张量并进行标准化
    # 0.1307和0.3081是MNIST数据集的均值和标准差
    transform = transforms.Compose([
        transforms.ToTensor(),  # 将PIL图像转换为张量，值范围[0,1]
        transforms.Normalize((0.1307,), (0.3081,))  # 标准化：(x - mean) / std
    ])
    
    # 下载并加载MNIST数据集
    dataset1 = datasets.MNIST('../data', train=True, download=True,
                       transform=transform)
    dataset2 = datasets.MNIST('../data', train=False,
                       transform=transform)
    
    # 创建数据加载器（自动进行批处理和打乱）
    train_loader = torch.utils.data.DataLoader(dataset1, **train_kwargs)
    test_loader = torch.utils.data.DataLoader(dataset2, **test_kwargs)

    # === 5. 模型实例化 ===
    model = Net().to(device)
    print(f'\nModel architecture:\n{model}\n')
    
    # 计算模型参数数量
    total_params = sum(p.numel() for p in model.parameters())
    print(f'Total parameters: {total_params:,}\n')
    
    # === 6. 优化器配置 ===
    # Adadelta是一种自适应学习率的优化算法
    optimizer = optim.Adadelta(model.parameters(), lr=args.lr)

    # === 7. 学习率调度器 ===
    # StepLR：每个epoch将学习率乘以gamma（学习率衰减）
    scheduler = StepLR(optimizer, step_size=1, gamma=args.gamma)
    
    # === 8. TensorBoard初始化 ===
    writer = None
    if args.tensorboard:
        # 创建带时间戳的日志目录
        log_dir = os.path.join('runs', datetime.now().strftime('%Y%m%d-%H%M%S'))
        writer = SummaryWriter(log_dir)
        print(f'TensorBoard logging enabled. Run: tensorboard --logdir=runs\n')
        
        # 记录模型结构图
        dummy_input = torch.randn(1, 1, 28, 28).to(device)
        writer.add_graph(model, dummy_input)
    
    # === 9. 训练循环 ===
    print('Starting training...\n')
    for epoch in range(1, args.epochs + 1):
        # 训练一个epoch
        train(args, model, device, train_loader, optimizer, epoch, writer)
        # 在测试集上评估
        test_loss, accuracy = test(model, device, test_loader, epoch, writer)
        # 更新学习率
        scheduler.step()
        
        # 记录学习率到TensorBoard
        if writer is not None:
            writer.add_scalar('Learning_rate', scheduler.get_last_lr()[0], epoch)

    # === 10. 模型保存 ===
    if args.save_model:
        # 保存模型权重
        model_path = "mnist_cnn.pt"
        torch.save(model.state_dict(), model_path)
        print(f'\nModel saved to {model_path}')
        
        # 也可以保存完整的模型（包括结构）
        torch.save({
            'epoch': args.epochs,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'test_loss': test_loss,
            'accuracy': accuracy,
        }, 'mnist_cnn_checkpoint.pt')
        print(f'Checkpoint saved to mnist_cnn_checkpoint.pt')
    
    # 关闭TensorBoard writer
    if writer is not None:
        writer.close()
    
    print('\nTraining completed!')


if __name__ == '__main__':
    main()