"""Evaluate OCR accuracy against ground truth."""
import sys
import argparse
import json
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from app.recognizer import recognize_image
from app.evaluator import evaluate_single, evaluate_batch, format_summary, format_per_image_table

def main():
    parser = argparse.ArgumentParser(description="Evaluate OCR accuracy against ground truth.")
    parser.add_argument("--images-dir", type=str, default="evaluation/images", help="Directory containing evaluation images")
    parser.add_argument("--gt-dir", type=str, default="evaluation/ground_truth", help="Directory containing ground truth text files")
    parser.add_argument("--output-dir", type=str, default="evaluation/results", help="Directory to save evaluation results")
    parser.add_argument("--preprocess", type=str, default=None, help="Preprocessing method to apply")
    parser.add_argument("--single-line", action="store_true", help="Treat images as single lines (skip line detection)")
    
    args = parser.parse_args()
    
    images_dir = Path(args.images_dir)
    gt_dir = Path(args.gt_dir)
    output_dir = Path(args.output_dir)
    
    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        return
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_files = list(images_dir.glob("*.*"))
    image_files = [f for f in image_files if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]
    
    if not image_files:
        print(f"No images found in {images_dir}")
        return
        
    results = []
    
    for img_path in tqdm(image_files, desc="Evaluating"):
        gt_path = gt_dir / f"{img_path.stem}.txt"
        if not gt_path.exists():
            print(f"Warning: Missing ground truth for {img_path.name}. Skipping.")
            continue
            
        with open(gt_path, 'r', encoding='utf-8') as f:
            gt_text = f.read().strip()
            
        try:
            recognition_result = recognize_image(
                img_path, 
                preprocess=args.preprocess,
                single_line=args.single_line
            )
            
            evaluation = evaluate_single(
                reference=gt_text,
                hypothesis=recognition_result.text,
                image_name=img_path.name,
                processing_time=recognition_result.total_processing_time_seconds
            )
            
            results.append(evaluation)
            
        except Exception as e:
            print(f"Error processing {img_path.name}: {e}")
            
    if not results:
        print("No valid results to summarize.")
        return
        
    summary = evaluate_batch(results)
    
    summary_text = format_summary(summary)
    print("\n" + summary_text)
    
    table_text = format_per_image_table(results)
    print("\n" + table_text)
    
    with open(output_dir / "evaluation_results.txt", "w", encoding='utf-8') as f:
        f.write(summary_text + "\n\n" + table_text)
        
    json_results = {
        "total_images": summary.total_images,
        "avg_cer": summary.avg_cer,
        "avg_wer": summary.avg_wer,
        "char_accuracy": summary.char_accuracy,
        "word_accuracy": summary.word_accuracy,
        "avg_time": summary.avg_time,
        "results": [
            {
                "image": r.image_name,
                "cer": r.cer,
                "wer": r.wer,
                "time": r.processing_time,
                "ground_truth": r.ground_truth,
                "recognized": r.recognized_text
            } for r in results
        ]
    }
    
    with open(output_dir / "evaluation_results.json", "w", encoding='utf-8') as f:
        json.dump(json_results, f, indent=4)
        
    print(f"\nResults saved to {output_dir}")

if __name__ == '__main__':
    main()
