# api/openai_api.py
from typing import Dict
import requests
import base64
import anthropic
from typing_extensions import Any
from core import prompting
from core.config import config
import threading
import time
import logging

logger = logging.getLogger(__name__)

class AnthropicAPI:
    def __init__(self) -> None:
        api_key = config.anthropic_api_key
        if not api_key:
            logger.error("Anthropic API key not found in configuration")
            raise ValueError("Anthropic API key not configured. Please set ANTHROPIC_API_KEY in .env file")
        self.client = anthropic.Client(api_key=api_key)
        self.max_retries = 5
        self.retry_delay = 1  # seconds
        self.context = "Return a Python script to plot the concept using matplotlib. Include only the code."

    @staticmethod
    def encode_image(image_path: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except IOError as e:
            print(f"Error reading image file: {e}")
            return ""

    def send_message_to_anthropic(self, message: str) -> None:
        full_context = self.context + "message is " + message
        prompting.output = ""
        prompting.shouldUpdate = "f"

        def streaming_thread():
            for attempt in range(self.max_retries):
                try:
                    with self.client.messages.stream(
                            max_tokens=4096,
                            messages=[{"role": "user", "content": [{"type": "text", "text": full_context}]}],
                            model=prompting.model,
                    ) as stream:
                        for text in stream.text_stream:
                            prompting.output += text
                            prompting.shouldUpdate = "f"
                    break  # If successful, break out of the retry loop
                except Exception as e:
                    error_message = str(e)
                    if 'overloaded_error' in error_message and attempt < self.max_retries - 1:
                        print(f"Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        print(f"Error in streaming thread: {error_message}")
                        prompting.output += f"\nError occurred: {error_message}\n"
                        break
            time.sleep(1)  # Add a 1000ms delay
            prompting.shouldUpdate = "t"

        threading.Thread(target=streaming_thread).start()

    def send_image_to_anthropic(self, image_path: str) -> None:
        prompting.output = ""
        prompting.shouldUpdate = "f"

        base64_image = self.encode_image(image_path)
        if not base64_image:
            prompting.output = "Error: Could not encode image."
            prompting.shouldUpdate = "t"
            return

        def streaming_thread():
            for attempt in range(self.max_retries):
                try:
                    prompting.output = "#started       \n"
                    with self.client.messages.stream(
                            max_tokens=4096,
                            messages=[{
                                "role": "user",
                                "content": [{
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": base64_image
                                    }
                                }]
                            }],
                            model="claude-3-opus-20240229",
                    ) as stream:
                        for text in stream.text_stream:
                            prompting.output += text
                    break  # If successful, break out of the retry loop
                except Exception as e:
                    error_message = str(e)
                    if 'overloaded_error' in error_message and attempt < self.max_retries - 1:
                        print(f"Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        print(f"Error in streaming thread: {error_message}")
                        prompting.output += f"\nError occurred: {error_message}\n"
                        break
            prompting.shouldUpdate = "t"

        threading.Thread(target=streaming_thread).start()