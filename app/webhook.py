"""Webhook endpoint handlers for Telex.im integration."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
from services.agent_service import MapRouteAgent
from utils.logger import setup_logger
from datetime import datetime, timezone
import uuid

logger = setup_logger(__name__)
router = APIRouter()
agent = MapRouteAgent()


class SimpleTelexMessage(BaseModel):
    """Simple message format."""
    message: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None


def latest_text(parts: Optional[List[dict]]) -> str:
    """
    Extract the last valid text from message parts.
    Skips HTML, status messages, empty parts, and nested data.
    """
    if not parts:
        logger.debug("No message parts received")
        return ""
    
    for i, p in enumerate(reversed(parts)):
        if not isinstance(p, dict):
            logger.debug(f"Skipping non-dict part at reversed index {i}")
            continue
        kind = p.get("kind")
        text = p.get("text", "")
        if not text or not text.strip():
            continue
        if text.startswith("<") or "Calculating" in text or "..." in text:
            continue
        if kind == "text":
            logger.debug(f"Selected text part {i}: '{text.strip()[:50]}'")
            return text.strip()
        if kind == "data" and isinstance(p.get("data"), list):
            for j, item in enumerate(reversed(p["data"])): 
                if isinstance(item, dict):
                    nested_text = item.get("text", "")
                    if nested_text and not nested_text.startswith("<") and "Calculating" not in nested_text:
                        logger.debug(f"Selected nested data text part {i}.{j}: '{nested_text[:50]}'")
                        return nested_text.strip()
    logger.debug("No valid text found in message parts")
    return ""


def extract_last_directions(text: str) -> str:
    """
    Extract only the last 'directions from ...' query from a concatenated string.
    """
    if isinstance(text, str) and "directions from" in text:
        parts = text.split("directions from")
        if len(parts) > 1:
            last_text = "directions from" + parts[-1].strip()
            logger.debug(f"Extracted last directions query: '{last_text[:100]}'")
            return last_text
    if isinstance(text, str):
        return text.strip()
    return ""  # safe fallback


def make_task_result(
    rid: any,
    *,
    content: str,
    context_id: str,
    task_id: str,
    state: str = "completed",
    user_echo: str | None = None,
    attachments: Optional[List[dict]] = None,
    quick_replies: Optional[List[dict]] = None,
    artifact_name: str = "assistantResponse"
):
    """Return MapRoute-style task envelope, always HTTP 200 safe."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = {
        "id": task_id,
        "contextId": context_id,
        "status": {
            "state": state,
            "timestamp": now,
            "message": {
                "kind": "message",
                "role": "agent",
                "parts": [{"kind": "text", "text": content}],
                "messageId": str(uuid.uuid4()),
                "taskId": None,
                "metadata": None,
            },
        },
        "artifacts": [
            {
                "artifactId": str(uuid.uuid4()),
                "name": artifact_name,
                "parts": [{"kind": "text", "text": content}],
            }
        ],
        "history": [],
        "kind": "task",
    }

    if attachments:
        result["status"]["message"]["attachments"] = attachments
        result["artifacts"].append({
            "artifactId": str(uuid.uuid4()),
            "name": "attachments",
            "parts": [{"kind": "data", "data": attachments}]
        })

    if quick_replies:
        result["status"]["message"]["quick_replies"] = quick_replies
        result["artifacts"].append({
            "artifactId": str(uuid.uuid4()),
            "name": "quickReplies",
            "parts": [{"kind": "data", "data": quick_replies}]
        })

    if user_echo is not None:
        result["history"].append({
            "kind": "message",
            "role": "user",
            "parts": [{"kind": "text", "text": user_echo}],
            "messageId": str(uuid.uuid4()),
            "taskId": None,
            "metadata": None,
        })
    return {"jsonrpc": "2.0", "id": rid, "result": result}


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook requests from Telex.im.
    Supports both simple JSON and A2A protocol formats.
    Returns MapRoute A2A-compliant responses always.
    """
    try:
        body = await request.json()
        logger.info("Received webhook request")

        # --- log full incoming message for debugging ---
        logger.debug(f"Full webhook payload: {body}")

        rid = body.get("id", str(uuid.uuid4()))
        message_text = ""

        if body.get("jsonrpc") == "2.0":
            # --- A2A protocol ---
            params = body.get("params", {})
            message_obj = params.get("message", {})
            parts = message_obj.get("parts", [])

            # --- log message parts ---
            logger.debug(f"A2A message parts: {parts}")

            message_text = latest_text(parts)
            message_text = extract_last_directions(message_text)

            if not message_text:
                resp = make_task_result(
                    rid,
                    content="❌ No valid text found in A2A message parts.",
                    context_id=str(uuid.uuid4()),
                    task_id=str(uuid.uuid4()),
                    state="failed",
                    user_echo=None
                )
                return JSONResponse(content=resp)

            response = await agent.process_message(message_text)
            resp = make_task_result(
                rid,
                content=response.text,
                context_id=str(uuid.uuid4()),
                task_id=str(uuid.uuid4()),
                user_echo=message_text,
                attachments=getattr(response, "attachments", None),
                quick_replies=getattr(response, "quick_replies", None)
            )
            return JSONResponse(content=resp)

        else:
            # --- Simple JSON format ---
            message_obj = body.get("message") or body.get("text")
            if isinstance(message_obj, dict) and "parts" in message_obj:
                parts = message_obj.get("parts")
                logger.debug(f"Simple JSON message parts: {parts}")
                message_text = latest_text(parts)
            else:
                message_text = message_obj

            message_text = extract_last_directions(message_text)

            if not message_text:
                resp = make_task_result(
                    rid,
                    content="❌ No message field found. Please send a 'message' field.",
                    context_id=str(uuid.uuid4()),
                    task_id=str(uuid.uuid4()),
                    state="failed",
                    user_echo=None
                )
                return JSONResponse(content=resp)

            response = await agent.process_message(message_text)
            resp = make_task_result(
                rid,
                content=response.text,
                context_id=str(uuid.uuid4()),
                task_id=str(uuid.uuid4()),
                user_echo=message_text,
                attachments=getattr(response, "attachments", None),
                quick_replies=getattr(response, "quick_replies", None)
            )
            return JSONResponse(content=resp)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        rid = body.get("id") if isinstance(body, dict) else str(uuid.uuid4())
        resp = make_task_result(
            rid,
            content=f"⚠️ Internal server error: {str(e)}",
            context_id=str(uuid.uuid4()),
            task_id=str(uuid.uuid4()),
            state="failed",
            user_echo=None
        )
        return JSONResponse(content=resp)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MapRoute AI Agent",
        "version": "1.0.0",
        "protocol": "A2A + Simple REST"
    }


@router.get("/manifest")
async def manifest():
    """Manifest endpoint required by Telex to fetch your agent's metadata."""
    return JSONResponse(
        content={
            "name": "MapRoute Agent",
            "description": "An intelligent travel assistant that provides directions, distances, and estimated times between locations using AI and mapping APIs.",
            "version": "1.0.0",
            "homepage_url": "https://maproute-agent-production.up.railway.app",
            "author": {
                "name": "Abuchi Nwajagu Collins",
                "email": "collinsthegreat@gmail.com"
            },
            "capabilities": {
                "a2a": True,
                "interactive": True,
                "text": True,
                "links": True
            },
            "endpoints": {
                "webhook": "https://maproute-agent-production.up.railway.app/webhook"
            },
            "tags": ["travel", "navigation", "AI agent", "maps", "directions"]
        }
    )
