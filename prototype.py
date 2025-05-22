# fedex_route_optimizer/emissions/emissions_calculator.py
"""
Module for calculating vehicle emissions based on route data and vehicle characteristics.
"""

import logging
from typing import Dict, Any

from config import settings  # ✅ Fixed: Changed from relative to absolute import

logger = logging.getLogger(__name__)

def calculate_emissions(distance_meters: float, vehicle_config: Dict[str, Any]) -> float:
    """
    Calculate emissions based on distance and vehicle configuration.

    Args:
        distance_meters: Distance in meters
        vehicle_config: Dictionary with vehicle details (fuel type, efficiency)

    Returns:
        Emissions in kilograms of CO2
    """
    try:
        distance_km = distance_meters / 1000.0

        if "fuel_efficiency_l_per_100km" in vehicle_config:
            # Internal combustion vehicle
            liters_used = (distance_km * vehicle_config["fuel_efficiency_l_per_100km"]) / 100.0
            fuel_type = vehicle_config.get("fuel_type", "diesel")
            emission_factor = settings.get_emission_factor(fuel_type)
            emissions = liters_used * emission_factor
        elif "energy_efficiency_kwh_per_100km" in vehicle_config:
            # Electric vehicle
            kwh_used = (distance_km * vehicle_config["energy_efficiency_kwh_per_100km"]) / 100.0
            emission_factor = settings.get_emission_factor("electric")
            emissions = kwh_used * emission_factor
        else:
            logger.warning("Invalid vehicle configuration for emissions calculation.")
            return 0.0

        return emissions

    except Exception as e:
        logger.error(f"Error calculating emissions: {e}")
        return 0.0
