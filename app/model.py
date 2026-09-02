import logging
import time
import gc
from pathlib import Path

import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from app.config import MODEL_PATH, MODEL_NAME, DEVICE, OFFLINE_MODE, apply_offline_env
from app.errors import ModelNotFoundError

logger = logging.getLogger("ocr")

class TrOCRModel:
    """Singleton model manager for TrOCR Large Handwritten.
    
    Loads model and processor once, reuses for all inference.
    """
    _instance = None
    _processor = None
    _model = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def processor(self):
        if not self._loaded:
            self.load()
        return self._processor

    @property
    def model(self):
        if not self._loaded:
            self.load()
        return self._model

    @property
    def device(self):
        return DEVICE

    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, model_path: str | Path = None) -> None:
        """Load model and processor from local path."""
        path = Path(model_path) if model_path else MODEL_PATH
        
        if OFFLINE_MODE:
            apply_offline_env()
        
        # Check model files exist
        if not path.exists() or not any(path.iterdir()):
            raise ModelNotFoundError(str(path))
        
        logger.info(f"Loading TrOCR model from {path}...")
        start = time.time()
        
        try:
            from transformers import AutoImageProcessor, RobertaTokenizer
            local_image_processor = AutoImageProcessor.from_pretrained(str(path), local_files_only=True)
            local_tokenizer = RobertaTokenizer.from_pretrained(str(path), local_files_only=True)
            self._processor = TrOCRProcessor(image_processor=local_image_processor, tokenizer=local_tokenizer)
            
            self._model = VisionEncoderDecoderModel.from_pretrained(
                str(path),
                local_files_only=True
            )
            
            from app.config import QUANTIZE_MODEL
            if QUANTIZE_MODEL and DEVICE == "cpu":
                logger.info("Applying dynamic INT8 quantization for faster CPU inference...")
                self._model = torch.quantization.quantize_dynamic(
                    self._model, {torch.nn.Linear}, dtype=torch.qint8
                )
                
            self._model.to(DEVICE)
            self._model.eval()
            self._loaded = True
            
            elapsed = time.time() - start
            param_count = sum(p.numel() for p in self._model.parameters())
            logger.info(f"Model loaded in {elapsed:.2f}s ({param_count/1e6:.0f}M parameters)")
            logger.info(f"Device: {DEVICE}")
        except Exception as e:
            if "not found" in str(e).lower() or "does not appear" in str(e).lower():
                raise ModelNotFoundError(str(path))
            raise ModelNotFoundError(f"Failed to load model: {e}")

    def unload(self) -> None:
        """Unload model to free memory."""
        self._model = None
        self._processor = None
        self._loaded = False
        gc.collect()
        logger.info("Model unloaded.")

    @classmethod
    def get_instance(cls) -> 'TrOCRModel':
        return cls()
