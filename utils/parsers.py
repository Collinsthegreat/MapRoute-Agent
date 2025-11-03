"""Message parsing utilities."""
import re
from typing import Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MessageParser:
    """Parse user messages to extract intent and locations."""
    
    # Patterns for extracting locations
    DIRECTION_PATTERNS = [
        r'directions?\s+from\s+(.+?)\s+to\s+(.+)',
        r'route\s+from\s+(.+?)\s+to\s+(.+)',
        r'how\s+to\s+get\s+from\s+(.+?)\s+to\s+(.+)',
        r'navigate\s+from\s+(.+?)\s+to\s+(.+)',
        r'from\s+(.+?)\s+to\s+(.+)',
    ]
    
    @classmethod
    def parse_route_request(cls, message: str) -> Optional[Tuple[str, str]]:
        """
        Parse a route request message to extract origin and destination.
        
        Args:
            message: User message text
            
        Returns:
            Tuple of (origin, destination) or None if parsing fails
        """
        message = message.lower().strip()
        
        for pattern in cls.DIRECTION_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                origin = match.group(1).strip()
                destination = match.group(2).strip()
                
                logger.info(f"Parsed request: {origin} -> {destination}")
                return origin, destination
        
        logger.warning(f"Could not parse route request: {message}")
        return None
    
    @classmethod
    def is_route_request(cls, message: str) -> bool:
        """
        Check if message is a route request.
        
        Args:
            message: User message text
            
        Returns:
            True if message appears to be a route request
        """
        keywords = ['direction', 'route', 'navigate', 'from', 'to', 'how to get']
        message_lower = message.lower()
        
        return any(keyword in message_lower for keyword in keywords)