import cv2
import numpy as np
from app.preprocessing import preprocess_image
from app.line_detector import detect_lines

img_path = r"C:\Users\harsh\.gemini\antigravity\brain\a3a24b8c-bdde-43e5-af51-0f577adcf3c1\.user_uploaded\media_1788314189105.jpg"
print("Testing strong mode...")
prep_res = preprocess_image(img_path, mode="strong")
cv2.imwrite("test_images/strong_prep.jpg", prep_res.image)
lines = detect_lines(prep_res.image)
print(f"Detected lines: {len(lines.lines)}")
