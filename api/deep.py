from openai import OpenAI
import threading
import time
import src.prompting as prompting

APIKEY = "sk-17311621c9084367a3308e67d3cdf823"


class DeepAPI:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=APIKEY, base_url="https://api.deepseek.com/beta")
        self.max_retries = 5
        self.retry_delay = 1  # seconds
        self.sys_prompt = """ You are an assistant that teaches people STEM and more. You are verbose! You love math formulas because of their precision. You love to show off your knowledge but only when appropriate! You were the math olympiad winner. You are also an expert at physics. 
        Always use html compatible latex for math if there is math so the formulas are properly rendered. This is critical for you."
            "If you think there is a good way to visualize a concept, mention it, if not, don't mention it."
            
            Always respond with appropriate html tags inside <> that follow these styles and pad these tags from the left.
    Put all this inside <div class="container2"> section by section in your output. I've already defined container class.
    <h3></h3> <h4> </h4> <h5> </h5> and so on
    <p></p>
    <h1></h1>
    <hr></hr>
    
    Respond with html tags because you are addding to an html file, not making one. 
    """


    def _build_context(self, message: str) -> str:
        context = (
            f"The message is: {message}\n"
            
            f"REMEMBER and use the following only if needed and useful to this conversation:\n"
            f"Previous message by me was: {prompting.messages[-2]}\n"
            f"Previous response by you was: {prompting.chat[-1]}\n"
            f"Previous to previous message by me was: {prompting.messages[-3]}\n"
            f"Previous to previous response by you was: {prompting.chat[-2]}\n"
            f"Previous to previous to previous message by me was: {prompting.messages[-4]}\n"
            f"Previous to previous to previous response by you was: {prompting.chat[-3]}"
            f"}}"

        )
        return context

    def send_message_to_deep(self, message: str) -> None:
        prompting.messages = prompting.messages[-3:] + [message]
        full_context = self._build_context(message)
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
                    stream = self.client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": self.sys_prompt},
                            {"role": "user", "content": full_context}
                        ],
                        stream=True
                    )

                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            prompting.output += chunk.choices[0].delta.content
                            prompting.shouldUpdate = "t"

                    break  # If successful, break out of the retry loop
                except Exception as e:
                    error_message = str(e)
                    if attempt < self.max_retries - 1:
                        print(f"Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        print(f"Error in streaming thread: {error_message}")
                        prompting.output += f"\nError occurred: {error_message}\n"
                        break

            time.sleep(1)  # Add a 1000ms delay
            prompting.shouldUpdate = "t"

        threading.Thread(target=streaming_thread).start()
