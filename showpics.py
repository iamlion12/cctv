import os.path

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainterPath
from PyQt5.QtWidgets import (QMainWindow, QGraphicsView,
                             QGraphicsScene, QFileDialog,
                             QPushButton, QHBoxLayout,
                             QVBoxLayout, QWidget)

class pushButton(QPushButton):
    def __init__(self, function, arrow_key, master=None):
        super(QPushButton, self).__init__(master)
        self.master = master
        self.arrow_key = arrow_key
        self.function = function

    def keyPressEvent(self, event):
        if event.key() == self.arrow_key:
            f = self.function
            self.master.f()
        else:
            super(pushButton, self).keyPressEvent(event)

class pictureViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.setStyleSheet(open("pics_style.qss", "r").read())

        self.image_viewer = QtImageViewer()

        self.next_btn = QPushButton()
        self.next_btn.setObjectName('next')
        self.next_btn.setFixedSize(70, 140)

        self.previous_btn = QPushButton()
        self.previous_btn.setObjectName('previous')
        self.previous_btn.setFixedSize(70, 140)

        self.current_image = 0
        self.images = None

        ctrl_btns_lyt = QHBoxLayout()
        ctrl_btns_lyt.addWidget(self.previous_btn)
        ctrl_btns_lyt.addStretch(1)
        ctrl_btns_lyt.addWidget(self.next_btn)

        main_lyt = QVBoxLayout()
        main_lyt.setContentsMargins(0,0,0,0)
        main_lyt.addLayout(ctrl_btns_lyt)

        self.setCentralWidget(self.image_viewer)
        self.image_viewer.setLayout(main_lyt)

        self.next_btn.clicked.connect(self.next)
        self.previous_btn.clicked.connect(self.previous)
        self.resize(800, 512)

    def start(self, filename):
        self.filename = os.path.splitext(filename)[0]
        self.current_image = 0
        self.images = {int(os.path.splitext(img)[0]):img for img in os.listdir(os.path.join('./warnings/', self.filename))}
        self.show_image(self.current_image)

    def show_image(self, file_number):
        if self.filename:
            if file_number in self.images.keys():
                self.image_viewer.loadImageFromFile(os.path.join('./warnings/', self.filename, self.images[file_number]))
            else:
                return

    def next(self):

        if self.current_image+1 > len(self.images)-1:
            self.current_image = 0
        else:
            self.current_image += 1

        self.show_image(self.current_image)

    def previous(self):

        if self.current_image-1 < 0:
            self.current_image = len(self.images) - 1
        else:
            self.current_image -= 1

        self.show_image(self.current_image)

class QtImageViewer(QGraphicsView):

    # Mouse button signals emit image scene (x, y) coordinates.
    # !!! For image (row, column) matrix indexing, row = y and column = x.
    leftMouseButtonPressed = pyqtSignal(float, float)
    rightMouseButtonPressed = pyqtSignal(float, float)
    leftMouseButtonReleased = pyqtSignal(float, float)
    rightMouseButtonReleased = pyqtSignal(float, float)
    leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)

    def __init__(self, master=None):
        QGraphicsView.__init__(self, master)

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Store a local handle to the scene's current image pixmap.
        self._pixmapHandle = None

        # Image aspect ratio mode.
        # !!! ONLY applies to full image. Aspect ratio is always ignored when zooming.
        #   Qt.IgnoreAspectRatio: Scale image to fit viewport.
        #   Qt.KeepAspectRatio: Scale image to fit inside viewport, preserving aspect ratio.
        #   Qt.KeepAspectRatioByExpanding: Scale image to fill the viewport, preserving aspect ratio.
        self.aspectRatioMode = Qt.KeepAspectRatio

        # Scroll bar behaviour.
        #   Qt.ScrollBarAlwaysOff: Never shows a scroll bar.
        #   Qt.ScrollBarAlwaysOn: Always shows a scroll bar.
        #   Qt.ScrollBarAsNeeded: Shows a scroll bar only when zoomed.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Stack of QRectF zoom boxes in scene coordinates.
        self.zoomStack = []

        # Flags for enabling/disabling mouse interaction.
        self.canZoom = True
        self.canPan = True

    def hasImage(self):
        """ Returns whether or not the scene contains an image pixmap.
        """
        return self._pixmapHandle is not None

    def clearImage(self):
        """ Removes the current image pixmap from the scene if it exists.
        """
        if self.hasImage():
            self.scene.removeItem(self._pixmapHandle)
            self._pixmapHandle = None

    def pixmap(self):
        """ Returns the scene's current image pixmap as a QPixmap, or else None if no image exists.
        :rtype: QPixmap | None
        """
        if self.hasImage():
            return self._pixmapHandle.pixmap()
        return None

    def image(self):
        """ Returns the scene's current image pixmap as a QImage, or else None if no image exists.
        :rtype: QImage | None
        """
        if self.hasImage():
            return self._pixmapHandle.pixmap().toImage()
        return None

    def setImage(self, image):
        """ Set the scene's current image pixmap to the input QImage or QPixmap.
        Raises a RuntimeError if the input image has type other than QImage or QPixmap.
        :type image: QImage | QPixmap
        """
        if type(image) is QPixmap:
            pixmap = image
        elif type(image) is QImage:
            pixmap = QPixmap.fromImage(image)
        else:
            raise RuntimeError("ImageViewer.setImage: Argument must be a QImage or QPixmap.")
        if self.hasImage():
            self._pixmapHandle.setPixmap(pixmap)
        else:
            self._pixmapHandle = self.scene.addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))  # Set scene size to image size.
        self.updateViewer()

    def loadImageFromFile(self, fileName=""):
        """
        Load an image from file.
        """
        image = QImage(fileName)
        self.setImage(image)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        if not self.hasImage():
            return
        if len(self.zoomStack) and self.sceneRect().contains(self.zoomStack[-1]):
            self.fitInView(self.zoomStack[-1], Qt.IgnoreAspectRatio)  # Show zoomed rect (ignore aspect ratio).
        else:
            self.zoomStack = []  # Clear the zoom stack (in case we got here because of an invalid zoom).
            self.fitInView(self.sceneRect(), self.aspectRatioMode)  # Show entire image (use current aspect ratio mode).

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        self.updateViewer()

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            if self.canPan:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.leftMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.RightButton:
            if self.canZoom:
                self.setDragMode(QGraphicsView.RubberBandDrag)
            self.rightMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        QGraphicsView.mouseReleaseEvent(self, event)
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.leftMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.RightButton:
            if self.canZoom:
                viewBBox = self.zoomStack[-1] if len(self.zoomStack) else self.sceneRect()
                selectionBBox = self.scene.selectionArea().boundingRect().intersected(viewBBox)
                self.scene.setSelectionArea(QPainterPath())  # Clear current selection area.
                if selectionBBox.isValid() and (selectionBBox != viewBBox):
                    self.zoomStack.append(selectionBBox)
                    self.updateViewer()
            self.setDragMode(QGraphicsView.NoDrag)
            self.rightMouseButtonReleased.emit(scenePos.x(), scenePos.y())

    def mouseDoubleClickEvent(self, event):
        """ Show entire image.
        """
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.leftMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.RightButton:
            if self.canZoom:
                self.zoomStack = []  # Clear zoom stack.
                self.updateViewer()
            self.rightMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        QGraphicsView.mouseDoubleClickEvent(self, event)


if __name__ == '__main__':
    import sys
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        try:
            from PyQt4.QtGui import QApplication
        except ImportError:
            raise ImportError("ImageViewerQt: Requires PyQt5 or PyQt4.")
    print('Using Qt ' + QT_VERSION_STR)

    def handleLeftClick(x, y):
        row = int(y)
        column = int(x)
        print("Clicked on image pixel (row="+str(row)+", column="+str(column)+")")

    # Create the application.
    app = QApplication(sys.argv)

    window = pictureViewer()
    window.show()
    window.start('cut.mp4')
    sys.exit(app.exec_())
