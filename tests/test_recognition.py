"""Tests for recognition pipeline."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_core.recognizer import RecognitionResult, LineRecognition
from ocr_core.postprocessor import postprocess_text, detect_ocr_issues, assemble_lines
from ocr_core.config import MODEL_PATH, MODEL_NAME, DEVICE, OFFLINE_MODE


def test_recognition_result_structure() -> None:
    """Test RecognitionResult has required fields."""
    result = RecognitionResult(
        success=True,
        text="Sample text",
        lines=[],
        total_processing_time_seconds=1.0,
    )
    assert hasattr(result, "success")
    assert hasattr(result, "text")
    assert hasattr(result, "model")
    assert hasattr(result, "lines")
    assert hasattr(result, "total_processing_time_seconds")


def test_line_recognition_structure() -> None:
    """Test LineRecognition has required fields."""
    line = LineRecognition(
        line_number=1,
        text="Sample text",
        processing_time_seconds=1.0,
        quality_score=0.8,
    )
    assert hasattr(line, "text")
    assert hasattr(line, "line_number")
    assert hasattr(line, "processing_time_seconds")
    assert hasattr(line, "quality_score")


def test_result_to_dict() -> None:
    """Test to_dict returns valid dict with all keys."""
    result = RecognitionResult(
        success=True,
        text="Sample text",
        lines=[],
        total_processing_time_seconds=1.5,
    )
    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["success"] is True
    assert d["model"] == MODEL_NAME
    assert d["device"] == DEVICE


def test_invalid_image_path() -> None:
    """Test recognize_image with bad path raises error."""
    from ocr_core.recognizer import recognize_image
    from ocr_core.errors import RecognitionError
    with pytest.raises((RecognitionError, Exception)):
        recognize_image("invalid/path/to/image.jpg")


def test_json_output_format() -> None:
    """Test result dict has correct keys."""
    result = RecognitionResult(
        success=True,
        text="Sample text",
        lines=[],
        total_processing_time_seconds=2.0,
    )
    d = result.to_dict()
    for key in ["success", "model", "device", "offline", "text", "lines",
                "total_processing_time_seconds", "warnings"]:
        assert key in d


def test_postprocess_text() -> None:
    """Test strips whitespace, normalizes spaces."""
    assert postprocess_text("  hello   world  ") == "hello world"


def test_detect_ocr_issues_empty() -> None:
    """Test empty string produces warning."""
    warnings = detect_ocr_issues("")
    assert len(warnings) > 0
    assert any("no output" in w.lower() for w in warnings)


def test_detect_ocr_issues_repeated() -> None:
    """Test repeated chars produce warning."""
    warnings = detect_ocr_issues("hellllllllo")
    assert len(warnings) > 0
    assert any("repeated" in w.lower() for w in warnings)


def test_assemble_lines() -> None:
    """Test joins lines with newlines."""
    result = assemble_lines(["line1", "line2"])
    assert "line1" in result
    assert "line2" in result


@pytest.mark.skipif(not Path(MODEL_PATH).exists(), reason="Model not downloaded")
def test_integration_single_line() -> None:
    """Integration test: recognize a synthetic image."""
    from PIL import Image
    from ocr_core.recognizer import recognize_pil_image
    img = Image.new("RGB", (200, 50), color="white")
    result = recognize_pil_image(img, preprocess="none", single_line=True)
    assert result.success is True
    assert isinstance(result.text, str)
