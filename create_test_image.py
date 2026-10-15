from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

out_dir = Path(__file__).parent / "test_images"
out_dir.mkdir(exist_ok=True)

img = Image.new('RGB', (800, 200), color='white')
d = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

d.text((50, 80), "This is a test of the TrOCR offline system.", fill="black", font=font)
out_file = out_dir / "sample.png"
img.save(str(out_file))
print(f"Test image created at {out_file}")
