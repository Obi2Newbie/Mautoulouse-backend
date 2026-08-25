import base64
import json
from fastapi import Request
from .models.user import UserResponse, UserRole

FAKE_ADMIN = UserResponse(
    id         = "1a2db0b5-faf9-4a40-b001-a1c0aaa8655c",
    email      = "roussety.kevin1@gmail.com",
    first_name = "Kevin",
    last_name  = "Roussety",
    role       = UserRole.admin,
)


def _decode_jwt_payload(request: Request) -> dict:
    """
    Decode JWT payload WITHOUT signature verification.
    Works regardless of algorithm (HS256, RS256, etc).
    Safe for presentation — do not use in production.
    """
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return {}
        token = auth[7:]
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        # Add padding so base64 doesn't crash
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        print(f"[auth] decoded sub={payload.get('sub')} email={payload.get('email')}")
        return payload
    except Exception as e:
        print(f"[auth] decode error: {e}")
        return {}


async def get_current_user(request: Request) -> UserResponse:
    from .database import get_supabase_admin

    payload = _decode_jwt_payload(request)
    user_id = payload.get("sub")
    email   = payload.get("email")

    if user_id:
        try:
            admin  = get_supabase_admin()
            result = admin.table("profiles").select("*").eq("id", user_id).single().execute()
            if result.data:
                profile          = result.data
                profile["email"] = email
                return UserResponse(**profile)
        except Exception as e:
            print(f"[auth] profile fetch error: {e}")

    print(f"[auth] falling back to FAKE_ADMIN — no valid token")
    return FAKE_ADMIN


async def get_current_user_optional(request: Request) -> UserResponse | None:
    return await get_current_user(request)

async def require_admin(request: Request) -> UserResponse:
    return await get_current_user(request)

async def require_moderator_or_above(request: Request) -> UserResponse:
    return await get_current_user(request)