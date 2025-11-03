"""Webhook endpoint handlers for Telex.im integration."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from models.schemas import TelexMessage, TelexResponse
from services.agent_service import MapRouteAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()
agent = MapRouteAgent()


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook requests from Telex.im.
    
    Expects JSON payload with a 'message' field containing the user's text.
    Returns a JSON response formatted for Telex.im.
    """
    try:
        # Parse incoming request
        body = await request.json()
        logger.info(f"Received webhook request: {body}")
        
        # Validate request structure
        try:
            telex_message = TelexMessage(**body)
        except Exception as e:
            logger.error(f"Invalid request structure: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
        
        # Process the message
        response = await agent.process_message(telex_message.message)
        
        # Return formatted response
        response_dict = response.to_dict()
        logger.info(f"Sending response: {response_dict}")
        
        return JSONResponse(content=response_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}", exc_info=True)
        
        # Return a friendly error response
        error_response = TelexResponse(
            text="⚠️ Sorry, I encountered an unexpected error. Please try again in a moment.",
            quick_replies=['Try again', 'Help']
        )
        return JSONResponse(
            content=error_response.to_dict(),
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