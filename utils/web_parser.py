import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout


def extract_main_text(url, timeout=5)->str:
    try:
        # Send a GET request to the URL with a specified timeout
        response = requests.get(url, timeout=timeout)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the HTML content of the webpage
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the main content using specific HTML tags (e.g., <p> for paragraphs)
            main_content = []
            for paragraph in soup.find_all('p'):
                # Extract text from the paragraph tag and strip any extra whitespace
                text = paragraph.get_text().strip()
                if text:  # Only add non-empty text to the main content
                    main_content.append(text)

            # Join the list of extracted paragraphs into a single string
            main_text = '\n'.join(main_content).strip()
            
            if not main_text:
                print("Warning: No text extracted from the main content.")
                
            return main_text
        
        else:
            # If the request was not successful, raise an exception
            print(f"Error: HTTP {response.status_code}")
            return None

    except Timeout:
        # Handle timeout (request took too long to complete)
        print("Request timed out. Skipping...")
        return None

    except RequestException as e:
        # Handle other request exceptions (e.g., connection errors)
        print(f"Request Error: {e}")
        return None

    except Exception as e:
        # Handle other unexpected errors during parsing
        print(f"Error: {e}")
        return None

class WebParser:
    def __init__(self): 
        self.driver = None

    def parseURL(self, url) -> str:
        # Send a GET request to the URL
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            return response.text
        return ""