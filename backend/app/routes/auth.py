from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import Token
from app.schemas.student import StudentCreate, Student
from app.schemas.teacher import TeacherCreate, Teacher
from app.services import auth_service
from app.security.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token

router = APIRouter()

@router.post("/student/register", response_model=Student, status_code=status.HTTP_201_CREATED)
def register_student(student: StudentCreate, db: Session = Depends(get_db)):
    """
    Register a new student.
    """
    return auth_service.create_student(db, student)

@router.post("/teacher/register", response_model=Teacher, status_code=status.HTTP_201_CREATED)
def register_teacher(teacher: TeacherCreate, db: Session = Depends(get_db)):
    """
    Register a new teacher.
    """
    return auth_service.create_teacher(db, teacher)

@router.post("/student/login", response_model=Token)
def login_student(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login as a student and get an access token.
    """
    student = auth_service.authenticate_student(db, form_data.username, form_data.password)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": student.username, "role": "student"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/teacher/login", response_model=Token)
def login_teacher(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login as a teacher and get an access token.
    """
    teacher = auth_service.authenticate_teacher(db, form_data.username, form_data.password)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": teacher.username, "role": "teacher"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
