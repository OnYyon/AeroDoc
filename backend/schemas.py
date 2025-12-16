from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from models import UserRole


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole
    
    class Config:
        use_enum_values = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True


# Chat schemas
class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatResponse(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Message schemas
class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    content: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Document schemas
class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    uploaded_at: datetime
    file_type: str
    
    class Config:
        from_attributes = True

