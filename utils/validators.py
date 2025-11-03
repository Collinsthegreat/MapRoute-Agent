"""Input validation utilities."""
from typing import Tuple, Optional
import re


class LocationValidator:
    """Validate and sanitize location inputs."""
    
    MIN_LENGTH = 2
    MAX_LENGTH = 100
    
    # Characters allowed in location names
    ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-,\.]+$')
    
    @classmethod
    def validate_location(cls, location: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a location string.
        
        Args:
            location: Location string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not location or not location.strip():
            return False, "Location cannot be empty"
        
        location = location.strip()
        
        if len(location) < cls.MIN_LENGTH:
            return False, f"Location must be at least {cls.MIN_LENGTH} characters"
        
        if len(location) > cls.MAX_LENGTH:
            return False, f"Location must not exceed {cls.MAX_LENGTH} characters"
        
        if not cls.ALLOWED_PATTERN.match(location):
            return False, "Location contains invalid characters"
        
        return True, None
    
    @classmethod
    def sanitize_location(cls, location: str) -> str:
        """
        Sanitize location string.
        
        Args:
            location: Location string to sanitize
            
        Returns:
            Sanitized location string
        """
        # Remove extra whitespace
        location = ' '.join(location.split())
        
        # Remove potentially dangerous characters
        location = re.sub(r'[<>\'";]', '', location)
        
        return location.strip()