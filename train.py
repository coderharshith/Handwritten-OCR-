import sys
import os
import csv
import argparse
from pathlib import Path
from tqdm import tqdm
from PIL import Image

import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

sys.path.insert(0, str(Path(__file__).parent))
from ocr_core.config import MODEL_PATH, DEVICE

class HandwritingDataset(Dataset):
    def __init__(self, root_dir, processor, max_length=128):
        self.root_dir = Path(root_dir)
        self.processor = processor
        self.max_length = max_length
        self.samples = []
        csv_path = self.root_dir / "labels.csv"
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.samples.append({"image": row["image"], "text": row["text"]})
        
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        row = self.samples[idx]
        image_path = self.root_dir / "images" / row['image']
        text = str(row['text'])
        
        image = Image.open(image_path).convert("RGB")
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
        
        labels = self.processor.tokenizer(
            text, padding="max_length", max_length=self.max_length, truncation=True
        ).input_ids
        
        labels = [label if label != self.processor.tokenizer.pad_token_id else -100 for label in labels]
        
        return {"pixel_values": pixel_values, "labels": torch.tensor(labels)}

def compute_metrics(pred_strs, label_strs):
    import jiwer
    cer = jiwer.cer(" ".join(label_strs), " ".join(pred_strs)) if label_strs else 0.0
    wer = jiwer.wer(" ".join(label_strs), " ".join(pred_strs)) if label_strs else 0.0
    return cer, wer

def main():
    parser = argparse.ArgumentParser(description="Fine-tune TrOCR on custom handwriting dataset")
    parser.add_argument("--dataset-dir", required=True, help="Path to dataset root")
    parser.add_argument("--output-dir", default="models/finetuned", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--max-length", type=int, default=128, help="Max sequence length")
    
    args = parser.parse_args()
    
    from transformers import AutoImageProcessor, RobertaTokenizer
    local_image_processor = AutoImageProcessor.from_pretrained(str(MODEL_PATH))
    local_tokenizer = RobertaTokenizer.from_pretrained(str(MODEL_PATH))
    processor = TrOCRProcessor(image_processor=local_image_processor, tokenizer=local_tokenizer)
    model = VisionEncoderDecoderModel.from_pretrained(str(MODEL_PATH))
    model.to(DEVICE)
    
    train_dataset = HandwritingDataset(Path(args.dataset_dir) / "train", processor, args.max_length)
    val_dataset = HandwritingDataset(Path(args.dataset_dir) / "validation", processor, args.max_length)
    test_dataset = HandwritingDataset(Path(args.dataset_dir) / "test", processor, args.max_length)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size)
    
    optimizer = AdamW(model.parameters(), lr=args.learning_rate)
    
    best_cer = float('inf')
    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    for epoch in range(args.epochs):
        model.train()
        train_loss = 0
        for batch in tqdm(train_loader, desc=f"Epoch {epoch+1} Train"):
            optimizer.zero_grad()
            pixel_values = batch["pixel_values"].to(DEVICE)
            labels = batch["labels"].to(DEVICE)
            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        print(f"Epoch {epoch+1} Loss: {train_loss / len(train_loader)}")
        
        model.eval()
        val_preds, val_labels = [], []
        with torch.no_grad():
            for batch in tqdm(val_loader, desc=f"Epoch {epoch+1} Val"):
                pixel_values = batch["pixel_values"].to(DEVICE)
                labels = batch["labels"].to(DEVICE)
                generated_ids = model.generate(pixel_values)
                pred_str = processor.batch_decode(generated_ids, skip_special_tokens=True)
                labels[labels == -100] = processor.tokenizer.pad_token_id
                label_str = processor.batch_decode(labels, skip_special_tokens=True)
                val_preds.extend(pred_str)
                val_labels.extend(label_str)
                
        cer, wer = compute_metrics(val_preds, val_labels)
        print(f"Validation CER: {cer:.4f}, WER: {wer:.4f}")
        
        if cer < best_cer:
            best_cer = cer
            model.save_pretrained(out_path)
            processor.save_pretrained(out_path)
            print("Saved new best model.")
            
    print("Training complete. Evaluating on test set...")
    model = VisionEncoderDecoderModel.from_pretrained(out_path)
    model.to(DEVICE)
    model.eval()
    test_preds, test_labels = [], []
    with torch.no_grad():
        for batch in tqdm(test_loader, desc="Test"):
            pixel_values = batch["pixel_values"].to(DEVICE)
            labels = batch["labels"].to(DEVICE)
            generated_ids = model.generate(pixel_values)
            pred_str = processor.batch_decode(generated_ids, skip_special_tokens=True)
            labels[labels == -100] = processor.tokenizer.pad_token_id
            label_str = processor.batch_decode(labels, skip_special_tokens=True)
            test_preds.extend(pred_str)
            test_labels.extend(label_str)
            
    cer, wer = compute_metrics(test_preds, test_labels)
    print(f"Test CER: {cer:.4f}, WER: {wer:.4f}")

if __name__ == '__main__':
    main()
