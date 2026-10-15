from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class StudentBase(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    profile_image: Optional[str] = None

class StudentCreate(StudentBase):
    password: str

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = None
    password: Optional[str] = None

class StudentInDBBase(StudentBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class Student(StudentInDBBase):
    pass
