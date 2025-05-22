# fedex_route_optimizer/utils/logger_setup.py
"""
Configure logging for the application.
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime

def setup_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Add timestamp to log file name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = log_dir / f"{log_file}_{timestamp}.log"
        
        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger