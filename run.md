# Handwritten OCR Setup & Run Guide

## 1. Installation (New Setup)
`cd d:\OCR\handwritten-ocr` — Navigate to the project folder.
`python -m venv .venv` — Create an isolated Python virtual environment.
`.venv\Scripts\activate` — Activate the virtual environment (Windows).
`pip install -r requirements.txt` — Install all required dependencies.
`python download_model.py` — Download the 2.2GB AI model for offline use (Run only once).

## 2. Running the Web Dashboard
`.venv\Scripts\activate` — Activate the environment (if you closed the terminal).
`python app.py` — Start the local web server.
`http://127.0.0.1:7860` — Open this URL in your web browser to use the app.

## 3. Running from Command Line
`.venv\Scripts\activate` — Activate the environment.
`python ocr.py path\to\image.jpg` — Extract text from an image directly in the terminal.

## 4. Crucial Tip
**Preprocessing Mode:** Always use "Light" or "None" in the Web App; "Strong" destroys cursive handwriting and causes the AI to hallucinate numbers.
