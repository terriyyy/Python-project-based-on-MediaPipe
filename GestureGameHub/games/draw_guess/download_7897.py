import os
import requests
import time
# 端口
PROXY_PORT = 7897
FILES_TO_DOWNLOAD = [
    'cloud.npy', 
    'face.npy', 
    'flower.npy', 
    'star.npy'
]

# 保存路径
BASE_DIR = os.path.join('games', 'draw_guess')
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"

# 设置代理
proxies = {
    'http': f'http://127.0.0.1:{PROXY_PORT}',
    'https': f'http://127.0.0.1:{PROXY_PORT}'
}

def download_file(filename):
    url = BASE_URL + filename
    save_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
        print(f" {filename} 已存在，跳过")
        return

    print(f" 正在通过端口 {PROXY_PORT} 下载 {filename} ...")
    try:
        r = requests.get(url, stream=True, proxies=proxies, timeout=30)
        
        if r.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f" {filename} 下载成功")
        else:
            print(f" 下载失败，状态码: {r.status_code}")
            
    except Exception as e:
        print(f"下载出错: {e}")

if __name__ == "__main__":
    print(f"开始使用代理端口 {PROXY_PORT} 下载...")
    
    try:
        requests.get("https://www.google.com", proxies=proxies, timeout=5)
        print(" 网络通道测试通过！")
    except:
        print("无法连接 Google，。尝试强制下载...")

    for file in FILES_TO_DOWNLOAD:
        download_file(file)
        
    print("\n>>> 尝试下载结束。")