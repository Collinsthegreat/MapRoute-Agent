"""Webhook endpoint handlers for Telex.im integration."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
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


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook requests from Telex.im.
    Supports both simple JSON and A2A protocol formats.
    """
    try:
        body = await request.json()
        logger.info(f"Received webhook request")
        
        message_text = None
        
        # Check if it's A2A protocol (JSON-RPC 2.0)
        if "jsonrpc" in body and body.get("jsonrpc") == "2.0":
            logger.info("Detected A2A protocol request")
            
            # Extract message from A2A format
            params = body.get("params", {})
            message_obj = params.get("message", {})
            parts = message_obj.get("parts", [])
            
            logger.info(f"Found {len(parts)} parts in message")
            
            # Get text from parts - ONLY take the FIRST clean text part
            for i, part in enumerate(parts):
                part_kind = part.get("kind") or part.get("type")
                part_text = part.get("text", "")
                
                logger.info(f"Part {i}: kind={part_kind}, text_preview={part_text[:50] if part_text else 'empty'}")
                
                # Skip empty parts
                if not part_text or not part_text.strip():
                    continue
                
                # Skip HTML content
                if part_text.startswith("<p>") or part_text.startswith("<"):
                    logger.info(f"Skipping HTML part {i}")
                    continue
                
                # Skip status messages
                if "Calculating" in part_text or "..." in part_text:
                    logger.info(f"Skipping status message part {i}")
                    continue
                
                # Skip data kind (it's nested content)
                if part_kind == "data":
                    logger.info(f"Skipping data part {i}")
                    continue
                
                # Take ONLY the first valid text
                if part_kind == "text" and part_text.strip():
                    message_text = part_text.strip()
                    logger.info(f"✓ Extracted clean text from part {i}: '{message_text}'")
                    break  # STOP after first valid text
            
            if not message_text:
                logger.error("No valid text found in A2A message parts")
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32602,
                            "message": "No valid text content in message parts"
                        }
                    },
                    status_code=400
                )
            
            # Process message
            logger.info(f"Processing message: '{message_text}'")
            response = await agent.process_message(message_text)
            
            # Return A2A format response
            a2a_response = {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "message": {
                        "kind": "message",
                        "role": "agent",
                        "parts": [
                            {
                                "kind": "text",
                                "text": response.text
                            }
                        ],
                        "messageId": f"{message_obj.get('messageId', 'msg')}_response"
                    }
                }
            }
            
            # Add map link if available
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
            
            logger.info(f"Sending A2A response with {len(a2a_response['result']['message']['parts'])} parts")
            return JSONResponse(content=a2a_response)
        
        # Simple format: {"message": "..."}
        else:
            logger.info("Detected simple message format")
            
            if "message" in body:
                message_text = body["message"]
            elif "text" in body:
                message_text = body["text"]
            else:
                return JSONResponse(
                    content={
                        "text": "❌ No message field found. Please send a 'message' field.",
                        "success": False
                    },
                    status_code=400
                )
            
            # Process message
            logger.info(f"Processing simple message: '{message_text}'")
            response = await agent.process_message(message_text)
            
            # Simple response
            response_data = {
                "text": response.text,
                "success": True
            }
            
            if response.attachments:
                response_data["attachments"] = response.attachments
            
            if response.quick_replies:
                response_data["quick_replies"] = response.quick_replies
            
            if response.metadata:
                response_data["metadata"] = response.metadata
            
            logger.info(f"Sending simple response")
            return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        
        # Determine if A2A format
        is_a2a = isinstance(body, dict) and "jsonrpc" in body
        
        if is_a2a:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {
                        "code": -32603,
                        "message": "Internal server error",
                        "data": str(e)
                    }
                },
                status_code=500
            )
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