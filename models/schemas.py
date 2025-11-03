"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class TelexMessage(BaseModel):
    """Incoming message from Telex.im."""
    message: str = Field(..., description="User message text")
    user_id: Optional[str] = Field(None, description="User identifier")
    channel_id: Optional[str] = Field(None, description="Channel identifier")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('message')
    def message_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class Location(BaseModel):
    """Geocoded location information."""
    name: str
    latitude: float
    longitude: float
    display_name: Optional[str] = None


class RouteInfo(BaseModel):
    """Route calculation result."""
    origin: Location
    destination: Location
    distance_km: float
    duration_minutes: float
    map_url: str
    summary: str


class TelexResponse(BaseModel):
    """Response format for Telex.im."""
    text: str = Field(..., description="Main response text")
    quick_replies: Optional[list[str]] = Field(None, description="Quick reply options")
    attachments: Optional[list[Dict[str, Any]]] = Field(None, description="Attachments like links")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.dict().items() if v is not None}


class ErrorResponse(BaseModel):
    """Error response format."""
    error: str
    message: str
    suggestion: Optional[str] = None