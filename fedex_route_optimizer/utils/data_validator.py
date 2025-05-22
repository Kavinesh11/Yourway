import re
import datetime
import logging
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger_setup import setup_logger

class DataValidator:
    """
    Validates input data before processing to ensure data integrity and 
    prevent potential errors in the routing and emissions calculation.
    """
    
    def __init__(self):
        """Initialize the DataValidator with logger."""
        self.logger = setup_logger("DataValidator")
        
        # Regular expressions for validation
        self._zip_code_pattern = re.compile(r'^\d{5}(-\d{4})?$')  # US ZIP code format
        self._email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')  # Basic email format
        self._phone_pattern = re.compile(r'^\+?[\d\s\(\)-]{7,20}$')  # International phone format
        
        # Acceptable vehicle types
        self._valid_vehicle_types = [
            "Delivery Van", "Box Truck", "Semi-Truck", "Electric Vehicle",
            "Hybrid", "Compact Car", "SUV", "Pickup Truck"
        ]
        
        # Acceptable fuel types
        self._valid_fuel_types = [
            "Gasoline", "Diesel", "Electric", "Hybrid", "Natural Gas", "Hydrogen"
        ]
    
    def validate_location(self, location):
        """
        Validates if a location string is properly formatted.
        
        Args:
            location (str): The location string to validate
            
        Returns:
            bool: True if the location is valid, False otherwise
        """
        if not location or not isinstance(location, str):
            self.logger.warning(f"Invalid location format: {location}")
            return False
            
        # Basic validation - check if string is not just whitespace
        if len(location.strip()) < 3:
            self.logger.warning(f"Location too short: {location}")
            return False
            
        # Location strings shouldn't be extremely long
        if len(location) > 200:
            self.logger.warning(f"Location string too long: {len(location)} chars")
            return False
            
        return True
    
    def validate_coordinates(self, lat, lon):
        """
        Validates if latitude and longitude are within valid ranges.
        
        Args:
            lat (float): Latitude value to validate
            lon (float): Longitude value to validate
            
        Returns:
            bool: True if coordinates are valid, False otherwise
        """
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            
            if not (-90 <= lat_float <= 90):
                self.logger.warning(f"Invalid latitude: {lat_float}")
                return False
                
            if not (-180 <= lon_float <= 180):
                self.logger.warning(f"Invalid longitude: {lon_float}")
                return False
                
            return True
            
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid coordinate format: lat={lat}, lon={lon}")
            return False
    
    def validate_date(self, date_str, date_format="%Y-%m-%d"):
        """
        Validates if a date string is properly formatted.
        
        Args:
            date_str (str): Date string to validate
            date_format (str): Expected date format (default: YYYY-MM-DD)
            
        Returns:
            bool: True if date is valid, False otherwise
        """
        try:
            datetime.datetime.strptime(date_str, date_format)
            return True
        except ValueError:
            self.logger.warning(f"Invalid date format. Expected {date_format}, got {date_str}")
            return False
    
    def validate_time(self, time_str, time_format="%H:%M"):
        """
        Validates if a time string is properly formatted.
        
        Args:
            time_str (str): Time string to validate
            time_format (str): Expected time format (default: HH:MM)
            
        Returns:
            bool: True if time is valid, False otherwise
        """
        try:
            datetime.datetime.strptime(time_str, time_format)
            return True
        except ValueError:
            self.logger.warning(f"Invalid time format. Expected {time_format}, got {time_str}")
            return False
    
    def validate_zip_code(self, zip_code):
        """
        Validates if a ZIP code is properly formatted.
        
        Args:
            zip_code (str): ZIP code to validate
            
        Returns:
            bool: True if ZIP code is valid, False otherwise
        """
        if not isinstance(zip_code, str):
            self.logger.warning(f"ZIP code must be a string, got {type(zip_code)}")
            return False
            
        if self._zip_code_pattern.match(zip_code):
            return True
        else:
            self.logger.warning(f"Invalid ZIP code format: {zip_code}")
            return False
    
    def validate_email(self, email):
        """
        Validates if an email is properly formatted.
        
        Args:
            email (str): Email to validate
            
        Returns:
            bool: True if email is valid, False otherwise
        """
        if not isinstance(email, str):
            self.logger.warning(f"Email must be a string, got {type(email)}")
            return False
            
        if self._email_pattern.match(email):
            return True
        else:
            self.logger.warning(f"Invalid email format: {email}")
            return False
    
    def validate_phone(self, phone):
        """
        Validates if a phone number is properly formatted.
        
        Args:
            phone (str): Phone number to validate
            
        Returns:
            bool: True if phone number is valid, False otherwise
        """
        if not isinstance(phone, str):
            self.logger.warning(f"Phone must be a string, got {type(phone)}")
            return False
            
        if self._phone_pattern.match(phone):
            return True
        else:
            self.logger.warning(f"Invalid phone format: {phone}")
            return False
    
    def validate_vehicle_type(self, vehicle_type):
        """
        Validates if a vehicle type is in the list of acceptable types.
        
        Args:
            vehicle_type (str): Vehicle type to validate
            
        Returns:
            bool: True if vehicle type is valid, False otherwise
        """
        if not isinstance(vehicle_type, str):
            self.logger.warning(f"Vehicle type must be a string, got {type(vehicle_type)}")
            return False
            
        if vehicle_type in self._valid_vehicle_types:
            return True
        else:
            self.logger.warning(f"Invalid vehicle type: {vehicle_type}")
            return False
    
    def validate_fuel_type(self, fuel_type):
        """
        Validates if a fuel type is in the list of acceptable types.
        
        Args:
            fuel_type (str): Fuel type to validate
            
        Returns:
            bool: True if fuel type is valid, False otherwise
        """
        if not isinstance(fuel_type, str):
            self.logger.warning(f"Fuel type must be a string, got {type(fuel_type)}")
            return False
            
        if fuel_type in self._valid_fuel_types:
            return True
        else:
            self.logger.warning(f"Invalid fuel type: {fuel_type}")
            return False
    
    def validate_api_key(self, api_key):
        """
        Validates if an API key string is properly formatted.
        
        Args:
            api_key (str): API key to validate
            
        Returns:
            bool: True if API key format is valid, False otherwise
        """
        if not isinstance(api_key, str):
            self.logger.warning(f"API key must be a string, got {type(api_key)}")
            return False
            
        # Most API keys are alphanumeric and have a minimum length
        if len(api_key.strip()) < 8:
            self.logger.warning("API key is too short")
            return False
            
        return True
    
    def validate_weight(self, weight):
        """
        Validates if a weight value is valid.
        
        Args:
            weight (float or str): Weight value to validate
            
        Returns:
            bool: True if weight is valid, False otherwise
        """
        try:
            weight_float = float(weight)
            
            if weight_float <= 0:
                self.logger.warning(f"Weight must be positive, got {weight_float}")
                return False
                
            return True
            
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid weight format: {weight}")
            return False
    
    def validate_distance(self, distance):
        """
        Validates if a distance value is valid.
        
        Args:
            distance (float or str): Distance value to validate
            
        Returns:
            bool: True if distance is valid, False otherwise
        """
        try:
            distance_float = float(distance)
            
            if distance_float < 0:
                self.logger.warning(f"Distance cannot be negative, got {distance_float}")
                return False
                
            return True
            
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid distance format: {distance}")
            return False
    
    def validate_integer(self, value, min_val=None, max_val=None):
        """
        Validates if a value is an integer and within the specified range.
        
        Args:
            value: Value to validate
            min_val (int, optional): Minimum acceptable value
            max_val (int, optional): Maximum acceptable value
            
        Returns:
            bool: True if value is valid, False otherwise
        """
        try:
            int_value = int(value)
            
            if min_val is not None and int_value < min_val:
                self.logger.warning(f"Value {int_value} is less than minimum {min_val}")
                return False
                
            if max_val is not None and int_value > max_val:
                self.logger.warning(f"Value {int_value} is greater than maximum {max_val}")
                return False
                
            return True
            
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid integer format: {value}")
            return False