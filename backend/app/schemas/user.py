from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
import re


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove caracteres não numéricos exceto +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Se não tem +, assume Brasil e adiciona +55
        if not cleaned.startswith('+'):
            # Remove zero inicial do DDD se existir
            if cleaned.startswith('0'):
                cleaned = cleaned[1:]
            cleaned = f'+55{cleaned}'
        
        # Valida formato internacional
        phone_pattern = re.compile(r'^\+[1-9]\d{10,14}$')
        if not phone_pattern.match(cleaned):
            raise ValueError('Invalid phone number format. Use format: (XX) XXXXX-XXXX or +55XXXXXXXXXXX')
        
        return cleaned


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
