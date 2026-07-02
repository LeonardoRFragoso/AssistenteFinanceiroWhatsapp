from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from app.models.message_template import MessageTone


ALLOWED_PLACEHOLDERS = {
    "{customer_name}",
    "{amount}",
    "{description}",
    "{due_date}",
    "{payment_link}",
    "{qr_code_note}",
    "{company_name}",
}

MAX_TEMPLATE_LENGTH = 2000

AGGRESSIVE_WORDS = [
    "idiota", "imbecil", "caloteiro", "ladrão", "ladrao", "vagabundo",
    "miserável", "miseravel", "desgraçado", "desgracado", "lixo",
]


class MessageTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tone: MessageTone = MessageTone.NEUTRAL
    template_text: str = Field(..., min_length=1, max_length=MAX_TEMPLATE_LENGTH)

    @field_validator("template_text")
    @classmethod
    def validate_template_text(cls, v: str) -> str:
        text_lower = v.lower()
        for word in AGGRESSIVE_WORDS:
            if word in text_lower:
                raise ValueError(f"Template contains inappropriate language. Aggressive/abusive words are not allowed.")
        return v


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tone: Optional[MessageTone] = None
    template_text: Optional[str] = Field(None, min_length=1, max_length=MAX_TEMPLATE_LENGTH)

    @field_validator("template_text")
    @classmethod
    def validate_template_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        text_lower = v.lower()
        for word in AGGRESSIVE_WORDS:
            if word in text_lower:
                raise ValueError(f"Template contains inappropriate language. Aggressive/abusive words are not allowed.")
        return v


class MessageTemplateResponse(BaseModel):
    id: int
    user_id: int
    name: str
    tone: MessageTone
    template_text: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageTemplateListResponse(BaseModel):
    items: List[MessageTemplateResponse]
    total: int


class MessageTemplatePreviewRequest(BaseModel):
    customer_name: str = "João"
    amount: str = "150.00"
    description: str = "serviço"
    due_date: str = "2026-07-15"
    payment_link: str = "https://example.com/pay/abc"
    qr_code_note: str = "Sandbox/Demo — não representa Pix real"
    company_name: str = "PayFlow AI"


class MessageTemplatePreviewResponse(BaseModel):
    rendered_text: str
    template_id: int
    template_name: str
