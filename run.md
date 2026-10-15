# Booklet Evaluation System — User & Execution Guide

**Booklet Evaluation System** is a full-stack, offline-capable handwritten answer evaluation platform powered by Microsoft's `trocr-large-handwritten` AI model, FastAPI, MySQL, and a responsive web dashboard.

---

## 1. Prerequisites

Before starting the application, ensure the following are installed and configured:

1. **Python 3.10+** (Python 3.10 to 3.13 supported)
2. **XAMPP / MySQL Server**:
   - MySQL service running on port 3306 with database named `evaluation`.
   - Installed in `D:\xampp` (started automatically by `run.bat`).
3. **NVIDIA GPU (Optional)**:
   - If an NVIDIA GPU (e.g., RTX 3050+) is present, the system automatically uses CUDA for 10x-20x faster OCR processing.
   - If no GPU is available, it automatically runs in CPU mode.
4. **Downloaded Model Weights**:
   - Offline TrOCR model weights stored under `models/trocr-large-handwritten`.

---

## 2. Quick Start (Recommended)

### Option 1: 1-Click Batch Runner (`run.bat`)
Simply double-click **`run.bat`** in the project root folder (`d:\OCR\handwritten-ocr\run.bat`).

This script automatically:
1. Verifies the `.venv` virtual environment and TrOCR model files.
2. Starts the XAMPP MySQL database service in the background (if not already running).
3. Activates the Python virtual environment.
4. Starts the FastAPI server on `http://127.0.0.1:8000`.

---

### Option 2: Command-Line (PowerShell / Command Prompt)

If you prefer starting the server manually:

#### Step 1: Start MySQL
Open XAMPP Control Panel and start **MySQL**, or run:
```powershell
Start-Process "D:\xampp\mysql_start.bat"
```

#### Step 2: Activate Virtual Environment
```powershell
cd d:\OCR\handwritten-ocr
.\.venv\Scripts\Activate.ps1
```
*(In standard Windows CMD, use `call .venv\Scripts\activate.bat`)*

#### Step 3: Start the FastAPI Application
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 3. Accessing the Application

Once the server is running, open your web browser and navigate to:

**http://127.0.0.1:8000**

| Portal | URL | Default Credentials | Description |
|---|---|---|---|
| **Unified Login** | `http://127.0.0.1:8000` | — | Role selection (Faculty / Student) & login forms |
| **Teacher Dashboard** | `http://127.0.0.1:8000/teacher-dashboard.html` | `gsssteacher` / `gsss@23` | Booklet evaluation, student management, OCR results |
| **Student Dashboard** | `http://127.0.0.1:8000/student-dashboard.html` | Created by Teacher | View scores and evaluated answers |
| **Teacher Registration**| `http://127.0.0.1:8000/register-teacher.html` | — | Register a new faculty account |
| **Student Registration**| `http://127.0.0.1:8000/register-student.html` | — | Register a new student account |

---

## 4. Step-by-Step Teacher Guide (OCR Evaluation)

### Step 1: Log In
- Go to `http://127.0.0.1:8000`.
- Select the **Faculty** tab.
- Enter username `gsssteacher` and password `gsss@23` (or your registered credentials).
- Click **Sign in as Teacher**.

### Step 2: Evaluate Booklets
1. In the **Upload Student PDFs or ZIP** box:
   - Drag and drop your scanned student answer PDF (e.g., student answersheet) or click **Choose Files**.
2. *(Optional)* In the **Upload Answer Key** box:
   - Upload the faculty answer key PDF to enable automatic grading and scoring.
3. Select **Processing Options**:
   - **Preprocessing Mode**: `Light (Fast)` (recommended), `Medium`, `Strong`, or `None`.
   - **Recognition Mode**: `Full Page (Recommended)` or `Single Line`.
4. Click **Run OCR**:
   - The model renders PDF pages to high-resolution images in memory.
   - The TrOCR neural network extracts handwritten text line-by-line.
   - The Q&A parser automatically segments text by question numbers (e.g., `1a`, `1b`, `2`, `3`).
   - If an Answer Key was uploaded, answers are evaluated and graded against key concepts.

### Step 3: Review Results
- Extracted answers appear in the **OCR Results** viewer formatted into individual, scrollable Q&A cards with word-wrapping:
  - **Question Badge** (`Q 1a`, `Q 1b`, etc.)
  - **Score Badge** (marks awarded / max marks)
  - **Answer Text** (clean, formatted handwritten text)
- Result statistics display: **Processing Time**, **Recognition Quality**, **Lines Detected**, and **Warnings**.

### Step 4: Download Results
- **Download Q&A JSON**: Exports a structured JSON file mapping question numbers to answers:
  ```json
  {
    "1a": "Steps in designing a machine learning system...",
    "1b": "Candidate - Elimination Algorithm...",
    "3": "Choosing a Representation for the Target function..."
  }
  ```
- **Download Result JSON**: Exports complete evaluation metadata including total score and timings.

### Step 5: Manage Students
- Click the **Manage Students** tab in the top navigation bar.
- Add new student usernames and passwords.
- Remove student records or view all registered student accounts.

---

## 5. Student Guide

1. Navigate to `http://127.0.0.1:8000`.
2. Select the **Student** tab and sign in using your assigned credentials.
3. View your evaluated question marks, individual question feedback, and overall booklet score.

---

## 6. Project Architecture & File Structure

```
handwritten-ocr/
├── backend/                        # FastAPI Backend Service
│   ├── app/
│   │   ├── main.py                 # Application entry point & static file mount
│   │   ├── database.py             # Database engine & session config
│   │   ├── routes/
│   │   │   ├── auth.py             # JWT authentication endpoints
│   │   │   └── teachers.py         # OCR processing, grading & student management APIs
│   │   ├── models/                 # SQLAlchemy ORM models (Student, Teacher)
│   │   ├── schemas/                # Pydantic validation schemas
│   │   └── security/               # Password hashing & JWT token management
├── frontend/                       # Web Client (Vanilla HTML5 / CSS3 / ES6)
│   ├── index.html                  # Unified Teacher & Student Login page
│   ├── teacher-dashboard.html      # Teacher evaluation dashboard & Q&A viewer
│   ├── student-dashboard.html      # Student evaluation dashboard
│   ├── register-teacher.html       # Teacher registration page
│   ├── register-student.html       # Student registration page
│   ├── css/
│   │   ├── dashboard.css           # 2-column SaaS dashboard design & Q&A cards
│   │   ├── login.css               # Modern split-pane login styling
│   │   └── global.css              # Typography, color tokens & resets
│   └── js/
│       └── login.js                # Auth handling & redirection logic
├── ocr_core/                       # Core Offline AI & Image Processing Engine
│   ├── config.py                   # Device (CUDA/CPU), model paths & OCR settings
│   ├── model.py                    # TrOCR singleton loader
│   ├── recognizer.py               # Line-by-line handwritten text recognition
│   ├── line_detector.py            # Text line segmentation from images
│   ├── preprocessing.py            # Deskew, denoise, CLAHE, binarization
│   ├── qa_extractor.py             # Regex-based Question/Answer extraction
│   ├── grader.py                   # Fuzzy keyword matching and grading logic
│   └── db.py                       # MySQL database helper routines
├── models/
│   └── trocr-large-handwritten/    # Offline HuggingFace TrOCR model weights
├── run.bat                         # 1-Click launcher script (starts MySQL & server)
├── start_server.bat                # Direct server starter script
├── setup.bat                       # One-time environment setup script
└── run.md                          # This documentation file
```

---

## 7. Troubleshooting & FAQ

### Q: "Port 8000 is already in use"
Another instance of the server is running in the background. Free the port using PowerShell:
```powershell
$proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($proc) { Stop-Process -Id $proc -Force }
```

### Q: "Can't connect to MySQL server on localhost ([WinError 10061])"
MySQL is not running. Start XAMPP MySQL:
- Open XAMPP Control Panel and click **Start** next to MySQL.
- Or run in terminal: `Start-Process "D:\xampp\mysql_start.bat"`

### Q: OCR processing takes 1-2 minutes per document
- Dense, multi-page handwritten booklets contain 40-80 text lines per page.
- On **CPU**, each line takes ~1.5-2 seconds to evaluate with `trocr-large`.
- If an **NVIDIA GPU** is available, CUDA acceleration is activated automatically for 10x-20x speedup.
- Use `Preprocess: Light` and `Mode: Full Page` for optimal performance.

### Q: How to stop or restart the application cleanly?
Press `Ctrl + C` in the terminal window running uvicorn, or close the terminal, then double-click `run.bat` again.
