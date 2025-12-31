import torch
import torch.nn as nn

class DrawCNN(nn.Module):
    def __init__(self, num_classes):
        super(DrawCNN, self).__init__()
        # 输入是一张 28x28 的单通道灰度图
        self.layer1 = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1), # 卷积层
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2)       # 池化层：28x28 -> 14x14
        )
        self.layer2 = nn.Sequential(
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2)                             # 池化层：14x14 -> 7x7
        )
        self.fc = nn.Sequential(
            nn.Linear(32 * 7 * 7, 128),                 # 全连接层
            nn.ReLU(),
            nn.Linear(128, num_classes)                 # 输出分类概率
        )

    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = out.view(out.size(0), -1) # 展平
        out = self.fc(out)
        return out