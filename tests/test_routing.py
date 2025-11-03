import asyncio
from models.schemas import Location
from services.routing_service import RoutingService

async def test_route():
    routing = RoutingService()
    
    origin = Location(name="New York", latitude=40.7127281, longitude=-74.0060152)
    destination = Location(name="Florida", latitude=27.7567667, longitude=-81.4639835)
    
    route_info = await routing.calculate_route(origin, destination)
    
    if route_info:
        print(route_info.summary)
        print("Google Maps URL:", route_info.map_url)
    else:
        print("Failed to get route.")

# Run the test
asyncio.run(test_route())
