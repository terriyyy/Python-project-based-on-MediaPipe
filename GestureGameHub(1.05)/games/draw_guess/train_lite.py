import os
import requests
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from cnn_model import DrawCNN

# 1. 配置想猜的物体 (可自己添加，必须是 QuickDraw 存在的类别)
CLASSES = ['apple', 'banana', 'book', 'car', 'cat', 'clock', 'cloud', 'face', 'flower', 'star']
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(DATA_DIR, 'draw_model.pth')
LABEL_PATH = os.path.join(DATA_DIR, 'labels.txt')
MAX_ITEMS_PER_CLASS = 2000 # 每个类别只取2000张图训练，速度快

def download_data():
    base_url = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"
    data = []
    labels = []
    
    print("开始下载并加载数据...")
    for idx, cls in enumerate(CLASSES):
        file_name = f"{cls}.npy"
        file_path = os.path.join(DATA_DIR, file_name)
        
        # 如果本地没有，就下载
        if not os.path.exists(file_path):
            print(f"Downloading {cls}...")
            url = base_url + file_name.replace(' ', '%20')
            r = requests.get(url)
            with open(file_path, 'wb') as f:
                f.write(r.content)
        
        # 加载数据
        ary = np.load(file_path)
        ary = ary[:MAX_ITEMS_PER_CLASS] # 截取一部分
        data.append(ary)
        labels.append(np.full(len(ary), idx))
        
        # 删掉npy文件节省空间 (可选)
        # os.remove(file_path) 
        
    print(">>> 数据加载完成！")
    return np.concatenate(data), np.concatenate(labels)

def train():
    # 准备数据
    X_raw, y_raw = download_data()
    
    # 归一化并转 Tensor
    X = torch.from_numpy(X_raw).float() / 255.0
    X = X.view(-1, 1, 28, 28) # 变形为 [N, 1, 28, 28]
    y = torch.from_numpy(y_raw).long()
    
    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=64, shuffle=True)
    
    # 初始化模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = DrawCNN(len(CLASSES)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    print(f">>> 开始训练 (Device: {device})...")
    model.train()
    epochs = 5 # 训练5轮
    
    for epoch in range(epochs):
        total_loss = 0
        correct = 0
        total = 0
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {total_loss/len(loader):.4f}, Acc: {100 * correct / total:.2f}%")
        
    # 保存模型
    torch.save(model.state_dict(), MODEL_PATH)
    # 保存标签
    with open(LABEL_PATH, 'w') as f:
        f.write('\n'.join(CLASSES))
        
    print(f">>> 模型已保存至: {MODEL_PATH}")

if __name__ == "__main__":
    train()