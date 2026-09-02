import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import torch
from PIL import Image

from app.config import (DEVICE, MODEL_NAME, OFFLINE_MODE, MAX_NEW_TOKENS,
                        NUM_BEAMS, LENGTH_PENALTY, EARLY_STOPPING,
                        DEFAULT_PREPROCESSING, MARK_UNCLEAR, QUALITY_THRESHOLD_LOW,
                        UNCLEAR_MARKER)
from app.errors import RecognitionError
from app.model import TrOCRModel
from app.preprocessing import preprocess_image, compute_image_quality, validate_and_load_image
from app.line_detector import detect_lines, DetectedLine
from app.postprocessor import postprocess_text, detect_ocr_issues, compute_quality_score, assemble_lines

logger = logging.getLogger("ocr")

@dataclass
class LineRecognition:
    line_number: int
    text: str
    processing_time_seconds: float
    quality_score: float
    warnings: List[str] = field(default_factory=list)
    bbox: Optional[dict] = None  # {x, y, width, height}

@dataclass
class RecognitionResult:
    success: bool
    text: str
    lines: List[LineRecognition]
    total_processing_time_seconds: float
    warnings: List[str] = field(default_factory=list)
    model: str = MODEL_NAME
    device: str = DEVICE
    offline: bool = OFFLINE_MODE

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "model": self.model,
            "device": self.device,
            "offline": self.offline,
            "text": self.text,
            "lines": [{"line_number": l.line_number, "text": l.text,
                       "processing_time_seconds": round(l.processing_time_seconds, 2),
                       "quality_score": round(l.quality_score, 2),
                       "warnings": l.warnings,
                       "bbox": l.bbox} for l in self.lines],
            "total_processing_time_seconds": round(self.total_processing_time_seconds, 2),
            "warnings": self.warnings
        }


def recognize_line(line_image: Image.Image, trocr: TrOCRModel, max_new_tokens: int = None,
                   num_beams: int = None, length_penalty: float = None,
                   early_stopping: bool = None) -> tuple:
    """Recognize text from a single line image using TrOCR.
    
    Returns:
        tuple: (recognized_text, elapsed_seconds)
    """
    start_time = time.time()

    if line_image.mode != "RGB":
        line_image = line_image.convert("RGB")

    pixel_values = trocr.processor(images=line_image, return_tensors="pt").pixel_values
    pixel_values = pixel_values.to(trocr.device)

    kwargs = {
        "max_new_tokens": max_new_tokens if max_new_tokens is not None else MAX_NEW_TOKENS,
        "num_beams": num_beams if num_beams is not None else NUM_BEAMS,
        "length_penalty": length_penalty if length_penalty is not None else LENGTH_PENALTY,
        "early_stopping": early_stopping if early_stopping is not None else EARLY_STOPPING,
    }

    with torch.inference_mode():
        generated_ids = trocr.model.generate(pixel_values, **kwargs)

    text = trocr.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    text = text.strip()

    elapsed_seconds = time.time() - start_time

    del pixel_values
    del generated_ids

    return text, elapsed_seconds


def _pil_from_cv2(cv_image: np.ndarray) -> Image.Image:
    """Convert a cv2 BGR or grayscale image to PIL RGB Image."""
    if len(cv_image.shape) == 2:
        return Image.fromarray(cv_image).convert("RGB")
    elif cv_image.shape[2] == 3:
        import cv2
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    else:
        return Image.fromarray(cv_image).convert("RGB")


def recognize_pil_image(image: Image.Image, preprocess: str = None, single_line: bool = False,
                        max_new_tokens: int = None, num_beams: int = None,
                        length_penalty: float = None, early_stopping: bool = None) -> RecognitionResult:
    """Recognize handwritten text from a PIL Image.
    
    Args:
        image: PIL Image to process
        preprocess: Preprocessing mode (none/light/medium/strong)
        single_line: If True, treat as single text line
        max_new_tokens: Max tokens to generate
        num_beams: Beam search width
        length_penalty: Length penalty for generation
        early_stopping: Whether to use early stopping
        
    Returns:
        RecognitionResult with recognized text and metadata
    """
    start_time = time.time()
    warnings = []

    try:
        trocr = TrOCRModel.get_instance()
        if not trocr.is_loaded():
            trocr.load()

        preprocess_mode = preprocess if preprocess else DEFAULT_PREPROCESSING
        preprocessed = preprocess_image(image, mode=preprocess_mode)
        warnings.extend(preprocessed.warnings)

        quality_metrics = compute_image_quality(preprocessed.image)

        recognized_lines = []

        if single_line:
            pil_line = _pil_from_cv2(preprocessed.image)
            text, ptime = recognize_line(
                pil_line, trocr, max_new_tokens, num_beams, length_penalty, early_stopping
            )
            text = postprocess_text(text)
            issues = detect_ocr_issues(text)
            quality_score = compute_quality_score(quality_metrics, text, ptime)

            if MARK_UNCLEAR and quality_score < QUALITY_THRESHOLD_LOW and issues:
                text = f"{text} {UNCLEAR_MARKER}"

            recognized_lines.append(LineRecognition(
                line_number=1,
                text=text,
                processing_time_seconds=ptime,
                quality_score=quality_score,
                warnings=issues,
                bbox=None
            ))
            warnings.extend([f"Line 1: {w}" for w in issues])
        else:
            pil_preprocessed = _pil_from_cv2(preprocessed.image)
            line_result = detect_lines(pil_preprocessed)
            warnings.extend(line_result.warnings)

            if line_result.confidence < 0.5:
                warnings.append(
                    "WARNING: Unable to confidently detect individual text lines. "
                    "Recognition may be unreliable."
                )

            for detected_line in line_result.lines:
                text, ptime = recognize_line(
                    detected_line.image, trocr, max_new_tokens, num_beams,
                    length_penalty, early_stopping
                )
                text = postprocess_text(text)
                issues = detect_ocr_issues(text)
                quality_score = compute_quality_score(quality_metrics, text, ptime)

                if MARK_UNCLEAR and quality_score < QUALITY_THRESHOLD_LOW and issues:
                    text = f"{text} {UNCLEAR_MARKER}"

                recognized_lines.append(LineRecognition(
                    line_number=detected_line.line_id,
                    text=text,
                    processing_time_seconds=ptime,
                    quality_score=quality_score,
                    warnings=issues,
                    bbox=detected_line.to_dict()
                ))
                warnings.extend([f"Line {detected_line.line_id}: {w}" for w in issues])

        full_text = assemble_lines([rl.text for rl in recognized_lines])
        total_time = time.time() - start_time

        return RecognitionResult(
            success=True,
            text=full_text,
            lines=recognized_lines,
            total_processing_time_seconds=total_time,
            warnings=warnings
        )

    except RecognitionError:
        raise
    except Exception as e:
        logger.exception("Error during recognition")
        raise RecognitionError(f"Recognition failed: {str(e)}") from e


def recognize_image(image_path: Union[str, Path], mode: str = None, preprocess: str = None,
                    show_lines: bool = False, max_new_tokens: int = None, num_beams: int = None,
                    length_penalty: float = None, early_stopping: bool = None,
                    single_line: bool = False) -> RecognitionResult:
    """Recognize handwritten text from an image file.
    
    Args:
        image_path: Path to the image file
        mode: Recognition mode (unused, kept for API compat)
        preprocess: Preprocessing mode (none/light/medium/strong)
        show_lines: Whether to include line detection info
        max_new_tokens: Max tokens to generate
        num_beams: Beam search width
        length_penalty: Length penalty for generation
        early_stopping: Whether to use early stopping
        single_line: If True, treat as single text line
        
    Returns:
        RecognitionResult with recognized text and metadata
    """
    try:
        from app.utils import validate_image_path
        path = validate_image_path(image_path)
        pil_image = Image.open(path).convert("RGB")
        return recognize_pil_image(
            pil_image, preprocess, single_line, max_new_tokens, num_beams,
            length_penalty, early_stopping
        )
    except RecognitionError:
        raise
    except Exception as e:
        raise RecognitionError(f"Failed to process image {image_path}: {str(e)}") from e
