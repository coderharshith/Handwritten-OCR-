import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routes import auth, teachers, students

# Create all tables in the database (silently skip if DB is unavailable)
try:
    Base.metadata.create_all(bind=engine)
except Exception as _db_err:
    print(f"[WARN] Could not create DB tables at startup: {_db_err}")
    print("[WARN] Server will start anyway. DB features may be unavailable.")

app = FastAPI(title="Booklet Evaluation System", version="1.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(teachers.router, prefix="/api/teachers", tags=["Teachers"])
app.include_router(students.router, prefix="/api/students", tags=["Students"])

# Determine frontend path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

from fastapi.responses import RedirectResponse

# Mount frontend folder to / if it exists
if os.path.isdir(FRONTEND_DIR):
    @app.get("/ocr-dashboard/")
    def redirect_old_dashboard_slash():
        return RedirectResponse(url="/teacher-dashboard.html")
        
    @app.get("/ocr-dashboard")
    def redirect_old_dashboard():
        return RedirectResponse(url="/teacher-dashboard.html")

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to Booklet Evaluation System API. Frontend not found."}
