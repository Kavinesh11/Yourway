import os
import json
import logging
from datetime import datetime

class EmissionsCalculator:
    """
    Class to calculate emissions for different routes and vehicle types.
    Uses emission factors based on vehicle type, speed, gradient, and other factors.
    """
    
    def __init__(self, settings=None):
        self.settings = settings
        self.logger = logging.getLogger("EmissionsCalculator")
        
        # Load emission factors from configuration
        self.emission_factors = self._load_emission_factors()
        
    def _load_emission_factors(self):
        """Load emission factors from config file or use defaults."""
        try:
            # Try to load from config file
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            config_file = os.path.join(config_dir, "emission_factors.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                # Use default emission factors if file not found
                return {
                    "Delivery Van": {
                        "base_emission_rate": 275,  # g CO2 per km
                        "fuel_efficiency": 12,  # mpg
                        "payload_factor": 0.05  # % increase per 100kg
                    },
                    "Box Truck": {
                        "base_emission_rate": 450,
                        "fuel_efficiency": 8,
                        "payload_factor": 0.08
                    },
                    "Semi-Truck": {
                        "base_emission_rate": 900,
                        "fuel_efficiency": 6,
                        "payload_factor": 0.1
                    },
                    "Electric Vehicle": {
                        "base_emission_rate": 50,  # Lower due to no direct emissions
                        "fuel_efficiency": 100,  # equivalent mpg (for calculation)
                        "payload_factor": 0.03
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error loading emission factors: {str(e)}")
            # Return default emission factors
            return {
                "Delivery Van": {"base_emission_rate": 275, "fuel_efficiency": 12, "payload_factor": 0.05},
                "Box Truck": {"base_emission_rate": 450, "fuel_efficiency": 8, "payload_factor": 0.08},
                "Semi-Truck": {"base_emission_rate": 900, "fuel_efficiency": 6, "payload_factor": 0.1},
                "Electric Vehicle": {"base_emission_rate": 50, "fuel_efficiency": 100, "payload_factor": 0.03}
            }
    
    def calculate_emissions(self, distance_miles, vehicle_type, avg_speed_mph=55, gradient=0, payload_kg=0, 
                          traffic_congestion=0, weather_conditions="normal"):
        """
        Calculate CO2 emissions for a given route and vehicle.
        
        Args:
            distance_miles: Distance in miles
            vehicle_type: Type of vehicle (must match keys in emission_factors)
            avg_speed_mph: Average speed in mph
            gradient: Average gradient of the route (percentage)
            payload_kg: Payload weight in kg
            traffic_congestion: Traffic congestion factor (0-1 scale)
            weather_conditions: Weather conditions affecting emissions
            
        Returns:
            Estimated CO2 emissions in kg
        """
        try:
            # Get vehicle-specific emission factors
            if vehicle_type not in self.emission_factors:
                self.logger.warning(f"Unknown vehicle type: {vehicle_type}, using Delivery Van as default")
                vehicle_type = "Delivery Van"
                
            vehicle_factors = self.emission_factors[vehicle_type]
            
            # Base emission calculation (convert miles to km)
            distance_km = distance_miles * 1.60934
            base_emissions = distance_km * vehicle_factors["base_emission_rate"]
            
            # Apply adjustments
            
            # Speed adjustment (optimal efficiency is typically around 55-60 mph)
            if avg_speed_mph < 30:
                speed_factor = 1.2  # Higher emissions at very low speeds
            elif avg_speed_mph > 75:
                speed_factor = 1.15  # Higher emissions at very high speeds
            else:
                speed_factor = 1.0
                
            # Gradient adjustment
            gradient_factor = 1.0 + (abs(gradient) * 0.02)  # 2% increase per gradient point
            
            # Payload adjustment
            payload_factor = 1.0 + (payload_kg / 100 * vehicle_factors["payload_factor"])
            
            # Traffic congestion adjustment
            traffic_factor = 1.0 + (traffic_congestion * 0.3)  # Up to 30% increase in heavy traffic
            
            # Weather adjustment
            weather_factor = 1.0
            if weather_conditions.lower() == "rain":
                weather_factor = 1.05
            elif weather_conditions.lower() == "snow":
                weather_factor = 1.1
            elif weather_conditions.lower() == "strong wind":
                weather_factor = 1.08
                
            # Calculate final emissions (in grams)
            total_emissions_g = base_emissions * speed_factor * gradient_factor * payload_factor * traffic_factor * weather_factor
            
            # Convert to kg
            total_emissions_kg = total_emissions_g / 1000
            
            return total_emissions_kg
        
        except Exception as e:
            self.logger.error(f"Error calculating emissions: {str(e)}")
            # Return a default estimation
            return distance_miles * 0.4  # Simple fallback estimate
    
    def get_vehicle_baseline_emissions(self, fuel_type):
        """
        Get baseline emissions for a vehicle based on fuel type.
        
        Args:
            fuel_type: Type of fuel used
            
        Returns:
            Baseline CO2 emissions in g/km
        """
        # Default emissions by fuel type (g CO2/km)
        baseline_emissions = {
            "Gasoline": 210,
            "Diesel": 180,
            "Electric": 50,  # Based on average electricity generation mix
            "Hybrid": 130,
            "Natural Gas": 160
        }
        
        return baseline_emissions.get(fuel_type, 200)  # Default if fuel type not found
    
    def compare_route_emissions(self, routes, vehicle_type):
        """
        Compare emissions between multiple routes.
        
        Args:
            routes: List of route dictionaries with distance and other attributes
            vehicle_type: Type of vehicle to use for comparison
            
        Returns:
            List of routes with emissions data added
        """
        for route in routes:
            emissions = self.calculate_emissions(
                route['distance'], 
                vehicle_type,
                route.get('avg_speed', 55),
                route.get('gradient', 0),
                route.get('traffic_congestion', 0),
                route.get('weather_conditions', 'normal')
            )
            route['emissions'] = emissions
            route['emissions_text'] = f"{emissions:.2f} kg CO2"
            
        return routes
    
    def generate_emissions_report(self, route, vehicle_type):
        """
        Generate a detailed emissions report for a specific route.
        
        Args:
            route: Dictionary containing route information
            vehicle_type: Type of vehicle used
            
        Returns:
            String containing the emissions report
        """
        emissions = self.calculate_emissions(
            route['distance'],
            vehicle_type,
            route.get('avg_speed', 55),
            route.get('gradient', 0)
        )
        
        # Get vehicle emission factors
        factors = self.emission_factors.get(vehicle_type, self.emission_factors["Delivery Van"])
        
        report = f"EMISSIONS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += f"{'='*50}\n\n"
        report += f"Route: {route.get('origin_name', 'Origin')} to {route.get('destination_name', 'Destination')}\n"
        report += f"Distance: {route['distance']:.1f} miles ({route['distance'] * 1.60934:.1f} km)\n"
        report += f"Vehicle Type: {vehicle_type}\n\n"
        
        report += f"ESTIMATED EMISSIONS\n"
        report += f"{'-'*50}\n"
        report += f"Total CO2: {emissions:.2f} kg\n"
        report += f"CO2 per mile: {emissions / route['distance']:.2f} kg\n"
        report += f"CO2 per km: {emissions / (route['distance'] * 1.60934):.2f} kg\n\n"
        
        report += f"BASELINE INFORMATION\n"
        report += f"{'-'*50}\n"
        report += f"Base emission rate: {factors['base_emission_rate']} g CO2/km\n"
        report += f"Fuel efficiency: {factors['fuel_efficiency']} mpg\n\n"
        
        report += f"ENVIRONMENTAL IMPACT\n"
        report += f"{'-'*50}\n"
        report += f"Trees needed to offset: {emissions / 21:.1f} trees (yearly absorption)\n"
        
        # Compare with alternatives
        if vehicle_type != "Electric Vehicle":
            ev_emissions = self.calculate_emissions(route['distance'], "Electric Vehicle")
            report += f"\nCOMPARISON\n"
            report += f"{'-'*50}\n"
            report += f"Electric vehicle emissions: {ev_emissions:.2f} kg CO2\n"
            report += f"Potential reduction: {emissions - ev_emissions:.2f} kg CO2 ({((emissions - ev_emissions) / emissions) * 100:.1f}%)\n"
        
        return report