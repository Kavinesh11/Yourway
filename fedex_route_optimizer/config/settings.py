# fedex_route_optimizer/config/settings.py
"""
Configuration module for the FedEx SMART Route Optimizer.
Handles loading and providing access to configuration settings.
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Configuration for API connections."""
    key: str
    base_url: str
    timeout: int = 30
    rate_limit: int = 100

@dataclass
class AppConfig:
    """Main application configuration."""
    api_keys: Dict[str, APIConfig]
    vehicle_models: Dict[str, Dict[str, Any]]
    emission_factors: Dict[str, float]
    default_values: Dict[str, Any]
    cache_settings: Dict[str, Any]

# Global configuration instance
_config: Optional[AppConfig] = None

def load_config(config_path: Path) -> None:
    """
    Load configuration from the specified YAML file.
    
    Args:
        config_path: Path to the configuration file
    """
    global _config
    
    try:
        with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
            
        # Process API keys - check environment variables first
        api_keys = {}
        for api_name, api_config in config_data.get('apis', {}).items():
            env_key = f"FEDEX_API_{api_name.upper()}_KEY"
            api_key = os.environ.get(env_key, api_config.get('key', ''))
            
            api_keys[api_name] = APIConfig(
                key=api_key,
                base_url=api_config.get('base_url', ''),
                timeout=api_config.get('timeout', 30),
                rate_limit=api_config.get('rate_limit', 100)
            )
            
        # Create application configuration
        _config = AppConfig(
            api_keys=api_keys,
            vehicle_models=config_data.get('vehicle_models', {}),
            emission_factors=config_data.get('emission_factors', {}),
            default_values=config_data.get('defaults', {}),
            cache_settings=config_data.get('cache', {})
        )
        
        logger.info(f"Configuration loaded successfully from {config_path}")
        
    except (yaml.YAMLError, IOError) as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

def get_api_key(api_name: str) -> str:
    """
    Get API key for the specified API.
    
    Args:
        api_name: Name of the API
        
    Returns:
        API key as string
    """
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    
    if api_name not in _config.api_keys:
        logger.warning(f"API key not found for {api_name}")
        return ""
        
    return _config.api_keys[api_name].key

def get_api_config(api_name: str) -> APIConfig:
    """
    Get complete API configuration.
    
    Args:
        api_name: Name of the API
        
    Returns:
        APIConfig object
    """
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    
    if api_name not in _config.api_keys:
        logger.warning(f"API configuration not found for {api_name}")
        return APIConfig(key="", base_url="")
        
    return _config.api_keys[api_name]

def get_vehicle_model(vehicle_type: str) -> Dict[str, Any]:
    """
    Get vehicle model configuration.
    
    Args:
        vehicle_type: Type of vehicle
        
    Returns:
        Vehicle model parameters as dictionary
    """
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    
    return _config.vehicle_models.get(vehicle_type, {})

def get_emission_factor(fuel_type: str) -> float:
    """
    Get emission factor for the specified fuel type.
    
    Args:
        fuel_type: Type of fuel
        
    Returns:
        Emission factor as float
    """
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    
    return _config.emission_factors.get(fuel_type, 0.0)

def get_default(key: str, default: Any = None) -> Any:
    """
    Get default value for the specified key.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value
    """
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    
    return _config.default_values.get(key, default)

# Example config.yaml structure for reference
EXAMPLE_CONFIG = """
apis:
  tomtom:
    key: YOUR_TOMTOM_API_KEY
    base_url: https://api.tomtom.com/routing/1/
    timeout: 30
    rate_limit: 100
  google_maps:
    key: YOUR_GOOGLE_MAPS_API_KEY
    base_url: https://maps.googleapis.com/maps/api/
  aqicn:
    key: YOUR_AQICN_API_KEY
    base_url: https://api.waqi.info/
  osrm:
    base_url: http://router.project-osrm.org/

vehicle_models:
  delivery_van:
    weight_empty_kg: 2500
    max_load_kg: 1500
    fuel_type: diesel
    fuel_efficiency_l_per_100km: 12.0
  cargo_truck:
    weight_empty_kg: 7500
    max_load_kg: 5000
    fuel_type: diesel
    fuel_efficiency_l_per_100km: 25.0
  electric_van:
    weight_empty_kg: 2700
    max_load_kg: 1300
    energy_type: electric
    energy_efficiency_kwh_per_100km: 20.0

emission_factors:
  diesel: 2.68  # kg CO2 per liter
  gasoline: 2.31  # kg CO2 per liter
  electric: 0.5  # kg CO2 per kWh (depends on local grid)

defaults:
  route_algorithm: "fastest"
  include_traffic: true
  include_weather: true
  default_vehicle: "delivery_van"
  max_route_alternatives: 3

cache:
  enabled: true
  expiry_seconds: 600
  max_size_mb: 100
"""