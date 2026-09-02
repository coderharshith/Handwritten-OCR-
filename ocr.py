import sys
import os
import argparse
import json
import logging
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from app.config import (
    PROJECT_ROOT, MODEL_NAME, OFFLINE_MODE, OUTPUT_DIR, 
    SUPPORTED_EXTENSIONS, DEFAULT_PREPROCESSING, 
    MAX_NEW_TOKENS, NUM_BEAMS, ensure_directories, apply_offline_env
)
from app.errors import OCRError
from app.recognizer import recognize_image
from app.utils import setup_logging, display_system_info, save_text_output, save_json_output

def main():
    parser = argparse.ArgumentParser(description="Handwritten OCR - TrOCR Large CLI")
    parser.add_argument("image_path", nargs="?", help="Path to input image")
    parser.add_argument("--input", help="Path to input image")
    parser.add_argument("--input-dir", help="Directory of images to process")
    parser.add_argument("--preprocess", default=DEFAULT_PREPROCESSING, choices=["none", "light", "medium", "strong"], help="Preprocessing mode")
    parser.add_argument("--offline", action="store_true", help="Force offline mode")
    parser.add_argument("--low-memory", action="store_true", help="Enable low memory mode")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout instead of normal text")
    parser.add_argument("--show-lines", action="store_true", help="Show detected line info")
    parser.add_argument("--single-line", action="store_true", help="Treat input as single text line")
    parser.add_argument("--max-tokens", type=int, default=MAX_NEW_TOKENS, help="Max new tokens for generation")
    parser.add_argument("--num-beams", type=int, default=NUM_BEAMS, help="Beam search width")
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if args.offline:
        os.environ["OFFLINE_MODE"] = "1"
        apply_offline_env()
    
    if args.low_memory:
        os.environ["LOW_MEMORY_MODE"] = "1"
    
    ensure_directories()
    
    if not args.json:
        display_system_info()
    
    input_path = args.input or args.image_path
    input_dir = args.input_dir
    
    if not input_path and not input_dir:
        parser.error("Must provide either an image path or an input directory")
    
    images_to_process = []
    
    if input_dir:
        dir_path = Path(input_dir)
        if not dir_path.is_dir():
            logger.error(f"Input directory not found: {input_dir}")
            sys.exit(1)
        
        for ext in SUPPORTED_EXTENSIONS:
            images_to_process.extend(dir_path.glob(f"*{ext}"))
            images_to_process.extend(dir_path.glob(f"*{ext.upper()}"))
    elif input_path:
        images_to_process.append(Path(input_path))
    
    if not images_to_process:
        logger.error("No valid images found to process.")
        sys.exit(1)
    
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for img_path in tqdm(images_to_process, disable=args.json):
        try:
            result = recognize_image(
                str(img_path),
                preprocess=args.preprocess,
                single_line=args.single_line
            )
            
            stem = img_path.stem
            txt_out = out_dir / f"{stem}_result.txt"
            json_out = out_dir / f"{stem}_result.json"
            
            save_text_output(result.text, txt_out)
            save_json_output(result.to_dict(), json_out)
            
            if args.json:
                print(json.dumps(result.to_dict(), ensure_ascii=False))
            else:
                print(f"\n--- Result for {img_path.name} ---")
                print(f"Recognized Text:\n{result.text}")
                print(f"Processing Time: {result.total_processing_time_seconds:.2f}s")
                if result.warnings:
                    print(f"Warnings: {', '.join(result.warnings)}")
                
                if args.show_lines and result.lines:
                    print("\nLines:")
                    for idx, line in enumerate(result.lines):
                        print(f"  Line {idx+1}: {line.text}")
                
        except OCRError as e:
            if args.json:
                print(json.dumps({"error": str(e), "file": str(img_path)}))
            else:
                logger.error(f"OCR failed for {img_path}: {e}")
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e), "file": str(img_path)}))
            else:
                logger.error(f"Unexpected error processing {img_path}: {e}", exc_info=True)

if __name__ == '__main__':
    main()
