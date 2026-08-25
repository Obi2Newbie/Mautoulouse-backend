from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class AnswerCreate(BaseModel):
    question_id: str
    body:        str
    parent_id:   Optional[str] = None   # None = top-level, set = reply

    @field_validator("body")
    @classmethod
    def body_length(cls, v):
        if len(v) < 10:
            raise ValueError("La réponse doit contenir au moins 10 caractères")
        return v


class AnswerUpdate(BaseModel):
    body: str


class AnswerResponse(BaseModel):
    id:          str
    question_id: str
    parent_id:   Optional[str]   = None
    body:        str
    author_id:   str
    is_accepted: bool             = False
    created_at:  Optional[datetime] = None
    updated_at:  Optional[datetime] = None
    # From answers_summary view:
    first_name:  Optional[str]   = None
    last_name:   Optional[str]   = None
    vote_score:  Optional[int]   = 0
    # Replies (nested)
    replies:     Optional[List["AnswerResponse"]] = []

    class Config:
        from_attributes = True


AnswerResponse.model_rebuild()
