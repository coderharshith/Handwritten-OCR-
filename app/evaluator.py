import logging
from dataclasses import dataclass, field
from typing import List

import jiwer

from app.errors import EvaluationError

logger = logging.getLogger("ocr")

@dataclass
class ImageEvaluation:
    image_name: str
    cer: float
    wer: float
    processing_time: float
    recognized_text: str
    ground_truth: str

@dataclass
class EvaluationSummary:
    total_images: int
    avg_cer: float
    avg_wer: float
    char_accuracy: float  # max(0, 1 - avg_cer) -- carefully derived
    word_accuracy: float  # max(0, 1 - avg_wer)
    avg_time: float
    per_image: List[ImageEvaluation] = field(default_factory=list)

def compute_cer(reference: str, hypothesis: str) -> float:
    if not reference and not hypothesis:
        return 0.0
    if not reference and hypothesis:
        return 1.0
    try:
        return jiwer.cer(reference, hypothesis)
    except Exception as e:
        logger.error(f"Error computing CER: {e}")
        return 1.0

def compute_wer(reference: str, hypothesis: str) -> float:
    if not reference and not hypothesis:
        return 0.0
    if not reference and hypothesis:
        return 1.0
    try:
        return jiwer.wer(reference, hypothesis)
    except Exception as e:
        logger.error(f"Error computing WER: {e}")
        return 1.0

def evaluate_single(reference: str, hypothesis: str, image_name: str = "", processing_time: float = 0.0) -> ImageEvaluation:
    cer = compute_cer(reference, hypothesis)
    wer = compute_wer(reference, hypothesis)
    
    return ImageEvaluation(
        image_name=image_name,
        cer=cer,
        wer=wer,
        processing_time=processing_time,
        recognized_text=hypothesis,
        ground_truth=reference
    )

def evaluate_batch(results: List[ImageEvaluation]) -> EvaluationSummary:
    if not results:
        return EvaluationSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0, [])
        
    total_images = len(results)
    avg_cer = sum(r.cer for r in results) / total_images
    avg_wer = sum(r.wer for r in results) / total_images
    avg_time = sum(r.processing_time for r in results) / total_images
    
    # Note: Character accuracy and word accuracy are approximations derived from error rates.
    char_accuracy = max(0.0, 1.0 - avg_cer)
    word_accuracy = max(0.0, 1.0 - avg_wer)
    
    return EvaluationSummary(
        total_images=total_images,
        avg_cer=avg_cer,
        avg_wer=avg_wer,
        char_accuracy=char_accuracy,
        word_accuracy=word_accuracy,
        avg_time=avg_time,
        per_image=results
    )

def format_summary(summary: EvaluationSummary) -> str:
    return (
        f"Evaluation Results\n"
        f"------------------\n"
        f"Images evaluated: {summary.total_images}\n\n"
        f"CER: {summary.avg_cer * 100:.2f}%\n"
        f"WER: {summary.avg_wer * 100:.2f}%\n\n"
        f"Character Accuracy: {summary.char_accuracy * 100:.2f}% (estimated from CER)\n"
        f"Word Accuracy: {summary.word_accuracy * 100:.2f}% (estimated from WER)\n\n"
        f"Average inference time: {summary.avg_time:.2f} sec/image"
    )

def format_per_image_table(results: List[ImageEvaluation]) -> str:
    lines = ["Image | CER | WER | Time"]
    for r in results:
        lines.append(f"{r.image_name} | {r.cer:.4f} | {r.wer:.4f} | {r.processing_time:.2f}")
    return "\n".join(lines)
