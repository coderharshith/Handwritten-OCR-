import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.auth import TokenData

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token") # Common token URL, but we'll have separate for student/teacher so maybe just use a generic one or don't strict-tie it here.

def verify_password(plain_password, hashed_password):
    try:
        if pwd_context.verify(plain_password, hashed_password):
            return True
    except Exception:
        pass
    # Fallback to plain text comparison for legacy MySQL entries
    return plain_password == hashed_password

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    
    if token_data.role == "student":
        user = db.query(Student).filter(Student.username == token_data.username).first()
    elif token_data.role == "teacher":
        user = db.query(Teacher).filter(Teacher.username == token_data.username).first()
    else:
        raise credentials_exception
        
    if user is None:
        raise credentials_exception
    return {"user": user, "role": token_data.role}

def get_current_active_student(current_user: dict = Depends(get_current_user)):
    user = current_user.get("user")
    role = current_user.get("role")
    if role != "student" or not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive student or not a student")
    return user

def get_current_active_teacher(current_user: dict = Depends(get_current_user)):
    user = current_user.get("user")
    role = current_user.get("role")
    if role != "teacher" or not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive teacher or not a teacher")
    return user
