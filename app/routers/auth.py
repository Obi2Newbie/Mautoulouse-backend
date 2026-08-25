from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
import time

from ..database import get_supabase, get_supabase_admin
from ..dependencies import get_current_user
from ..models.user import (
    SignUpRequest, LoginRequest, AuthResponse,
    UserResponse, ProfileUpdate, UserRole,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(payload: SignUpRequest, supabase: Client = Depends(get_supabase)):
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
        msg = str(e).lower()
        if "already" in msg or "exists" in msg:
            raise HTTPException(status_code=400, detail="Un compte existe déjà avec cet email")
        if "password" in msg:
            raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")
        raise HTTPException(status_code=400, detail=f"Erreur inscription: {str(e)}")

    if not result.user:
        raise HTTPException(status_code=400, detail="Inscription échouée")

    user_id = result.user.id
    admin   = get_supabase_admin()

    try:
        admin.table("profiles").upsert({
            "id":          user_id,
            "first_name":  payload.first_name,
            "last_name":   payload.last_name,
            "origin_city": payload.origin_city,
            "role":        "user",
        }, on_conflict="id").execute()
    except Exception as e:
        print(f"[signup] profile upsert error: {e}")

    time.sleep(0.5)

    profile = admin.table("profiles").select("*").eq("id", user_id).single().execute()

    if not profile.data:
        fake = UserResponse(
            id=user_id, email=payload.email,
            first_name=payload.first_name, last_name=payload.last_name,
            role=UserRole.user, origin_city=payload.origin_city,
        )
        return AuthResponse(
            access_token=result.session.access_token if result.session else "token",
            user=fake,
        )

    p = profile.data
    p["email"] = payload.email   # inject email — not stored in profiles table

    return AuthResponse(
        access_token=result.session.access_token if result.session else "token",
        user=UserResponse(**p),
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

    admin = get_supabase_admin()
    profile = admin.table("profiles").select("*").eq("id", result.user.id).single().execute()

    if not profile.data:
        meta = result.user.user_metadata or {}
        admin.table("profiles").upsert({
            "id":         result.user.id,
            "first_name": meta.get("first_name", "Nouveau"),
            "last_name":  meta.get("last_name",  "Membre"),
            "role":       "user",
        }, on_conflict="id").execute()
        profile = admin.table("profiles").select("*").eq("id", result.user.id).single().execute()

    p = profile.data
    p["email"] = result.user.email   # inject email — not stored in profiles table

    return AuthResponse(
        access_token=result.session.access_token,
        user=UserResponse(**p),
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

    result = supabase.table("profiles").update(updates).eq("id", current_user.id).execute()
    print(f"[update_me] result={result.data}")

    if not result.data:
        fetched = supabase.table("profiles").select("*").eq("id", current_user.id).single().execute()
        p = fetched.data
        if p:
            p["email"] = current_user.email
            return UserResponse(**p)
        return current_user

    p = result.data[0]
    p["email"] = current_user.email   # preserve email in response
    return UserResponse(**p)


@router.delete("/me", status_code=204)
async def delete_me(current_user: UserResponse = Depends(get_current_user)):
    try:
        admin = get_supabase_admin()
        admin.auth.admin.delete_user(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/forgot-password", status_code=200)
async def forgot_password(
    payload: dict,
    supabase: Client = Depends(get_supabase),
):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email requis")
    try:
        supabase.auth.reset_password_email(
            email,
            options={"redirect_to": "https://mautoulouse-d8h7.vercel.app/reset-password"}
        )
    except Exception as e:
        print(f"[forgot-password] {e}")
    # Always return success — don't reveal if email exists
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    payload: dict,
    supabase: Client = Depends(get_supabase),
):
    access_token = payload.get("access_token")
    new_password = payload.get("password")
    if not access_token or not new_password:
        raise HTTPException(status_code=400, detail="Token et mot de passe requis")
    try:
        supabase.auth.set_session(access_token, "")
        supabase.auth.update_user({"password": new_password})
        return {"message": "Mot de passe mis à jour avec succès"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur: {str(e)}")