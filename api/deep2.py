from openai import OpenAI
import threading
import time
import src.prompting as prompting

APIKEY = "sk-17311621c9084367a3308e67d3cdf823"


class DeepAPI2:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=APIKEY, base_url="https://api.deepseek.com/beta")
        self.max_retries = 5
        self.retry_delay = 1  # seconds
        self.sys_prompt = """ 
            Your job is to return a formatted python script to help me plot a concept in the selected text using numpy and matplotlib"
            "save as gif in the end"
            "If important details are missing, think up the details and do not return anything besides the code. All comments with hashtags!"
            "Think through the animation section by section carefully and write your thinking inside comments.
            " You must return a script no matter what"
            " make sure to call plt.show() after creating your plot."
            " When executed a proper popup must appear with the plot on the desktop"
            "Use dark backgrounds for the animations and 3d plots"
            "Remember: MatplotlibDeprecationWarning: The w_zaxis attribute was deprecated in Matplotlib 3.1 and will be removed in 3.8. Use zaxis instead.
  ax.zaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))"
            "Use lines of 1 width, not 2. Use red, white, purple, brown as colors in a way that's compatible with matplotlib. Don't use non standard libraries."
           " Your output should be inside a 1600X900 rectanglular popup, and the shapes must not deform!"
            "Add these lines after creating the `ax` object so that user never sees grids and numbers:
                add:                   
                ax.xaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
                ax.yaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
                ax.zaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
                To completely remove the axes, you can use:
                                    
                ax.set_axis_off()

            Some example scripts are 
            In the end, save the animation or graph as a gif or png.

            Integration:
            Prompt: Imagine Integration by showing rectangles increase in resolution under a cubic 2d curve mapping x to y.
            Response: ```python import numpy as np import matplotlib matplotlib.use('Qt5Agg') import matplotlib.pyplot as plt from matplotlib.animation import FuncAnimation # Define the cubic polynomial function def cubic_polynomial(x): return x**3 - 3*x**2 + 2*x + 1 # Create the figure and axis fig, ax = plt.subplots(figsize=(16, 9)) fig.patch.set_facecolor('black') ax.set_facecolor('black') ax.set_xlim(0, 3) ax.set_ylim(0, 5) ax.set_xlabel('X', color='white') ax.set_ylabel('Y', color='white') ax.tick_params(axis='x', colors='white') ax.tick_params(axis='y', colors='white') ax.grid(False) # Plot the cubic polynomial function x_vals = np.linspace(0, 3, 1000) y_vals = cubic_polynomial(x_vals) curve, = ax.plot(x_vals, y_vals, color='red', linewidth=1) # Initialize rectangles rectangles = [] # Function to update the rectangles def update(frame): num_rects = 10 + frame * 10 # Increase number of rectangles from 10 to 1000 x_rects = np.linspace(0, 3, num_rects + 1) y_rects = cubic_polynomial(x_rects) width = x_rects[1] - x_rects[0] # Clear previous rectangles for rect in rectangles: rect.remove() rectangles.clear() # Plot new rectangles for i in range(num_rects): rect = ax.fill_between([x_rects[i], x_rects[i+1]], 0, y_rects[i], color='purple', alpha=0.5) rectangles.append(rect) return rectangles # Create the animation ani = FuncAnimation(fig, update, frames=100, interval=100, blit=False) plt.show() ``` ### Explanation: 1. **Cubic Polynomial Function**: The function `cubic_polynomial(x)` defines a cubic polynomial that we will integrate. 2. **Figure Setup**: The figure and axis are set up with a dark background and white text for better visibility. 3. **Curve Plotting**: The cubic polynomial is plotted using `ax.plot`. 4. **Rectangles Initialization**: Rectangles are initialized as an empty list. 5. **Update Function**: The `update` function increases the number of rectangles from 10 to 1000 over time. Each frame increases the resolution of the rectangles, demonstrating the concept of integration as the rectangles get smaller and more closely approximate the area under the curve. 6. **Animation**: The `FuncAnimation` function is used to animate the process, with the number of frames set to 100 and an interval of 100 milliseconds between frames. This script will visualize the process of integration by approximating the area under the cubic polynomial curve with increasingly finer rectangles.
            
            Sin and Cos relation to triangles and circles:
            Prompt: Imagine a vector rotating, project its x and y components to make a triangle, and sketch its path to make a circle. 
            Response: ```python import numpy as np import matplotlib matplotlib.use('Qt5Agg') import matplotlib.pyplot as plt from matplotlib.animation import FuncAnimation # Define the fixed point and vector length fixed_point = (0, 0) vector_length = 5 # Create the figure and axis fig, ax = plt.subplots(figsize=(16, 9)) fig.patch.set_facecolor('black') ax.set_facecolor('black') ax.set_xlim(-6, 6) ax.set_ylim(-6, 6) ax.set_xlabel('X', color='white') ax.set_ylabel('Y', color='white') ax.tick_params(axis='x', colors='white') ax.tick_params(axis='y', colors='white') ax.grid(False) # Initialize the vector, triangle, and circle vector, = ax.plot([], [], color='red', linewidth=1) triangle, = ax.plot([], [], color='purple', linewidth=1) circle, = ax.plot([], [], color='white', linewidth=1, linestyle='--') # Function to update the vector, triangle, and circle def update(frame): angle = np.radians(frame) x_end = fixed_point[0] + vector_length * np.cos(angle) y_end = fixed_point[1] + vector_length * np.sin(angle) # Update the vector vector.set_data([fixed_point[0], x_end], [fixed_point[1], y_end]) # Calculate the projected x and y components x_proj = fixed_point[0] + vector_length * np.cos(angle) y_proj = fixed_point[1] y_proj_end = fixed_point[1] + vector_length * np.sin(angle) # Update the triangle triangle.set_data([fixed_point[0], x_proj, x_end, fixed_point[0]], [fixed_point[1], y_proj, y_proj_end, fixed_point[1]]) # Update the circle circle_x = fixed_point[0] + vector_length * np.cos(np.linspace(0, 2*np.pi, 100)) circle_y = fixed_point[1] + vector_length * np.sin(np.linspace(0, 2*np.pi, 100)) circle.set_data(circle_x, circle_y) return vector, triangle, circle # Create the animation ani = FuncAnimation(fig, update, frames=np.arange(0, 360, 2), interval=50, blit=True) plt.show() ``` ### Explanation: 1. **Fixed Point and Vector Length**: The vector is fixed at the origin `(0, 0)` and has a fixed length of 5 units. 2. **Figure Setup**: The figure and axis are set up with a dark background and white text for better visibility. 3. **Vector, Triangle, and Circle Initialization**: The vector, triangle, and circle are initialized as empty plots. 4. **Update Function**: The `update` function calculates the new position of the vector based on the current angle of rotation. The x and y components of the vector are projected onto the x and y axes, respectively, forming a triangle. Additionally, the circle is updated to show the path traced by the rotating vector. 5. **Animation**: The `FuncAnimation` function is used to animate the process, with the angle of rotation increasing from 0 to 360 degrees in steps of 2 degrees. The interval between frames is set to 50 milliseconds. This script will visualize a vector rotating around a fixed point, with its x and y components projected onto the axes, forming a triangle, and the circle traced by the vector is also shown.
            
            prompt: make a dot rotate on the perimeter of circle and join the x and y axis projection with the center to make a triangle
            response:``````python import numpy as np import matplotlib matplotlib.use('Qt5Agg') import matplotlib.pyplot as plt from matplotlib.animation import FuncAnimation # Create the figure and axis fig, ax = plt.subplots(figsize=(16, 9)) fig.patch.set_facecolor('black') ax.set_facecolor('black') ax.set_xlim(-6, 6) ax.set_ylim(-6, 6) ax.set_aspect('equal') ax.grid(False) ax.set_axis_off() # Initialize the circle, vector, and triangle circle, = ax.plot([], [], color='white', linewidth=1, linestyle='--') vector, = ax.plot([], [], color='red', linewidth=1) triangle, = ax.plot([], [], color='purple', linewidth=1) # Function to update the circle, vector, and triangle def update(frame): angle = np.radians(frame) radius = 5 # Update the circle circle_x = radius * np.cos(np.linspace(0, 2*np.pi, 100)) circle_y = radius * np.sin(np.linspace(0, 2*np.pi, 100)) circle.set_data(circle_x, circle_y) # Update the vector x_end = radius * np.cos(angle) y_end = radius * np.sin(angle) vector.set_data([0, x_end], [0, y_end]) # Update the triangle triangle.set_data([0, x_end, 0, 0], [0, 0, y_end, 0]) return circle, vector, triangle # Create the animation ani = FuncAnimation(fig, update, frames=np.arange(0, 360, 2), interval=50, blit=True) plt.show() ``` ### Explanation: 1. **Figure Setup**: The figure and axis are set up with a dark background and no grid or axes for better visualization. 2. **Circle, Vector, and Triangle Initialization**: The circle, vector, and triangle are initialized as empty plots. 3. **Update Function**: The `update` function calculates the new position of the vector based on the current angle of rotation. The x and y components of the vector are projected onto the x and y axes, respectively, forming a triangle. Additionally, the circle is updated to show the path traced by the rotating vector. 4. **Animation**: The `FuncAnimation` function is used to animate the process, with the angle of rotation increasing from 0 to 360 degrees in steps of 2 degrees. The interval between frames is set to 50 milliseconds. This script will visualize a vector rotating around a fixed point, with its x and y components projected onto the axes, forming a triangle, and the circle traced by the vector is also shown.```
            
            
            Prompt: show me a circular linked list
            Reponse: ```

import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

matplotlib.use('Qt5Agg')

# Define the circular linked list nodes
class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

# Create a circular linked list with 5 nodes
head = Node(1)
current = head
for i in range(2, 6):
    current.next = Node(i)
    current = current.next
current.next = head  # Make it circular

# Create the figure and axis
fig, ax = plt.subplots(figsize=(10, 10))
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.set_xlim(-6, 6)
ax.set_ylim(-6, 6)
ax.set_aspect('equal')
ax.grid(False)
ax.set_axis_off()

# Initialize the boxes and lines
boxes = []
tails = []
lines = []

# Function to update the boxes and lines
def update(frame):
    # Clear previous boxes and lines
    for box in boxes:
        box.remove()
    for tail in tails:
        tail.remove()
    for line in lines:
        line.remove()
    boxes.clear()
    tails.clear()
    lines.clear()

    # Plot new boxes and lines
    current = head
    num_nodes = 5
    radius = 4
    for i in range(num_nodes):
        angle = 2 * np.pi * i / num_nodes - np.pi / 2
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)

        # Create boxes
        box = ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, color='purple', alpha=0.5))
        boxes.append(box)

        # Create tail boxes
        tail = ax.add_patch(plt.Rectangle((x + 0.5, y - 0.5), 1, 1, color='green', alpha=0.5))
        tails.append(tail)

        # Add text
        ax.text(x, y, str(current.value), ha='center', va='center', color='white')

        # Draw lines
        if i < frame:
            next_angle = 2 * np.pi * ((i + 1) % num_nodes) / num_nodes - np.pi / 2
            next_x = radius * np.cos(next_angle)
            next_y = radius * np.sin(next_angle)
            line, = ax.plot([x + 1, next_x - 0.5], [y, next_y], color='white', linewidth=1)
            lines.append(line)

        current = current.next

    return boxes + tails + lines

# Create the animation
ani = FuncAnimation(fig, update, frames=np.arange(0, 6, 0.1), interval=200, blit=False)
plt.show()```
         
            Data structure, linked list basic:
            Prompt: show me a basic linked list
            Response:```
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Define the linked list nodes
class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

# Create a linked list with 5 nodes
head = Node(1)
current = head
for i in range(2, 6):
    current.next = Node(i)
    current = current.next

# Create the figure and axis
fig, ax = plt.subplots(figsize=(16, 9))
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.set_xlim(-1, 8)
ax.set_ylim(-1, 6)
ax.set_xlabel('X', color='white')
ax.set_ylabel('Y', color='white')
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')
ax.grid(False)
ax.set_axis_off()

# Initialize the boxes and lines
boxes = []
lines = []

# Function to update the boxes and lines
def update(frame):
    # Clear previous boxes and lines
    for box in boxes:
        box.remove()
    for line in lines:
        line.remove()
    boxes.clear()
    lines.clear()

    # Plot new boxes and lines
    current = head
    x_pos = 0
    while current and x_pos <= frame:
        # Divide each box into 2 boxes
        box1 = ax.add_patch(plt.Rectangle((x_pos * 1.5, 2), 0.5, 1, color='purple', alpha=0.5))
        box2 = ax.add_patch(plt.Rectangle((x_pos * 1.5 + 0.5, 2), 0.5, 1, color='blue', alpha=0.5))
        boxes.extend([box1, box2])

        # Add text to each box
        ax.text(x_pos * 1.5 + 0.25, 2.5, 'head', ha='center', va='center', color='white')
        ax.text(x_pos * 1.5 + 0.75, 2.5, 'tail', ha='center', va='center', color='white')

        if current.next and x_pos < frame:
            # Make the line go from the middle of the second smaller box to the middle of the first smaller box of the next node
            line, = ax.plot([x_pos * 1.5 + 0.75, (x_pos + 1) * 1.5 + 0.25], [2.5, 2.5], color='white', linewidth=1)
            lines.append(line)

        # Color the first box of the head node red
        if x_pos == 0:
            head_box = ax.add_patch(plt.Rectangle((x_pos * 1.5, 2), 0.5, 1, color='purple', alpha=0.5))
            boxes.append(head_box)

        x_pos += 1
        current = current.next

    return boxes + lines

# Create the animation
ani = FuncAnimation(fig, update, frames=np.arange(0, 8, 0.1), interval=200, blit=False)
plt.show()```
         
         
         For swapping use:
         # Function to swap two squares with a 2-point curve
def swap(x1, x2):
    if x1 == x2:
        return

    # Calculate the curve points
    y_mid = 1  # Midpoint height
    x_mid = (x1 + x2) / 2

    # Create the curve path
    t = np.linspace(0, 1, 100)
    x_path1 = x1 + (x2 - x1) * t
    y_path1 = y_mid * np.sin(np.pi * t)
    x_path2 = x2 + (x1 - x2) * t
    y_path2 = y_mid * np.sin(np.pi * t)

    # Animate the swap
    for i in range(100):
        # Move the first square along the curve
        squares[x1].set_xy((x_path1[i], y_path1[i]))
        texts[x1].set_position((x_path1[i] + 0.5, y_path1[i] + 0.5))

        # Move the second square along the curve
        squares[x2].set_xy((x_path2[i], y_path2[i]))
        texts[x2].set_position((x_path2[i] + 0.5, y_path2[i] + 0.5))

        # Pause to show the movement
        plt.pause(0.01)

    # Update the final positions
    squares[x1].set_xy((x2, 0))
    texts[x1].set_position((x2 + 0.5, 0.5))
    squares[x2].set_xy((x1, 0))
    texts[x2].set_position((x1 + 0.5, 0.5))

    # Swap the references in the lists
    squares[x1], squares[x2] = squares[x2], squares[x1]
    texts[x1], texts[x2] = texts[x2], texts[x1]

# Example usage of the swap function
swap(0, 9)

plt.show()
         """


    def _build_context(self, message: str) -> str:
        context = (
            f"The message is: {message}\n"



        )
        return context

    def send_message_to_deep(self, message: str) -> None:
        prompting.messages = prompting.messages[-3:] + [message]
        full_context = self._build_context(message)
        prompting.output = ""

        prompting.shouldUpdate = "f"

        def streaming_thread():
            for attempt in range(self.max_retries):
                try:
                    stream = self.client.chat.completions.create(
                        model="deepseek-coder",
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
