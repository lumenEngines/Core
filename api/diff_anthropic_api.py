"""
Dedicated Anthropic API for diff viewer operations.
Isolated from main application to avoid threading issues.
"""

import anthropic
import os
import json


class DiffAnthropicAPI:
    """Isolated Anthropic API client for diff operations."""
    
    def __init__(self):
        self.client = None
        self.model = "claude-3-5-sonnet-20240620"
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Anthropic client with API key."""
        try:
            # Try to get API key from environment
            api_key = os.getenv('ANTHROPIC_API_KEY')
            
            if not api_key:
                # Try to load from settings file
                settings_path = os.path.join(os.path.dirname(__file__), 'app_settings.json')
                if os.path.exists(settings_path):
                    with open(settings_path, 'r') as f:
                        settings = json.load(f)
                        api_key = settings.get('anthropic_api_key')
            
            if not api_key:
                # Try to load from existing anthropic_api.py config
                try:
                    import anthropic_api
                    if hasattr(anthropic_api, 'AnthropicAPI'):
                        temp_api = anthropic_api.AnthropicAPI()
                        if hasattr(temp_api, 'client') and temp_api.client:
                            # Use the same API key as the main client
                            self.client = temp_api.client
                            print("✓ Using existing Anthropic API configuration for diff viewer")
                            # Test the client with a simple call
                            self._test_client()
                            return
                except Exception as e:
                    print(f"Could not reuse existing API config: {e}")
            
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
                print("✓ Anthropic API initialized for diff viewer")
                # Test the client with a simple call
                self._test_client()
            else:
                print("✗ No Anthropic API key found for diff viewer")
                
        except Exception as e:
            print(f"✗ Error initializing Anthropic API for diff viewer: {e}")
            self.client = None
    
    def _test_client(self):
        """Test the API client with a simple call."""
        try:
            print("Testing diff API client...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0.1,
                system="You are a helpful assistant. Respond with exactly: TEST_OK",
                messages=[{"role": "user", "content": "Test"}]
            )
            
            if response.content and len(response.content) > 0:
                content = response.content[0].text.strip()
                print(f"✓ Diff API test successful: '{content}'")
            else:
                print("✗ Diff API test failed: No content in response")
                print(f"Response: {response}")
                
        except Exception as e:
            print(f"✗ Diff API test failed: {e}")
            self.client = None
    
    def send_message(self, message: str) -> str:
        """Send a message to Anthropic API and get response."""
        if not self.client:
            raise Exception("Anthropic API not initialized")
        
        try:
            print(f"Making API call with model: {self.model}")
            print(f"Message length: {len(message)}")
            print(f"Message preview: {message[:200]}...")
            
            # Use system prompt to ensure plain text code output only
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent code generation
                system="You are a code editor assistant. You MUST return ONLY the complete modified file content as plain text code. Do NOT include any explanations, markdown formatting, HTML tags, or code block delimiters (like ```). Return the raw code exactly as it should appear in the file.",
                messages=[
                    {
                        "role": "user", 
                        "content": message
                    }
                ]
            )
            
            # Debug API response
            print(f"API Response received - Content blocks: {len(response.content) if response.content else 0}")
            print(f"Response object: {response}")
            print(f"Response usage: {getattr(response, 'usage', 'No usage info')}")
            
            if response.content:
                content = response.content[0].text
                print(f"Content length: {len(content)}, Preview: {content[:100]}...")
                return content
            else:
                print("No content in API response")
                print(f"Full response object: {vars(response)}")
                return ""
            
        except Exception as e:
            print(f"API call exception: {str(e)}")
            print(f"Exception type: {type(e)}")
            raise Exception(f"API call failed: {str(e)}")


# Global instance for diff operations
diff_anthropic_api = DiffAnthropicAPI()