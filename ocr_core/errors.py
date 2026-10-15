class OCRError(Exception):
    """Base exception for OCR application errors."""
    def __init__(self, message: str, technical_detail: str = ""):
        self.message = message
        self.technical_detail = technical_detail
        super().__init__(message)

    def user_message(self) -> str:
        return self.message

class ModelNotFoundError(OCRError):
    def __init__(self, model_path: str = ""):
        msg = ("ERROR: TrOCR model is not available locally.\n\n"
               "Run 'python download_model.py' while internet access is enabled.\n"
               "After the model is downloaded, OCR can run completely offline.")
        super().__init__(msg, f"Model path: {model_path}")

class InvalidImageError(OCRError):
    def __init__(self, detail: str = "The uploaded file could not be decoded as a valid image."):
        super().__init__(f"Invalid image:\n{detail}")

class PreprocessingError(OCRError):
    def __init__(self, detail: str = "Image preprocessing failed."):
        super().__init__(f"Preprocessing error:\n{detail}")

class LineDetectionError(OCRError):
    def __init__(self, detail: str = "Text line detection failed."):
        super().__init__(f"Line detection error:\n{detail}")

class RecognitionError(OCRError):
    def __init__(self, detail: str = "OCR recognition failed."):
        super().__init__(f"Recognition error:\n{detail}")

class EvaluationError(OCRError):
    def __init__(self, detail: str = "Evaluation failed."):
        super().__init__(f"Evaluation error:\n{detail}")
