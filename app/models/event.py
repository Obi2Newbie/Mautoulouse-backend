from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, time, datetime
from enum import Enum


class EventStatus(str, Enum):
    draft     = "draft"
    published = "published"
    past      = "past"


class AttendeeStatus(str, Enum):
    going      = "going"
    interested = "interested"


# ── Request schemas ──────────────────────────────────────────
class EventCreate(BaseModel):
    title:       str
    description: str
    date:        date
    time:        time
    location:    str
    price_cents: int            = 0   # 0 = free
    capacity:    int
    category:    str
    tags:        List[str]      = []
    youtube_url: Optional[str]  = None
    status:      EventStatus    = EventStatus.draft

    @field_validator("price_cents")
    @classmethod
    def price_positive(cls, v):
        if v < 0:
            raise ValueError("Le prix ne peut pas être négatif")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v):
        if v <= 0:
            raise ValueError("La capacité doit être supérieure à 0")
        return v


class EventUpdate(BaseModel):
    title:       Optional[str]        = None
    description: Optional[str]        = None
    date:        Optional[date]       = None
    time:        Optional[time]       = None
    location:    Optional[str]        = None
    price_cents: Optional[int]        = None
    capacity:    Optional[int]        = None
    category:    Optional[str]        = None
    tags:        Optional[List[str]]  = None
    youtube_url: Optional[str]        = None
    status:      Optional[EventStatus]= None


class AttendEvent(BaseModel):
    status: AttendeeStatus = AttendeeStatus.going


# ── Response schemas ─────────────────────────────────────────
class EventResponse(BaseModel):
    id:               str
    title:            str
    description:      str
    date:             date
    time:             time
    location:         str
    price_cents:      int
    capacity:         int
    category:         str
    status:           EventStatus
    youtube_url:      Optional[str]  = None
    created_by:       str
    created_at:       Optional[datetime] = None
    # From events_summary view:
    going_count:      Optional[int]  = 0
    interested_count: Optional[int]  = 0
    tags:             Optional[List[str]] = []

    class Config:
        from_attributes = True


class AttendeeResponse(BaseModel):
    event_id:   str
    user_id:    str
    status:     AttendeeStatus
    created_at: Optional[datetime] = None
