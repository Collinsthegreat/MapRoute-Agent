"""Routing service using LocationIQ API with retry/backoff and TTL caching."""
import httpx
import asyncio
import time
from typing import Optional, Tuple
from app.config import settings
from models.schemas import Location, RouteInfo
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RoutingService:
    """Service for calculating routes using LocationIQ Directions API."""

    BASE_URL = "https://us1.locationiq.com/v1/directions/driving"

    def __init__(self, cache_ttl: int = 3600):
        """
        Args:
            cache_ttl: Time in seconds to keep cached routes (default 1 hour)
        """
        self.api_key = settings.locationiq_api_key
        self.timeout = settings.request_timeout
        self.cache_ttl = cache_ttl
        # cache: { (origin_name, dest_name): (RouteInfo, timestamp) }
        self.cache: dict[Tuple[str, str], Tuple[RouteInfo, float]] = {}

    async def calculate_route(
        self, 
        origin: Location, 
        destination: Location,
        max_retries: int = 3,
        backoff_factor: float = 1.0
    ) -> Optional[RouteInfo]:
        """Calculate route with retry/backoff and TTL caching."""
        cache_key = (origin.name.lower(), destination.name.lower())
        # Check cache
        if cache_key in self.cache:
            route_info, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Using cached route for {origin.name} -> {destination.name}")
                return route_info
            else:
                logger.info(f"Cache expired for {origin.name} -> {destination.name}")
                del self.cache[cache_key]

        coordinates = f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
        params = {
            'key': self.api_key,
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true'
        }
        url = f"{self.BASE_URL}/{coordinates}"

        attempt = 0
        while attempt <= max_retries:
            try:
                async with httpx.AsyncClient(verify=False) as client:
                    response = await client.get(url, params=params, timeout=self.timeout)

                    if response.status_code == 429:
                        # Too many requests – exponential backoff
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"429 Too Many Requests – retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        attempt += 1
                        continue

                    response.raise_for_status()
                    data = response.json()
                    route = data['routes'][0]

                    distance_km = route['distance'] / 1000
                    duration_minutes = route['duration'] / 60

                    map_url = self._generate_map_url(origin, destination)
                    summary_text = self._create_summary(origin.name, destination.name, distance_km, duration_minutes)

                    route_info = RouteInfo(
                        origin=origin,
                        destination=destination,
                        distance_km=round(distance_km, 2),
                        duration_minutes=round(duration_minutes, 1),
                        map_url=map_url,
                        summary=summary_text
                    )

                    # Cache route with timestamp
                    self.cache[cache_key] = (route_info, time.time())
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

        logger.error(f"Max retries exceeded for route {origin.name} -> {destination.name}")
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
        time_str = f"{hours} hour{'s' if hours != 1 else ''} {minutes} min" if hours > 0 else f"{minutes} min"
        return (
            f"🚗 Route from {origin_name} to {dest_name}:\n"
            f"📏 Distance: {distance:.2f} km\n"
            f"⏱️ Estimated time: {time_str}"
        )
