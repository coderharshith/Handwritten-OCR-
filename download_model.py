import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.append(str(PROJECT_ROOT))

import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

def main():
    model_name = "microsoft/trocr-large-handwritten"
    model_path = PROJECT_ROOT / "models" / "trocr-large-handwritten"
    
    print(f"Downloading model: {model_name}")
    print(f"Target directory: {model_path}")
    
    model_path.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    
    try:
        print("\n1. Downloading Processor...")
        from transformers import AutoImageProcessor, RobertaTokenizer
        image_processor = AutoImageProcessor.from_pretrained(model_name)
        tokenizer = RobertaTokenizer.from_pretrained(model_name)
        processor = TrOCRProcessor(image_processor=image_processor, tokenizer=tokenizer)
        processor.save_pretrained(str(model_path))
        print("Processor downloaded and saved successfully.")
        
        print("\n2. Downloading Model (this may take a while for large models)...")
        model = VisionEncoderDecoderModel.from_pretrained(model_name)
        model.save_pretrained(str(model_path))
        print("Model downloaded and saved successfully.")
        
        download_time = time.time() - start_time
        print(f"\nDownload completed in {download_time:.2f} seconds.")
        
        print("\n3. Verifying local installation...")
        print("Loading locally saved model...")
        
        local_image_processor = AutoImageProcessor.from_pretrained(str(model_path), local_files_only=True)
        from transformers import RobertaTokenizer
        local_tokenizer = RobertaTokenizer.from_pretrained(str(model_path), local_files_only=True)
        local_processor = TrOCRProcessor(image_processor=local_image_processor, tokenizer=local_tokenizer)
        local_model = VisionEncoderDecoderModel.from_pretrained(str(model_path), local_files_only=True)
        local_model.eval()
        
        print("Creating dummy image...")
        dummy_image = Image.new('RGB', (100, 30), color='white')
        
        print("Running inference on dummy image...")
        pixel_values = local_processor(images=dummy_image, return_tensors="pt").pixel_values
        
        with torch.no_grad():
            generated_ids = local_model.generate(pixel_values, max_new_tokens=10)
            
        text = local_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        print("Verification successful!")
        print(f"Dummy output: '{text}'")
        
        print("\nModel is ready for offline use.")
        
    except Exception as e:
        print(f"\nAn error occurred during download or verification:\n{e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
