"""Pydantic request/response models."""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import uuid


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


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class MappingDecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    note: Optional[str] = None


class RecordDecisionIn(BaseModel):
    """Evaluator decision on a current record."""
    evaluation: Literal["مقبول", "يحتاج لتطوير", "غير مكتمل"]
    work_hours: float = Field(ge=0)
    notes: Optional[str] = None


class DraftUpdateIn(BaseModel):
    """Consultant draft edit — only mutable fields."""
    model_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
