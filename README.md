# Handwritten OCR — TrOCR Large Handwritten

A production-ready, offline handwritten OCR application using **microsoft/trocr-large-handwritten**.

Runs **100% locally on CPU only** after the initial model download. No GPU required. No cloud APIs. Your images never leave your machine.

---

## Table of Contents

- [Installation](#installation)
- [CPU-Only Setup](#cpu-only-setup)
- [Model Download](#model-download)
- [Offline Mode](#offline-mode)
- [Running OCR](#running-ocr)
- [Full-Page OCR](#full-page-ocr)
- [Single-Line OCR](#single-line-ocr)
- [Gradio GUI](#gradio-gui)
- [FastAPI API](#fastapi-api)
- [Accuracy Evaluation](#accuracy-evaluation)
- [CER and WER](#cer-and-wer)
- [Fine-Tuning](#fine-tuning)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)
- [Project Architecture](#project-architecture)

---

## Installation

### Prerequisites

- Python 3.11
- Windows 10/11

### Automatic Setup (Recommended)

```powershell
cd handwritten-ocr
setup.bat
```

This will:
1. Check Python installation
2. Create a virtual environment (`.venv`)
3. Install CPU-only PyTorch
4. Install all dependencies
5. Create required directories
6. Download the TrOCR model (~2.2 GB)
7. Run a verification test

### Manual Setup

```powershell
cd handwritten-ocr

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install CPU-only PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install dependencies
pip install -r requirements.txt

# Download the model
python download_model.py
```

---

## CPU-Only Setup

This application explicitly uses CPU only:

```
Device: CPU
GPU: Disabled
Offline Mode: Enabled
Model: microsoft/trocr-large-handwritten
```

No CUDA, NVIDIA GPU, TensorRT, or ROCm is required.

**RAM Requirements:**
- Minimum: 8 GB RAM
- Recommended: 16 GB RAM
- The TrOCR Large model has ~558M parameters and requires approximately 2-4 GB of RAM when loaded

---

## Model Download

The model is downloaded once during setup:

```powershell
python download_model.py
```

This downloads `microsoft/trocr-large-handwritten` from Hugging Face and saves it locally to:

```
models/trocr-large-handwritten/
```

After download, all inference runs locally using `local_files_only=True`.

---

## Offline Mode

After the model is downloaded, the application runs completely offline.

The offline mode is enabled by default. Configuration options:

**Environment variables:**
```
OFFLINE_MODE=true
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

**CLI flag:**
```powershell
python ocr.py --offline image.png
```

If the model is not available locally, you will see:
```
ERROR: TrOCR model is not available locally.

Run 'python download_model.py' while internet access is enabled.
After the model is downloaded, OCR can run completely offline.
```

---

## Running OCR

### CLI — Single Image

```powershell
python ocr.py image.png
```

or:

```powershell
python ocr.py --input image.png
```

### CLI — Directory of Images

```powershell
python ocr.py --input-dir input/
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--preprocess` | Preprocessing mode: `none`, `light`, `medium`, `strong` (default: `light`) |
| `--offline` | Force offline mode |
| `--low-memory` | Enable low-memory mode (reduces max image dimensions) |
| `--output` | Output directory (default: `output/`) |
| `--json` | Output JSON to stdout |
| `--show-lines` | Show detected line information |
| `--single-line` | Treat input as a single text line |
| `--max-tokens` | Max tokens to generate (default: 200) |
| `--num-beams` | Beam search width (default: 1) |

### Output

Results are saved to `output/`:
- `{filename}_result.txt` — plain text
- `{filename}_result.json` — structured JSON

---

## Full-Page OCR

For full-page handwritten images, the application automatically:

1. Validates the image
2. Preprocesses (orientation, deskew, denoise, contrast)
3. Detects individual text lines using projection profile analysis
4. Crops each line
5. Sends each line to TrOCR independently
6. Sorts lines top-to-bottom
7. Assembles the full text
8. Post-processes and checks for quality issues

```powershell
python ocr.py full_page.png
```

---

## Single-Line OCR

For images containing a single line of handwriting:

```powershell
python ocr.py --single-line line_image.png
```

This skips line detection and sends the entire image directly to TrOCR.

---

## Gradio GUI

Launch the web interface:

```powershell
python app.py
```

Or use the batch script:

```powershell
run.bat
```

The GUI opens at `http://127.0.0.1:7860` and provides:

- Image upload and preview
- Preprocessing mode selection
- Full Page / Single Line mode
- Recognized text display
- Processing time
- Estimated recognition quality
- Warnings
- Download `.txt` and `.json` results

---

## FastAPI API

Start the API server:

```powershell
python api.py
```

### Endpoints

**Health check:**
```
GET http://127.0.0.1:8000/health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cpu",
  "offline": true,
  "model": "microsoft/trocr-large-handwritten"
}
```

**OCR:**
```
POST http://127.0.0.1:8000/ocr
Content-Type: multipart/form-data
```

Parameters:
- `file`: Image file (required)
- `preprocess`: Preprocessing mode (optional, default: "light")
- `single_line`: Boolean (optional, default: false)

---

## Accuracy Evaluation

### Setup

Place evaluation images and ground truth text files:

```
evaluation/
├── images/
│   ├── 001.png
│   ├── 002.png
│   └── 003.png
└── ground_truth/
    ├── 001.txt
    ├── 002.txt
    └── 003.txt
```

Each `.txt` file should contain the ground truth text for the corresponding image.

### Run Evaluation

```powershell
python evaluate.py
```

Options:
```powershell
python evaluate.py --images-dir evaluation/images --gt-dir evaluation/ground_truth --output-dir evaluation/results
```

### Output

```
Evaluation Results
------------------
Images evaluated: 100

CER: 6.42%
WER: 12.17%

Character Accuracy: 93.58% (estimated from CER)
Word Accuracy: 87.83% (estimated from WER)

Average inference time: 4.71 sec/image
```

Per-image results are also displayed and saved to `evaluation/results/`.

---

## CER and WER

**CER (Character Error Rate):** The edit distance between the predicted and reference text at the character level, normalized by the reference length.

**WER (Word Error Rate):** The edit distance between the predicted and reference text at the word level, normalized by the reference length.

**Character Accuracy** is derived as `max(0, 1 - CER)`. This is an approximation and should not be treated as an independently validated metric.

These metrics are computed using the `jiwer` library.

---

## Fine-Tuning

The application is designed to support fine-tuning on custom handwriting datasets.

### Dataset Format

```
dataset/
├── train/
│   ├── images/
│   │   ├── 001.png
│   │   └── 002.png
│   └── labels.csv
├── validation/
│   ├── images/
│   └── labels.csv
└── test/
    ├── images/
    └── labels.csv
```

**labels.csv format:**
```csv
image,text
001.png,"This is handwritten text."
002.png,"Another handwritten sentence."
```

### Run Fine-Tuning

```powershell
python train.py --dataset-dir dataset/ --epochs 3 --batch-size 4
```

> **Note:** Fine-tuning on CPU is functional but will be very slow. A GPU is strongly recommended for fine-tuning.

Fine-tuning does NOT run automatically during normal installation.

---

## Known Limitations

### Model Limitations

- **English only:** `microsoft/trocr-large-handwritten` was fine-tuned on the IAM handwriting dataset (English). It is NOT a universal multilingual handwriting model.
- **Do NOT expect reliable recognition** for Kannada, Hindi, Tamil, Telugu, or other non-English scripts without evaluation or fine-tuning.
- **Single-line optimized:** TrOCR is designed for single text-line images. Full-page recognition depends on the line detection quality.

### Accuracy Expectations

The published Microsoft TrOCR benchmark reports **2.89 cased CER on the IAM test set**. This is a dataset-specific benchmark result, NOT a universal accuracy guarantee.

Accuracy can decrease significantly with:
- Unfamiliar handwriting styles
- Poor lighting or blur
- Shadows or skew
- Low resolution images
- Unusual paper/background
- Heavy cursive handwriting
- Overlapping or cropped characters
- Non-English languages

**Always evaluate on your own data** using `python evaluate.py` to measure actual CER/WER.

### Technical Limitations

- CPU inference is slower than GPU (typically 2-10 seconds per line)
- The model requires ~2-4 GB RAM when loaded
- Very large images are automatically resized
- Line detection uses projection profile analysis, which may struggle with complex layouts

---

## Troubleshooting

### Model not found

```
ERROR: TrOCR model is not available locally.
```

**Solution:** Run `python download_model.py` with internet access.

### Out of memory

**Solution:** Use `--low-memory` mode:
```powershell
python ocr.py --low-memory image.png
```

Or set in `.env`:
```
LOW_MEMORY_MODE=true
```

### Slow processing

- CPU inference for TrOCR Large typically takes 2-10 seconds per text line
- Use `--num-beams 1` (default) for fastest inference
- Use `--low-memory` to reduce image sizes
- Preprocessing adds some overhead; use `--preprocess none` for fastest results

### Import errors

Make sure you activated the virtual environment:
```powershell
.\.venv\Scripts\activate
```

### Gradio not launching

Check port 7860 is available. The GUI binds to `127.0.0.1:7860`.

---

## Performance

### CPU Inference Times (Approximate)

These are rough estimates and vary by hardware and image complexity:

| Scenario | Time |
|----------|------|
| Single line, no preprocessing | 2-5 seconds |
| Single line, light preprocessing | 3-6 seconds |
| Full page (10 lines), light preprocessing | 20-60 seconds |
| Model loading (first run) | 15-45 seconds |

**These are not guaranteed speeds.** Actual times depend on:
- CPU model and speed
- Available RAM
- Image size and complexity
- Preprocessing mode
- Number of detected lines
- Beam search width

### Memory Usage

- Model loading: ~2-4 GB RAM
- Per-image processing: ~200-500 MB additional
- Total recommended: 8-16 GB RAM

---

## Project Architecture

```
handwritten-ocr/
│
├── app/                    # Core application modules
│   ├── __init__.py         # Package init
│   ├── config.py           # Central configuration
│   ├── errors.py           # Custom exceptions
│   ├── model.py            # Singleton TrOCR model loader
│   ├── preprocessing.py    # Image preprocessing pipeline
│   ├── line_detector.py    # Text line detection/segmentation
│   ├── recognizer.py       # Main OCR recognition engine
│   ├── postprocessor.py    # Text post-processing & quality
│   ├── evaluator.py        # CER/WER evaluation metrics
│   └── utils.py            # Logging, validation, utilities
│
├── models/                 # Downloaded model files
│   └── trocr-large-handwritten/
│
├── input/                  # Input images
├── output/                 # OCR results
├── test_images/            # Test images
├── evaluation/             # Evaluation data
│   ├── images/
│   ├── ground_truth/
│   └── results/
│
├── tests/                  # Automated tests
│   ├── test_model.py
│   ├── test_preprocessing.py
│   ├── test_recognition.py
│   └── test_evaluation.py
│
├── app.py                  # Gradio GUI
├── api.py                  # FastAPI REST API
├── ocr.py                  # CLI interface
├── evaluate.py             # Evaluation script
├── download_model.py       # Model download script
├── train.py                # Fine-tuning script
│
├── requirements.txt        # Python dependencies
├── setup.bat               # Windows setup script
├── run.bat                 # Launch GUI script
├── .env.example            # Environment config template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

### Data Flow

```
Input Image
    ↓
Image Validation (format, dimensions, corruption)
    ↓
Image Preprocessing (orientation, deskew, denoise, contrast)
    ↓
Text-Line Detection (projection profile segmentation)
    ↓
Individual Line Cropping
    ↓
TrOCR Large Handwritten (per-line recognition)
    ↓
Post-processing (whitespace cleanup, issue detection)
    ↓
Quality Assessment (image quality + output characteristics)
    ↓
Text Assembly (line ordering, reconstruction)
    ↓
Output (JSON + TXT)
```

---

## Security & Privacy

- **Local-first:** All processing happens on your local machine
- **No cloud APIs:** Images are never uploaded to Google, OpenAI, Microsoft, or any cloud service
- **Offline after setup:** After the initial model download, no internet is required
- **No content logging:** Handwritten content is NOT logged by default

---

## License

This project uses `microsoft/trocr-large-handwritten` which is available under the MIT license from Microsoft.
