import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# --- 配置 ---
WINDOW_SIZE = 5  # 时间窗口：看过去 5 帧
# 输入特征数 = 63 (单帧特征) * 5 (帧数) = 315

def create_window_dataset(X, y, window_size):
    """把连续的时间流数据转换成滑动窗口数据"""
    Xs, ys = [], []
    # 从第 N 帧开始，往前取 N 帧
    for i in range(window_size, len(X)):
        # 如果这几帧的标签不一样（说明动作切换了），丢弃
        if y[i] != y[i-window_size]: 
            continue
            
        # 展平窗口：[t-4, t-3, t-2, t-1, t] -> 一维向量
        window = X[i-window_size:i].flatten()
        Xs.append(window)
        ys.append(y[i])
        
    return np.array(Xs), np.array(ys)

def train():
    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, 'gesture_data_seq.csv') # 读取新文件
    model_path = os.path.join(current_dir, 'gesture_model_seq.pkl')
    
    if not os.path.exists(data_path):
        print("未找到数据！请先运行 data_collector.py")
        return

    print("正在处理时序数据...")
    df = pd.read_csv(data_path)
    
    X_raw = df.iloc[:, :-1].values
    y_raw = df.iloc[:, -1].values
    
    # 制作滑动窗口数据集
    X, y = create_window_dataset(X_raw, y_raw, WINDOW_SIZE)
    
    print(f"数据集构建完成: {X.shape[0]} 个样本，每个样本 {X.shape[1]} 维特征")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("正在训练随机森林 (Sequence Model)...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    acc = accuracy_score(y_test, clf.predict(X_test))
    print(f"模型准确率: {acc:.2f}")
    
    joblib.dump(clf, model_path)
    print("模型保存成功！")

if __name__ == "__main__":
    train()