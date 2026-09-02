from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs(r"d:\OCR\handwritten-ocr\test_images", exist_ok=True)
img = Image.new('RGB', (800, 200), color='white')
d = ImageDraw.Draw(img)

# Fallback to default font if we can't load a cursive one easily
try:
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

d.text((50, 80), "This is a test of the TrOCR offline system.", fill="black", font=font)
img.save(r"d:\OCR\handwritten-ocr\test_images\sample.png")
print("Test image created at test_images/sample.png")
