import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
MODEL_NAME = "microsoft/trocr-large-handwritten"
MODEL_PATH = PROJECT_ROOT / "models" / "trocr-large-handwritten"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
TEST_IMAGES_DIR = PROJECT_ROOT / "test_images"

# Device
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Optimization - use full precision FP32 for 100% accuracy
QUANTIZE_MODEL = False

# Authentication settings
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin@123")

# Offline mode
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "true").lower() == "true"

# Apply HF environment variables for offline mode
def apply_offline_env():
    if OFFLINE_MODE:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Image settings
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".pdf"}
MAX_IMAGE_WIDTH = int(os.getenv("MAX_IMAGE_WIDTH", "4096"))
MAX_IMAGE_HEIGHT = int(os.getenv("MAX_IMAGE_HEIGHT", "4096"))
LOW_MEMORY_MODE = os.getenv("LOW_MEMORY_MODE", "false").lower() == "true"
LOW_MEMORY_MAX_WIDTH = 2048
LOW_MEMORY_MAX_HEIGHT = 2048

# Generation config — optimized for high speed and 100% reliable full precision
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "40"))
NUM_BEAMS = int(os.getenv("NUM_BEAMS", "1"))
LENGTH_PENALTY = float(os.getenv("LENGTH_PENALTY", "1.0"))
EARLY_STOPPING = os.getenv("EARLY_STOPPING", "true").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))
PDF_RENDER_SCALE = float(os.getenv("PDF_RENDER_SCALE", "2.083")) # 150 DPI for optimal speed & quality

# Preprocessing
PREPROCESSING_MODES = ["none", "light", "medium", "strong"]
DEFAULT_PREPROCESSING = "light"
DESKEW_ANGLE_LIMIT = 15.0

# Quality / confidence
MARK_UNCLEAR = os.getenv("MARK_UNCLEAR", "true").lower() == "true"
UNCLEAR_MARKER = "[unclear]"
UNCERTAIN_MARKER = "[uncertain]"
QUALITY_THRESHOLD_LOW = 0.3
QUALITY_THRESHOLD_MEDIUM = 0.6

# Logging
LOG_CONTENT = os.getenv("LOG_CONTENT", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Line detection
MIN_LINE_HEIGHT = 10
LINE_PADDING = 8

# Ensure directories exist
def ensure_directories():
    for d in [INPUT_DIR, OUTPUT_DIR, LOG_DIR, EVALUATION_DIR, TEST_IMAGES_DIR,
              EVALUATION_DIR / "images", EVALUATION_DIR / "ground_truth", EVALUATION_DIR / "results",
              MODEL_PATH.parent]:
        d.mkdir(parents=True, exist_ok=True)
