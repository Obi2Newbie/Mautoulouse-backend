from fastapi import APIRouter, Depends, HTTPException, Request
from supabase import Client
from typing import List

from ..database import get_supabase_admin
from ..models.answer import AnswerCreate, AnswerUpdate, AnswerResponse
from ..models.question import VoteRequest

router = APIRouter(prefix="/answers", tags=["answers"])


def _build_thread(flat: list) -> List[AnswerResponse]:
    by_id     = {a["id"]: {**a, "replies": []} for a in flat}
    top_level = []
    for a in flat:
        if a.get("parent_id"):
            parent = by_id.get(a["parent_id"])
            if parent:
                parent["replies"].append(by_id[a["id"]])
        else:
            top_level.append(by_id[a["id"]])
    return [AnswerResponse(**a) for a in top_level]


# ── LIST ──────────────────────────────────────────────────────
@router.get("/question/{question_id}", response_model=List[AnswerResponse])
async def list_answers(question_id: str, supabase: Client = Depends(get_supabase_admin)):
    result = (
        supabase.table("answers_summary")
        .select("*")
        .eq("question_id", question_id)
        .order("created_at", desc=False)
        .execute()
    )
    return _build_thread(result.data)


# ── CREATE ────────────────────────────────────────────────────
@router.post("/", response_model=AnswerResponse, status_code=201)
async def create_answer(
    payload:  AnswerCreate,
    request:  Request,
    supabase: Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    question = supabase.table("questions").select("id").eq("id", payload.question_id).single().execute()
    if not question.data:
        raise HTTPException(status_code=404, detail="Question introuvable")

    result = supabase.table("answers").insert({
        "question_id": payload.question_id,
        "body":        payload.body,
        "author_id":   current_user.id,
        "parent_id":   payload.parent_id,
        "is_accepted": False,
    }).execute()

    answer_id = result.data[0]["id"]
    view = supabase.table("answers_summary").select("*").eq("id", answer_id).single().execute()
    return AnswerResponse(**{**view.data, "replies": []})


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: str,
    payload:   AnswerUpdate,
    request:   Request,
    supabase:  Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    supabase.table("answers").update({"body": payload.body}).eq("id", answer_id).execute()
    view = supabase.table("answers_summary").select("*").eq("id", answer_id).single().execute()
    return AnswerResponse(**{**view.data, "replies": []})


# ── DELETE ────────────────────────────────────────────────────
@router.delete("/{answer_id}", status_code=204)
async def delete_answer(
    answer_id: str,
    request:   Request,
    supabase:  Client = Depends(get_supabase_admin),
):
    supabase.table("answers").delete().eq("id", answer_id).execute()


# ── ACCEPT ────────────────────────────────────────────────────
# ── ACCEPT ────────────────────────────────────────────────────
@router.post("/{answer_id}/accept", status_code=200)
async def accept_answer(
    answer_id: str,
    request:   Request,
    supabase:  Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)

    # Get the answer to find the question
    answer = supabase.table("answers").select("question_id").eq("id", answer_id).single().execute()
    if not answer.data:
        raise HTTPException(status_code=404, detail="Réponse introuvable")

    question_id = answer.data["question_id"]

    # Verify current user is the question author
    question = supabase.table("questions").select("author_id").eq("id", question_id).single().execute()
    if not question.data or question.data["author_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Seul l'auteur de la question peut accepter une réponse")

    # Un-accept all previous answers for this question
    supabase.table("answers").update({"is_accepted": False}).eq("question_id", question_id).execute()

    # Accept the selected answer
    supabase.table("answers").update({"is_accepted": True}).eq("id", answer_id).execute()

    return {"message": "Réponse acceptée"}


# ── VOTE ──────────────────────────────────────────────────────
@router.post("/{answer_id}/vote")
async def vote_answer(
    answer_id: str,
    payload:   VoteRequest,
    request:   Request,
    supabase:  Client = Depends(get_supabase_admin),
):
    from ..dependencies import get_current_user
    current_user = await get_current_user(request)
    user_id = current_user.id

    # Check existing vote
    existing = (
        supabase.table("answer_votes")
        .select("id, value")
        .eq("answer_id", answer_id)
        .eq("user_id", user_id)
        .execute()
    )

    if existing.data:
        row = existing.data[0]
        if row["value"] == payload.value:
            # Same vote — remove (toggle off)
            supabase.table("answer_votes").delete().eq("id", row["id"]).execute()
        else:
            # Different vote — flip
            supabase.table("answer_votes").update({"value": payload.value}).eq("id", row["id"]).execute()
    else:
        # New vote
        supabase.table("answer_votes").insert({
            "answer_id": answer_id,
            "user_id":   user_id,
            "value":     payload.value,
        }).execute()

    # Return new score
    all_votes = supabase.table("answer_votes").select("value").eq("answer_id", answer_id).execute()
    score = sum(r["value"] for r in all_votes.data)
    return {"vote_score": score}