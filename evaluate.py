"""Evaluate OCR accuracy against ground truth datasets."""
import sys
import argparse
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from ocr_core.config import EVALUATION_DIR, DEFAULT_PREPROCESSING
from ocr_core.recognizer import recognize_image
from ocr_core.evaluator import evaluate_single, evaluate_batch, format_summary, format_per_image_table
from ocr_core.utils import setup_logging, save_text_output, save_json_output

def main():
    parser = argparse.ArgumentParser(description="Evaluate OCR accuracy against ground truth")
    parser.add_argument("--images-dir", default=str(EVALUATION_DIR / "images"), help="Directory containing test images")
    parser.add_argument("--gt-dir", default=str(EVALUATION_DIR / "ground_truth"), help="Directory containing ground truth .txt files")
    parser.add_argument("--output-dir", default=str(EVALUATION_DIR / "results"), help="Directory to save evaluation results")
    parser.add_argument("--preprocess", default=DEFAULT_PREPROCESSING, choices=["none", "light", "medium", "strong"], help="Preprocessing mode")
    parser.add_argument("--single-line", action="store_true", help="Treat images as single lines")
    
    args = parser.parse_args()
    setup_logging()
    
    images_dir = Path(args.images_dir)
    gt_dir = Path(args.gt_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not images_dir.exists():
        print(f"Images directory not found: {images_dir}")
        print("Please place test images in evaluation/images and ground truth in evaluation/ground_truth")
        sys.exit(1)
        
    image_files = sorted([f for f in images_dir.iterdir() if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".pdf"]])
    if not image_files:
        print(f"No image files found in {images_dir}")
        sys.exit(1)
        
    evaluations = []
    print(f"Evaluating {len(image_files)} images...")
    
    for img_path in tqdm(image_files):
        gt_path = gt_dir / f"{img_path.stem}.txt"
        if not gt_path.exists():
            print(f"[SKIP] Ground truth file not found: {gt_path.name}")
            continue
            
        with open(gt_path, "r", encoding="utf-8") as f:
            ground_truth = f.read().strip()
            
        try:
            result = recognize_image(str(img_path), preprocess=args.preprocess, single_line=args.single_line)
            evaluation = evaluate_single(ground_truth, result.text, image_name=img_path.name, processing_time=result.total_processing_time_seconds)
            evaluations.append(evaluation)
        except Exception as e:
            print(f"[ERROR] Failed to process {img_path.name}: {e}")
            
    if not evaluations:
        print("No matching images and ground truth pairs evaluated.")
        sys.exit(1)
        
    summary = evaluate_batch(evaluations)
    summary_text = format_summary(summary)
    per_image_text = format_per_image_table(evaluations)
    
    full_report = f"{summary_text}\n\n{per_image_text}"
    print("\n" + full_report)
    
    save_text_output(full_report, output_dir / "evaluation_results.txt")
    save_json_output({
        "total_images": summary.total_images,
        "avg_cer": summary.avg_cer,
        "avg_wer": summary.avg_wer,
        "char_accuracy": summary.char_accuracy,
        "word_accuracy": summary.word_accuracy,
        "avg_time": summary.avg_time
    }, output_dir / "evaluation_results.json")
    print(f"\nResults saved to {output_dir}")

if __name__ == "__main__":
    main()
