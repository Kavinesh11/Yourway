# tomtom_connector.py

import requests

def get_traffic_data(api_key, origin, destination):
    """
    Fetch real-time traffic data from TomTom API.
    :param api_key: TomTom API key
    :param origin: Tuple (lat, lon)
    :param destination: Tuple (lat, lon)
    :return: Travel time in seconds considering traffic
    """
    url = (
        f"https://api.tomtom.com/routing/1/calculateRoute/"
        f"{origin[0]},{origin[1]}:{destination[0]},{destination[1]}/json"
        f"?key={api_key}&traffic=true"
    )
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        travel_time_sec = data["routes"][0]["summary"]["travelTimeInSeconds"]
        return travel_time_sec
    else:
        raise Exception(f"TomTom API Error: {response.status_code} - {response.text}")
