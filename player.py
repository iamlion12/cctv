import os
import re
import sys
import vlc
import time

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QFrame,
                             QVBoxLayout, QPushButton, QSlider, QHBoxLayout,
                             QAction, QFileDialog, QDateTimeEdit, QLineEdit,
                             QListWidget, QGraphicsDropShadowEffect, QLabel,
                             QMessageBox, QDesktopWidget, QProgressBar,
                             QGraphicsView, QGraphicsScene)

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainterPath

from db import db_api
from showpics import pictureViewer

class pathLineEdit(QLineEdit):
    def __init__(self, master=None):
        super(pathLineEdit, self).__init__(master)
        self.master = master

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter:
            self.master.select_folder(self.text())
        else:
            super(pathLineEdit, self).keyPressEvent(event)

class loadModules(QtCore.QRunnable):

    def __init__(self, master):
        super(loadModules, self).__init__()
        self.master = master

    @QtCore.pyqtSlot()
    def run(self):

        global load_model
        from keras.models import load_model

        global image
        from keras.preprocessing import image

        global tf
        import tensorflow as tf

        global mask_rcnn
        import mask_rcnn

        self.master.analyse_btn.setEnabled(True)


class AnalyseWorker(QtCore.QRunnable):
    """
    init
    """
    def __init__(self, file, master):
        super(AnalyseWorker, self).__init__()
        self.master = master
        self.master.on_analyse = True
        self.file = file

    @QtCore.pyqtSlot()
    def run(self):

        self.master.analyse_window.progress_bar.setValue(0)

        def draw_box(img, boxes, labels, color=[[0, 255, 0], [255, 0, 0]]):
            """Draw 3-pixel width bounding boxes on the given image array.
            color: list of 3 int values for RGB.
            """
            for label, box in zip(labels, boxes):

                y1, y2, x1, x2 = box
                img[y1:y1 + 2, x1:x2] = color[label]
                img[y2:y2 + 2, x1:x2] = color[label]
                img[y1:y2, x1:x1 + 2] = color[label]
                img[y1:y2, x2:x2 + 2] = color[label]

            return img

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
                    try:
                        end = start + l[start:].index(0)
                        time.append((start, end))

                    except ValueError:
                        time.append((start, len(l)))
                        break
                except ValueError:
                    break

            return time

        os.system('rm frames/*.jpg')

        self.master.analyse_window.status_lbl.setText("Starting...")

        self.master.analyse_window.status_lbl.setText("Getting access to database...")

        db = db_api.create_connection(os.path.join(os.getcwd(), 'db','data.db'))

        file_id = db_api.select_file(db, self.file)
        if file_id:
            self.master.analyse_window.status_lbl.setText("File already in db, skiping...")
        else:
            self.master.analyse_window.status_lbl.setText("Adding filename in database...")
            with db:
                file_id = db_api.add_file(db, self.file)

        self.master.analyse_window.status_lbl.setText("Extracting frames from video...")
        path_to_file = os.path.join(self.master.path, self.file)
        print(path_to_file)
        command  = r"ffmpeg -i {0} -vf fps=1 ./frames/%d.jpg".format(re.escape(path_to_file))
        os.system(command)
        self.master.analyse_window.status_lbl.setText("Loading models...")

        frames = os.listdir('./frames/')

        rcnn_model = mask_rcnn.load_mask_rcnn()
        self.master.analyse_window.status_lbl.setText("Successfully loaded 1st model, loading second model...")

        DEVICE = "/cpu:0"
        with tf.device(DEVICE):
            model = load_model("./model.h5")
        model._make_predict_function()
        graph = tf.get_default_graph()

        self.master.analyse_window.status_lbl.setText("Successfully loaded 2nd model...")

        self.master.analyse_window.status_lbl.setText("Starting analyse {0} frames".format(len(frames)))

        file = os.path.splitext(self.file)[0]
        warning_folder = os.path.join('./warnings', file)
        if not os.path.isdir(warning_folder): os.mkdir(warning_folder)

        labels = {}

        start = time.time()

        progress = 0
        progress_delta = 100/len(frames)

        for framefile in frames:

            files_until_finish = len(frames)-len(labels.keys())

            self.master.analyse_window.status_lbl.setText("Frame #{0}, {1} files until finish.".format(framefile[:-4], files_until_finish))

            img = image.img_to_array(image.load_img("./frames/"+framefile))

            peoples, boxes = mask_rcnn.select_people(rcnn_model, img)

            with graph.as_default():

                results = list([model.predict(np.expand_dims(
                    image.img_to_array(image.array_to_img(people).resize((128,128))), axis=0)) for people in peoples])

            labels[int(framefile[:-4])] = list([np.argmax(out) for out in results])

            img = draw_box(img, boxes, labels[int(framefile[:-4])])
            image.array_to_img(img).save(os.path.join(warning_folder, framefile))

            progress += progress_delta

            self.master.analyse_window.progress_bar.setValue(progress)

        end = time.time()

        self.master.analyse_window.status_lbl.setText('Done. Elapsed time: {0:.2f}s'.format(end - start))
        print('Done. Elapsed time: {0:.2f}s'.format(end - start))

        del model
        del rcnn_model

        warning_points = [1 if 1 in labels[key] else 0 for key in sorted(labels.keys())]

        warning_points = replace(warning_points)

        import datetime

        times = find_time(warning_points)

        with db:
            time_in_db = db_api.select_time(db, file_id)
            if not time_in_db:
                for _time in times:
                    db_api.add_time(db,
                                    (str(datetime.timedelta(seconds=_time[0])),
                                     str(datetime.timedelta(seconds=_time[1])),
                                     file_id,))

        self.master.stop_analyse()


class Analyse(QMainWindow):
    def __init__(self, master=None):
        super(Analyse, self).__init__(master)

        self.master = master

        self.initUI()

    def initUI(self):

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.setFixedSize(512, 128)

        self.status_lbl = QLabel("Please wait...")
        self.status_lbl.setObjectName('status_lbl')

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName('progress_bar')
        self.progress_bar.setValue(0)

        self.widget = QWidget(self)
        self.widget.setObjectName('analyse_wd')
        self.setCentralWidget(self.widget)

        lyt = QVBoxLayout()
        lyt.addWidget(self.status_lbl)
        lyt.addWidget(self.progress_bar)
        self.widget.setLayout(lyt)

    def on(self):

        self.activateWindow()
        self.show()
        self.centerOnScreen()

    def off(self):

        self.close()
        self.master.analyse_btn.setEnabled(True)

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

        self.initUI()
        self.isPaused = False
        self.setStyleSheet(open("style.qss", "r").read())

    def initUI(self):
        """
        Set up the user interface, signals & slots
        For better understaning, I made some shortcuts for variables,
        which is the instance of the QtWidgets classes.
        List of shortcuts(made):
        *btn - QPushButton;
        *lbl - QLabel;
        *slr - QSlider;
        *lyt - Q_lyt;
        *ctrl - ctrl;
        """
        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        #video widget
        self.videoframe = QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window,
                               QtGui.QColor(0,0,0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        #time value
        self.timevalue = QDateTimeEdit()
        self.timevalue.setDisplayFormat('hh:mm:ss')
        self.timevalue.setReadOnly(True)
        self.timevalue.setFixedSize(80, 30)

        #position slider
        self.position_slr = QSlider(QtCore.Qt.Horizontal, self)
        self.position_slr.setToolTip("Position")
        self.position_slr.setMaximum(1000)
        self.position_slr.sliderMoved.connect(self.set_position)

        #play button
        self.play_btn = QPushButton()
        self.play_btn.setProperty("onplay", True)
        self.play_btn.setObjectName("play")
        self.play_btn.clicked.connect(self.play_pause)

        #stop button
        self.stop_btn = QPushButton()
        self.stop_btn.setObjectName('stop')
        self.stop_btn.clicked.connect(self.stop)

        #analyse button
        self.analyse_btn = QPushButton('Analyse')
        self.analyse_btn.setObjectName('analyse')
        self.analyse_btn.setFixedSize(70, 28)
        self.analyse_btn.clicked.connect(self.start_analyse)
        self.analyse_window = Analyse(self)
        self.analyse_window.off()
        self.analyse_btn.setEnabled(False)
        self.on_analyse = False

        self.details_btn = QPushButton('Details')
        self.details_btn.setVisible(False)
        self.details_btn.setObjectName('details')
        self.details_btn.setFixedSize(70, 28)
        self.details_btn.clicked.connect(self.show_details)

        self.details_wd = pictureViewer()
        self.details_wd.close()

        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(1)
        worker = loadModules(self)
        self.threadpool.start(worker)

        self.path_input = pathLineEdit(self)
        self.path_input.setObjectName('path')

        self.folder_btn = QPushButton()
        self.folder_btn.setObjectName('folder')
        self.folder_btn.clicked.connect(lambda x: self.select_folder(foldername=''))

        self.fileslist_lbl = QLabel('Playlist:')
        self.fileslist_lbl.setObjectName('lbl')
        self.fileslist_lbl.setIndent(12)

        self.fileslist = QListWidget()
        self.fileslist.itemClicked.connect(self.select_file)

        self.warnings_lbl = QLabel('Warnings time:')
        self.warnings_lbl.setObjectName('lbl')
        self.warnings_lbl.setIndent(12)

        self.warningslist = QListWidget()

        #volume slider
        self.volume_slr = QSlider(QtCore.Qt.Horizontal, self)
        self.volume_slr.setMaximum(100)
        self.volume_slr.setValue(self.mediaplayer.audio_get_volume())
        self.volume_slr.setToolTip("Volume")
        self.volume_slr.valueChanged.connect(self.set_volume)

        #setting up layouts
        folder_lyt = QHBoxLayout()
        folder_lyt.addWidget(self.path_input)
        folder_lyt.addWidget(self.folder_btn)

        leftside_lyt = QVBoxLayout()
        leftside_lyt.setContentsMargins(0,10,0,0)
        leftside_lyt.addSpacing(6)
        leftside_lyt.addWidget(self.fileslist_lbl)
        leftside_lyt.addWidget(self.fileslist)

        analyse_btns = QHBoxLayout()
        analyse_btns.addWidget(self.details_btn)
        analyse_btns.addWidget(self.analyse_btn)
        leftside_lyt.addLayout(analyse_btns)

        leftside_lyt.addWidget(self.warnings_lbl)
        leftside_lyt.addWidget(self.warningslist)
        leftside_lyt.addLayout(folder_lyt)
        leftside_lyt.addSpacing(6)

        self.leftside_bg = QWidget()
        self.leftside_bg.setObjectName("leftside_bg")
        self.leftside_bg.setLayout(leftside_lyt)

        ctrl_lyt = QHBoxLayout()
        ctrl_lyt.addSpacing(20)
        ctrl_lyt.addWidget(self.play_btn)
        ctrl_lyt.setSpacing(0)
        ctrl_lyt.addWidget(self.stop_btn)
        ctrl_lyt.addStretch(1)
        ctrl_lyt.addWidget(self.volume_slr)

        ctrl_panel_lyt = QVBoxLayout()
        ctrl_panel_lyt.setContentsMargins(60,12,60,12)
        ctrl_panel_lyt.addWidget(self.timevalue, 0, QtCore.Qt.AlignLeft)
        ctrl_panel_lyt.addWidget(self.position_slr)
        ctrl_panel_lyt.addLayout(ctrl_lyt)

        rightside_lyt = QVBoxLayout()
        rightside_lyt.addWidget(self.videoframe)
        rightside_lyt.addLayout(ctrl_panel_lyt)

        main_lyt = QHBoxLayout()
        main_lyt.setSpacing(0)
        main_lyt.setContentsMargins(0,0,0,0)
        main_lyt.addWidget(self.leftside_bg)
        main_lyt.addLayout(rightside_lyt, 60)

        self.widget.setLayout(main_lyt)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.updateUI)

        #creates connection to db
        self.db = db_api.create_connection(os.path.join(os.getcwd(), 'db','data.db'))

    def play_pause(self):
        """
        Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.play_btn.setProperty("onplay", True)
            self.play_btn.setStyle(self.play_btn.style())
            self.isPaused = True

        else:
            if self.mediaplayer.play() == -1:
                return
            self.mediaplayer.play()
            self.play_btn.setProperty("onplay", False)
            self.play_btn.setStyle(self.play_btn.style())

            self.timer.start()
            self.isPaused = False

    def start_analyse(self):

        self.analyse_btn.setEnabled(False)

        try:
            file = self.fileslist.currentItem().text()
        except AttributeError:
            self.analyse_btn.setEnabled(True)
            QMessageBox.information(self, "Warning!", "You should to select a file.")
            return

        if not self.on_analyse:
            self.setEnabled(False)
            self.analyse_window.on()

            try:
                worker = AnalyseWorker(file, self)
                self.threadpool.start(worker)
            except Exception as e:
                print(e)
        else:
            return

    def show_details(self):

        try:
            file = self.fileslist.currentItem().text()
        except AttributeError:
            self.analyse_btn.setEnabled(True)
            QMessageBox.information(self, "Warning!", "You should to select a file.")
            return

        item = self.fileslist.currentItem().text()
        if os.path.isdir(os.path.join('warnings', os.path.splitext(item)[0])):
            self.details_wd.show()
            self.details_wd.start(self.fileslist.currentItem().text())
        else:
            return


    def stop_analyse(self):
        self.analyse_window.off()
        self.setEnabled(True)
        self.on_analyse = False

    def stop(self):
        """
        stop player
        """
        if self.mediaplayer.is_playing():
            self.timevalue.setTime(QtCore.QTime.fromMSecsSinceStartOfDay(0))

        self.mediaplayer.stop()


    def select_file(self, item):
        self.open_file(filename = self.path+'/'+item.text())

    def check_warnings_time(self, filename):
        with self.db:
            file_id = db_api.select_file(self.db, filename)
            if file_id:

                #if file in db, then add warning times in list bellow
                timelist = db_api.select_time(self.db, file_id)

                self.warningslist.clear()
                for time in timelist:
                    self.warningslist.addItem(time[0]+"-"+time[1])

                self.details_btn.setVisible(True)

            else:
                self.details_btn.setVisible(False)
                self.warningslist.clear()
                self.warningslist.addItem("There is nothing to show.")

    def open_file(self, filename=''):
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
        self.play_pause()

    def set_volume(self, Volume):
        """
        Set the volume
        """
        self.mediaplayer.audio_set_volume(Volume)

    def set_position(self, position):
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

    def set_time(self, time):
        """
        Set time to display
        """
        self.mediaplayer.set_time(time)

    def select_folder(self, foldername=''):
        if foldername == '':
            foldername = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
            self.path_input.setText(foldername)
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
        self.position_slr.setValue(self.mediaplayer.get_position() * 1000)
        self.timevalue.setTime(QtCore.QTime.fromMSecsSinceStartOfDay(self.mediaplayer.get_position()*self.duration))
        self.volume_slr.setValue(self.mediaplayer.audio_get_volume())

        if not self.mediaplayer.is_playing():
            # no need to call this function if nothing is played
            self.timer.stop()
            if not self.isPaused:
                # after the video finished, the play button stills shows
                # "Pause", not the desired behavior of a media player
                # this will fix it
                self.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = Player()
    player.show()
    player.resize(1280, 720)
    if sys.argv[1:]:
        player.OpenFile(sys.argv[1])
    sys.exit(app.exec_())
