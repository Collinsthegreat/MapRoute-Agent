"""Webhook endpoint handlers for Telex.im integration."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
from services.agent_service import MapRouteAgent
from utils.logger import setup_logger

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


def format_telex_error(error_message: str, code: int = -32603, id_value: Optional[str] = None, data: Optional[str] = None):
    """Return standardized Telex-style JSON-RPC error response."""
    error_response = {
        "jsonrpc": "2.0",
        "id": id_value,
        "error": {
            "code": code,
            "message": error_message
        }
    }
    if data:
        error_response["error"]["data"] = data
    return JSONResponse(content=error_response, status_code=500 if code == -32603 else 400)


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook requests from Telex.im.
    Supports both simple JSON and A2A protocol formats.
    """
    try:
        body = await request.json()
        logger.info("Received webhook request")

        message_text = None

        # Check if it's A2A protocol (JSON-RPC 2.0)
        if body.get("jsonrpc") == "2.0":
            logger.debug("Detected A2A protocol request")
            params = body.get("params", {})
            message_obj = params.get("message", {})
            parts = message_obj.get("parts", [])

            message_text = latest_text(parts)
            message_text = extract_last_directions(message_text)

            if not message_text:
                logger.error("No valid text found in A2A message parts")
                return format_telex_error(
                    "No valid text content in message parts",
                    code=-32602,
                    id_value=body.get("id")
                )

            logger.info(f"Processing message sent to agent: '{message_text}'")
            response = await agent.process_message(message_text)

            a2a_response = {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "message": {
                        "kind": "message",
                        "role": "agent",
                        "parts": [{"kind": "text", "text": response.text}],
                        "messageId": f"{message_obj.get('messageId', 'msg')}_response"
                    }
                }
            }

            if response.attachments:
                for attachment in response.attachments:
                    a2a_response["result"]["message"]["parts"].append({
                        "kind": "data",
                        "data": {
                            "type": "link",
                            "url": attachment.get("url"),
                            "title": attachment.get("title", "View Map")
                        }
                    })

            logger.debug(f"Sending A2A response with {len(a2a_response['result']['message']['parts'])} parts")
            return JSONResponse(content=a2a_response)

        # Simple format: {"message": "..." } OR {"message": {...}}
        else:
            logger.debug("Detected simple message format")
            message_obj = body.get("message") or body.get("text")

            if isinstance(message_obj, dict) and "parts" in message_obj:
                message_text = latest_text(message_obj.get("parts"))
            else:
                message_text = message_obj

            message_text = extract_last_directions(message_text)

            if not message_text:
                return JSONResponse(
                    content={
                        "text": "❌ No message field found. Please send a 'message' field.",
                        "success": False
                    },
                    status_code=400
                )

            logger.info(f"Processing simple message sent to agent: '{message_text}'")
            response = await agent.process_message(message_text)

            response_data = {"text": response.text, "success": True}
            if response.attachments:
                response_data["attachments"] = response.attachments
            if response.quick_replies:
                response_data["quick_replies"] = response.quick_replies
            if response.metadata:
                response_data["metadata"] = response.metadata

            logger.debug("Sending simple response")
            return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        try:
            body = await request.json()
        except Exception:
            body = {}

        is_a2a = isinstance(body, dict) and "jsonrpc" in body
        if is_a2a:
            return format_telex_error("Internal server error", data=str(e), id_value=body.get("id"))
        else:
            return JSONResponse(
                content={
                    "text": "⚠️ Sorry, I encountered an error. Please try again.",
                    "error": str(e),
                    "success": False
                },
                status_code=500
            )


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
    """
    Manifest endpoint required by Telex to fetch your agent's metadata.
    """
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
