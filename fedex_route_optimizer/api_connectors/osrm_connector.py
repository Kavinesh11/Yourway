# osrm_connector.py

import requests

def get_osrm_route(origin, destination, profile="driving"):
    """
    Get route data between origin and destination using OSRM.
    :param origin: Tuple (lat, lon)
    :param destination: Tuple (lat, lon)
    :param profile: routing profile ('driving', 'walking', 'cycling')
    :return: Dictionary with distance (meters) and duration (seconds)
    """
    base_url = "http://router.project-osrm.org/route/v1"
    coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    url = f"{base_url}/{profile}/{coords}?overview=false"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['routes']:
            route = data['routes'][0]
            return {
                "distance_meters": route["distance"],
                "duration_seconds": route["duration"]
            }
        else:
            raise ValueError("No route found.")
    else:
        raise Exception(f"OSRM API Error: {response.status_code} - {response.text}")
