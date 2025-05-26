import requests
import base64
import prompting


APIKEY = ""

def encode_image(image_path): 
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

def send_image_to_gpt(imagePath):

    base64_image = encode_image(imagePath)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIKEY}"
    }

    payload = {
        "model": "gpt-4-turbo",
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": prompting.system_prompt
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            },
        ],
    }


def send_text_to_gpt(text):

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIKEY}"
    }

    payload = {
        "model": "gpt-4-turbo",
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": prompting.system_prompt
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                         "type": "text",
                         "text": text
                    }
                ]
            },
        ],
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        
        # Parsing the message content from the first choice (assuming it's the relevant response)
        message_content = data.get('choices', [{}])[0].get('message', {}).get('content', 'Error: No content found')
        return message_content
        
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP Error occurred: {http_err}"
    except Exception as err:
        return f"Other error occurred: {err}"
