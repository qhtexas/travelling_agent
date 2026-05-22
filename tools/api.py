import cv2
import numpy as np
import ddddocr
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn
from contextlib import asynccontextmanager

# ==========================================
# 全局变量定义与 FastAPI 生命周期管理
# ==========================================

# 声明全局 OCR 检测器变量，在服务启动时只初始化一次，避免每次请求都重新加载模型，大幅度降低接口延迟
ocr_detector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 推荐的生命周期管理器（Lifespan Context Manager）。
    在 FastAPI 服务启动前（Before Startup）执行 `yield` 之前的代码；
    在服务关闭后（After Shutdown）执行 `yield` 之后的代码。
    """
    global ocr_detector
    
    # 初始化 ddddocr 识别引擎。
    # - det=False: 禁用目标检测模型（这里做滑块匹配不需要通用目标框选）
    # - ocr=False: 禁用 OCR 字符识别（此处只需滑块缺口计算）
    # - show_ad=False: 不显示 ddddocr 的控制台广告信息
    ocr_detector = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
    print(">>> 成功加载 ddddocr 识别引擎（仅加载一次，常驻内存） <<<")
    
    yield  # 此时服务开始运行，等待并处理客户端请求
    
    # 服务关闭时清理资源
    ocr_detector = None
    print(">>> 已释放 ddddocr 识别引擎资源 <<<")

# 创建 FastAPI 实例，注入声明的生命周期管理器，并添加项目元信息
app = FastAPI(
    title="滑块缺口多边形匹配接口",
    description="该 API 提供自动切割多边形滑块并在背景图中查找其准确匹配位置（中心点坐标）的服务。",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
# 图像处理核心算法：滑块多边形轮廓提取
# ==========================================

def find_target_contour(img):
    """
    利用 OpenCV 提取原始滑块拼接图（Elements Sheet）中的多边形滑块零件轮廓。
    
    参数:
        img: 使用 cv2.imdecode 解码得到的 OpenCV 图像矩阵（BGR 或 BGRA）。
    返回:
        target_contour: 滑块零件的 OpenCV 轮廓数组（如果未找到则返回 None）。
    """
    # 步骤 1：判断图像是否包含 Alpha 通道（4通道图像）
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3]   # 提取 Alpha（透明度）通道
        rgb = img[:, :, :3]    # 提取 RGB 颜色通道
        
        # 定义背景判定：
        # - RGB 值为纯白色 (255, 255, 255)
        white_mask = (rgb[:, :, 0] == 255) & (rgb[:, :, 1] == 255) & (rgb[:, :, 2] == 255)
        # - 或者 Alpha 通道小于 128 (判定为透明/半透明)
        bg_mask = white_mask | (alpha < 128)
    else:
        # 如果是 3 通道 BGR 图像或单通道灰度图
        if len(img.shape) == 3:
            rgb = img[:, :, :3]
            white_mask = (rgb[:, :, 0] == 255) & (rgb[:, :, 1] == 255) & (rgb[:, :, 2] == 255)
        else:
            white_mask = (img == 255)
        bg_mask = white_mask  # 仅使用白色作为背景色

    # 步骤 2：对背景掩膜取反，得到前景物体（即包含滑块、滑轨、滑块按钮的区域）
    fg_mask = ~bg_mask
    # 将布尔型掩膜转换为 8 位无符号整型二值图 (0 代表背景，255 代表前景)
    fg_img = fg_mask.astype(np.uint8) * 255
    
    # 步骤 3：查找二值化图中的所有外部轮廓
    # - cv2.RETR_EXTERNAL: 只检测最外层轮廓，忽略孔洞内部轮廓
    # - cv2.CHAIN_APPROX_SIMPLE: 压缩水平、垂直和对角分割，仅保留终点坐标
    contours, _ = cv2.findContours(fg_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 步骤 4：通过几何特征过滤，在所有轮廓中寻找到真正的“滑块零件”
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)  # 获取该轮廓的外接矩形参数 (x, y, 宽, 高)
        area = cv2.contourArea(c)         # 获取轮廓的实际像素面积
        aspect_ratio = w / h              # 计算宽高比
        
        # 过滤规则 A：面积过小的噪声（小于 500 像素）直接排除
        if area < 500:
            continue
            
        # 过滤规则 B：排除灰色的长条滑轨（滑轨的宽度极大，宽高比远大于 3.0）
        if w > 300 or aspect_ratio > 3.0:
            continue
            
        # 过滤规则 C：排除左侧的蓝色拖动按钮（按钮通常位于 x=0 附近起步，且宽高比偏向矩形，如 1.8 左右）
        # 这里限定滑块的起点 x 坐标必须大于 20，且长宽比必须接近 1:1（长宽比小于 1.5）
        if x < 20 or aspect_ratio > 1.5:
            continue
            
        # 成功匹配所有过滤条件的轮廓即为目标五边形滑块
        return c
        
    return None

# ==========================================
# FastAPI 路由定义与主入口
# ==========================================

@app.post("/match", summary="进行滑块多边形切割并计算在背景图中的匹配位置")
async def match_slider(
    background: UploadFile = File(..., description="背景图文件（如 suit1.png，即带有缺口阴影的完整背景底图）"),
    slider: UploadFile = File(..., description="需要切分的滑块要素图（如 test1.png，即包含滑轨、滑块、按钮的拼合图）")
):
    """
    匹配处理核心接口。
    
    工作原理：
    1. 接收客户端以 Multipart/form-data 格式上传的两个图像文件。
    2. 读取文件字节流，并使用 OpenCV 解码拼合图。
    3. 通过 `find_target_contour` 自动捕捉多边形滑块轮廓。
    4. 创建纯透明画板，将该多边形轮廓内的滑块像素“剪纸式”拷贝过来，得到完美的透明背景多边形滑块。
    5. 将多边形滑块重新编码为 PNG 内存字节流，传入 `ddddocr` 做滑块距离检测。
    6. 计算并返回缺口中心坐标。
    """
    try:
        # 异步读取上传文件的原始字节数据 (bytes)
        bg_bytes = await background.read()
        slider_bytes = await slider.read()
        
        # 将滑块图片文件二进制流转换为 numpy 数组，并解码成 OpenCV 矩阵
        # cv2.IMREAD_UNCHANGED: 保持图片原通道（如带透明度的 PNG 会包含第 4 个 Alpha 通道）
        img_slider = cv2.imdecode(np.frombuffer(slider_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
        if img_slider is None:
            raise HTTPException(status_code=400, detail="滑块图像解码失败，请确认文件格式是否正确。")
            
        # 获取滑块零件的多边形轮廓
        contour = find_target_contour(img_slider)
        if contour is None:
            raise HTTPException(status_code=422, detail="无法在上传的滑块图像中自动定位到有效的滑块轮廓。")
            
        # 计算该轮廓的边界矩形，以确定切割范围
        tx, ty, tw, th = cv2.boundingRect(contour)
        
        # 将轮廓中所有点的坐标向左上方平移 tx, ty，使轮廓对齐到以新切图左上角 (0, 0) 为原点的局部坐标系中
        local_contour = contour - [tx, ty]
        
        # 创建一块全新、与外接矩形大小一致的 4 通道画布（全部像素默认为 0，代表完全透明的背景）
        cropped_target = np.zeros((th, tw, 4), dtype=np.uint8)
        
        # 在单通道掩膜上绘制填充的白色多边形区域 (值为 255)
        # -1: 代表绘制并填充多边形内部
        mask = np.zeros((th, tw), dtype=np.uint8)
        cv2.drawContours(mask, [local_contour], -1, 255, -1)
        
        # 提取并拷贝原始拼合图在对应边界框范围内的 RGB 颜色信息
        cropped_target[:, :, :3] = img_slider[ty:ty+th, tx:tx+tw, :3]
        
        # 确定切出图的 Alpha 通道（透明度）：
        # 如果原拼合图自带 Alpha 属性，我们将“多边形内部的非透明像素”与“新建掩膜”做位与运算，确保透明边缘绝对干净；
        # 若是 3 通道图片，则直接把 mask 赋给 Alpha 通道（多边形内部不透明 255，外部完全透明 0）。
        if img_slider.shape[2] == 4:
            cropped_target[:, :, 3] = cv2.bitwise_and(img_slider[ty:ty+th, tx:tx+tw, 3], mask)
        else:
            cropped_target[:, :, 3] = mask
            
        # 将处理好的多边形滑块图像在内存中编码为 PNG 格式
        success, encoded_cropped = cv2.imencode('.png', cropped_target)
        if not success:
            raise HTTPException(status_code=500, detail="多边形滑块切割图像编码失败。")
        # 转换为字节流以备传入 ddddocr
        cropped_bytes = encoded_cropped.tobytes()
        
        # 确保全局检测引擎正常工作
        if ocr_detector is None:
            raise HTTPException(status_code=500, detail="DdddOcr 检测引擎尚未初始化完毕。")
            
        # 将切割后的多边形滑块字节流与原始背景图字节流传入 ddddocr 进行滑动缺口检测
        # - simple_target=False: 表示我们使用包含丰富色彩纹理的滑块来进行更加精细的匹配
        match_res = ocr_detector.slide_match(cropped_bytes, bg_bytes, simple_target=False)
        
        # 获取匹配的中心点横纵坐标 (target_x, target_y)
        center_x = match_res.get("target_x")
        center_y = match_res.get("target_y")
        
        # 兼容性处理：若 ddddocr 版本在特定输出下使用不同 key，尝试从 target 列表中提取
        if center_x is None or center_y is None:
            target_coords = match_res.get("target")
            if target_coords and len(target_coords) == 2:
                center_x, center_y = target_coords
                
        # 如果获取依然为空，则认为匹配计算失败
        if center_x is None or center_y is None:
            raise HTTPException(status_code=422, detail=f"滑块缺口比对失败。匹配引擎输出: {match_res}")
            
        # 返回成功匹配数据（包含中心点坐标和引擎的匹配置信度）
        return {
            "center_x": int(center_x),
            "center_y": int(center_y),
            "confidence": float(match_res.get("confidence", 0.0))
        }
        
    except HTTPException as he:
        # 直接透传主动抛出的 HTTP 异常
        raise he
    except Exception as e:
        # 捕获意料之外的代码异常，封装成 500 服务器错误返回
        raise HTTPException(status_code=500, detail=f"服务器内部异常: {str(e)}")

# ==========================================
# 调试与开发主启动入口
# ==========================================

if __name__ == "__main__":
    # 本地启动 uvicorn 服务器
    # - host="127.0.0.1": 仅允许本地回路访问
    # - port=8088: 设置服务监听端口为 8088
    # - log_level="info": 打印普通信息级别日志
    uvicorn.run("api:app", host="127.0.0.1", port=8088, log_level="info")
