from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    user      = "user"
    moderator = "moderator"
    admin     = "admin"


# ── Request schemas ──────────────────────────────────────────
class SignUpRequest(BaseModel):
    email:       EmailStr
    password:    str
    first_name:  str
    last_name:   str
    origin_city: Optional[str] = None


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class ProfileUpdate(BaseModel):
    first_name:  Optional[str] = None
    last_name:   Optional[str] = None
    origin_city: Optional[str] = None
    bio:         Optional[str] = None


class RoleUpdate(BaseModel):
    role: UserRole


# ── Response schemas ─────────────────────────────────────────
class UserResponse(BaseModel):
    id:          str
    email:       Optional[str]  = None
    first_name:  str
    last_name:   str
    origin_city: Optional[str]  = None
    bio:         Optional[str]  = None
    role:        UserRole       = UserRole.user
    created_at:  Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token:  str
    token_type:    str = "bearer"
    user:          UserResponse
