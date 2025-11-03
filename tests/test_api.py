import httpx
import asyncio
import json

async def test_locationiq():
    api_key = "pk.88bb5c56c7a6813016f3ee4ee309c920"
    url = "https://us1.locationiq.com/v1/directions/driving"
    
    params = {
        'key': api_key,
        'coordinates': '3.3941795,6.4550575;7.4892974,9.0643305',
        'overview': 'full',
        'geometries': 'geojson',
        'steps': 'true'
    }
    
    print("Testing LocationIQ Directions API...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                route = data['routes'][0]
                distance_km = route['distance'] / 1000
                duration_min = route['duration'] / 60
                
                print(f"✅ Success!")
                print(f"Distance: {distance_km:.2f} km")
                print(f"Duration: {duration_min:.1f} minutes")
                print(f"\nFull response:\n{json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_locationiq())