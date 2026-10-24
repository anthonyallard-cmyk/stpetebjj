import json
import secrets
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.database import db_cursor, get_site_settings
from app.services.ai_chat import process_chat_turn


def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

router = APIRouter(prefix="/api/chat", tags=["ai_chat"])


class ChatMessageInput(BaseModel):
    session_id: str | None = None
    message: str


@router.get("/session")
async def get_chat_session(request: Request, session_id: str = ""):
    site = get_site_settings()
    enabled = site.get("ai_enabled", "true").lower() == "true"
    try:
        max_per_session = max(1, int(site.get("ai_max_messages_per_session") or 15))
    except ValueError:
        max_per_session = 15

    sid = (session_id or "").strip()
    if not sid or len(sid) > 80:
        sid = f"spb-{secrets.token_hex(12)}"

    ip = get_client_ip(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM ai_chat_sessions WHERE session_id = ?", (sid,))
        sess = cur.fetchone()
        if not sess:
            cur.execute(
                "INSERT INTO ai_chat_sessions (session_id, ip_address, messages_count, terminated, termination_reason) VALUES (?, ?, 0, 0, '')",
                (sid, ip),
            )
            messages = []
            terminated = False
            reason = ""
            count = 0
        else:
            terminated = bool(sess["terminated"])
            reason = sess["termination_reason"] or ""
            count = sess["messages_count"]
            cur.execute(
                "SELECT id, role, content, actions_json, created_at FROM ai_chat_messages WHERE session_id = ? ORDER BY id ASC LIMIT 50",
                (sid,),
            )
            messages = []
            for r in cur.fetchall():
                try:
                    acts = json.loads(r["actions_json"] or "[]")
                except Exception:
                    acts = []
                messages.append({
                    "id": str(r["id"]),
                    "role": r["role"],
                    "content": r["content"],
                    "actions": acts,
                })

    return {
        "enabled": enabled,
        "session_id": sid,
        "messages": messages,
        "terminated": terminated,
        "termination_reason": reason,
        "remaining_messages": 0 if terminated else max(0, max_per_session - count),
        "max_messages": max_per_session,
    }


@router.post("/message")
async def send_chat_message(payload: ChatMessageInput, request: Request):
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please enter a message.")
    if len(text) > 800:
        raise HTTPException(status_code=400, detail="Please keep messages under 800 characters.")

    sid = (payload.session_id or "").strip()
    if not sid or len(sid) > 80:
        sid = f"spb-{secrets.token_hex(12)}"

    ip = get_client_ip(request)
    result = process_chat_turn(session_id=sid, ip_address=ip, user_message=text)
    result["session_id"] = sid
    return result
