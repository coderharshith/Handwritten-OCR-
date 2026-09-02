from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs(r"d:\OCR\handwritten-ocr\test_images", exist_ok=True)
img = Image.new('RGB', (600, 150), color='white')
d = ImageDraw.Draw(img)

# Use Windows built-in handwriting-style fonts
try:
    font = ImageFont.truetype("C:\\Windows\\Fonts\\segoesc.ttf", 60)
except Exception:
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\comic.ttf", 60)
    except Exception:
        font = ImageFont.load_default()

d.text((30, 30), "Hello World!", fill="black", font=font)
img.save(r"d:\OCR\handwritten-ocr\test_images\good_sample.png")
print("High-quality test image created at test_images/good_sample.png")
