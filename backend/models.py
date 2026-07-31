"""Pydantic request/response models."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import uuid
import re


Role = Literal["admin", "consultant", "evaluator"]


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if "@" not in v or len(v) < 5:
            raise ValueError("عنوان بريد غير صالح")
        return v


class UserOut(BaseModel):
    id: str
    email: str
    name_ar: str
    role: Role
    person_id: Optional[str] = None
    must_change_password: bool = False


PASSWORD_STRENGTH_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def _validate_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("كلمة المرور يجب أن تحتوي 8 أحرف على الأقل")
    if not PASSWORD_STRENGTH_RE.match(v):
        raise ValueError("كلمة المرور يجب أن تحتوي حروفاً وأرقاماً")
    return v


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_strength(v)


class ForgotPasswordIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if "@" not in v:
            raise ValueError("عنوان بريد غير صالح")
        return v


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_strength(v)


class MappingDecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    note: Optional[str] = None


class RecordDecisionIn(BaseModel):
    evaluation: Literal["مقبول", "يحتاج لتطوير", "غير مكتمل"]
    work_hours: float = Field(ge=0)
    notes: Optional[str] = None


class DraftUpdateIn(BaseModel):
    model_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
