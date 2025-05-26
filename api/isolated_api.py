"""
Isolated API interface for Project Manager to avoid interfering with main Lumen interface.
This module provides direct API calls that don't route through the main streaming system.
"""

import os
import json
import time
from typing import Optional


class IsolatedAnthropicAPI:
    """Isolated Anthropic API client for Project Manager use only."""
    
    def __init__(self):
        """Initialize the isolated API client."""
        self.api_key = None
        self._load_api_key()
    
    def _load_api_key(self):
        """Load API key from environment or config."""
        # Try environment variable first
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            # Try to load from existing anthropic_api module
            try:
                import sys
                # Add src directory to path if not already there
                src_dir = os.path.dirname(os.path.abspath(__file__))
                if src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
                
                import anthropic_api
                # Check for the APIKEY constant
                if hasattr(anthropic_api, 'APIKEY'):
                    self.api_key = anthropic_api.APIKEY
                else:
                    # Fallback to instance attributes
                    api_instance = anthropic_api.AnthropicAPI()
                    if hasattr(api_instance, 'api_key'):
                        self.api_key = api_instance.api_key
                    elif hasattr(api_instance, 'client') and hasattr(api_instance.client, 'api_key'):
                        self.api_key = api_instance.client.api_key
            except Exception as e:
                print(f"Error loading Anthropic API key: {e}")
        
        if self.api_key:
            print("✓ Anthropic API key loaded for isolated API")
        else:
            print("Warning: No Anthropic API key found for isolated API")
    
    def call_anthropic_direct(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """
        Make a direct API call to Anthropic without routing through main interface.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            
        Returns:
            API response text or None if failed
        """
        if not self.api_key:
            print("No API key available for Anthropic")
            return None
        
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return message.content[0].text
            
        except ImportError:
            print("Anthropic library not available")
            return None
        except Exception as e:
            print(f"Error in direct Anthropic API call: {e}")
            return None


class IsolatedGroqAPI:
    """Isolated Groq API client for Project Manager use only."""
    
    def __init__(self):
        """Initialize the isolated API client."""
        self.api_key = None
        self._load_api_key()
    
    def _load_api_key(self):
        """Load API key from environment or config."""
        # Try environment variable first
        self.api_key = os.environ.get('GROQ_API_KEY')
        
        if not self.api_key:
            # Try to load from existing groq_api module
            try:
                import sys
                # Add src directory to path if not already there
                src_dir = os.path.dirname(os.path.abspath(__file__))
                if src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
                
                import groq_api
                api_instance = groq_api.GroqAPI()
                # Extract API key from client
                if hasattr(api_instance, 'client') and hasattr(api_instance.client, 'api_key'):
                    self.api_key = api_instance.client.api_key
                elif hasattr(api_instance, 'api_key'):
                    self.api_key = api_instance.api_key
            except Exception as e:
                print(f"Error loading Groq API key: {e}")
        
        if self.api_key:
            print("✓ Groq API key loaded for isolated API")
        else:
            print("Warning: No Groq API key found for isolated API")
    
    def call_groq_direct(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """
        Make a direct API call to Groq without routing through main interface.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            
        Returns:
            API response text or None if failed
        """
        if not self.api_key:
            print("No API key available for Groq")
            return None
        
        try:
            from groq import Groq
            
            client = Groq(api_key=self.api_key)
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama3-8b-8192",
                max_tokens=max_tokens,
            )
            
            return chat_completion.choices[0].message.content
            
        except ImportError:
            print("Groq library not available")
            return None
        except Exception as e:
            print(f"Error in direct Groq API call: {e}")
            return None


class IsolatedAPIManager:
    """Manager for isolated API calls in Project Manager."""
    
    def __init__(self):
        """Initialize the API manager."""
        self.anthropic_api = IsolatedAnthropicAPI()
        self.groq_api = IsolatedGroqAPI()
    
    def call_api(self, prompt: str, api_preference: str = 'anthropic', max_tokens: int = 1000) -> Optional[str]:
        """
        Make an isolated API call based on preference.
        
        Args:
            prompt: The prompt to send
            api_preference: 'anthropic' or 'groq'
            max_tokens: Maximum tokens in response
            
        Returns:
            API response text or None if failed
        """
        if api_preference.lower() == 'anthropic':
            return self.anthropic_api.call_anthropic_direct(prompt, max_tokens)
        elif api_preference.lower() == 'groq':
            return self.groq_api.call_groq_direct(prompt, max_tokens)
        else:
            print(f"Unknown API preference: {api_preference}")
            return None
    
    def is_api_available(self, api_preference: str = 'anthropic') -> bool:
        """
        Check if an API is available.
        
        Args:
            api_preference: 'anthropic' or 'groq'
            
        Returns:
            True if API is available
        """
        if api_preference.lower() == 'anthropic':
            return self.anthropic_api.api_key is not None
        elif api_preference.lower() == 'groq':
            return self.groq_api.api_key is not None
        else:
            return False


# Create singleton instance
isolated_api_manager = IsolatedAPIManager()