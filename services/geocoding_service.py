"""Geocoding service for converting location names to coordinates."""
import httpx
from typing import Optional
from app.config import settings
from models.schemas import Location
from utils.logger import setup_logger

logger = setup_logger(__name__)


class GeocodingService:
    """Service for geocoding locations using LocationIQ API."""
    
    BASE_URL = "https://us1.locationiq.com/v1/search"
    
    def __init__(self):
        self.api_key = settings.locationiq_api_key
        self.timeout = settings.request_timeout
    
    async def geocode(self, location_name: str) -> Optional[Location]:
        """
        Geocode a location name to coordinates.
        
        Args:
            location_name: Name of the location to geocode
            
        Returns:
            Location object with coordinates or None if geocoding fails
        """
        params = {
            'key': self.api_key,
            'q': location_name,
            'format': 'json',
            'limit': 1
        }
        
        try:
            # ⚠️ TEMPORARY FIX: Disable SSL verification to test SSL-related connection issue
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                if not data or len(data) == 0:
                    logger.warning(f"No geocoding results for: {location_name}")
                    return None
                
                result = data[0]
                location = Location(
                    name=location_name,
                    latitude=float(result['lat']),
                    longitude=float(result['lon']),
                    display_name=result.get('display_name')
                )
                
                logger.info(f"Geocoded {location_name}: ({location.latitude}, {location.longitude})")
                return location
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error geocoding {location_name}: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error geocoding {location_name}: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Data parsing error geocoding {location_name}: {e}")
            return None
