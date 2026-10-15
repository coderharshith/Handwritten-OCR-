import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ocr_core.config import MIN_LINE_HEIGHT, LINE_PADDING, MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT
from ocr_core.errors import LineDetectionError

logger = logging.getLogger("ocr")


@dataclass
class DetectedLine:
    """A single detected text line with coordinates and cropped image."""
    line_id: int
    x: int
    y: int
    width: int
    height: int
    image: Image.Image  # Cropped PIL Image of this line

    def to_dict(self) -> dict:
        return {"line_id": int(self.line_id), "x": int(self.x), "y": int(self.y),
                "width": int(self.width), "height": int(self.height)}


@dataclass
class LineDetectionResult:
    """Result of line detection on an image."""
    lines: List[DetectedLine]
    is_single_line: bool
    confidence: float  # 0-1, how confident we are in the segmentation
    warnings: List[str] = field(default_factory=list)
    debug_image: Optional[np.ndarray] = None  # Image with drawn line boxes


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale if needed."""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _binarize_for_text(image: np.ndarray) -> np.ndarray:
    """Use Sobel X to detect vertical edges (text) and suppress horizontal notebook lines."""
    gray = _to_grayscale(image)
    # Detect vertical edges (suppresses horizontal notebook lines)
    grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
    abs_grad_x = cv2.convertScaleAbs(grad_x)
    # Binarize
    _, binary = cv2.threshold(abs_grad_x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def _create_debug_image(image: np.ndarray, lines: List[DetectedLine]) -> np.ndarray:
    """Create annotated image with line boxes."""
    debug_img = image.copy()
    for line in lines:
        cv2.rectangle(debug_img, (line.x, line.y), 
                      (line.x + line.width, line.y + line.height), 
                      (0, 255, 0), 2)
        cv2.putText(debug_img, f"Line {line.line_id}", (line.x, max(0, line.y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return debug_img

def _find_local_extrema(arr: np.ndarray, window: int = 20, find_max: bool = True) -> List[int]:
    """Find local maxima or minima in a 1D array."""
    extrema = []
    for i in range(window, len(arr) - window):
        neighborhood = arr[i-window : i+window+1]
        if find_max:
            if arr[i] == np.max(neighborhood) and arr[i] > np.max(arr) * 0.05:
                extrema.append(i)
        else:
            if arr[i] == np.min(neighborhood):
                extrema.append(i)
                
    result = []
    if not extrema: return result
    
    curr = extrema[0]
    for val in extrema[1:]:
        if val - curr < window:
            if find_max:
                if arr[val] > arr[curr]: curr = val
            else:
                if arr[val] < arr[curr]: curr = val
        else:
            result.append(curr)
            curr = val
    result.append(curr)
    return result

def detect_lines(image_input: Union[str, Path, Image.Image, np.ndarray], padding: int = None) -> LineDetectionResult:
    """Robust line detection using Sobel edges and smoothed projection profiles."""
    try:
        pad = padding if padding is not None else LINE_PADDING
        
        if isinstance(image_input, (str, Path)):
            pil_image = Image.open(image_input).convert("RGB")
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, Image.Image):
            cv_image = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            cv_image = image_input.copy()
        else:
            raise LineDetectionError("Unsupported image input type.")
            
        binary = _binarize_for_text(cv_image)
        h, w = cv_image.shape[:2]
        
        # Remove vertical margin lines (like red notebook margins)
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
        text_only = cv2.subtract(binary, vertical_lines)
        
        # Erase the vertical margin lines by blanching with white background
        cv_image_clean = cv_image.copy()
        if np.any(vertical_lines > 0):
            vert_dilate = cv2.dilate(vertical_lines, np.ones((3,3), np.uint8), iterations=1)
            cv_image_clean[vert_dilate > 0] = [255, 255, 255]
        
        # Morphological closing — wider kernel keeps formula fractions, sub/superscripts together
        merge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, h // 120)))
        merged_text = cv2.morphologyEx(text_only, cv2.MORPH_CLOSE, merge_kernel)
        
        # Horizontal projection
        proj = np.sum(merged_text, axis=1)
        
        # Smooth projection profile with a window matching typical text line pitch
        smooth_win = max(25, int(h * 0.02))
        kernel = np.ones(smooth_win) / smooth_win
        proj_smoothed = np.convolve(proj, kernel, mode='same')
        
        from scipy.signal import find_peaks
        min_distance = max(22, int(h * 0.018))
        prominence = (np.max(proj_smoothed) * 0.06) if np.max(proj_smoothed) > 0 else 1.0
        peaks, _ = find_peaks(proj_smoothed, distance=min_distance, prominence=prominence)
        
        detected_lines = []
        warnings = []
        confidence = 1.0
        
        if len(peaks) <= 1:
            is_single = True
            pil_crop = Image.fromarray(cv2.cvtColor(cv_image_clean, cv2.COLOR_BGR2RGB))
            detected_lines.append(
                DetectedLine(line_id=1, x=0, y=0, width=w, height=h, image=pil_crop)
            )
            if len(peaks) == 0:
                warnings.append("No distinct lines found, processing entire image as one line.")
                confidence = 0.5
        else:
            is_single = False
            # Find valleys (cut points) between adjacent peaks
            valleys = []
            for i in range(len(peaks) - 1):
                p1, p2 = peaks[i], peaks[i + 1]
                v = p1 + int(np.argmin(proj_smoothed[p1:p2]))
                valleys.append(v)
                
            bounds = [0] + valleys + [h]
            
            line_idx = 1
            for i in range(len(bounds) - 1):
                y_start = max(0, bounds[i] - 4)
                y_end = min(h, bounds[i + 1] + 4)
                
                slice_crop = cv_image_clean[y_start:y_end, :]
                slice_gray = cv2.cvtColor(slice_crop, cv2.COLOR_BGR2GRAY)
                # Filter out blank notebook lines or empty margins
                ink_count = np.sum(slice_gray < 185)
                if ink_count < 450:
                    continue
                
                # Find horizontal extent of this line to crop tight
                binary_slice = text_only[y_start:y_end, :]
                vert_proj = np.sum(binary_slice, axis=0)
                max_vp = np.max(vert_proj) if len(vert_proj) > 0 else 0
                if max_vp > 0:
                    is_text_x = vert_proj > (max_vp * 0.01)
                    x_indices = np.where(is_text_x)[0]
                    x_start = max(0, x_indices[0] - pad)
                    x_end = min(w, x_indices[-1] + pad)
                else:
                    x_start, x_end = 0, w
                    
                final_crop = cv_image_clean[y_start:y_end, x_start:x_end]
                if final_crop.shape[0] > 10 and final_crop.shape[1] > 10:
                    pil_crop = Image.fromarray(cv2.cvtColor(final_crop, cv2.COLOR_BGR2RGB))
                    detected_lines.append(
                        DetectedLine(
                            line_id=line_idx,
                            x=x_start,
                            y=y_start,
                            width=x_end - x_start,
                            height=y_end - y_start,
                            image=pil_crop
                        )
                    )
                    line_idx += 1
                    
        debug_image = _create_debug_image(cv_image_clean, detected_lines)
        
        return LineDetectionResult(
            lines=detected_lines,
            is_single_line=is_single,
            confidence=confidence,
            warnings=warnings,
            debug_image=debug_image
        )
        
    except Exception as e:
        raise LineDetectionError(f"Line detection failed: {str(e)}")
