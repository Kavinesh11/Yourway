# fedex_route_optimizer/api_connectors/base_connector.py
"""
Base API connector class that defines common functionality for all API connectors.
"""

import logging
import requests
import time
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class BaseAPIConnector:
    """Base class for API connectors with common functionality."""
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 0.1  # seconds
    
    def _make_request(self, endpoint: str, method: str = "GET", 
                     params: Optional[Dict[str, Any]] = None, 
                     data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Make a request to the API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body data
            headers: Request headers
            
        Returns:
            API response as dictionary
        """
        # Apply rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        
        # Prepare request
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if not headers:
            headers = {}
        
        # Include API key in parameters if provided
        if self.api_key and params:
            params["key"] = self.api_key
        elif self.api_key:
            params = {"key": self.api_key}
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                headers=headers,
                timeout=self.timeout
            )
            self.last_request_time = time.time()
            
            # Check for errors
            response.raise_for_status()
            
            # Return response
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

# fedex_route_optimizer/api_connectors/tomtom_connector.py
"""
TomTom API connector for real-time traffic data.
"""

import logging
from typing import Dict, Any, List, Tuple
from .base_connector import BaseAPIConnector

logger = logging.getLogger(__name__)

class TomTomAPI(BaseAPIConnector):
    """TomTom API client for routing and traffic data."""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://api.tomtom.com/",
            timeout=30
        )
    
    def get_route(self, origin: Tuple[float, float], destination: Tuple[float, float], 
                  waypoints: List[Tuple[float, float]] = None, 
                  vehicle_type: str = "car", 
                  departure_time: str = "now",
                  traffic: bool = True) -> Dict[str, Any]:
        """
        Get route information between points.
        
        Args:
            origin: Origin coordinates (latitude, longitude)
            destination: Destination coordinates (latitude, longitude)
            waypoints: List of waypoint coordinates
            vehicle_type: Type of vehicle
            departure_time: Departure time (ISO format or "now")
            traffic: Include traffic information
            
        Returns:
            Route information
        """
        # Format coordinates
        origin_str = f"{origin[1]},{origin[0]}"  # TomTom expects lon,lat format
        destination_str = f"{destination[1]},{destination[0]}"
        
        # Format waypoints if provided
        waypoints_str = ""
        if waypoints:
            waypoints_str = ":" + ":".join([f"{wp[1]},{wp[0]}" for wp in waypoints])
            
        # Build route coordinates string
        route_str = f"{origin_str}{waypoints_str}:{destination_str}"
        
        # Prepare parameters
        params = {
            "routeType": "fastest",
            "traffic": str(traffic).lower(),
            "vehicleHeading": 0,
            "sectionType": "traffic",
            "report": "effectiveSettings",
            "routeRepresentation": "summaryOnly",
            "computeBestOrder": "true",
            "computeTravelTimeFor": "all"
        }
        
        # Add vehicle parameters based on type
        if vehicle_type in ["truck", "delivery"]:
            params.update({
                "vehicleMaxSpeed": 90,
                "vehicleWeight": 3500,  # kg
                "vehicleAxleWeight": 1500,  # kg
                "vehicleLength": 5.5,  # meters
                "vehicleWidth": 2.5,  # meters
                "vehicleHeight": 2.8,  # meters
            })
        
        # Make API request
        endpoint = f"routing/1/calculateRoute/{route_str}/json"
        response = self._make_request(endpoint, params=params)
        
        return response
    
    def get_traffic_flow(self, area: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Get traffic flow information for an area.
        
        Args:
            area: List of coordinates defining the area
            
        Returns:
            Traffic flow information
        """
        # Format area coordinates
        bbox = f"{min(p[1] for p in area)},{min(p[0] for p in area)}," \
               f"{max(p[1] for p in area)},{max(p[0] for p in area)}"
        
        # Make API request
        endpoint = "traffic/services/4/flowSegmentData/relative0/10/json"
        params = {"bbox": bbox, "zoom": 10}
        response = self._make_request(endpoint, params=params)
        
        return response
    
    def get_traffic_incidents(self, area: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Get traffic incidents for an area.
        
        Args:
            area: List of coordinates defining the area
            
        Returns:
            Traffic incidents information
        """
        # Format area coordinates
        bbox = f"{min(p[1] for p in area)},{min(p[0] for p in area)}," \
               f"{max(p[1] for p in area)},{max(p[0] for p in area)}"
        
        # Make API request
        endpoint = "traffic/services/4/incidentDetails/s3/json"
        params = {"bbox": bbox}
        response = self._make_request(endpoint, params=params)
        
        return response

# fedex_route_optimizer/api_connectors/google_maps_connector.py
"""
Google Maps API connector for mapping and routing alternatives.
"""

import logging
from typing import Dict, Any, List, Tuple
from .base_connector import BaseAPIConnector

logger = logging.getLogger(__name__)

class GoogleMapsAPI(BaseAPIConnector):
    """Google Maps API client for routing."""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://maps.googleapis.com/maps/api/",
            timeout=30
        )
    
    def get_directions(self, origin: Tuple[float, float], destination: Tuple[float, float],
                      waypoints: List[Tuple[float, float]] = None,
                      mode: str = "driving",
                      departure_time: str = "now",
                      traffic_model: str = "best_guess",
                      alternatives: bool = True) -> Dict[str, Any]:
        """
        Get directions between points.
        
        Args:
            origin: Origin coordinates (latitude, longitude)
            destination: Destination coordinates (latitude, longitude)
            waypoints: List of waypoint coordinates
            mode: Transportation mode
            departure_time: Departure time
            traffic_model: Traffic prediction model
            alternatives: Return alternative routes
            
        Returns:
            Directions information
        """
        # Format coordinates
        origin_str = f"{origin[0]},{origin[1]}"
        destination_str = f"{destination[0]},{destination[1]}"
        
        # Format waypoints if provided
        waypoints_param = None
        if waypoints:
            waypoints_str = "|".join([f"{wp[0]},{wp[1]}" for wp in waypoints])
            waypoints_param = f"optimize:true|{waypoints_str}"
        
        # Prepare parameters
        params = {
            "origin": origin_str,
            "destination": destination_str,
            "mode": mode,
            "departure_time": "now" if departure_time == "now" else departure_time,
            "traffic_model": traffic_model,
            "alternatives": str(alternatives).lower(),
        }
        
        if waypoints_param:
            params["waypoints"] = waypoints_param
        
        # Make API request
        endpoint = "directions/json"
        response = self._make_request(endpoint, params=params)
        
        return response
    
    def get_distance_matrix(self, origins: List[Tuple[float, float]], 
                           destinations: List[Tuple[float, float]],
                           mode: str = "driving",
                           departure_time: str = "now") -> Dict[str, Any]:
        """
        Get distance matrix between multiple origins and destinations.
        
        Args:
            origins: List of origin coordinates
            destinations: List of destination coordinates
            mode: Transportation mode
            departure_time: Departure time
            
        Returns:
            Distance matrix information
        """
        # Format coordinates
        origins_str = "|".join([f"{o[0]},{o[1]}" for o in origins])
        destinations_str = "|".join([f"{d[0]},{d[1]}" for d in destinations])
        
        # Prepare parameters
        params = {
            "origins": origins_str,
            "destinations": destinations_str,
            "mode": mode,
            "departure_time": "now" if departure_time == "now" else departure_time,
        }
        
        # Make API request
        endpoint = "distancematrix/json"
        response = self._make_request(endpoint, params=params)
        
        return response

# fedex_route_optimizer/api_connectors/aqicn_connector.py
"""
AQICN API connector for air quality data.
"""

import logging
from typing import Dict, Any, Tuple
from .base_connector import BaseAPIConnector

logger = logging.getLogger(__name__)

class AQICNAPI(BaseAPIConnector):
    """AQICN API client for air quality data."""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://api.waqi.info/",
            timeout=30
        )
    
    def get_air_quality(self, location: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get air quality information for a location.
        
        Args:
            location: Location coordinates (latitude, longitude)
            
        Returns:
            Air quality information
        """
        # Prepare parameters
        params = {
            "token": self.api_key  # AQICN uses token instead of key
        }
        
        # Make API request
        endpoint = f"feed/geo:{location[0]};{location[1]}/"
        response = self._make_request(endpoint, params=params)
        
        return response
    
    def get_weather_forecast(self, location: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get weather forecast for a location.
        
        Args:
            location: Location coordinates (latitude, longitude)
            
        Returns:
            Weather forecast information
        """
        # First get the station ID from the location
        air_quality = self.get_air_quality(location)
        
        if air_quality.get('status') == 'ok' and 'data' in air_quality:
            station_id = air_quality['data'].get('idx')
            
            if station_id:
                # Now get the weather forecast for this station
                endpoint = f"feed/@{station_id}/forecast/"
                params = {"token": self.api_key}
                response = self._make_request(endpoint, params=params)
                return response
        
        logger.warning(f"Could not get weather forecast for location {location}")
        return {"status": "error", "data": None}

# fedex_route_optimizer/api_connectors/osrm_connector.py
"""
OSRM API connector for open-source routing.
"""

import logging
from typing import Dict, Any, List, Tuple
from .base_connector import BaseAPIConnector

logger = logging.getLogger(__name__)

class OSRMAPI(BaseAPIConnector):
    """OSRM API client for routing."""
    
    def __init__(self):
        super().__init__(
            api_key="",  # OSRM doesn't require an API key
            base_url="http://router.project-osrm.org/",
            timeout=30
        )
    
    def get_route(self, origin: Tuple[float, float], destination: Tuple[float, float],
                 waypoints: List[Tuple[float, float]] = None,
                 profile: str = "car") -> Dict[str, Any]:
        """
        Get route information between points.
        
        Args:
            origin: Origin coordinates (longitude, latitude)
            destination: Destination coordinates (longitude, latitude)
            waypoints: List of waypoint coordinates
            profile: Routing profile
            
        Returns:
            Route information
        """
        # Format coordinates - OSRM expects lon,lat format
        coordinates = [f"{origin[1]},{origin[0]}"]
        
        if waypoints:
            for wp in waypoints:
                coordinates.append(f"{wp[1]},{wp[0]}")
                
        coordinates.append(f"{destination[1]},{destination[0]}")
        
        # Format coordinates string
        coordinates_str = ";".join(coordinates)
        
        # Make API request
        endpoint = f"route/v1/{profile}/{coordinates_str}"
        params = {
            "overview": "full",
            "alternatives": "true",
            "steps": "true",
            "annotations": "true"
        }
        response = self._make_request(endpoint, params=params)
        
        return response
    
    def get_table(self, locations: List[Tuple[float, float]], profile: str = "car") -> Dict[str, Any]:
        """
        Get distance/duration matrix between multiple locations.
        
        Args:
            locations: List of coordinates
            profile: Routing profile
            
        Returns:
            Distance table information
        """
        # Format coordinates - OSRM expects lon,lat format
        coordinates = [f"{loc[1]},{loc[0]}" for loc in locations]
        coordinates_str = ";".join(coordinates)
        
        # Make API request
        endpoint = f"table/v1/{profile}/{coordinates_str}"
        params = {
            "annotations": "distance,duration"
        }
        response = self._make_request(endpoint, params=params)
        
        return response
    
    def get_trip(self, locations: List[Tuple[float, float]], profile: str = "car") -> Dict[str, Any]:
        """
        Get optimized round trip visiting all locations.
        
        Args:
            locations: List of coordinates
            profile: Routing profile
            
        Returns:
            Trip information
        """
        # Format coordinates - OSRM expects lon,lat format
        coordinates = [f"{loc[1]},{loc[0]}" for loc in locations]
        coordinates_str = ";".join(coordinates)
        
        # Make API request
        endpoint = f"trip/v1/{profile}/{coordinates_str}"
        params = {
            "roundtrip": "true",
            "source": "first",
            "destination": "last",
            "steps": "true"
        }
        response = self._make_request(endpoint, params=params)
        
        return response