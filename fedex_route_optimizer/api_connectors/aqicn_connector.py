# aqicn_connector.py

import requests

def get_air_quality(lat, lon, api_token):
    """
    Fetch air quality index from AQICN API for given coordinates.
    :param lat: Latitude
    :param lon: Longitude
    :param api_token: AQICN API Token
    :return: AQI value (int)
    """
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={api_token}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "ok":
            return data["data"]["aqi"]
        else:
            raise ValueError("AQICN returned non-ok status.")
    else:
        raise Exception(f"AQICN API Error: {response.status_code} - {response.text}")
