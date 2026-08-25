from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import List

from ..database import get_supabase, get_supabase_admin
from ..models.photo import FAQCreate, FAQUpdate, FAQResponse

router = APIRouter(prefix="/faqs", tags=["faqs"])

KEVIN_UUID = "1a2db0b5-faf9-4a40-b001-a1c0aaa8655c"


@router.get("/", response_model=List[FAQResponse])
async def list_faqs(supabase: Client = Depends(get_supabase)):
    result = (
        supabase.table("faqs")
        .select("*")
        .eq("published", True)
        .order("display_order", desc=False)
        .execute()
    )
    return result.data


@router.get("/all", response_model=List[FAQResponse])
async def list_all_faqs(supabase: Client = Depends(get_supabase_admin)):
    result = supabase.table("faqs").select("*").order("display_order").execute()
    return result.data


@router.post("/", response_model=FAQResponse, status_code=201)
async def create_faq(
    payload:  FAQCreate,
    supabase: Client = Depends(get_supabase_admin),
):
    result = supabase.table("faqs").insert({
        **payload.model_dump(),
        "created_by": KEVIN_UUID,
    }).execute()
    return result.data[0]


@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id:   str,
    payload:  FAQUpdate,
    supabase: Client = Depends(get_supabase_admin),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    result = supabase.table("faqs").update(updates).eq("id", faq_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="FAQ introuvable")
    return result.data[0]


@router.delete("/{faq_id}", status_code=204)
async def delete_faq(
    faq_id:   str,
    supabase: Client = Depends(get_supabase_admin),
):
    supabase.table("faqs").delete().eq("id", faq_id).execute()
