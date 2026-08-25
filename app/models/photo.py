from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AlbumCreate(BaseModel):
    event_id:    Optional[str] = None
    title:       str
    description: Optional[str] = None


class AlbumResponse(BaseModel):
    id:           str
    event_id:     Optional[str]  = None
    event_title:  Optional[str]  = None
    title:        str
    description:  Optional[str]  = None
    created_by:   str
    created_at:   Optional[datetime] = None
    photos_count: Optional[int]  = 0

    class Config:
        from_attributes = True


class PhotoResponse(BaseModel):
    id:              str
    album_id:        str
    mime_type:       str
    file_name:       str
    file_size_bytes: int
    caption:         Optional[str]  = None
    uploaded_by:     str
    created_at:      Optional[datetime] = None
    # base64 data — only returned by GET /photos/{id}
    data:            Optional[str]  = None

    class Config:
        from_attributes = True


class FAQCreate(BaseModel):
    question:      str
    answer:        str
    category:      str = "Général"
    published:     bool = False
    display_order: int  = 0


class FAQUpdate(BaseModel):
    question:      Optional[str]  = None
    answer:        Optional[str]  = None
    category:      Optional[str]  = None
    published:     Optional[bool] = None
    display_order: Optional[int]  = None


class FAQResponse(BaseModel):
    id:            str
    question:      str
    answer:        str
    category:      str
    published:     bool
    display_order: int
    created_at:    Optional[datetime] = None

    class Config:
        from_attributes = True
