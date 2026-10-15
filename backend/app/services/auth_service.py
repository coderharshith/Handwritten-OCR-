from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.student import StudentCreate
from app.schemas.teacher import TeacherCreate
from app.security.auth import get_password_hash, verify_password

def create_student(db: Session, student: StudentCreate):
    if db.query(Student).filter(Student.username == student.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    if db.query(Student).filter(Student.email == student.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    hashed_password = get_password_hash(student.password)
    db_student = Student(
        full_name=student.full_name,
        username=student.username,
        email=student.email,
        password_hash=hashed_password,
        profile_image=student.profile_image
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

def create_teacher(db: Session, teacher: TeacherCreate):
    if db.query(Teacher).filter(Teacher.username == teacher.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    if db.query(Teacher).filter(Teacher.email == teacher.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    hashed_password = get_password_hash(teacher.password)
    db_teacher = Teacher(
        full_name=teacher.full_name,
        username=teacher.username,
        email=teacher.email,
        password_hash=hashed_password,
        profile_image=teacher.profile_image
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher

def authenticate_student(db: Session, username: str, password: str):
    student = db.query(Student).filter(Student.username == username).first()
    if not student:
        return None
    if not verify_password(password, student.password_hash):
        return None
    return student

def authenticate_teacher(db: Session, username: str, password: str):
    teacher = db.query(Teacher).filter(Teacher.username == username).first()
    if not teacher:
        return None
    if not verify_password(password, teacher.password_hash):
        return None
    return teacher
