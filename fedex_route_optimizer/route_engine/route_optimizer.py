# fedex_route_optimizer/route_engine/route_optimizer.py
"""
Route optimization engine that combines data from various APIs to calculate the most efficient routes.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import time
from datetime import datetime
import polyline  # For Google polyline decoding - you may need to install: pip install polyline

logger = logging.getLogger(__name__)

class RouteOptimizer:
    """Core route optimization engine."""
    
    def __init__(self, api_clients: Dict[str, Any]):
        """
        Initialize the route optimizer.
        
        Args:
            api_clients: Dictionary of API client instances
        """
        self.api_clients = api_clients
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 600  # 10 minutes
    
    def calculate_routes(self, origin: str, destination: str, vehicle_type: str = "delivery_van", 
                        optimization_priority: str = "balanced", stops: List[str] = None) -> Dict[str, Any]:
        """
        Calculate routes - this is the method your UI is calling.
        
        Args:
            origin: Origin address or location
            destination: Destination address or location
            vehicle_type: Type of vehicle
            optimization_priority: Route optimization priority (time, emissions, balanced)
            stops: List of intermediate stops
            
        Returns:
            Dictionary containing route calculation results
        """
        try:
            # Convert addresses to coordinates if needed
            origin_coords = self._geocode_address(origin)
            destination_coords = self._geocode_address(destination)
            
            # Convert stops to coordinates if provided
            stop_coords = []
            if stops:
                for stop in stops:
                    stop_coord = self._geocode_address(stop)
                    if stop_coord:
                        stop_coords.append(stop_coord)
            
            # Call the main optimization method
            result = self.optimize_route(
                origin=origin_coords,
                destination=destination_coords,
                stops=stop_coords if stop_coords else None,
                vehicle_type=vehicle_type,
                optimization_criteria=optimization_priority
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating routes: {e}")
            return {
                "status": "error",
                "message": str(e),
                "routes": [],
                "metadata": {
                    "error_details": str(e),
                    "generated_at": datetime.now().isoformat()
                }
            }
    
    def _geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert an address string to coordinates.
        This is a placeholder - you'd use a geocoding service.
        """
        # Placeholder geocoding - replace with actual geocoding service
        geocoding_map = {
            "Chennai Central Railway Station": (13.0827, 80.2707),
            "Chennai International Airport": (12.9941, 80.1709),
            # Add more locations as needed for testing
        }
        
        coords = geocoding_map.get(address)
        if coords:
            return coords
        
        # If not in our map, try to use Google Maps API if available
        try:
            if "google_maps" in self.api_clients:
                # This would be actual geocoding call
                result = self.api_clients["google_maps"].geocode(address)
                if result:
                    return (result[0]["geometry"]["location"]["lat"], 
                           result[0]["geometry"]["location"]["lng"])
        except Exception as e:
            logger.warning(f"Geocoding failed for {address}: {e}")
        
        # Return Chennai coordinates as default for demo
        return (13.0827, 80.2707)
    
    def optimize_route(self, origin: Tuple[float, float], destination: Tuple[float, float],
                      stops: List[Tuple[float, float]] = None,
                      vehicle_type: str = "delivery_van",
                      departure_time: str = "now",
                      optimization_criteria: str = "balanced",
                      max_alternatives: int = 3) -> Dict[str, Any]:
        """
        Find the optimal route based on multiple criteria.
        
        Args:
            origin: Origin point coordinates (latitude, longitude)
            destination: Destination point coordinates
            stops: List of intermediate stops
            vehicle_type: Type of vehicle
            departure_time: Departure time
            optimization_criteria: Route optimization criteria (time, emissions, balanced)
            max_alternatives: Maximum number of alternative routes to return
            
        Returns:
            Dictionary containing optimized route information
        """
        logger.info(f"Optimizing route from {origin} to {destination} with {len(stops) if stops else 0} stops")
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(origin, destination, stops, vehicle_type, optimization_criteria)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info("Returning cached route result")
                return cached_result
            
            # Get real-time traffic data for the route area
            route_area = self._get_route_area(origin, destination, stops)
            traffic_data = self._get_traffic_data(route_area)
            
            # Get weather data for the route area
            weather_data = self._get_weather_data(route_area)
            
            # Get primary route options (using TomTom for traffic-aware routing)
            tomtom_routes = self._get_tomtom_routes(origin, destination, stops, vehicle_type, departure_time)
            
            # Get alternative route options (using Google Maps for comparison)
            gmaps_routes = self._get_google_routes(origin, destination, stops, vehicle_type, departure_time)
            
            # Get open-source routes (using OSRM for baseline comparison)
            osrm_routes = self._get_osrm_routes(origin, destination, stops, vehicle_type)
            
            # If no routes from APIs, create a dummy route for demo
            if not tomtom_routes and not gmaps_routes and not osrm_routes:
                dummy_routes = self._create_dummy_routes(origin, destination, stops)
                all_routes = self._normalize_routes(dummy_routes)
            else:
                # Combine and normalize route data from different providers
                all_routes = self._normalize_routes(tomtom_routes, gmaps_routes, osrm_routes)
            
            # Calculate emissions for each route
            routes_with_emissions = self._calculate_emissions(all_routes, vehicle_type)
            
            # Score and rank routes based on optimization criteria
            scored_routes = self._score_routes(routes_with_emissions, optimization_criteria)
            
            # Limit the number of alternatives
            final_routes = scored_routes[:max_alternatives]
            
            # Prepare the response
            result = {
                "status": "success",
                "query": {
                    "origin": origin,
                    "destination": destination,
                    "stops": stops,
                    "vehicle_type": vehicle_type,
                    "optimization_criteria": optimization_criteria
                },
                "routes": final_routes,
                "metadata": {
                    "traffic_conditions": self._summarize_traffic(traffic_data),
                    "weather_conditions": self._summarize_weather(weather_data),
                    "route_count": len(final_routes),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Cache the result
            self._add_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in optimize_route: {e}")
            return {
                "status": "error",
                "message": str(e),
                "routes": [],
                "metadata": {
                    "error_details": str(e),
                    "generated_at": datetime.now().isoformat()
                }
            }
    
    def _create_dummy_routes(self, origin, destination, stops=None) -> List[Dict[str, Any]]:
        """Create dummy routes for demo purposes when APIs are not available."""
        import math
        
        # Calculate approximate distance using Haversine formula
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # Earth's radius in meters
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_phi / 2) ** 2 + 
                 math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        
        base_distance = haversine_distance(origin[0], origin[1], destination[0], destination[1])
        
        # Create multiple route alternatives
        routes = []
        route_variants = [
            {"name": "Fastest Route", "distance_factor": 1.0, "time_factor": 1.0},
            {"name": "Shortest Route", "distance_factor": 0.95, "time_factor": 1.1},
            {"name": "Eco-Friendly Route", "distance_factor": 1.05, "time_factor": 1.05}
        ]
        
        for i, variant in enumerate(route_variants):
            distance = int(base_distance * variant["distance_factor"])
            # Assume average speed of 40 km/h in city
            duration = int((distance / 1000) * 3600 / 40 * variant["time_factor"])
            
            route = {
                "provider": "demo",
                "route_id": f"demo-{i}",
                "summary": {
                    "lengthInMeters": distance,
                    "travelTimeInSeconds": duration,
                    "trafficDelayInSeconds": max(0, int(duration * 0.1))  # 10% traffic delay
                },
                "geometry": [
                    {"latitude": origin[0], "longitude": origin[1]},
                    {"latitude": destination[0], "longitude": destination[1]}
                ],
                "legs": [],
                "raw": {"route_name": variant["name"]}
            }
            routes.append(route)
        
        return routes
    
    def _generate_cache_key(self, origin, destination, stops, vehicle_type, criteria) -> str:
        """Generate a unique cache key for a route request."""
        stops_str = "" if not stops else "-".join([f"{s[0]}:{s[1]}" for s in stops])
        return f"{origin[0]}:{origin[1]}-{destination[0]}:{destination[1]}-{stops_str}-{vehicle_type}-{criteria}"
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a route result from cache if valid."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.cache_ttl:
                return entry["data"]
        return None
    
    def _add_to_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Add a route result to cache."""
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
    
    def _get_route_area(self, origin, destination, stops=None) -> List[Tuple[float, float]]:
        """Calculate the geographic area covering all route points."""
        points = [origin, destination]
        if stops:
            points.extend(stops)
            
        # Add some padding to the bounding box
        padding = 0.05  # approximately 5km at equator
        
        min_lat = min(p[0] for p in points) - padding
        max_lat = max(p[0] for p in points) + padding
        min_lng = min(p[1] for p in points) - padding
        max_lng = max(p[1] for p in points) + padding
        
        return [
            (min_lat, min_lng),  # Southwest
            (min_lat, max_lng),  # Southeast
            (max_lat, max_lng),  # Northeast
            (max_lat, min_lng)   # Northwest
        ]
    
    def _get_traffic_data(self, area: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Get traffic data for the route area."""
        try:
            if "tomtom" in self.api_clients:
                return self.api_clients["tomtom"].get_traffic_flow(area)
            else:
                return {"status": "demo", "message": "Demo mode - no real traffic data"}
        except Exception as e:
            logger.warning(f"Failed to get traffic data: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_weather_data(self, area: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Get weather data for the route area."""
        try:
            if "aqicn" in self.api_clients:
                # Use the center point of the area for weather
                center_lat = sum(p[0] for p in area) / len(area)
                center_lng = sum(p[1] for p in area) / len(area)
                
                return self.api_clients["aqicn"].get_air_quality((center_lat, center_lng))
            else:
                return {"status": "demo", "data": {"aqi": 45}, "message": "Demo mode"}
        except Exception as e:
            logger.warning(f"Failed to get weather data: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_tomtom_routes(self, origin, destination, stops, vehicle_type, departure_time) -> List[Dict[str, Any]]:
        """Get routes from TomTom API."""
        try:
            if "tomtom" not in self.api_clients:
                return []
                
            response = self.api_clients["tomtom"].get_route(
                origin=origin,
                destination=destination,
                waypoints=stops,
                vehicle_type=vehicle_type,
                departure_time=departure_time,
                traffic=True
            )
            
            if response.get("routes"):
                return [
                    {
                        "provider": "tomtom",
                        "route_id": f"tt-{i}",
                        "summary": route.get("summary", {}),
                        "geometry": route.get("legs", [{}])[0].get("points", []),
                        "legs": route.get("legs", []),
                        "raw": route
                    }
                    for i, route in enumerate(response.get("routes", []))
                ]
            
            return []
        except Exception as e:
            logger.warning(f"Failed to get TomTom routes: {e}")
            return []
    
    def _get_google_routes(self, origin, destination, stops, vehicle_type, departure_time) -> List[Dict[str, Any]]:
        """Get routes from Google Maps API."""
        try:
            if "google_maps" not in self.api_clients:
                return []
                
            response = self.api_clients["google_maps"].get_directions(
                origin=origin,
                destination=destination,
                waypoints=stops,
                mode="driving",
                departure_time=departure_time,
                alternatives=True
            )
            
            if response.get("routes"):
                return [
                    {
                        "provider": "google",
                        "route_id": f"gm-{i}",
                        "summary": {
                            "lengthInMeters": route.get("legs", [{}])[0].get("distance", {}).get("value", 0),
                            "travelTimeInSeconds": route.get("legs", [{}])[0].get("duration", {}).get("value", 0),
                            "trafficDelayInSeconds": max(0, 
                                route.get("legs", [{}])[0].get("duration_in_traffic", {}).get("value", 0) - 
                                route.get("legs", [{}])[0].get("duration", {}).get("value", 0))
                        },
                        "geometry": self._decode_google_polyline(route.get("overview_polyline", {}).get("points", "")),
                        "legs": route.get("legs", []),
                        "raw": route
                    }
                    for i, route in enumerate(response.get("routes", []))
                ]
            
            return []
        except Exception as e:
            logger.warning(f"Failed to get Google Maps routes: {e}")
            return []
    
    def _get_osrm_routes(self, origin, destination, stops, vehicle_type) -> List[Dict[str, Any]]:
        """Get routes from OSRM API."""
        try:
            if "osrm" not in self.api_clients:
                return []
                
            response = self.api_clients["osrm"].get_route(
                origin=origin,
                destination=destination,
                waypoints=stops,
                profile="car"  # OSRM uses 'car', 'bike', 'foot'
            )
            
            if response.get("routes"):
                return [
                    {
                        "provider": "osrm",
                        "route_id": f"osrm-{i}",
                        "summary": {
                            "lengthInMeters": route.get("distance", 0),
                            "travelTimeInSeconds": route.get("duration", 0),
                            "trafficDelayInSeconds": 0  # OSRM doesn't provide traffic delays
                        },
                        "geometry": self._decode_osrm_geometry(route.get("geometry", "")),
                        "legs": route.get("legs", []),
                        "raw": route
                    }
                    for i, route in enumerate(response.get("routes", []))
                ]
            
            return []
        except Exception as e:
            logger.warning(f"Failed to get OSRM routes: {e}")
            return []
    
    def _normalize_routes(self, *route_lists) -> List[Dict[str, Any]]:
        """Normalize route data from different providers to a common format."""
        all_routes = []
        
        for routes in route_lists:
            if not routes:
                continue
                
            for route in routes:
                # Extract common route information
                normalized_route = {
                    "id": route["route_id"],
                    "provider": route["provider"],
                    "distance_meters": route["summary"].get("lengthInMeters", 0),
                    "duration_seconds": route["summary"].get("travelTimeInSeconds", 0),
                    "traffic_delay_seconds": route["summary"].get("trafficDelayInSeconds", 0),
                    "geometry": route.get("geometry", []),
                    "raw_data": route.get("raw", {})
                }
                
                all_routes.append(normalized_route)
        
        return all_routes
    
    def _calculate_emissions(self, routes: List[Dict[str, Any]], vehicle_type: str) -> List[Dict[str, Any]]:
        """
        Calculate estimated emissions for each route.
        Note: This would be replaced with a call to the emissions calculator module.
        """
        # Placeholder for emissions calculation
        # In a real implementation, this would use the EmissionsCalculator class
        for route in routes:
            # Simple placeholder calculation - would be replaced with actual emissions model
            distance_km = route["distance_meters"] / 1000
            
            # Very simplified emissions model
            if vehicle_type == "delivery_van":
                emissions_kg = distance_km * 0.2  # kg CO2 per km
            elif vehicle_type == "cargo_truck":
                emissions_kg = distance_km * 0.5  # kg CO2 per km
            elif vehicle_type == "electric_van":
                emissions_kg = distance_km * 0.05  # kg CO2 per km
            else:
                emissions_kg = distance_km * 0.2  # default
            
            route["emissions_kg_co2"] = round(emissions_kg, 2)
        
        return routes
    
    def _score_routes(self, routes: List[Dict[str, Any]], criteria: str) -> List[Dict[str, Any]]:
        """Score and rank routes based on the optimization criteria."""
        if not routes:
            return routes
            
        # Calculate score weights based on criteria
        if criteria == "time":
            time_weight = 0.8
            emissions_weight = 0.2
        elif criteria == "emissions":
            time_weight = 0.2
            emissions_weight = 0.8
        else:  # balanced
            time_weight = 0.5
            emissions_weight = 0.5
        
        # Find min/max values for normalization
        min_time = min(r["duration_seconds"] for r in routes)
        max_time = max(r["duration_seconds"] for r in routes)
        time_range = max(1, max_time - min_time)  # Avoid division by zero
        
        min_emissions = min(r["emissions_kg_co2"] for r in routes)
        max_emissions = max(r["emissions_kg_co2"] for r in routes)
        emissions_range = max(0.1, max_emissions - min_emissions)  # Avoid division by zero
        
        # Calculate scores
        for route in routes:
            time_score = 1 - ((route["duration_seconds"] - min_time) / time_range) if time_range > 0 else 1
            emissions_score = 1 - ((route["emissions_kg_co2"] - min_emissions) / emissions_range) if emissions_range > 0 else 1
            
            # Combined weighted score (0-100)
            route["score"] = int((time_weight * time_score + emissions_weight * emissions_score) * 100)
            
            # Add readable descriptions based on scores
            if route["score"] >= 80:
                route["recommendation"] = "Highly Recommended"
            elif route["score"] >= 60:
                route["recommendation"] = "Recommended"
            else:
                route["recommendation"] = "Alternative Option"
        
        # Sort routes by score (descending)
        return sorted(routes, key=lambda r: r["score"], reverse=True)
    
    def _summarize_traffic(self, traffic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize traffic conditions."""
        if traffic_data.get("status") == "error":
            return {"status": "unknown", "description": "Traffic data unavailable"}
        
        if traffic_data.get("status") == "demo":
            return {"status": "normal", "description": "Normal traffic conditions (demo mode)"}
        
        # Extract and summarize traffic data
        # This is a simplified example - actual implementation would analyze the data
        return {
            "status": "normal",
            "description": "Normal traffic conditions",
            "average_flow": "moderate"
        }
    
    def _summarize_weather(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize weather conditions."""
        if weather_data.get("status") == "error":
            return {"status": "unknown", "description": "Weather data unavailable"}
        
        # Extract and summarize weather data
        # This is a simplified example - actual implementation would analyze the data
        if "data" in weather_data and weather_data["data"] is not None:
            aqi = weather_data["data"].get("aqi", 45)
            
            if aqi < 50:
                status = "good"
                description = "Good air quality, no impact on transportation"
            elif aqi < 100:
                status = "moderate"
                description = "Moderate air quality, minimal impact"
            else:
                status = "poor"
                description = "Poor air quality, may affect visibility"
                
            return {
                "status": status,
                "description": description,  
                "aqi": aqi
            }
        
        return {"status": "good", "description": "Good weather conditions (demo mode)", "aqi": 45}
    
    def _decode_google_polyline(self, polyline_str: str) -> List[Dict[str, float]]:
        """Decode Google Maps polyline format."""
        try:
            # Use the polyline library to decode
            coords = polyline.decode(polyline_str)
            return [{"latitude": lat, "longitude": lng} for lat, lng in coords]
        except Exception as e:
            logger.warning(f"Failed to decode polyline: {e}")
            return []
    
    def _decode_osrm_geometry(self, geometry: str) -> List[Dict[str, float]]:
        """Decode OSRM geometry format."""
        try:
            # OSRM also uses polyline encoding
            coords = polyline.decode(geometry)
            return [{"latitude": lat, "longitude": lng} for lat, lng in coords]
        except Exception as e:
            logger.warning(f"Failed to decode OSRM geometry: {e}")
            return []