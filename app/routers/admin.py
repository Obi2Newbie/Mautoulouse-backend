from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import List

from ..database import get_supabase, get_supabase_admin
from ..models.user import UserResponse, RoleUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


# ── ANALYTICS ─────────────────────────────────────────────────
@router.get("/analytics")
async def get_analytics(
    supabase: Client = Depends(get_supabase_admin),
):
    result = supabase.rpc("get_analytics").execute()
    return result.data


# ── USERS ─────────────────────────────────────────────────────
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    supabase: Client = Depends(get_supabase_admin),
):
    """Return all registered profiles."""
    result = supabase.table("profiles").select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id:      str,
    supabase: Client = Depends(get_supabase_admin),
):
    result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return result.data


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id:      str,
    payload:      RoleUpdate,
    supabase: Client = Depends(get_supabase_admin),
):
    """Change a user's role (user / moderator / admin)."""
    result = (
        supabase.table("profiles")
        .update({"role": payload.role})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return result.data[0]


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id:      str,
    supabase: Client = Depends(get_supabase_admin),
):
    """
    Permanently delete a user.
    Deletes from auth.users which cascades to profiles.
    """
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
