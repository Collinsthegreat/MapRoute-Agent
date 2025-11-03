"""Webhook endpoint handlers for Telex.im integration."""
from fastapi import APIRouter, HTTPException, Request
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
        logger.info(f"Received webhook: {body}")
        
        message_text = None
        
        # Check if it's A2A protocol (JSON-RPC 2.0)
        if "jsonrpc" in body and body.get("jsonrpc") == "2.0":
            logger.info("Detected A2A protocol request")
            
            # Extract message from A2A format
            params = body.get("params", {})
            message_obj = params.get("message", {})
            parts = message_obj.get("parts", [])
            
            # Get text from parts
            for part in parts:
                if part.get("kind") == "text" or part.get("type") == "text":
                    message_text = part.get("text", "")
                    if message_text:
                        break
            
            if not message_text:
                logger.error("No text found in A2A message parts")
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32602,
                            "message": "No text content in message parts"
                        }
                    },
                    status_code=400
                )
            
            # Process message
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
            
            logger.info(f"Sending A2A response: {a2a_response}")
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
            
            logger.info(f"Sending simple response: {response_data}")
            return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        
        # Return appropriate error format
        if "jsonrpc" in body:
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
        "version": "1.0.0"
    }