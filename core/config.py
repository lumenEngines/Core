"""
Configuration management for Lumen application.
Handles loading API keys and other settings from environment variables.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Application configuration manager."""
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        # Load .env file if it exists
        # Look for .env in the project root (parent of core directory)
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try current directory as fallback
            load_dotenv()
        
        # Load API keys from environment
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        
        # Application settings
        self.debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
    def get_api_key(self, service: str) -> Optional[str]:
        """
        Get API key for a specific service.
        
        Args:
            service: Name of the service (anthropic, deepseek, openai, groq)
            
        Returns:
            API key string or None if not found
        """
        service = service.lower()
        key_map = {
            'anthropic': self.anthropic_api_key,
            'deepseek': self.deepseek_api_key,
            'openai': self.openai_api_key,
            'groq': self.groq_api_key
        }
        return key_map.get(service)
    
    def validate(self) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if all required config is valid
        """
        # At least one API key should be present
        api_keys = [
            self.anthropic_api_key,
            self.deepseek_api_key,
            self.openai_api_key,
            self.groq_api_key
        ]
        
        return any(key and key != 'your_api_key_here' for key in api_keys)


# Create singleton instance
config = Config()