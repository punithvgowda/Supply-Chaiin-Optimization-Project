import requests

def get_alternative_route(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Fetches an alternative route using the public OSRM API.
    Note: Public OSRM API should not be heavily loaded, but fine for MVP prototyping.
    Coordinates format for OSRM: lon,lat
    """
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "alternatives": "true" # Request alternative routes
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                # Return the second route if available (as alternative), else first
                route_index = 1 if len(data['routes']) > 1 else 0
                return data['routes'][route_index]['geometry']
    except Exception as e:
        print(f"Error fetching route: {e}")
    
    return None
