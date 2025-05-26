import threading
import time
import subprocess
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QEvent

class CustomEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, plot_path):
        super().__init__(CustomEvent.EVENT_TYPE)
        self.plot_path = plot_path
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class PlotThread(threading.Thread):
    def __init__(self, formatted_python, groq_api2, groq_api4):
        threading.Thread.__init__(self)
        self.groq_api2 = groq_api2
        self.formatted_python = formatted_python
        self.groq_api4 = groq_api4
        self.plot_window = None
        self.exception_count = 0
        self.session_id = time.time()  # Use timestamp as session ID

    def run(self):
        while True:
            try:
                with open('src.graph', 'w') as file:
                    file.write(self.formatted_python)

                subprocess.run(['python', 'src.graph'], check=True)

                plot_files = [f for f in os.listdir() if f.endswith(('.png', '.pdf'))]

                if plot_files:
                    latest_plot = max(plot_files, key=os.path.getmtime)
                    QApplication.instance().postEvent(QApplication.instance().activeWindow(),
                                                    CustomEvent(latest_plot))
                break

            except Exception as e:
                self.exception_count += 1
                if self.exception_count >= 1:
                    print("Too many exceptions in this session. Aborting.")
                    x = f"The following code failed to execute:\n\n{self.formatted_python} with exception " + str(e)
                    print(x)
                    self.groq_api2.send_message_to_groq(x)
                    break


class PlotWindow(QMainWindow):
    def __init__(self, plot_path):
        super().__init__()
        self.setWindowTitle("Plot Viewer")
        self.setGeometry(100, 100, 600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        if plot_path.endswith('.png'):
            pixmap = QPixmap(plot_path)
            label = QLabel()
            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            figure = plt.figure()
            canvas = FigureCanvas(figure)
            layout.addWidget(canvas)
            plt.close(figure)
