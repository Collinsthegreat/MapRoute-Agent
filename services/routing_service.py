"""Routing service using LocationIQ API (simpler alternative)."""
import httpx
from typing import Optional
from app.config import settings
from models.schemas import Location, RouteInfo
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RoutingService:
    """Service for calculating routes using LocationIQ Directions API."""
    
    # Removed .php and coordinates will go in URL path
    BASE_URL = "https://us1.locationiq.com/v1/directions/driving"

    def __init__(self):
        self.api_key = settings.locationiq_api_key
        self.timeout = settings.request_timeout
    
    async def calculate_route(
        self, 
        origin: Location, 
        destination: Location
    ) -> Optional[RouteInfo]:
        """
        Calculate route between two locations using LocationIQ.
        
        Args:
            origin: Starting location
            destination: Ending location
            
        Returns:
            RouteInfo object or None if calculation fails
        """
        # Coordinates go directly in the URL path
        coordinates = f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
        
        params = {
            'key': self.api_key,
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true'
        }
        
        url = f"{self.BASE_URL}/{coordinates}"
        
        try:
            async with httpx.AsyncClient(verify=False) as client:    
                response = await client.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                route = data['routes'][0]
                
                distance_km = route['distance'] / 1000  # Convert meters to km
                duration_minutes = route['duration'] / 60  # Convert seconds to minutes
                
                map_url = self._generate_map_url(origin, destination)
                
                summary_text = self._create_summary(
                    origin.name,
                    destination.name,
                    distance_km,
                    duration_minutes
                )
                
                route_info = RouteInfo(
                    origin=origin,
                    destination=destination,
                    distance_km=round(distance_km, 2),
                    duration_minutes=round(duration_minutes, 1),
                    map_url=map_url,
                    summary=summary_text
                )
                
                logger.info(f"Calculated route: {distance_km:.2f}km, {duration_minutes:.1f}min")
                return route_info
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calculating route: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error calculating route: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Data parsing error calculating route: {e}")
            return None
    
    def _generate_map_url(self, origin: Location, destination: Location) -> str:
        """Generate Google Maps URL for the route."""
        return (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin.latitude},{origin.longitude}"
            f"&destination={destination.latitude},{destination.longitude}"
        )
    
    def _create_summary(
        self, 
        origin_name: str, 
        dest_name: str, 
        distance: float, 
        duration: float
    ) -> str:
        """Create a human-readable route summary."""
        hours = int(duration // 60)
        minutes = int(duration % 60)
        
        time_str = ""
        if hours > 0:
            time_str = f"{hours} hour{'s' if hours > 1 else ''} {minutes} min"
        else:
            time_str = f"{minutes} min"
        
        return (
            f"🚗 Route from {origin_name} to {dest_name}:\n"
            f"📏 Distance: {distance:.2f} km\n"
            f"⏱️ Estimated time: {time_str}"
        )
