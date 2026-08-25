from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# ── Request schemas ──────────────────────────────────────────
class QuestionCreate(BaseModel):
    title: str
    body:  str
    tags:  List[str] = []

    @field_validator("title")
    @classmethod
    def title_length(cls, v):
        if len(v) < 10:
            raise ValueError("Le titre doit contenir au moins 10 caractères")
        return v

    @field_validator("body")
    @classmethod
    def body_length(cls, v):
        if len(v) < 20:
            raise ValueError("La description doit contenir au moins 20 caractères")
        return v


class QuestionUpdate(BaseModel):
    title: Optional[str]      = None
    body:  Optional[str]      = None
    tags:  Optional[List[str]]= None


class VoteRequest(BaseModel):
    value: int  # 1 or -1

    @field_validator("value")
    @classmethod
    def valid_vote(cls, v):
        if v not in (1, -1):
            raise ValueError("La valeur du vote doit être 1 ou -1")
        return v


# ── Response schemas ─────────────────────────────────────────
class AuthorMini(BaseModel):
    id:         str
    first_name: str
    last_name:  str


class QuestionResponse(BaseModel):
    id:            str
    title:         str
    body:          str
    author_id:     str
    views:         int              = 0
    created_at:    Optional[datetime] = None
    updated_at:    Optional[datetime] = None
    # From questions_summary view:
    first_name:    Optional[str]    = None
    last_name:     Optional[str]    = None
    vote_score:    Optional[int]    = 0
    answers_count: Optional[int]    = 0
    tags:          Optional[List[str]] = []

    class Config:
        from_attributes = True
