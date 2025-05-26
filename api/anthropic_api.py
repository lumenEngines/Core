"""Anthropic API client for Lumen application."""

from typing import Dict, Optional
import requests
import base64
import anthropic
from typing_extensions import Any
import threading
import time
import logging
from core import prompting
from core.config import config
from .api_exceptions import (
    APIError, APIKeyError, APIConnectionError, 
    APIRateLimitError, APIResponseError, APITimeoutError
)

logger = logging.getLogger(__name__)


class AnthropicAPI:
    """Client for interacting with Anthropic's Claude API."""
    
    def __init__(self) -> None:
        """Initialize the Anthropic API client."""
        api_key = config.anthropic_api_key
        if not api_key:
            logger.error("Anthropic API key not found in configuration")
            raise APIKeyError("Anthropic API key not configured. Please set ANTHROPIC_API_KEY in .env file")
        
        try:
            self.client = anthropic.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise APIConnectionError(f"Failed to initialize Anthropic client: {e}")
        
        self.max_retries = 5
        self.retry_delay = 1  # seconds

    @staticmethod
    def encode_image(image_path: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except IOError as e:
            logger.error(f"Error reading image file: {e}")
            return ""

    def _build_context(self, message: str, include_chat_history: bool = True) -> str:
        #Use fun and clever emojis in your response but never say that you will use them. Don't use them in programming outputs.
        
        # Base context without history
        context = (
        "The message is:"
            f"{message}\n "
            "The system prompt is: {"
            f"Don't use special fonts, and always use html compatible latex for math if there is math so the formulas are properly rendered. This is critical for you. In HTML-compatible environments, we typically use ... for inline latex math and"
            f"If you think there is a good way to visualize a concept, mention it, if not, don't mention it."
        )
        
        # Add chat history if requested
        if include_chat_history:
            try:
                if len(prompting.messages) > 2 and len(prompting.chat) > 1:
                    context += (
                        f"REMEMBER and use the following only if needed and useful to this conversation:\n"
                        f"Previous message by me was: {prompting.messages[-2]}\n"
                        f"Previous response by you was: {prompting.chat[-1]}\n"
                        f"Previous to previous message by me was: {prompting.messages[-3]}\n"
                        f"Previous to previous response by you was: {prompting.chat[-2]}\n"
                        f"Previous to previous to previous message by me was: {prompting.messages[-4]}\n"
                        f"Previous to previous to previous response by you was: {prompting.chat[-3]}"
                    )
            except IndexError:
                # No sufficient history available
                pass
        
        context += "}"
        context += """You are an assistant that teaches people STEM and more.
         If asked to fix code or write code, you return perfectly formatted and complete code. 
        You love to show off your knowledge but only when appropriate! You were the math olympiad winner. You are also an expert at physics. 
        Always use html compatible latex for math if there is math so the formulas are properly rendered. This is critical for you.
        If you think there is a good way to visualize a concept, mention it, if not, don't mention it.
            
        Always respond with appropriate html tags inside <> that follow these styles and pad these tags from the left.
        Put all this inside <div class="container2"> section by section in your output. I've already defined container class.
        <h3></h3> <h4> </h4> <h5> </h5> and so on
        <p></p>
        <h1></h1>
        <hr></hr>
        Remember wise minds don't mention what they've done, they just do it and never talk about it.
        If you are returning complete code for an animation, comment instructions to make a gif and return the formatted file so it can be run by copying and pasting it."""

        return context

    def send_message_to_anthropic(self, message: str, include_chat_history: bool = True) -> None:
        prompting.messages = prompting.messages[-3:] + [message]
        full_context = self._build_context(message, include_chat_history)
        prompting.output = """
                 <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Lumen - Your Personal Assistant v2</title>

          <link href="https://fonts.googleapis.com/css2?family=Forum&family=Avenir:wght@300&display=swap" rel="stylesheet">
          <style>
            body {
              background-color: white;
            }
            .container {
              max-width: 800px;
              margin-top: 10px;
              background-color: white;
              border-radius: 10px;
              margin-left: 30px;
            }
            .container2 {
              max-width: 800px;
              background-color: white;
              margin-left: 30px;
            }
            h1, h2, h3, h4, h5, h6 {
              font-family: 'Forum', serif;
              color: #333;
              font-weight: 200; /* Lighter weight */
            }
            p {
              font-family: 'Avenir', sans-serif;
              color: #555;
            }
            h1 {
              font-size: 3.5rem;
              margin-bottom: 20px;
            }
            hr {
              height: 2px;
              border: none;
              background: linear-gradient(to right, #800000, #ffffff);
              margin: 30px 0;
            }
          </style>
          <script
                id = "MathJax-script" async src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"> </script>

        </head>
        <body>
          <div class="container">
            <div class="d-flex align-items-center">
              <h1>Lumen</h1>
            </div>
            <p class="lead">Your Personal Assistant v2</p>
            <hr>
          </div>
        </body>
        </html>"""
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
                except anthropic.RateLimitError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Rate limit hit. Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"Rate limit error after {self.max_retries} attempts: {e}")
                        prompting.output += f"\n❌ Error: API rate limit exceeded. Please try again later.\n"
                        break
                except anthropic.APITimeoutError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Timeout error. Attempt {attempt + 1} failed. Retrying...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Timeout error after {self.max_retries} attempts: {e}")
                        prompting.output += f"\n❌ Error: Request timed out. Please try again.\n"
                        break
                except Exception as e:
                    error_message = str(e)
                    if 'overloaded_error' in error_message and attempt < self.max_retries - 1:
                        logger.warning(f"Server overloaded. Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Error in streaming thread: {error_message}")
                        prompting.output += f"\n❌ Error occurred: {error_message}\n"
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
            context = "If you see text, return every single word in perfect formatting as before you do anything else."
            for attempt in range(self.max_retries):
                try:
                    prompting.output = "#started       \n"
                    with self.client.messages.stream(
                            max_tokens=4096,
                            messages=[ { "role": "user", "content": [ { "type": "image", "source": { "type": "base64", "media_type": "image/png", "data": base64_image } }, { "type": "text", "text": context } ] } ],
                            model="claude-3-opus-20240229",
                    ) as stream:
                        for text in stream.text_stream:
                            prompting.output += text
                    break  # If successful, break out of the retry loop
                except anthropic.RateLimitError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Rate limit hit. Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"Rate limit error after {self.max_retries} attempts: {e}")
                        prompting.output += f"\n❌ Error: API rate limit exceeded. Please try again later.\n"
                        break
                except anthropic.APITimeoutError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Timeout error. Attempt {attempt + 1} failed. Retrying...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Timeout error after {self.max_retries} attempts: {e}")
                        prompting.output += f"\n❌ Error: Request timed out. Please try again.\n"
                        break
                except Exception as e:
                    error_message = str(e)
                    if 'overloaded_error' in error_message and attempt < self.max_retries - 1:
                        logger.warning(f"Server overloaded. Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Error in streaming thread: {error_message}")
                        prompting.output += f"\n❌ Error occurred: {error_message}\n"
                        break
            time.sleep(1)  # Add a 1000ms delay
            prompting.shouldUpdate = "t"
        threading.Thread(target=streaming_thread).start()