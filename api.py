import sys
import io
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from PIL import Image

from app.config import MODEL_NAME, OFFLINE_MODE, ensure_directories, DEVICE
from app.recognizer import recognize_pil_image
from app.utils import setup_logging, display_system_info

app = FastAPI(title="Handwritten OCR API")

@app.on_event("startup")
async def startup_event():
    setup_logging()
    ensure_directories()
    display_system_info()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": True,
        "device": DEVICE,
        "offline": OFFLINE_MODE,
        "model": MODEL_NAME
    }

@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    preprocess: str = Form("light"),
    single_line: bool = Form(False)
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        result = recognize_pil_image(image, preprocess=preprocess, single_line=single_line)
        return JSONResponse(content=result.to_dict())
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
