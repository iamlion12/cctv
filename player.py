import os
import re
import sys
import vlc
import mask_rcnn
import numpy as np
from db import db_api
import tensorflow as tf
from keras.models import load_model
from keras.preprocessing import image

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QFrame,
                             QHBoxLayout, QPushButton, QSlider, QVBoxLayout,
                             QAction, QFileDialog, QDateTimeEdit, QLineEdit,
                             QListWidget, QGraphicsDropShadowEffect, QLabel,
                             QMessageBox, QDesktopWidget)

class Path_Line_Edit(QLineEdit):
    def __init__(self, master=None):
        super(Path_Line_Edit, self).__init__(master)
        self.master = master

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter:
            self.master.selectfolder(self.text())
        else:
            super(Path_Line_Edit, self).keyPressEvent(event)

class AnalyseWorker(QtCore.QRunnable):
    """
    init
    """

    def __init__(self, file, master):
        super(AnalyseWorker, self).__init__()
        self.master = master
        self.file = file

    @QtCore.pyqtSlot()
    def run(self):

        def replace(l, step = 5):

            for i in range(0, len(l), step):
                if l[i:i+step].count(1) > l[i:i+step].count(0):
                    if i+step < len(l):
                        for j in range(i, i+step): l[j] = 1
                    else:
                        for j in range(i, len(l)): l[j] = 1
                else:
                    if i+step < len(l):
                        for j in range(i, i+step): l[j] = 0
                    else:
                        for j in range(i, len(l)): l[j] = 0
            return l

        def find_time(l, end = 0):

            time = []

            while True:
                try:
                    start = end + l[end:].index(1)
                    print("start ", start)
                    try:
                        end = start + l[start:].index(0)
                        time.append((start, end))
                        print("end ", end)

                    except ValueError:
                        time.append((start, len(l)))
                        break
                except ValueError:
                    break

            return time

        print("Starting...")

        print("Getting access to database...")

        db = db_api.create_connection(os.path.join(os.getcwd(), 'db','data.db'))

        file_id = db_api.select_file(db, self.file)
        if file_id:
            print("File already in db, skiping...")
        else:
            print("Adding filename in database...")
            with db:
                file_id = db_api.add_file(db, self.file)

        print("Extracting frames from video...")
        path_to_file = os.path.join(self.master.path, self.file)
        print(path_to_file)
        command  = r"ffmpeg -i {0} -vf fps=1 ./frames/%d.jpg".format(re.escape(path_to_file))
        os.system(command)

        frames = os.listdir('./frames/')
        print("Starting analyse {0} frames".format(len(frames)))

        rcnn_model = mask_rcnn.load_mask_rcnn()
        print("Successfully loaded 1st model...")

        model = load_model("./model.h5")
        model._make_predict_function()
        graph = tf.get_default_graph()

        print("Successfully loaded 2nd model... Starting analyse")

        print("Startin analyse...")

        labels = {}

        for framefile in frames:

            print("Frame #{0}, {1} files until finish.".format(framefile[:-4], len(frames)-len(labels.keys())))

            peoples = mask_rcnn.select_people(rcnn_model, image.img_to_array(image.load_img("./frames/"+framefile)))
            with graph.as_default():
                results = list([model.predict(np.array([image.img_to_array(image.array_to_img(people).resize((128,128)))])) for people in peoples])
            labels[int(framefile[:-4])] = list([np.argmax(out) for out in results])

        print("Stopping analyse")

        del model
        del rcnn_model

        warning_points = [1 if 1 in labels[key] else 0 for key in sorted(labels.keys())]

        warning_points = replace(warning_points)

        import datetime

        times = find_time(warning_points)

        with db:
            for time in times:
                db_api.add_time(db, (str(datetime.timedelta(seconds=time[0])), str(datetime.timedelta(seconds=time[1])), file_id,))

        os.system('rm frames/*.jpg')

        self.master.stop_analyse()


class Analyse(QMainWindow):
    def __init__(self, master=None):
        super(Analyse, self).__init__(master)

        self.master = master

        self.initUI()

    def initUI(self):

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.statuslabel = QLabel("Please wait...")

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        layout = QVBoxLayout()
        layout.addWidget(self.statuslabel)
        self.widget.setLayout(layout)
        self.centerOnScreen()

    def on(self):

        self.activateWindow()
        self.show()

    def off(self):

        self.close()

    def centerOnScreen(self):
        '''
        centerOnScreen() Centers the window on the screen.
        '''
        resolution = QDesktopWidget().screenGeometry()
        self.move((resolution.width() / 2) - (self.frameSize().width() / 2),
                    (resolution.height() / 2) - (self.frameSize().height() / 2))

    def closeEvent(self, event):
        self.master.setEnabled(True)
        event.accept()



class Player(QMainWindow):
    """
    A simple Media Player using VLC and Qt
    """
    def __init__(self, master=None):
        super().__init__()
        self.setWindowTitle("CCTV by @XII")

        # creating a basic vlc instance
        self.instance = vlc.Instance()
        # creating an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()

        self.path = ''

        self.createUI()
        self.isPaused = False
        self.setStyleSheet(open("style.qss", "r").read())

    def createUI(self):
        """
        Set up the user interface, signals & slots
        """
        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        # Video widget
        self.videoframe = QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window,
                               QtGui.QColor(0,0,0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        #time value
        self.timevalue = QDateTimeEdit()
        self.timevalue.setDisplayFormat('hh:mm:ss.z')
        # self.timevalue.dateTimeChanged.connect(lambda x: self.setTime(self.timevalue.time().msecsSinceStartOfDay()))

        #position slider
        self.positionslider = QSlider(QtCore.Qt.Horizontal, self)
        self.positionslider.setToolTip("Position")
        self.positionslider.setMaximum(1000)
        self.positionslider.sliderMoved.connect(self.setPosition)

        #play button
        self.hbuttonbox = QHBoxLayout()
        self.playbutton = QPushButton("Play")
        self.hbuttonbox.addWidget(self.playbutton)
        self.playbutton.clicked.connect(self.PlayPause)

        #stop button
        self.stopbutton = QPushButton("Stop")
        self.hbuttonbox.addWidget(self.stopbutton)
        self.stopbutton.clicked.connect(self.Stop)

        #analyse button
        self.analysebutton = QPushButton('Analyse')
        self.analysebutton.clicked.connect(self.start_analyse)
        self.analyse_window = Analyse(self)
        self.analyse_window.off()
        self.threadpool = QtCore.QThreadPool()

        self.pathinput = Path_Line_Edit(self)

        self.folderbutton = QPushButton('Select folder')
        self.folderbutton.clicked.connect(lambda x: self.selectfolder(foldername=''))

        self.fileslist_label = QLabel("Playlist:")

        self.fileslist = QListWidget()
        self.fileslist.itemClicked.connect(self.selectfile)

        self.warnings_label = QLabel("Warnings time:")

        self.warningslist = QListWidget()
        # self.fileslist.itemClicked.connect(self.selectfile)

        self.leftvboxlayout = QVBoxLayout()
        self.leftvboxlayout.addWidget(self.fileslist_label)
        self.leftvboxlayout.addWidget(self.fileslist)
        self.leftvboxlayout.addStretch(1)
        self.leftvboxlayout.addWidget(self.warnings_label)
        self.leftvboxlayout.addWidget(self.warningslist)
        self.leftvboxlayout.addStretch(1)
        self.leftvboxlayout.addWidget(self.analysebutton)
        self.leftvboxlayout.addWidget(self.pathinput)
        self.leftvboxlayout.addWidget(self.folderbutton)

        #volume slider
        self.hbuttonbox.addStretch(1)
        self.volumeslider = QSlider(QtCore.Qt.Horizontal, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip("Volume")
        self.hbuttonbox.addWidget(self.volumeslider)
        self.volumeslider.valueChanged.connect(self.setVolume)

        #setting up layouts
        self.vboxlayout = QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe)
        self.vboxlayout.addWidget(self.timevalue)
        self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.mainlayout = QHBoxLayout()
        self.mainlayout.addLayout(self.leftvboxlayout)
        self.mainlayout.addLayout(self.vboxlayout, 60)

        self.widget.setLayout(self.mainlayout)

        open = QAction(QtGui.QIcon('open.png'), "&Open", self)
        open.setShortcut('Ctrl+O')
        open.setStatusTip('Open File')
        open.triggered.connect(lambda x: self.OpenFile(filename=''))
        exit = QAction("&Exit", self)
        exit.triggered.connect(sys.exit)
        menubar = self.menuBar()
        filemenu = menubar.addMenu("&File")
        filemenu.addAction(open)
        filemenu.addAction(exit)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.updateUI)

        #creates connection to db
        self.db = db_api.create_connection(os.path.join(os.getcwd(), 'db','data.db'))

    def PlayPause(self):
        """
        Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.isPaused = True

        else:
            if self.mediaplayer.play() == -1:
                self.OpenFile()
                return
            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.timer.start()
            self.isPaused = False

    def start_analyse(self):

        try:
            file = self.fileslist.currentItem().text()
        except AttributeError:
            QMessageBox.information(self, "Warning!", "You should to select a file.")
            return

        self.setEnabled(False)
        self.analyse_window.on()

        worker = AnalyseWorker(file, self)
        self.threadpool.start(worker)

    def stop_analyse(self):
        self.analyse_window.off()
        self.setEnabled(True)


    def Stop(self):
        """
        Stop player
        """
        self.mediaplayer.stop()
        self.timevalue.setTime(QtCore.QTime.fromMSecsSinceStartOfDay(self.mediaplayer.get_position()*self.duration))
        self.playbutton.setText("Play")

    def selectfile(self, item):
        self.OpenFile(filename = self.path+'/'+item.text())

    def check_warnings_time(self, filename):
        with self.db:
            file_id = db_api.select_file(self.db, filename)
            if file_id:

                #if file in db, then add warning times in list bellow
                timelist = db_api.select_time(self.db, file_id)

                self.warningslist.clear()
                for time in timelist:
                    self.warningslist.addItem(time[0]+"-"+time[1])

            else:
                self.warningslist.clear()
                self.warningslist.addItem("There is nothing to show.")

    def OpenFile(self, filename=''):
        """
        Open a media file in a MediaPlayer
        """
        if filename == '':
            filename = QFileDialog.getOpenFileName(self, "Open File", './')[0]
        if not filename:
            return

        self.check_warnings_time(os.path.split(filename)[1])

        # create the media
        self.media = self.instance.media_new(filename)

        # put the media in the media player
        self.mediaplayer.set_media(self.media)

        # parse the metadata of the file
        self.media.parse_async()

        fullpath = re.escape(filename)

        # get video duration
        time = os.popen("ffmpeg -i {0}".format(fullpath) + " 2>&1 | grep Duration | awk '{print $2}' | tr -d ,").read().split(':')
        self.duration = int(3600000*int(time[0])+60000*int(time[1])+1000*float(time[2]))

        # set the title of the track as window title
        self.setWindowTitle("CCTV: " + self.media.get_meta(0))

        # the media player has to be 'connected' to the QFrame
        # (otherwise a video would be displayed in it's own window)
        # this is platform specific!
        # you have to give the id of the QFrame (or similar object) to
        # vlc, different platforms have diffqerent functions for this
        if sys.platform == "linux": # for Linux using the X Server
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32": # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin": # for MacOS
            self.mediaplayer.set_agl(self.videoframe.windId())
        self.PlayPause()

    def setVolume(self, Volume):
        """
        Set the volume
        """
        self.mediaplayer.audio_set_volume(Volume)

    def setPosition(self, position):
        """
        Set the position
        """
        # setting the position to where the slider was dragged
        self.mediaplayer.set_position(position / 1000.0)
        # the vlc MediaPlayer needs a float value between 0 and 1, Qt
        # uses integer variables, so you need a factor; the higher the
        # factor, the more precise are the results
        # (1000 should be enough)
        self.timevalue.setTime(QtCore.QTime.fromMSecsSinceStartOfDay(self.mediaplayer.get_position()*self.duration))

    def setTime(self, time):
        """
        Set time to display
        """
        self.mediaplayer.set_time(time)

    def selectfolder(self, foldername=''):
        if foldername == '':
            foldername = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
            self.pathinput.setText(foldername)
            self.path = foldername
        if not foldername:
            return

        files = os.listdir(foldername)
        self.path = foldername
        self.fileslist.clear()
        for file in files:
            self.fileslist.addItem(file)

    def updateUI(self):
        """
        updates the user interface
        """
        # setting the slider to the desired position
        self.positionslider.setValue(self.mediaplayer.get_position() * 1000)
        self.timevalue.setTime(QtCore.QTime.fromMSecsSinceStartOfDay(self.mediaplayer.get_position()*self.duration))
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())

        if not self.mediaplayer.is_playing():
            # no need to call this function if nothing is played
            self.timer.stop()
            if not self.isPaused:
                # after the video finished, the play button stills shows
                # "Pause", not the desired behavior of a media player
                # this will fix it
                self.Stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = Player()
    player.show()
    player.resize(1280, 720)
    if sys.argv[1:]:
        player.OpenFile(sys.argv[1])
    sys.exit(app.exec_())
