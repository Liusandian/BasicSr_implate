"""
模型推理示例脚本
演示如何加载训练好的模型并进行预测
"""

import torch
import torch.nn.functional as F
from torchvision import datasets, transforms
import matplotlib.pyplot as plt
from main import Net

def load_model(model_path='mnist_cnn.pt'):
    """
    加载训练好的模型
    
    参数:
        model_path: 模型文件路径
    返回:
        加载好的模型
    """
    model = Net()
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()  # 设置为评估模式
    print(f"模型已从 {model_path} 加载")
    return model

def predict_single_image(model, image_tensor):
    """
    对单张图像进行预测
    
    参数:
        model: 训练好的模型
        image_tensor: 图像张量 [1, 28, 28]
    返回:
        predicted_class: 预测的类别（0-9）
        probabilities: 各类别的概率
    """
    with torch.no_grad():
        # 添加batch维度 [1, 1, 28, 28]
        if image_tensor.dim() == 3:
            image_tensor = image_tensor.unsqueeze(0)
        
        # 前向传播
        output = model(image_tensor)
        
        # 获取概率（log_softmax转为概率）
        probabilities = torch.exp(output)
        
        # 获取预测类别
        predicted_class = output.argmax(dim=1).item()
        
    return predicted_class, probabilities[0]

def visualize_prediction(image, true_label, predicted_label, probabilities):
    """
    可视化预测结果
    
    参数:
        image: 原始图像张量
        true_label: 真实标签
        predicted_label: 预测标签
        probabilities: 各类别概率
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # 显示图像
    if image.dim() == 3:
        image = image.squeeze(0)
    ax1.imshow(image.numpy(), cmap='gray')
    ax1.set_title(f'真实标签: {true_label}\n预测标签: {predicted_label}', 
                  fontsize=14, color='green' if true_label == predicted_label else 'red')
    ax1.axis('off')
    
    # 显示概率分布
    ax2.bar(range(10), probabilities.numpy())
    ax2.set_xlabel('数字', fontsize=12)
    ax2.set_ylabel('概率', fontsize=12)
    ax2.set_title('预测概率分布', fontsize=14)
    ax2.set_xticks(range(10))
    ax2.set_ylim([0, 1])
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig

def batch_inference(model, test_loader, num_samples=10):
    """
    批量推理并展示结果
    
    参数:
        model: 训练好的模型
        test_loader: 测试数据加载器
        num_samples: 要显示的样本数量
    """
    model.eval()
    correct = 0
    total = 0
    
    # 获取一批测试数据
    data_iter = iter(test_loader)
    images, labels = next(data_iter)
    
    with torch.no_grad():
        outputs = model(images)
        _, predicted = torch.max(outputs, 1)
        
        # 计算准确率
        correct = (predicted == labels).sum().item()
        total = labels.size(0)
    
    print(f"\n批次准确率: {100 * correct / total:.2f}% ({correct}/{total})")
    
    # 可视化前几个样本
    fig, axes = plt.subplots(2, 5, figsize=(15, 6))
    axes = axes.ravel()
    
    for i in range(min(num_samples, len(images))):
        image = images[i].squeeze()
        true_label = labels[i].item()
        pred_label = predicted[i].item()
        
        axes[i].imshow(image.numpy(), cmap='gray')
        color = 'green' if true_label == pred_label else 'red'
        axes[i].set_title(f'真: {true_label}, 预: {pred_label}', 
                         fontsize=12, color=color)
        axes[i].axis('off')
    
    plt.tight_layout()
    return fig

def main():
    """
    主函数：演示模型推理
    """
    print("=" * 60)
    print("MNIST模型推理示例")
    print("=" * 60)
    
    # 1. 加载模型
    try:
        model = load_model('mnist_cnn.pt')
    except FileNotFoundError:
        print("\n错误：未找到模型文件 'mnist_cnn.pt'")
        print("请先运行训练：python main.py --save-model")
        return
    
    # 2. 加载测试数据
    print("\n加载测试数据...")
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    test_dataset = datasets.MNIST('../data', train=False, 
                                 download=True, transform=transform)
    test_loader = torch.utils.data.DataLoader(test_dataset, 
                                             batch_size=100, shuffle=True)
    
    # 3. 单个样本推理
    print("\n" + "=" * 60)
    print("示例1：单张图像推理")
    print("=" * 60)
    
    sample_image, sample_label = test_dataset[0]
    predicted_class, probabilities = predict_single_image(model, sample_image)
    
    print(f"真实标签: {sample_label}")
    print(f"预测标签: {predicted_class}")
    print(f"\n各类别概率:")
    for i, prob in enumerate(probabilities):
        print(f"  数字 {i}: {prob.item():.4f} ({prob.item()*100:.2f}%)")
    
    # 可视化
    fig1 = visualize_prediction(sample_image, sample_label, 
                                predicted_class, probabilities)
    plt.savefig('prediction_single.png', dpi=150, bbox_inches='tight')
    print("\n单样本预测结果已保存到 prediction_single.png")
    
    # 4. 批量推理
    print("\n" + "=" * 60)
    print("示例2：批量推理")
    print("=" * 60)
    
    fig2 = batch_inference(model, test_loader, num_samples=10)
    plt.savefig('prediction_batch.png', dpi=150, bbox_inches='tight')
    print("批量预测结果已保存到 prediction_batch.png")
    
    # 5. 完整测试集评估
    print("\n" + "=" * 60)
    print("示例3：完整测试集评估")
    print("=" * 60)
    
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in test_loader:
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    accuracy = 100 * correct / total
    print(f"\n测试集总样本数: {total}")
    print(f"正确预测数: {correct}")
    print(f"测试集准确率: {accuracy:.2f}%")
    
    print("\n" + "=" * 60)
    print("推理完成！")
    print("=" * 60)
    
    # 显示图像（可选）
    # plt.show()

if __name__ == '__main__':
    main()

