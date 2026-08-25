from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from ..database import get_supabase, get_supabase_admin
from ..dependencies import get_current_user
from ..models.user import (
    SignUpRequest, LoginRequest, AuthResponse,
    UserResponse, ProfileUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(payload: SignUpRequest, supabase: Client = Depends(get_supabase)):
    # 1 — Create user in Supabase Auth
    try:
        result = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
            "options": {
                "data": {
                    "first_name": payload.first_name,
                    "last_name":  payload.last_name,
                }
            },
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result.user:
        raise HTTPException(status_code=400, detail="Inscription échouée")

    user_id = result.user.id

    # 2 — Upsert profile manually (don't rely on trigger alone)
    #     The trigger may have already created it — ON CONFLICT DO NOTHING handles that.
    admin_client = get_supabase_admin()
    admin_client.table("profiles").upsert({
        "id":          user_id,
        "first_name":  payload.first_name,
        "last_name":   payload.last_name,
        "origin_city": payload.origin_city,
        "role":        "user",
    }, on_conflict="id").execute()

    # 3 — Fetch the profile (now guaranteed to exist)
    profile = (
        admin_client.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if not profile.data:
        raise HTTPException(status_code=500, detail="Profil introuvable après création")

    return AuthResponse(
        access_token=result.session.access_token,
        user=UserResponse(**profile.data),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, supabase: Client = Depends(get_supabase)):
    try:
        result = supabase.auth.sign_in_with_password({
            "email":    payload.email,
            "password": payload.password,
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not result.user or not result.session:
        raise HTTPException(status_code=401, detail="Authentification échouée")

    # Use admin client so RLS doesn't block profile fetch
    admin_client = get_supabase_admin()
    profile = (
        admin_client.table("profiles")
        .select("*")
        .eq("id", result.user.id)
        .single()
        .execute()
    )

    # Profile might be missing if trigger failed — create it now
    if not profile.data:
        meta = result.user.user_metadata or {}
        admin_client.table("profiles").upsert({
            "id":         result.user.id,
            "first_name": meta.get("first_name", "Nouveau"),
            "last_name":  meta.get("last_name",  "Membre"),
            "role":       "user",
        }, on_conflict="id").execute()
        profile = (
            admin_client.table("profiles")
            .select("*")
            .eq("id", result.user.id)
            .single()
            .execute()
        )

    return AuthResponse(
        access_token=result.session.access_token,
        user=UserResponse(**profile.data),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload:      ProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
    supabase:     Client       = Depends(get_supabase_admin),
):
    updates = payload.model_dump(exclude_none=True)
    print(f"[update_me] user_id={current_user.id}, updates={updates}")

    if not updates:
        return current_user

    # Update the profile
    supabase.table("profiles").update(updates).eq("id", current_user.id).execute()

    # Always fetch fresh — don't rely on update() returning data
    fetched = supabase.table("profiles").select("*").eq("id", current_user.id).single().execute()

    if not fetched.data:
        return current_user

    p = fetched.data
    p["email"] = current_user.email
    return UserResponse(**p)


@router.delete("/me", status_code=204)
async def delete_me(
    current_user: UserResponse = Depends(get_current_user),
    supabase:     Client       = Depends(get_supabase),
):
    try:
        admin_client = get_supabase_admin()
        admin_client.auth.admin.delete_user(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))