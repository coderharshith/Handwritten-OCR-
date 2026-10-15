from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class TeacherBase(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    profile_image: Optional[str] = None

class TeacherCreate(TeacherBase):
    password: str

class TeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = None
    password: Optional[str] = None

class TeacherInDBBase(TeacherBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class Teacher(TeacherInDBBase):
    pass
