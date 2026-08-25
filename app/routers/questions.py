from fastapi import APIRouter, Depends, HTTPException, Query, Request
from supabase import Client
from typing import List, Optional

from ..database import get_supabase, get_supabase_admin
from ..models.question import (
    QuestionCreate, QuestionUpdate, QuestionResponse, VoteRequest,
)

router = APIRouter(prefix="/questions", tags=["questions"])


# ── LIST ──────────────────────────────────────────────────────
@router.get("/", response_model=List[QuestionResponse])
async def list_questions(
    tag:    Optional[str] = None,
    search: Optional[str] = None,
    limit:  int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    supabase: Client = Depends(get_supabase_admin),
):
    if search:
        result = supabase.rpc("search_questions", {"search_term": search}).execute()
        return result.data

    query = supabase.table("questions_summary").select("*")
    if tag:
        query = query.contains("tags", [tag])

    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


# ── GET ONE ───────────────────────────────────────────────────
@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str, supabase: Client = Depends(get_supabase_admin)):
    supabase.rpc("increment_question_views", {"question_id": question_id}).execute()
    result = (
        supabase.table("questions_summary")
        .select("*").eq("id", question_id).single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return result.data


# ── CREATE ────────────────────────────────────────────────────
@router.post("/", response_model=QuestionResponse, status_code=201)
async def create_question(
    payload:  QuestionCreate,
    request:  Request,
    supabase: Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    result = supabase.table("questions").insert({
        "title":     payload.title,
        "body":      payload.body,
        "author_id": current_user.id,
    }).execute()

    question_id = result.data[0]["id"]

    if payload.tags:
        supabase.table("question_tags").insert(
            [{"question_id": question_id, "tag": t} for t in payload.tags]
        ).execute()

    view = (
        supabase.table("questions_summary")
        .select("*").eq("id", question_id).single().execute()
    )
    return view.data


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    payload:     QuestionUpdate,
    request:     Request,
    supabase:    Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    existing = (
        supabase.table("questions")
        .select("author_id").eq("id", question_id).single().execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Question introuvable")

    updates = payload.model_dump(exclude_none=True, exclude={"tags"})
    if updates:
        supabase.table("questions").update(updates).eq("id", question_id).execute()

    if payload.tags is not None:
        supabase.table("question_tags").delete().eq("question_id", question_id).execute()
        if payload.tags:
            supabase.table("question_tags").insert(
                [{"question_id": question_id, "tag": t} for t in payload.tags]
            ).execute()

    view = (
        supabase.table("questions_summary")
        .select("*").eq("id", question_id).single().execute()
    )
    return view.data


# ── DELETE ────────────────────────────────────────────────────
@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: str,
    request:     Request,
    supabase:    Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    supabase.table("questions").delete().eq("id", question_id).execute()


# ── VOTE ──────────────────────────────────────────────────────
@router.post("/{question_id}/vote")
async def vote_question(
    question_id: str,
    payload:     VoteRequest,
    request:     Request,
    supabase:    Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)
    user_id = current_user.id

    # Check existing vote
    existing = (
        supabase.table("question_votes")
        .select("id, value")
        .eq("question_id", question_id)
        .eq("user_id", user_id)
        .execute()
    )

    if existing.data:
        row = existing.data[0]
        if row["value"] == payload.value:
            # Same vote — remove (toggle off)
            supabase.table("question_votes").delete().eq("id", row["id"]).execute()
        else:
            # Different vote — flip
            supabase.table("question_votes").update({"value": payload.value}).eq("id", row["id"]).execute()
    else:
        # New vote
        supabase.table("question_votes").insert({
            "question_id": question_id,
            "user_id":     user_id,
            "value":       payload.value,
        }).execute()

    # Return new score
    all_votes = supabase.table("question_votes").select("value").eq("question_id", question_id).execute()
    score = sum(r["value"] for r in all_votes.data)
    return {"vote_score": score}