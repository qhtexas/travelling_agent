from ultralytics import YOLO
from pathlib import Path
from PIL import Image
import cv2
model = YOLO("yolov8n-seg.pt")  # 加载预训练模型

path = Path(__file__).parent / "s.jpg"  # 替换为你的图片路径
img = Image.open(path)  # 打开图片
results = model(img)  # 进行目标检测和分割
annotated_img = results[0].plot()  # 获取带有检测结果的图像
cv2.imshow("Annotated Image", annotated_img)  # 显示图像