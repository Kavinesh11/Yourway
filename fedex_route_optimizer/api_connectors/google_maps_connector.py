# google_maps_connector.py

import requests

def geocode_address(address, api_key):
    """
    Geocode an address to latitude and longitude using Google Maps API.
    :param address: String address
    :param api_key: Google Maps API Key
    :return: Tuple (lat, lon)
    """
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get("results")
        if results:
            location = results[0]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            raise ValueError("No geocoding results found.")
    else:
        raise Exception(f"Google Maps API Error: {response.status_code} - {response.text}")
