import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.config import MIN_LINE_HEIGHT, LINE_PADDING, MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT
from app.errors import LineDetectionError

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
        
        # Horizontal projection
        proj = np.sum(text_only, axis=1)
        
        # Smooth projection
        kernel_size = max(5, h // 50)
        proj_smoothed = np.convolve(proj, np.ones(kernel_size)/kernel_size, mode='same')
        
        # Find peaks (centers of lines)
        peaks = _find_local_extrema(proj_smoothed, window=max(10, MIN_LINE_HEIGHT), find_max=True)
        
        detected_lines = []
        warnings = []
        confidence = 1.0
        
        if len(peaks) <= 1:
            is_single = True
            pil_crop = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            detected_lines.append(
                DetectedLine(line_id=1, x=0, y=0, width=w, height=h, image=pil_crop)
            )
            if len(peaks) == 0:
                warnings.append("No distinct lines found, processing entire image as one line.")
                confidence = 0.5
        else:
            is_single = False
            # Find valleys (cut points)
            valleys = _find_local_extrema(proj_smoothed, window=max(10, MIN_LINE_HEIGHT // 2), find_max=False)
            
            # Construct boundaries from valleys
            boundaries = []
            start_y = 0
            for v in valleys:
                if v > start_y:
                    boundaries.append((start_y, v))
                start_y = v
            if start_y < h:
                boundaries.append((start_y, h))
                
            # Filter boundaries that don't contain a peak
            valid_boundaries = []
            for (y1, y2) in boundaries:
                if any(y1 <= p <= y2 for p in peaks):
                    valid_boundaries.append((y1, y2))
                    
            if not valid_boundaries:
                # Fallback if logic fails
                valid_boundaries = [(0, h)]
                
            for idx, (y_start, y_end) in enumerate(valid_boundaries):
                # Crop the line vertically
                cropped = cv_image[y_start:y_end, :]
                
                # Find horizontal extent of this line to crop tight
                binary_slice = text_only[y_start:y_end, :]
                vert_proj = np.sum(binary_slice, axis=0)
                is_text_x = vert_proj > (np.max(vert_proj) * 0.05 if np.max(vert_proj) > 0 else 0)
                x_indices = np.where(is_text_x)[0]
                
                if len(x_indices) > 0:
                    x_start = max(0, x_indices[0] - pad)
                    x_end = min(w, x_indices[-1] + pad)
                else:
                    x_start, x_end = 0, w
                    
                y_start_pad = max(0, y_start - pad)
                y_end_pad = min(h, y_end + pad)
                
                final_crop = cv_image[y_start_pad:y_end_pad, x_start:x_end]
                
                if final_crop.shape[0] > 0 and final_crop.shape[1] > 0:
                    pil_crop = Image.fromarray(cv2.cvtColor(final_crop, cv2.COLOR_BGR2RGB))
                    detected_lines.append(
                        DetectedLine(line_id=idx + 1, x=x_start, y=y_start_pad, 
                                     width=x_end-x_start, height=y_end_pad-y_start_pad, image=pil_crop)
                    )
                    
        debug_image = _create_debug_image(cv_image, detected_lines)
        
        return LineDetectionResult(
            lines=detected_lines,
            is_single_line=is_single,
            confidence=confidence,
            warnings=warnings,
            debug_image=debug_image
        )
        
    except Exception as e:
        raise LineDetectionError(f"Line detection failed: {str(e)}")
