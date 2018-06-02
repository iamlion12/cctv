import os
import sys

from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QPushButton, QFrame,
                             QVBoxLayout, QHBoxLayout,
                             QApplication)

from PyQt5.QtGui import QPixmap

class pictureViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.next_btn = QPushButton()
        self.previous_btn = QPushButton()

        self.current_image = 0
        self.images = None

        ctrl_btns_lyt = QHBoxLayout()
        ctrl_btns_lyt.addWidget(self.next_btn)
        ctrl_btns_lyt.addWidget(self.previous_btn)

        self.graphic_scene = QGraphicScene

        main_lyt = QVBoxLayout()
        main_lyt.addWidget(QFrame)
        main_lyt.addLayout(control_btns_lyt)

        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.widget.setLayout(main_lyt)

    def start(self, filename):
        self.current_image = 0
        self.images = {int(os.path.splitext(img)[0]):img for img in os.listdir(os.path.join(os.path.splitext(filename)[0]))}
        self.show_image()

    def show_image()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = pictureViewer()
    window.show()
    sys.exit(app.exec_())
