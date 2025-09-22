from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="Username (3-30 characters, letters, numbers, underscore only)")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, and underscores')
        if v.startswith('_') or v.endswith('_'):
            raise ValueError('Username cannot start or end with underscore')
        return v

class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address for password reset")

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ValidationErrorResponse(BaseModel):
    valid: bool
    errors: list[str]

class MessageResponse(BaseModel):
    message: str