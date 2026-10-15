"""Tests for evaluation metrics."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_core.evaluator import (
    compute_cer,
    compute_wer,
    evaluate_single,
    evaluate_batch,
    format_summary,
    ImageEvaluation,
    EvaluationSummary,
)


def test_cer_identical() -> None:
    """Test CER on identical strings."""
    assert compute_cer("hello", "hello") == 0.0


def test_cer_different() -> None:
    """Test CER on different strings."""
    assert compute_cer("hello", "hallo") > 0.0


def test_cer_empty_both() -> None:
    """Test CER on empty strings."""
    assert compute_cer("", "") == 0.0


def test_wer_identical() -> None:
    """Test WER on identical strings."""
    assert compute_wer("hello world", "hello world") == 0.0


def test_wer_different() -> None:
    """Test WER on different strings."""
    assert compute_wer("hello world", "hello earth") > 0.0


def test_evaluate_single() -> None:
    """Test evaluate_single returns ImageEvaluation."""
    result = evaluate_single("hello world", "hello earth", image_name="test.png", processing_time=1.0)
    assert isinstance(result, ImageEvaluation)
    assert hasattr(result, "cer")
    assert hasattr(result, "wer")
    assert result.cer > 0
    assert result.wer > 0


def test_evaluate_batch() -> None:
    """Test evaluate_batch returns EvaluationSummary."""
    eval1 = evaluate_single("hello world", "hello earth", image_name="test1.png")
    eval2 = evaluate_single("foo bar", "foo baz", image_name="test2.png")
    summary = evaluate_batch([eval1, eval2])
    assert isinstance(summary, EvaluationSummary)
    assert summary.total_images == 2
    assert summary.avg_cer > 0
    assert summary.avg_wer > 0


def test_format_summary() -> None:
    """Test format_summary returns string with title."""
    eval1 = evaluate_single("hello", "hello", image_name="test.png")
    summary = evaluate_batch([eval1])
    text = format_summary(summary)
    assert "Evaluation Results" in text


def test_char_accuracy() -> None:
    """Test char accuracy is derived from CER."""
    cer = compute_cer("hello", "hallo")
    char_acc = max(0.0, 1.0 - cer)
    assert 0.0 <= char_acc <= 1.0


def test_empty_batch() -> None:
    """Test evaluate_batch with empty list."""
    summary = evaluate_batch([])
    assert summary.total_images == 0
    assert summary.avg_cer == 0.0
