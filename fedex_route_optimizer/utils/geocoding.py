import requests
import json
import os
import sys
import time
from urllib.parse import quote

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger_setup import setup_logger
from utils.data_validator import DataValidator

class GeocodingService:
    """
    Service for converting addresses to geographic coordinates (geocoding)
    and geographic coordinates to addresses (reverse geocoding).
    
    Supports multiple geocoding providers and handles API key management and error handling.
    """
    
    def __init__(self):
        """Initialize the GeocodingService with default settings and logger."""
        self.logger = setup_logger("GeocodingService")
        self.data_validator = DataValidator()
        
        # Load API keys from config
        self.api_keys = self._load_api_keys()
        
        # Set primary and fallback providers
        self.primary_provider = "google"
        self.fallback_provider = "tomtom"
        
        # Cache for geocoding results to reduce API calls
        self.geocode_cache = {}
        
    def _load_api_keys(self):
        """
        Load API keys from config file.
        
        Returns:
            dict: Dictionary containing API keys for different providers
        """
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
                "settings.json"
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get("api_keys", {})
            
            self.logger.warning("Config file not found, using empty API keys")
            return {}
            
        except Exception as e:
            self.logger.error(f"Error loading API keys: {str(e)}")
            return {}
    
    def geocode(self, address, provider=None):
        """
        Convert an address to geographic coordinates.
        
        Args:
            address (str): The address to geocode
            provider (str, optional): The geocoding provider to use
                                     (google, tomtom, osm, or None for default)
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding failed
        """
        if not self.data_validator.validate_location(address):
            self.logger.warning(f"Invalid address format: {address}")
            return None
            
        # Check cache first
        cache_key = f"{address.lower()}:{provider or self.primary_provider}"
        if cache_key in self.geocode_cache:
            self.logger.debug(f"Using cached geocoding result for {address}")
            return self.geocode_cache[cache_key]
            
        # Use specified provider or default to primary
        active_provider = provider or self.primary_provider
        
        # Try primary provider
        coords = self._geocode_with_provider(address, active_provider)
        
        # If primary fails, try fallback
        if coords is None and active_provider == self.primary_provider:
            self.logger.info(f"Primary geocoding provider failed, trying fallback")
            coords = self._geocode_with_provider(address, self.fallback_provider)
            
        # If both fail, try OpenStreetMap as last resort
        if coords is None and active_provider != "osm" and self.fallback_provider != "osm":
            self.logger.info("Trying OpenStreetMap as last resort")
            coords = self._geocode_with_provider(address, "osm")
        
        # Cache the result if successful
        if coords is not None:
            self.geocode_cache[cache_key] = coords
            
        return coords
    
    def _geocode_with_provider(self, address, provider):
        """
        Geocode an address using a specific provider.
        
        Args:
            address (str): The address to geocode
            provider (str): The geocoding provider to use
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding failed
        """
        try:
            if provider == "google":
                return self._geocode_google(address)
            elif provider == "tomtom":
                return self._geocode_tomtom(address)
            elif provider == "osm":
                return self._geocode_osm(address)
            else:
                self.logger.warning(f"Unknown geocoding provider: {provider}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error geocoding with {provider}: {str(e)}")
            return None
    
    def _geocode_google(self, address):
        """
        Geocode an address using Google Maps API.
        
        Args:
            address (str): The address to geocode
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding failed
        """
        api_key = self.api_keys.get("google_maps")
        if not api_key:
            self.logger.warning("Google Maps API key not found")
            return None
            
        encoded_address = quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            self.logger.warning(f"Google geocoding API returned status code {response.status_code}")
            return None
            
        data = response.json()
        
        if data["status"] != "OK":
            self.logger.warning(f"Google geocoding API returned status: {data['status']}")
            return None
            
        if not data["results"]:
            self.logger.warning("Google geocoding API returned no results")
            return None
            
        location = data["results"][0]["geometry"]["location"]
        return (location["lat"], location["lng"])
    
    def _geocode_tomtom(self, address):
        """
        Geocode an address using TomTom API.
        
        Args:
            address (str): The address to geocode
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding failed
        """
        api_key = self.api_keys.get("tomtom")
        if not api_key:
            self.logger.warning("TomTom API key not found")
            return None
            
        encoded_address = quote(address)
        url = f"https://api.tomtom.com/search/2/geocode/{encoded_address}.json?key={api_key}"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            self.logger.warning(f"TomTom geocoding API returned status code {response.status_code}")
            return None
            
        data = response.json()
        
        if not data.get("results"):
            self.logger.warning("TomTom geocoding API returned no results")
            return None
            
        position = data["results"][0]["position"]
        return (position["lat"], position["lon"])
    
    def _geocode_osm(self, address):
        """
        Geocode an address using OpenStreetMap Nominatim API.
        This is a free service with strict usage limits.
        
        Args:
            address (str): The address to geocode
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding failed
        """
        encoded_address = quote(address)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_address}&format=json&limit=1"
        
        # Add a user-agent as required by OSM's usage policy
        headers = {
            "User-Agent": "FedExRouteOptimizer/1.0"
        }
        
        # Respect OSM usage policy (max 1 request per second)
        time.sleep(1)
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            self.logger.warning(f"OSM geocoding API returned status code {response.status_code}")
            return None
            
        data = response.json()
        
        if not data:
            self.logger.warning("OSM geocoding API returned no results")
            return None
            
        return (float(data[0]["lat"]), float(data[0]["lon"]))
    
    def reverse_geocode(self, lat, lon, provider=None):
        """
        Convert geographic coordinates to an address.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            provider (str, optional): The geocoding provider to use
                                     (google, tomtom, osm, or None for default)
            
        Returns:
            str: The formatted address or None if reverse geocoding failed
        """
        if not self.data_validator.validate_coordinates(lat, lon):
            self.logger.warning(f"Invalid coordinates: lat={lat}, lon={lon}")
            return None
            
        # Cache key for reverse geocoding
        cache_key = f"rev:{lat},{lon}:{provider or self.primary_provider}"
        if cache_key in self.geocode_cache:
            self.logger.debug(f"Using cached reverse geocoding result for {lat},{lon}")
            return self.geocode_cache[cache_key]
            
        # Use specified provider or default to primary
        active_provider = provider or self.primary_provider
        
        # Try primary provider
        address = self._reverse_geocode_with_provider(lat, lon, active_provider)
        
        # If primary fails, try fallback
        if address is None and active_provider == self.primary_provider:
            self.logger.info(f"Primary reverse geocoding provider failed, trying fallback")
            address = self._reverse_geocode_with_provider(lat, lon, self.fallback_provider)
            
        # If both fail, try OpenStreetMap as last resort
        if address is None and active_provider != "osm" and self.fallback_provider != "osm":
            self.logger.info("Trying OpenStreetMap as last resort for reverse geocoding")
            address = self._reverse_geocode_with_provider(lat, lon, "osm")
        
        # Cache the result if successful
        if address is not None:
            self.geocode_cache[cache_key] = address
            
        return address
    
    def _reverse_geocode_with_provider(self, lat, lon, provider):
        """
        Reverse geocode coordinates using a specific provider.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            provider (str): The geocoding provider to use
            
        Returns:
            str: The formatted address or None if reverse geocoding failed
        """
        try:
            if provider == "google":
                return self._reverse_geocode_google(lat, lon)
            elif provider == "tomtom":
                return self._reverse_geocode_tomtom(lat, lon)
            elif provider == "osm":
                return self._reverse_geocode_osm(lat, lon)
            else:
                self.logger.warning(f"Unknown geocoding provider: {provider}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error reverse geocoding with {provider}: {str(e)}")
            return None
    
    def _reverse_geocode_google(self, lat, lon):
        """
        Reverse geocode coordinates using Google Maps API.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: The formatted address or None if reverse geocoding failed
        """
        api_key = self.api_keys.get("google_maps")
        if not api_key:
            self.logger.warning("Google Maps API key not found")
            return None
            
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            self.logger.warning(f"Google reverse geocoding API returned status code {response.status_code}")
            return None
            
        data = response.json()
        
        if data["status"] != "OK":
            self.logger.warning(f"Google reverse geocoding API returned status: {data['status']}")
            return None
            
        if not data["results"]:
            self.logger.warning("Google reverse geocoding API returned no results")
            return None
            
        return data["results"][0]["formatted_address"]
    
    def _reverse_geocode_tomtom(self, lat, lon):
        """
        Reverse geocode coordinates using TomTom API.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: The formatted address or None if reverse geocoding failed
        """
        api_key = self.api_keys.get("tomtom")
        if not api_key:
            self.logger.warning("TomTom API key not found")
            return None
            
        url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json?key={api_key}"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            self.logger.warning(f"TomTom reverse geocoding API returned status code {response.status_code}")
            return None
            
        data = response.json()
        
        if not data.get("addresses"):
            self.logger.warning("TomTom reverse geocoding API returned no results")
            return None
            
        address = data["addresses"][0]["address"]
        
        # Format the address from components
        formatted_address = []
        if "streetNumber" in address:
            formatted_address.append(f"{address['streetNumber']} {address.get('streetName', '')}")
        elif "streetName" in address:
            formatted_address.append(address["streetName"])
            
        if "municipality" in address:
            formatted_address.append(address["municipality"])
            
        if "countrySubdivision" in address:
            formatted_address.append(address["countrySubdivision"])
            
        if "postalCode" in address:
            formatted_address.append(address["postalCode"])
            
        if "country" in address:
            formatted_address.append(address["country"])
            
        return ", ".join(formatted_address)
    
    def _reverse_geocode_osm(self, lat, lon):
        """
        Reverse geocode coordinates using OpenStreetMap Nominatim API.
        This is a free service with strict usage limits.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: The formatted address or None if reverse geocoding failed
        """
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        
        # Add a user-agent as required by OSM's usage policy
        headers = {
            "User-Agent": "FedExRouteOptimizer/1.0"
        }
        
        # Respect OSM usage policy (max 1 request per second)
        time.sleep(1)
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            self.logger.warning(f"OSM reverse geocoding API returned status code {response.status_code}")
            return None
            
        data = response.json()
        
        if "error" in data:
            self.logger.warning(f"OSM reverse geocoding API returned error: {data['error']}")
            return None
            
        return data.get("display_name")
    
    def get_distance(self, origin_lat, origin_lon, dest_lat, dest_lon):
        """
        Calculate the straight-line distance between two points.
        
        Args:
            origin_lat (float): Origin latitude
            origin_lon (float): Origin longitude
            dest_lat (float): Destination latitude
            dest_lon (float): Destination longitude
            
        Returns:
            float: Distance in kilometers or None if calculation failed
        """
        try:
            from math import radians, sin, cos, sqrt, atan2
            
            # Earth radius in kilometers
            R = 6371.0
            
            # Convert coordinates to radians
            lat1 = radians(float(origin_lat))
            lon1 = radians(float(origin_lon))
            lat2 = radians(float(dest_lat))
            lon2 = radians(float(dest_lon))
            
            # Haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            
            a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            
            distance = R * c
            
            return distance
            
        except Exception as e:
            self.logger.error(f"Error calculating distance: {str(e)}")
            return None