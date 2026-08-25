from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from supabase import Client
from typing import List, Optional
import base64
import binascii

from ..database import get_supabase, get_supabase_admin
from ..models.photo import AlbumCreate, AlbumResponse, PhotoResponse

router = APIRouter(prefix="/albums", tags=["photos"])

KEVIN_UUID    = "1a2db0b5-faf9-4a40-b001-a1c0aaa8655c"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE      = 10 * 1024 * 1024  # 10 MB


def to_base64(raw) -> Optional[str]:
    """
    Convert BYTEA from PostgREST to clean base64.
    PostgREST can return BYTEA as:
      - hex string  : '\\x89504e47...'
      - list of ints: [137, 80, 78, 71, ...]
      - bytes       : b'\\x89PNG...'
    """
    if raw is None:
        return None

    # ── DEBUG — remove after confirming it works ──
    print(f"[photo] raw type={type(raw).__name__}, preview={repr(raw)[:80]}")

    try:
        if isinstance(raw, str):
            s = raw.strip()
            # PostgreSQL hex escape: \x89504e47...
            if s.startswith("\\x"):
                raw_bytes = bytes.fromhex(s[2:])
            # Plain hex without prefix
            elif all(c in "0123456789abcdefABCDEF" for c in s):
                raw_bytes = bytes.fromhex(s)
            else:
                # Already base64 (e.g. from the RPC function)
                raw_bytes = base64.b64decode(s + "==")
        elif isinstance(raw, list):
            raw_bytes = bytes(raw)
        elif isinstance(raw, (bytes, bytearray)):
            raw_bytes = bytes(raw)
        else:
            print(f"[photo] unexpected type: {type(raw)}")
            return None

        return base64.b64encode(raw_bytes).decode("ascii")

    except Exception as e:
        print(f"[photo] to_base64 error: {e}")
        return None


# ══ ALBUMS ═══════════════════════════════════════════════════

@router.get("/", response_model=List[AlbumResponse])
async def list_albums(supabase: Client = Depends(get_supabase_admin)):
    result = supabase.table("albums_summary").select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str, supabase: Client = Depends(get_supabase_admin)):
    result = (
        supabase.table("albums_summary").select("*")
        .eq("id", album_id).single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Album introuvable")
    return result.data


@router.post("/", response_model=AlbumResponse, status_code=201)
async def create_album(payload: AlbumCreate, supabase: Client = Depends(get_supabase_admin)):
    result = supabase.table("photo_albums").insert({
        "event_id":    payload.event_id,
        "title":       payload.title,
        "description": payload.description,
        "created_by":  KEVIN_UUID,
    }).execute()
    album_id = result.data[0]["id"]
    view = supabase.table("albums_summary").select("*").eq("id", album_id).single().execute()
    return view.data


@router.delete("/{album_id}", status_code=204)
async def delete_album(album_id: str, supabase: Client = Depends(get_supabase_admin)):
    supabase.table("photo_albums").delete().eq("id", album_id).execute()


# ══ PHOTOS ═══════════════════════════════════════════════════

@router.get("/{album_id}/photos", response_model=List[PhotoResponse])
async def list_photos(album_id: str, supabase: Client = Depends(get_supabase_admin)):
    result = (
        supabase.table("photos")
        .select("id, album_id, mime_type, file_name, file_size_bytes, caption, uploaded_by, created_at")
        .eq("album_id", album_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data


@router.get("/{album_id}/photos/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    album_id: str,
    photo_id: str,
    supabase: Client = Depends(get_supabase_admin),
):
    result = (
        supabase.table("photos")
        .select("id, album_id, mime_type, file_name, file_size_bytes, caption, uploaded_by, created_at, data")
        .eq("id", photo_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Photo introuvable")

    raw = result.data.pop("data", None)
    b64 = to_base64(raw)

    return PhotoResponse(**result.data, data=b64)


@router.post("/{album_id}/photos", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    album_id: str,
    file:     UploadFile = File(...),
    caption:  Optional[str] = Form(default=None),
    supabase: Client = Depends(get_supabase_admin),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Type non supporté. Acceptés : {', '.join(ALLOWED_TYPES)}")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Fichier trop lourd (max 10 MB)")

    album = supabase.table("photo_albums").select("id").eq("id", album_id).single().execute()
    if not album.data:
        raise HTTPException(status_code=404, detail="Album introuvable")

    # Store as hex string — most reliable BYTEA format for PostgREST
    hex_data = "\\x" + binascii.hexlify(contents).decode("ascii")

    result = supabase.table("photos").insert({
        "album_id":        album_id,
        "data":            hex_data,
        "mime_type":       file.content_type,
        "file_name":       file.filename,
        "file_size_bytes": len(contents),
        "caption":         caption,
        "uploaded_by":     KEVIN_UUID,
    }).execute()

    photo = result.data[0]
    photo.pop("data", None)
    return PhotoResponse(**photo)


@router.delete("/{album_id}/photos/{photo_id}", status_code=204)
async def delete_photo(
    album_id: str,
    photo_id: str,
    supabase: Client = Depends(get_supabase_admin),
):
    supabase.table("photos").delete().eq("id", photo_id).eq("album_id", album_id).execute()
