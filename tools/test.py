import torch

# 1. 见证奇迹的时刻：看 PyTorch 有没有成功抱上 CUDA 的大腿
print("CUDA 是否可用:", torch.cuda.is_available())

# 2. 让显卡自己报上名来，看看是不是你那张最新的 RTX 5060
if torch.cuda.is_available():
    print("当前主力的全能神卡:", torch.cuda.get_device_name(0))