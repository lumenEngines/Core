import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.animation import FFMpegWriter


def move(source_x, target_x, target_y, squares, texts):
    if source_x == target_x and squares[source_x].get_y() == target_y:
        return

    y_start = squares[source_x].get_y()
    y_mid = (y_start + target_y) / 2 + 1
    x_mid = (source_x + target_x) / 2

    t = np.linspace(0, 1, 20)
    x_path = source_x + (target_x - source_x) * t
    y_path = y_start + (target_y - y_start) * t + np.sin(np.pi * t)

    return [(x_path[i], y_path[i]) for i in range(20)]


fig, ax = plt.subplots(figsize=(16, 9))
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.set_xlim(-1, 16)
ax.set_ylim(-1, 6)
ax.set_axis_off()

left_squares = []
right_squares = []
merged_squares = []
left_texts = []
right_texts = []
merged_texts = []

left = [4, 8, 11, 14, 19]
right = [1, 9, 18, 22, 25]


def init():
    for i, value in enumerate(left):
        square = ax.add_patch(plt.Rectangle((i, 4), 1, 1, color='purple', alpha=0.5))
        text = ax.text(i + 0.5, 4.5, str(value), ha='center', va='center', color='white')
        left_squares.append(square)
        left_texts.append(text)

    for i, value in enumerate(right):
        square = ax.add_patch(plt.Rectangle((i + 5, 4), 1, 1, color='blue', alpha=0.5))
        text = ax.text(i + 5.5, 4.5, str(value), ha='center', va='center', color='white')
        right_squares.append(square)
        right_texts.append(text)

    return left_squares + right_squares + left_texts + right_texts


def animate(frame):
    i, j = frame // 20, frame % 20

    if i < len(left) + len(right):
        if i < len(left):
            source = i
            squares = left_squares
            texts = left_texts
        else:
            source = i - len(left)
            squares = right_squares
            texts = right_texts

        path = move(source, i, 0, squares, texts)
        squares[source].set_xy(path[j])
        texts[source].set_position((path[j][0] + 0.5, path[j][1] + 0.5))

    return left_squares + right_squares + left_texts + right_texts


anim = FuncAnimation(fig, animate, init_func=init, frames=(len(left) + len(right)) * 20, interval=50, blit=True)

writer = FFMpegWriter(fps=30, metadata=dict(artist='Your Name'), bitrate=5000)
anim.save('merge_sort_animation.mp4', writer=writer)

plt.close(fig)