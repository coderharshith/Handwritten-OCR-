"""Tests for preprocessing."""
import sys
from pathlib import Path

import pytest
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_core.config import PREPROCESSING_MODES
from ocr_core.utils import is_blank_image
from ocr_core.preprocessing import (
    detect_orientation,
    denoise_image,
    enhance_contrast,
    apply_threshold,
    compute_image_quality,
    get_preprocessing_candidates,
    preprocess_image,
)


def create_synthetic_image(blank: bool = False) -> np.ndarray:
    """Create a synthetic BGR image for testing."""
    img = np.ones((100, 300, 3), dtype=np.uint8) * 255
    if not blank:
        # Draw horizontal black bars to simulate text lines
        img[30:40, 20:280] = 0
        img[60:70, 20:280] = 0
    return img


def create_synthetic_pil(blank: bool = False) -> Image.Image:
    """Create a synthetic PIL Image for testing."""
    arr = create_synthetic_image(blank)
    return Image.fromarray(arr[:, :, ::-1])  # BGR to RGB


def test_preprocess_modes() -> None:
    """Test preprocessing modes exist and are valid."""
    assert len(PREPROCESSING_MODES) > 0
    assert isinstance(PREPROCESSING_MODES, list)
    assert "none" in PREPROCESSING_MODES
    assert "light" in PREPROCESSING_MODES


def test_blank_image_detection() -> None:
    """Test is_blank_image detects blank image."""
    img = create_synthetic_image(blank=True)
    assert is_blank_image(img) is True


def test_non_blank_image() -> None:
    """Test is_blank_image detects non-blank image."""
    img = create_synthetic_image(blank=False)
    assert is_blank_image(img) is False


def test_orientation_detection() -> None:
    """Test detect_orientation returns 0 for normal image."""
    img = create_synthetic_image()
    assert detect_orientation(img) == 0


def test_denoise() -> None:
    """Test denoise_image doesn't crash."""
    img = create_synthetic_image()
    result = denoise_image(img, "light")
    assert result is not None
    assert result.shape == img.shape


def test_contrast_enhance() -> None:
    """Test enhance_contrast doesn't crash."""
    img = create_synthetic_image()
    result = enhance_contrast(img)
    assert result is not None


def test_threshold() -> None:
    """Test apply_threshold returns binary image."""
    img = create_synthetic_image()
    result = apply_threshold(img, "otsu")
    assert result is not None
    unique = np.unique(result)
    assert all(v in [0, 255] for v in unique)


def test_image_quality() -> None:
    """Test compute_image_quality returns dict with expected keys."""
    img = create_synthetic_image()
    quality = compute_image_quality(img)
    assert isinstance(quality, dict)
    for key in ["blur_score", "contrast_score", "brightness", "noise_estimate", "edge_density"]:
        assert key in quality


def test_preprocessing_candidates() -> None:
    """Test get_preprocessing_candidates returns list."""
    pil_img = create_synthetic_pil()
    candidates = get_preprocessing_candidates(pil_img)
    assert isinstance(candidates, list)
    assert len(candidates) > 0


def test_preprocess_none_mode() -> None:
    """Test preprocessing with 'none' mode."""
    pil_img = create_synthetic_pil()
    result = preprocess_image(pil_img, mode="none")
    assert result is not None
    assert result.mode == "none"


def test_preprocess_light_mode() -> None:
    """Test preprocessing with 'light' mode."""
    pil_img = create_synthetic_pil()
    result = preprocess_image(pil_img, mode="light")
    assert result is not None
    assert result.mode == "light"
