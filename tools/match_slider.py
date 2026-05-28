import cv2
import numpy as np
import ddddocr
import json
import os
from pathlib import Path

def load_image(path):
    """Load an image supporting unicode paths on Windows."""
    try:
        return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    except Exception as e:
        print(f"Error loading image {path}: {e}")
        return None

def save_image(path, img):
    """Save an image supporting unicode paths on Windows."""
    try:
        ext = Path(path).suffix
        _, encoded_img = cv2.imencode(ext, img)
        encoded_img.tofile(str(path))
        return True
    except Exception as e:
        print(f"Error saving image to {path}: {e}")
        return False

def find_target_contour(img):
    """Automatically find the contour of the slide piece target."""
    if len(img.shape) == 3 and img.shape[2] == 4:
        # 4 channels: Use alpha channel to isolate foreground
        alpha = img[:, :, 3]
        rgb = img[:, :, :3]
        white_mask = (rgb[:, :, 0] == 255) & (rgb[:, :, 1] == 255) & (rgb[:, :, 2] == 255)
        bg_mask = white_mask | (alpha < 128)
    else:
        # 3 channels (BGR) or grayscale
        if len(img.shape) == 3:
            rgb = img[:, :, :3]
            white_mask = (rgb[:, :, 0] == 255) & (rgb[:, :, 1] == 255) & (rgb[:, :, 2] == 255)
        else:
            white_mask = (img == 255)
        bg_mask = white_mask

    fg_mask = ~bg_mask
    fg_img = fg_mask.astype(np.uint8) * 255
    
    # Find external contours
    contours, _ = cv2.findContours(fg_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        aspect_ratio = w / h
        
        # Filter contours based on size and shape:
        # 1. Slide piece usually has an area > 500 px.
        # 2. Slide piece is not the long track (w > 300 or aspect_ratio > 3.0).
        # 3. Slide piece is not the left-aligned blue button (typically at x < 20 or aspect_ratio > 1.5).
        if area < 500:
            continue
        if w > 300 or aspect_ratio > 3.0:
            continue
        if x < 20 or aspect_ratio > 1.5:
            continue
            
        # Found the target contour!
        return c
        
    return None

def main():
    # Base paths
    tools_dir = Path(__file__).parent
    test1_path = tools_dir / "test1.png"
    suit1_path = tools_dir / "suit1.png"
    
    cropped_path = tools_dir / "cropped_target.png"
    result_path = tools_dir / "match_result.png"
    
    print("--- 1. Loading slider elements sheet ---")
    img_test1 = load_image(test1_path)
    if img_test1 is None:
        print("Failed to load test1.png")
        return
        
    print(f"Loaded test1.png (shape: {img_test1.shape})")
    
    print("\n--- 2. Finding target slide piece contour ---")
    contour = find_target_contour(img_test1)
    if contour is None:
        print("Failed to auto-detect target slide piece in test1.png")
        return
    
    tx, ty, tw, th = cv2.boundingRect(contour)
    print(f"Detected target slide piece bounding box at: x={tx}, y={ty}, w={tw}, h={th}")
    
    # Shift contour coordinates to local (cropped image) coordinates
    local_contour = contour - [tx, ty]
    
    # Create a 4-channel transparent image for the cropped target
    cropped_target = np.zeros((th, tw, 4), dtype=np.uint8)
    
    # Create mask of the polygon contour
    mask = np.zeros((th, tw), dtype=np.uint8)
    cv2.drawContours(mask, [local_contour], -1, 255, -1)
    
    # Copy RGB channels and set alpha channel to the mask (or original alpha combined with mask)
    cropped_target[:, :, :3] = img_test1[ty:ty+th, tx:tx+tw, :3]
    if img_test1.shape[2] == 4:
        cropped_target[:, :, 3] = cv2.bitwise_and(img_test1[ty:ty+th, tx:tx+tw, 3], mask)
    else:
        cropped_target[:, :, 3] = mask
        
    save_image(cropped_path, cropped_target)
    print(f"Successfully cropped polygonal target and saved to: {cropped_path}")
    
    print("\n--- 3. Matching position with ddddocr ---")
    # Initialize ddddocr
    det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
    
    # Load cropped target as bytes
    with open(cropped_path, "rb") as f:
        target_bytes = f.read()
        
    # Load background image as bytes
    with open(suit1_path, "rb") as f:
        background_bytes = f.read()
        
    # Run slide match
    match_res = det.slide_match(target_bytes, background_bytes, simple_target=False)
    print("ddddocr Slide Match Raw Output:")
    print(json.dumps(match_res, indent=2))
    
    # Extract coordinates
    # Note: ddddocr returns the center coordinates of the match
    center_x = match_res.get("target_x")
    center_y = match_res.get("target_y")
    
    if center_x is None or center_y is None:
        # Try fallback target list
        target_coords = match_res.get("target")
        if target_coords and len(target_coords) == 2:
            center_x, center_y = target_coords
            
    if center_x is None or center_y is None:
        print("Error: Could not retrieve match coordinates from ddddocr output.")
        return
        
    # Calculate top-left corner of matched area
    top_left_x = int(center_x - tw // 2)
    top_left_y = int(center_y - th // 2)
    
    print(f"\nMatch results:")
    print(f"  - Matched Center Position: ({center_x}, {center_y})")
    print(f"  - Calculated Top-Left Box Corner: ({top_left_x}, {top_left_y})")
    print(f"  - Width: {tw}, Height: {th}")
    
    print("\n--- 4. Visualizing results ---")
    img_bg = load_image(suit1_path)
    if img_bg is not None:
        # Shift contour to the matched position
        matched_contour = local_contour + [top_left_x, top_left_y]
        # Draw the polygon contour at the matched position (green, line thickness 2)
        cv2.drawContours(img_bg, [matched_contour], -1, (0, 255, 0), 2)
        # Draw a small circle at the center
        cv2.circle(img_bg, (center_x, center_y), 3, (0, 0, 255), -1)
        
        save_image(result_path, img_bg)
        print(f"Visualization saved to: {result_path}")
    else:
        print("Failed to load background image for visualization.")


if __name__ == "__main__":
    main()
