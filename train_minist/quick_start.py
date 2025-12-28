"""
快速入门脚本
用于快速测试PyTorch环境和运行简单训练
"""

import sys

def check_environment():
    """检查PyTorch环境"""
    print("=" * 60)
    print("检查PyTorch环境")
    print("=" * 60)
    
    # 检查PyTorch
    try:
        import torch
        print(f"✓ PyTorch版本: {torch.__version__}")
        
        # 检查CUDA
        if torch.cuda.is_available():
            print(f"✓ CUDA可用: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA版本: {torch.version.cuda}")
        else:
            print("○ CUDA不可用，将使用CPU训练")
        
    except ImportError:
        print("✗ PyTorch未安装")
        print("  请运行: pip install torch torchvision")
        return False
    
    # 检查torchvision
    try:
        import torchvision
        print(f"✓ torchvision版本: {torchvision.__version__}")
    except ImportError:
        print("✗ torchvision未安装")
        print("  请运行: pip install torchvision")
        return False
    
    # 检查tensorboard
    try:
        import tensorboard
        print(f"✓ tensorboard已安装")
    except ImportError:
        print("○ tensorboard未安装（可选）")
        print("  可运行: pip install tensorboard")
    
    print("\n环境检查完成！")
    return True

def quick_test():
    """快速测试训练"""
    print("\n" + "=" * 60)
    print("运行快速测试（1个epoch）")
    print("=" * 60)
    
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torchvision import datasets, transforms
    from main import Net
    
    # 设备配置
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n使用设备: {device}")
    
    # 数据加载
    print("\n下载并加载MNIST数据...")
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    train_dataset = datasets.MNIST('../data', train=True, download=True,
                                  transform=transform)
    test_dataset = datasets.MNIST('../data', train=False, transform=transform)
    
    # 使用小批次加快测试
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=64, 
                                              shuffle=True)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=1000)
    
    # 创建模型
    print("\n创建模型...")
    model = Net().to(device)
    optimizer = optim.Adadelta(model.parameters(), lr=1.0)
    
    # 训练一个epoch
    print("\n开始训练（1个epoch）...\n")
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        if batch_idx >= 10:  # 只训练10个批次用于快速测试
            break
        
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = nn.functional.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        
        if batch_idx % 5 == 0:
            print(f'批次 {batch_idx}/10, 损失: {loss.item():.4f}')
    
    # 快速评估
    print("\n测试模型...")
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
            total += target.size(0)
            break  # 只测试一个批次
    
    accuracy = 100. * correct / total
    print(f'\n测试准确率: {correct}/{total} ({accuracy:.2f}%)')
    print("\n✓ 快速测试完成！环境配置正常。")

def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 60)
    print("下一步操作")
    print("=" * 60)
    print("\n1. 运行完整训练：")
    print("   python main.py --tensorboard --save-model")
    print("\n2. 查看训练过程（在新终端）：")
    print("   tensorboard --logdir=runs")
    print("\n3. 自定义训练参数：")
    print("   python main.py --epochs 20 --batch-size 128 --lr 1.0")
    print("\n4. 查看详细教程：")
    print("   打开文件：MNIST深度学习完整教程.md")
    print("\n5. 运行模型推理：")
    print("   python inference_example.py")
    print("\n" + "=" * 60)

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("MNIST深度学习项目 - 快速入门")
    print("=" * 60 + "\n")
    
    # 检查环境
    if not check_environment():
        print("\n请先安装必要的依赖：")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # 询问是否运行快速测试
    print("\n是否运行快速测试？(y/n):", end=" ")
    try:
        choice = input().lower().strip()
        if choice == 'y' or choice == 'yes' or choice == '':
            quick_test()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
    
    # 显示使用说明
    show_usage()
    
    print("\n祝学习愉快！🎓\n")

if __name__ == '__main__':
    main()

