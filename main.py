# fedex_route_optimizer/main.py
"""
FedEx SMART Route Optimizer - Main Application
This module serves as the entry point for the route optimization application.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Import application modules
from config import settings
from api_connectors import (
    tomtom_connector,
    google_maps_connector,
    aqicn_connector,
    osrm_connector
)
from route_engine import route_optimizer
from emissions import emissions_calculator
from ui import interface_manager
from utils import data_validator, geocoding, logger_setup

# Setup logging
logger = logger_setup.setup_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="FedEx SMART Route Optimizer - Dynamic routing with emissions calculation"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.yaml", 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["cli", "gui", "api"], 
        default="cli", 
        help="Application interface mode"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    return parser.parse_args()

def initialize_application(args):
    """Initialize application components based on configuration."""
    logger.info("Initializing FedEx SMART Route Optimizer...")
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
        
    settings.load_config(config_path)
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Initialize API connectors
    api_clients = {
        "tomtom": tomtom_connector.TomTomAPI(settings.get_api_key("tomtom")),
        "google_maps": google_maps_connector.GoogleMapsAPI(settings.get_api_key("google_maps")),
        "aqicn": aqicn_connector.AQICNAPI(settings.get_api_key("aqicn")),
        "osrm": osrm_connector.OSRMAPI()
    }
    
    # Initialize core components
    route_engine = route_optimizer.RouteOptimizer(api_clients)
    emissions_engine = emissions_calculator.EmissionsCalculator()
    
    return {
        "api_clients": api_clients,
        "route_engine": route_engine,
        "emissions_engine": emissions_engine
    }

def run_application(args, components):
    """Run the application in the specified mode."""
    logger.info(f"Starting application in {args.mode} mode")
    
    if args.mode == "cli":
        interface = interface_manager.CLIInterface(
            components["route_engine"],
            components["emissions_engine"]
        )
    elif args.mode == "gui":
        interface = interface_manager.GUIInterface(
            components["route_engine"],
            components["emissions_engine"]
        )
    elif args.mode == "api":
        interface = interface_manager.APIInterface(
            components["route_engine"],
            components["emissions_engine"]
        )
    
    interface.run()

def main():
    """Main application entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    try:
        # Initialize application components
        components = initialize_application(args)
        
        # Run the application
        run_application(args, components)
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Application terminated successfully")

if __name__ == "__main__":
    main()