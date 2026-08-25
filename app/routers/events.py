from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from supabase import Client
from typing import List, Optional
import base64
import binascii

from ..database import get_supabase, get_supabase_admin
from ..models.event import (
    EventCreate, EventResponse,
    AttendEvent, AttendeeResponse,
)

router = APIRouter(prefix="/events", tags=["events"])

KEVIN_UUID     = "1a2db0b5-faf9-4a40-b001-a1c0aaa8655c"
ALLOWED_TYPES  = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


# ── LIST ──────────────────────────────────────────────────────
@router.get("/", response_model=List[EventResponse])
async def list_events(
    status_filter: Optional[str] = "published",
    category:      Optional[str] = None,
    supabase: Client = Depends(get_supabase),
):
    query = supabase.table("events_summary").select("*")
    if status_filter:
        query = query.eq("status", status_filter)
    if category:
        query = query.eq("category", category)
    result = query.order("date", desc=True).execute()
    return result.data


# ── MY EVENTS ─────────────────────────────────────────────────
@router.get("/my-events")
async def my_events(
    request:  Request,
    supabase: Client = Depends(get_supabase_admin),
):
    """Return only the events the current user is attending."""
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    att = (
        supabase.table("event_attendees")
        .select("event_id")
        .eq("user_id", current_user.id)
        .execute()
    )
    event_ids = [r["event_id"] for r in att.data]
    if not event_ids:
        return []

    result = (
        supabase.table("events_summary")
        .select("*")
        .in_("id", event_ids)
        .order("date", desc=True)
        .execute()
    )
    return result.data


# ── GET ONE ───────────────────────────────────────────────────
@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, supabase: Client = Depends(get_supabase)):
    result = (
        supabase.table("events_summary")
        .select("*").eq("id", event_id).single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return result.data


# ── CREATE ────────────────────────────────────────────────────
@router.post("/", response_model=EventResponse, status_code=201)
async def create_event(
    payload:  EventCreate,
    supabase: Client = Depends(get_supabase_admin),
):
    data = payload.model_dump(exclude={"tags"})
    data["created_by"] = KEVIN_UUID
    data["date"]       = str(data["date"])
    data["time"]       = str(data["time"])

    result   = supabase.table("events").insert(data).execute()
    event_id = result.data[0]["id"]

    if payload.tags:
        supabase.table("event_tags").insert(
            [{"event_id": event_id, "tag": t} for t in payload.tags]
        ).execute()

    view = supabase.table("events_summary").select("*").eq("id", event_id).single().execute()
    return view.data


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    request:  Request,
    supabase: Client = Depends(get_supabase_admin),
):
    body = await request.json()
    tags = body.pop("tags", None)

    allowed = {"title","description","date","time","location","price_cents","capacity","category","status","youtube_url"}
    updates = {}
    for k, v in body.items():
        if k not in allowed or v is None:
            continue
        if k == "time" and isinstance(v, str):
            v = v if len(v) == 8 else f"{v}:00"
        if k == "youtube_url" and v == "":
            continue
        updates[k] = v

    if updates:
        supabase.table("events").update(updates).eq("id", event_id).execute()

    if tags is not None:
        supabase.table("event_tags").delete().eq("event_id", event_id).execute()
        if tags:
            supabase.table("event_tags").insert(
                [{"event_id": event_id, "tag": t} for t in tags]
            ).execute()

    view = supabase.table("events_summary").select("*").eq("id", event_id).single().execute()
    if not view.data:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return view.data


# ── DELETE ────────────────────────────────────────────────────
@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str, supabase: Client = Depends(get_supabase_admin)):
    supabase.table("events").delete().eq("id", event_id).execute()


# ── UPLOAD COVER ──────────────────────────────────────────────
@router.post("/{event_id}/cover", status_code=200)
async def upload_cover_image(
    event_id: str,
    file:     UploadFile = File(...),
    supabase: Client = Depends(get_supabase_admin),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Type non supporté (jpeg, png, webp)")
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 5 MB)")
    hex_data = "\\x" + binascii.hexlify(contents).decode("ascii")
    supabase.table("events").update({
        "cover_image_data":      hex_data,
        "cover_image_mime_type": file.content_type,
    }).eq("id", event_id).execute()
    return {"message": "Image de couverture mise à jour"}


# ── GET COVER ─────────────────────────────────────────────────
@router.get("/{event_id}/cover")
async def get_cover_image(event_id: str, supabase: Client = Depends(get_supabase_admin)):
    result = (
        supabase.table("events")
        .select("cover_image_data, cover_image_mime_type")
        .eq("id", event_id).single().execute()
    )
    if not result.data or not result.data.get("cover_image_data"):
        raise HTTPException(status_code=404, detail="Pas d'image de couverture")
    raw = result.data["cover_image_data"]
    if isinstance(raw, str) and raw.startswith("\\x"):
        raw_bytes = bytes.fromhex(raw[2:])
    else:
        raw_bytes = bytes(raw)
    return {
        "data":      base64.b64encode(raw_bytes).decode(),
        "mime_type": result.data["cover_image_mime_type"],
    }


# ── ATTEND ────────────────────────────────────────────────────
@router.post("/{event_id}/attend", response_model=AttendeeResponse, status_code=201)
async def attend_event(
    event_id: str,
    payload:  AttendEvent,
    request:  Request,
    supabase: Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    event = supabase.table("events_summary").select("*").eq("id", event_id).single().execute()
    if not event.data:
        raise HTTPException(status_code=404, detail="Événement introuvable")

    ev = event.data
    if payload.status == "going" and ev.get("going_count", 0) >= ev["capacity"]:
        raise HTTPException(status_code=409, detail="L'événement est complet")

    result = supabase.table("event_attendees").upsert({
        "event_id": event_id,
        "user_id":  current_user.id,
        "status":   payload.status,
    }, on_conflict="event_id,user_id").execute()
    return result.data[0]


# ── CANCEL ATTENDANCE ─────────────────────────────────────────
@router.delete("/{event_id}/attend", status_code=204)
async def cancel_attendance(
    event_id: str,
    request:  Request,
    supabase: Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    supabase.table("event_attendees").delete().match({
        "event_id": event_id,
        "user_id":  current_user.id,
    }).execute()


# ── LIST ATTENDEES ────────────────────────────────────────────
@router.get("/{event_id}/attendees")
async def list_attendees(event_id: str, supabase: Client = Depends(get_supabase_admin)):
    result = (
        supabase.table("event_attendees")
        .select("*, profiles(id, first_name, last_name)")
        .eq("event_id", event_id).execute()
    )
    return result.data