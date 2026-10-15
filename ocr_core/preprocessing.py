import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Union
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ocr_core.config import (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT, LOW_MEMORY_MODE,
                        LOW_MEMORY_MAX_WIDTH, LOW_MEMORY_MAX_HEIGHT,
                        DESKEW_ANGLE_LIMIT, PREPROCESSING_MODES)
from ocr_core.errors import PreprocessingError, InvalidImageError
from ocr_core.utils import validate_image_path

logger = logging.getLogger("ocr")


@dataclass
class PreprocessingResult:
    """Result of preprocessing an image."""
    image: np.ndarray          # Preprocessed image (BGR or grayscale)
    original: np.ndarray       # Original image preserved
    mode: str                  # Preprocessing mode used
    angle_corrected: float = 0.0  # Deskew angle applied
    steps_applied: list = field(default_factory=list)  # List of step names applied
    warnings: list = field(default_factory=list)


def validate_and_load_image(image_input: Union[str, Path, Image.Image]) -> Tuple[np.ndarray, Image.Image]:
    """Validate and load an image from path or PIL image."""
    try:
        if isinstance(image_input, (str, Path)):
            validate_image_path(str(image_input))  # raises InvalidImageError on failure
            pil_image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            pil_image = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            # Accept numpy arrays (BGR format from cv2)
            if len(image_input.shape) == 2:
                pil_image = Image.fromarray(image_input).convert("RGB")
            elif image_input.shape[2] == 3:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb)
            else:
                pil_image = Image.fromarray(image_input).convert("RGB")
        else:
            raise InvalidImageError("image_input must be a file path, PIL Image, or numpy array.")

        width, height = pil_image.size
        max_w = LOW_MEMORY_MAX_WIDTH if LOW_MEMORY_MODE else MAX_IMAGE_WIDTH
        max_h = LOW_MEMORY_MAX_HEIGHT if LOW_MEMORY_MODE else MAX_IMAGE_HEIGHT

        if width > max_w or height > max_h:
            ratio = min(max_w / width, max_h / height)
            new_w, new_h = int(width * ratio), int(height * ratio)
            pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return cv_image, pil_image
    except Exception as e:
        if isinstance(e, InvalidImageError):
            raise
        raise InvalidImageError(f"Error loading image: {str(e)}")


def detect_orientation(image: np.ndarray) -> int:
    """Detect image orientation (0, 90, 180, 270 degrees)."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    variances = []
    angles = [0, 90, 180, 270]
    
    for angle in angles:
        if angle == 0:
            rotated = binary
        elif angle == 90:
            rotated = cv2.rotate(binary, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            rotated = cv2.rotate(binary, cv2.ROTATE_180)
        elif angle == 270:
            rotated = cv2.rotate(binary, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        proj = np.sum(rotated, axis=1)
        variances.append(np.var(proj))
        
    best_idx = np.argmax(variances)
    sorted_vars = sorted(variances, reverse=True)
    
    if sorted_vars[1] > 0 and (sorted_vars[0] / sorted_vars[1]) > 1.5:
        return angles[best_idx]
    return 0


def correct_orientation(image: np.ndarray, angle: int) -> np.ndarray:
    """Rotate image by specified angle."""
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """Detect and correct text skew."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    angles = []
    for cnt in contours:
        if cv2.contourArea(cnt) > 50:
            rect = cv2.minAreaRect(cnt)
            angle = rect[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            angles.append(angle)
            
    if not angles:
        return image, 0.0
        
    median_angle = np.median(angles)
    
    if abs(median_angle) > 0.5 and abs(median_angle) <= DESKEW_ANGLE_LIMIT:
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        m = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        
        flags = cv2.INTER_CUBIC
        if len(image.shape) == 3:
            border_value = (255, 255, 255)
        else:
            border_value = 255
            
        rotated = cv2.warpAffine(image, m, (w, h), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=border_value)
        return rotated, median_angle
        
    return image, 0.0


def denoise_image(image: np.ndarray, strength: str = "light") -> np.ndarray:
    """High-speed edge-preserving denoising (0.01s vs 30s for fastNlMeans)."""
    if strength == "light":
        return cv2.bilateralFilter(image, d=5, sigmaColor=30, sigmaSpace=30)
    elif strength == "medium":
        return cv2.bilateralFilter(image, d=7, sigmaColor=50, sigmaSpace=50)
    elif strength == "strong":
        blurred = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        return cv2.GaussianBlur(blurred, (3, 3), 0)
    return image


def enhance_contrast(image: np.ndarray, use_clahe: bool = True) -> np.ndarray:
    """Enhance image contrast."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    if use_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)
    else:
        return cv2.equalizeHist(gray)


def apply_threshold(image: np.ndarray, method: str = "otsu") -> np.ndarray:
    """Apply thresholding to binarize image."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    if method == "otsu":
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    elif method == "adaptive":
        return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
    return gray


def compute_image_quality(image: np.ndarray) -> dict:
    """Compute image quality metrics."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    contrast_score = gray.std()
    brightness = gray.mean()
    
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise = np.abs(gray.astype(np.float32) - blurred.astype(np.float32)).mean()
    
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    
    quality_score = min(1.0, max(0.0, (blur_score / 1000.0) * 0.4 + (contrast_score / 128.0) * 0.4 + (edge_density * 10) * 0.2))
    
    return {
        "blur_score": float(blur_score),
        "contrast_score": float(contrast_score),
        "brightness": float(brightness),
        "noise_estimate": float(noise),
        "edge_density": float(edge_density),
        "quality": float(quality_score)
    }


def preprocess_image(image_input: Union[str, Path, Image.Image], mode: str = "light") -> PreprocessingResult:
    """Main preprocessing pipeline."""
    if mode not in PREPROCESSING_MODES and mode != "none":
        raise PreprocessingError(f"Invalid preprocessing mode: {mode}")
        
    try:
        image, _ = validate_and_load_image(image_input)
        original = image.copy()
        
        result = PreprocessingResult(
            image=image.copy(),
            original=original,
            mode=mode,
            angle_corrected=0.0,
            steps_applied=[],
            warnings=[]
        )
        
        if mode == "none":
            result.steps_applied.append("load_and_resize")
            return result
            
        angle = detect_orientation(result.image)
        if angle != 0:
            result.image = correct_orientation(result.image, angle)
            result.steps_applied.append(f"correct_orientation_{angle}")
            
        result.image, deskew_angle = deskew_image(result.image)
        result.angle_corrected = deskew_angle
        if deskew_angle != 0.0:
            result.steps_applied.append(f"deskew_{deskew_angle:.2f}")
            
        if mode == "light":
            result.image = denoise_image(result.image, "light")
            result.steps_applied.append("denoise_light")
            
        elif mode == "medium":
            result.image = denoise_image(result.image, "medium")
            result.steps_applied.append("denoise_medium")
            result.image = enhance_contrast(result.image, use_clahe=True)
            result.steps_applied.append("enhance_contrast_clahe")
            
        elif mode == "strong":
            result.image = denoise_image(result.image, "strong")
            result.steps_applied.append("denoise_strong")
            result.image = enhance_contrast(result.image, use_clahe=True)
            result.steps_applied.append("enhance_contrast_clahe")
            result.image = apply_threshold(result.image, "adaptive")
            result.steps_applied.append("adaptive_threshold")
            
        return result
        
    except InvalidImageError as e:
        raise PreprocessingError(f"Preprocessing failed due to invalid image: {str(e)}")
    except Exception as e:
        raise PreprocessingError(f"Unexpected error in preprocessing: {str(e)}")


def get_preprocessing_candidates(image_input: Union[str, Path, Image.Image]) -> List[PreprocessingResult]:
    """Generate multiple preprocessed candidates for fallback OCR."""
    candidates = []
    
    try:
        candidates.append(preprocess_image(image_input, mode="none"))
    except Exception as e:
        logger.warning(f"Failed to generate 'none' candidate: {e}")
        
    try:
        base_img, _ = validate_and_load_image(image_input)
    except Exception:
        return candidates
        
    try:
        res2 = PreprocessingResult(image=enhance_contrast(base_img.copy(), True), original=base_img.copy(), mode="custom")
        res2.steps_applied.append("contrast_enhanced")
        candidates.append(res2)
    except Exception as e:
        logger.warning(f"Failed to generate contrast candidate: {e}")
        
    try:
        res3 = PreprocessingResult(image=denoise_image(base_img.copy(), "light"), original=base_img.copy(), mode="custom")
        res3.steps_applied.append("light_denoise")
        candidates.append(res3)
    except Exception as e:
        logger.warning(f"Failed to generate light denoise candidate: {e}")
        
    try:
        img4 = denoise_image(base_img.copy(), "medium")
        img4 = enhance_contrast(img4, True)
        res4 = PreprocessingResult(image=img4, original=base_img.copy(), mode="custom")
        res4.steps_applied.extend(["medium_denoise", "contrast_enhanced"])
        candidates.append(res4)
    except Exception as e:
        logger.warning(f"Failed to generate medium denoise+contrast candidate: {e}")
        
    try:
        img5 = apply_threshold(base_img.copy(), "adaptive")
        res5 = PreprocessingResult(image=img5, original=base_img.copy(), mode="custom")
        res5.steps_applied.append("adaptive_threshold")
        candidates.append(res5)
    except Exception as e:
        logger.warning(f"Failed to generate adaptive threshold candidate: {e}")
        
    return candidates
