import logging
import json
import time
import sys
import platform
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from ocr_core.config import (
    PROJECT_ROOT, LOG_DIR, LOG_LEVEL, LOG_CONTENT, 
    SUPPORTED_EXTENSIONS, DEVICE, OFFLINE_MODE, MODEL_NAME
)
from ocr_core.errors import InvalidImageError

def setup_logging(log_dir: Path = None) -> logging.Logger:
    if log_dir is None:
        log_dir = LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('ocr')
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler
    fh = logging.FileHandler(log_dir / 'ocr.log')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

def get_system_info() -> dict:
    ram_gb = 0.0
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        ram_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
    except Exception:
        try:
            import os
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        ram_gb = round(int(line.split()[1]) / (1024 ** 2), 2)
                        break
        except Exception:
            ram_gb = 0.0
    return {
        "device": DEVICE,
        "gpu_status": "Disabled",
        "offline_mode": OFFLINE_MODE,
        "model_name": MODEL_NAME,
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "ram_gb": ram_gb
    }

def display_system_info():
    info = get_system_info()
    print("=" * 50)
    print("System Information")
    print("=" * 50)
    print(f"Device: {info['device']}")
    print(f"GPU: {info['gpu_status']}")
    print(f"Offline Mode: {'Enabled' if info['offline_mode'] else 'Disabled'}")
    print(f"Model: {info['model_name']}")
    print(f"Python Version: {info['python_version']}")
    print(f"PyTorch Version: {info['torch_version']}")
    print(f"Total RAM: {info['ram_gb']} GB")
    print("=" * 50)

def validate_image_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.exists():
        raise InvalidImageError(f"File not found: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise InvalidImageError(f"Unsupported file extension '{p.suffix}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
    
    if p.suffix.lower() == ".pdf":
        return p
        
    try:
        with Image.open(p) as img:
            img.verify()
    except Exception as e:
        raise InvalidImageError(f"Could not open or verify image: {e}")
    return p

def is_blank_image(image: np.ndarray, threshold: float = 0.99) -> bool:
    if len(image.shape) == 3:
        # Convert to grayscale if it's RGB
        if image.shape[2] == 3 or image.shape[2] == 4:
            gray = np.dot(image[...,:3], [0.2989, 0.5870, 0.1140])
        else:
            gray = image
    else:
        gray = image
        
    unique, counts = np.unique(gray, return_counts=True)
    if len(counts) == 0:
        return True
    
    max_count = np.max(counts)
    if (max_count / gray.size) > threshold:
        return True
    return False

class Timer:
    def __init__(self):
        self.start_time = None
        self.elapsed = 0.0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            self.elapsed = time.time() - self.start_time

def save_text_output(text: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

def save_json_output(data: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def get_image_info(image_path: Path) -> dict:
    try:
        with Image.open(image_path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "file_size_bytes": image_path.stat().st_size,
                "mode": img.mode
            }
    except Exception as e:
        raise InvalidImageError(f"Could not read image info: {e}")
