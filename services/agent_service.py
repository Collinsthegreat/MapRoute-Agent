"""Core agent service orchestrating geocoding and routing."""
import asyncio
from typing import Optional
from models.schemas import TelexResponse, ErrorResponse, RouteInfo
from services.geocoding_service import GeocodingService
from services.routing_service import RoutingService
from utils.parsers import MessageParser
from utils.validators import LocationValidator
from utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)


class MapRouteAgent:
    """AI Agent for handling map routing requests."""
    
    def __init__(self):
        self.geocoding_service = GeocodingService()
        self.routing_service = RoutingService()
        self.parser = MessageParser()
    
    async def process_message(self, message: str) -> TelexResponse:
        """
        Process an incoming message and generate a response.
        
        Args:
            message: User message text
            
        Returns:
            TelexResponse object with formatted response
        """
        logger.info(f"Processing message: {message}")
        
        # Check if this is a route request
        if not self.parser.is_route_request(message):
            return self._create_help_response()
        
        # Parse the route request
        locations = self.parser.parse_route_request(message)
        if not locations:
            return self._create_parse_error_response()
        
        origin_name, dest_name = locations
        
        # Validate locations
        origin_valid, origin_error = LocationValidator.validate_location(origin_name)
        dest_valid, dest_error = LocationValidator.validate_location(dest_name)
        
        if not origin_valid:
            return self._create_validation_error_response("origin", origin_error)
        if not dest_valid:
            return self._create_validation_error_response("destination", dest_error)
        
        # Sanitize locations
        origin_name = LocationValidator.sanitize_location(origin_name)
        dest_name = LocationValidator.sanitize_location(dest_name)
        
        # Get route with retry logic
        route_info = await self._get_route_with_retry(origin_name, dest_name)
        
        if not route_info:
            return self._create_route_error_response(origin_name, dest_name)
        
        return self._create_success_response(route_info)
    
    async def _get_route_with_retry(
        self, 
        origin_name: str, 
        dest_name: str,
        retries: int = None
    ) -> Optional[RouteInfo]:
        """
        Get route with retry logic.
        
        Args:
            origin_name: Origin location name
            dest_name: Destination location name
            retries: Number of retries (defaults to settings.max_retries)
            
        Returns:
            RouteInfo or None if all attempts fail
        """
        if retries is None:
            retries = settings.max_retries
        
        for attempt in range(retries):
            try:
                # Geocode both locations concurrently
                origin_task = self.geocoding_service.geocode(origin_name)
                dest_task = self.geocoding_service.geocode(dest_name)
                
                origin, destination = await asyncio.gather(origin_task, dest_task)
                
                if not origin:
                    logger.warning(f"Could not geocode origin: {origin_name}")
                    return None
                
                if not destination:
                    logger.warning(f"Could not geocode destination: {dest_name}")
                    return None
                
                # Calculate route
                route_info = await self.routing_service.calculate_route(origin, destination)
                
                if route_info:
                    return route_info
                
                # If route calculation failed, retry
                if attempt < retries - 1:
                    delay = settings.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay}s (attempt {attempt + 1}/{retries})")
                    await asyncio.sleep(delay)
            
            except Exception as e:
                logger.error(f"Error getting route (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(settings.retry_delay * (2 ** attempt))
        
        return None
    
    def _create_success_response(self, route_info: RouteInfo) -> TelexResponse:
        """Create a successful response with route information."""
        return TelexResponse(
            text=route_info.summary,
            attachments=[
                {
                    'type': 'link',
                    'url': route_info.map_url,
                    'title': '📍 View on Google Maps'
                }
            ],
            quick_replies=[
                'Get another route',
                'Help'
            ],
            metadata={
                'distance_km': route_info.distance_km,
                'duration_minutes': route_info.duration_minutes
            }
        )
    
    def _create_help_response(self) -> TelexResponse:
        """Create a help response."""
        return TelexResponse(
            text=(
                "👋 Hi! I'm your MapRoute assistant.\n\n"
                "I can help you find directions between locations.\n\n"
                "Try asking:\n"
                "• 'directions from Lagos to Abuja'\n"
                "• 'route from New York to Boston'\n"
                "• 'how to get from Paris to London'"
            ),
            quick_replies=[
                'Get directions',
                'Example route'
            ]
        )
    
    def _create_parse_error_response(self) -> TelexResponse:
        """Create a response for parsing errors."""
        return TelexResponse(
            text=(
                "❌ I couldn't understand your request.\n\n"
                "Please use the format:\n"
                "'directions from [origin] to [destination]'\n\n"
                "Example: 'directions from Lagos to Abuja'"
            ),
            quick_replies=['Help', 'Try again']
        )
    
    def _create_validation_error_response(
        self, 
        location_type: str, 
        error: str
    ) -> TelexResponse:
        """Create a response for validation errors."""
        return TelexResponse(
            text=f"❌ Invalid {location_type}: {error}\n\nPlease try again with a valid location name.",
            quick_replies=['Help', 'Try again']
        )
    
    def _create_route_error_response(
        self, 
        origin: str, 
        destination: str
    ) -> TelexResponse:
        """Create a response for route calculation errors."""
        return TelexResponse(
            text=(
                f"❌ Sorry, I couldn't find a route from {origin} to {destination}.\n\n"
                "This might be because:\n"
                "• One or both locations couldn't be found\n"
                "• There's no drivable route between them\n"
                "• The routing service is temporarily unavailable\n\n"
                "Please check the location names and try again."
            ),
            quick_replies=['Try different locations', 'Help']
        )