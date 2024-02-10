import traceback
from io import StringIO
from itertools import chain
from math import acos, pi
import os
import sys

from PyQt5.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit, QFileDialog, QScrollArea,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit, QAction, QShortcut)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt
import PyQt5.QtGui as QtGui

import lib.libbol as libbol
from widgets.data_editor import choose_data_editor
from lib.libbol import get_full_name


def catch_exception(func):
    def handle(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exc()
            #raise
    return handle


def catch_exception_with_dialog(func):
    def handle(*args, **kwargs):
        try:
            print(args, kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            print("hey")
            open_error_dialog(str(e), None)
    return handle


def catch_exception_with_dialog_nokw(func):
    def handle(*args, **kwargs):
        try:
            print(args, kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), None)
    return handle


def open_error_dialog(errormsg, self):
    errorbox = QtWidgets.QMessageBox()
    errorbox.critical(self, "Error", errormsg)
    errorbox.setFixedSize(500, 200)


class ErrorAnalyzer(QMdiSubWindow):
    @catch_exception
    def __init__(self, bol, *args, **kwargs):
        super().__init__(*args, **kwargs)
        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        self.setWindowTitle("Analysis Results")
        self.text_widget = QTextEdit(self)
        self.setWidget(self.text_widget)
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))
        self.text_widget.setFont(font)
        self.text_widget.setReadOnly(True)

        self.analyze_bol_and_write_results(bol)

    @catch_exception
    def analyze_bol_and_write_results(self, bol):
        results = StringIO()

        def write_line(line):
            results.write(line)
            results.write("\n")

        # Check enemy point linkage errors
        links = {}
        for group_index, group in enumerate(bol.enemypointgroups.groups):
            for i, point in enumerate(group.points):
                if point.link == -1:
                    continue

                if point.link not in links:
                    links[point.link] = [(group_index, i, point)]
                else:
                    links[point.link].append(((group_index, i, point)))

        for link_id, points in links.items():
            if len(points) == 1:
                group_index, i, point = points[0]
                write_line("Point {0} in enemy point group {1} has link {2}; No other point has link {2}".format(
                    i, group_index, point.link
                ))
        for group_index, group in enumerate(bol.enemypointgroups.groups):
            print(group.points[0].link, group.points[-1].link)
            if group.points[0].link == -1:
                write_line("Start point of enemy point group {0} has no valid link to form a loop".format(group_index))
            if group.points[-1].link == -1:
                write_line("End point of enemy point group {0} has no valid link to form a loop".format(group_index))

        # Check prev/next groups of checkpoints
        for i, group in enumerate(bol.checkpoints.groups):
            for index in chain(group.prevgroup, group.nextgroup):
                if index != -1:
                    if index < -1 or index+1 > len(bol.checkpoints.groups):
                        write_line("Checkpoint group {0} has invalid Prev or Nextgroup index {1}".format(
                            i, index
                        ))

        # Validate path id in objects
        for object in bol.objects.objects:
            if object.pathid < -1 or object.pathid + 1 > len(bol.routes):
                write_line("Map object {0} uses path id {1} that does not exist".format(
                    get_full_name(object.objectid), object.pathid
                ))

        # Validate Kart start positions
        if len(bol.kartpoints.positions) == 0:
            write_line("Map contains no kart start points")
        else:
            exist = [False for x in range(8)]

            for i, kartstartpos in enumerate(bol.kartpoints.positions):
                if kartstartpos.playerid == 0xFF:
                    if all(exist):
                        write_line("Duplicate kart start point for all karts")
                    exist = [True for x in range(8)]
                elif kartstartpos.playerid > 8:
                    write_line("A kart start point with an invalid player id exists: {0}".format(
                        kartstartpos.playerid
                    ))
                elif exist[kartstartpos.playerid]:
                    write_line("Duplicate kart start point for player id {0}".format(
                        kartstartpos.playerid))
                else:
                    exist[kartstartpos.playerid] = True

        # Check camera indices in areas
        for i, area in enumerate(bol.areas.areas):
            if area.camera_index < -1 or area.camera_index + 1 > len(bol.cameras):
                write_line("Area {0} uses invalid camera index {1}".format(i, area.camera_index))

        # Check cameras
        for i, camera in enumerate(bol.cameras):
            if camera.nextcam < -1 or camera.nextcam + 1 > len(bol.cameras):
                write_line("Camera {0} uses invalid nextcam (next camera) index {1}".format(
                    i, camera.nextcam
                ))
            if camera.route < -1 or camera.route + 1 > len(bol.routes):
                write_line("Camera {0} uses invalid path id {1}".format(i,
                                                                        camera.route))

        if len(bol.checkpoints.groups) == 0:
            write_line("You need at least one checkpoint group!")

        if len(bol.enemypointgroups.groups) == 0:
            write_line("You need at least one enemy point group!")

        self.check_checkpoints_convex(bol, write_line)

        text = results.getvalue()
        if not text:
            text = "No known common errors detected!"
        self.text_widget.setText(text)

    def check_checkpoints_convex(self, bol, write_line):
        for gindex, group in enumerate(bol.checkpoints.groups):
            if len(group.points) > 1:
                for i in range(1, len(group.points)):
                    c1 = group.points[i-1]
                    c2 = group.points[i]

                    lastsign = None

                    for p1, mid, p3 in ((c1.start, c2.start, c2.end),
                                        (c2.start, c2.end, c1.end),
                                        (c2.end, c1.end, c1.start),
                                        (c1.end, c1.start, c2.start)):
                        side1 = p1 - mid
                        side2 = p3 - mid
                        prod = side1.x * side2.z - side2.x * side1.z
                        if lastsign is None:
                            lastsign = prod > 0
                        else:
                            if not (lastsign == (prod > 0)):
                                write_line("Quad formed by checkpoints {0} and {1} in checkpoint group {2} isn't convex.".format(
                                    i-1, i, gindex
                                ))
                                break


class AddPikObjectWindow(QMdiSubWindow):
    triggered = pyqtSignal(object)
    closing = pyqtSignal()

    def closeEvent(self, event):
        self.closing.emit()
        super().closeEvent(event)

    @catch_exception
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "windowtype" in kwargs:
            self.window_name = kwargs["windowtype"]
        else:
            self.window_name = "Add Object"

        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))

        self.centralwidget = QWidget(self)
        self.setWidget(self.centralwidget)
        self.entity = None

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        self.dummywidget = QWidget(self)
        self.dummywidget.setMaximumSize(0,0)


        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setAlignment(Qt.AlignTop)
        self.verticalLayout.addWidget(self.dummywidget)



        self.setup_dropdown_menu()



        self.hbox1 = QHBoxLayout(self.centralwidget)
        self.hbox2 = QHBoxLayout(self.centralwidget)


        self.label1 = QLabel(self.centralwidget)
        self.label2 = QLabel(self.centralwidget)
        self.label3 = QLabel(self.centralwidget)
        self.label1.setText("Group")
        self.label2.setText("Position in Group")
        self.label3.setText("(-1 means end of Group)")
        self.group_edit = QLineEdit(self.centralwidget)
        self.position_edit = QLineEdit(self.centralwidget)

        self.group_edit.setValidator(QtGui.QIntValidator(0, 2**31-1))
        self.position_edit.setValidator(QtGui.QIntValidator(-1, 2**31-1))

        self.hbox1.setAlignment(Qt.AlignRight)
        self.hbox2.setAlignment(Qt.AlignRight)


        self.verticalLayout.addLayout(self.hbox1)
        self.verticalLayout.addLayout(self.hbox2)
        self.hbox1.addWidget(self.label1)
        self.hbox1.addWidget(self.group_edit)
        self.hbox2.addWidget(self.label2)
        self.hbox2.addWidget(self.position_edit)
        self.hbox2.addWidget(self.label3)

        self.group_edit.setDisabled(True)
        self.position_edit.setDisabled(True)


        self.editor_widget = None
        self.editor_layout = QScrollArea()#QVBoxLayout(self.centralwidget)
        self.verticalLayout.addWidget(self.editor_layout)
        #self.textbox_xml = QTextEdit(self.centralwidget)
        self.button_savetext = QPushButton(self.centralwidget)
        self.button_savetext.setText("Add Object")
        self.button_savetext.setToolTip("Hotkey: Ctrl+S")
        self.button_savetext.setMaximumWidth(400)
        self.button_savetext.setDisabled(True)

        self.verticalLayout.addWidget(self.button_savetext)
        self.setWindowTitle(self.window_name)
        self.created_object = None
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self).activated.connect(self.emit_add_object)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.CTRL + Qt.Key_S:
            self.emit_add_object()
        else:
            super().keyPressEvent(event)

    def emit_add_object(self):
        self.button_savetext.pressed.emit()

    def get_content(self):
        try:
            if not self.group_edit.text():
                group = None
            else:
                group = int(self.group_edit.text())
            if not self.position_edit.text():
                position = None
            else:
                position = int(self.position_edit.text())
            return self.created_object, group, position

        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)
            return None

    def setup_dropdown_menu(self):
        self.category_menu = QtWidgets.QComboBox(self)
        self.category_menu.addItem("-- select type --")

        self.verticalLayout.addWidget(self.category_menu)

        self.objecttypes = {
            "Enemy route point": libbol.EnemyPoint,
            "Checkpoint": libbol.Checkpoint,
            "Map object route point": libbol.RoutePoint,
            "Map object": libbol.MapObject,
            "Area": libbol.Area,
            "Camera": libbol.Camera,
            "Respawn point": libbol.JugemPoint,
            "Kart start point": libbol.KartStartPoint,
            "Enemy point group": libbol.EnemyPointGroup,
            "Checkpoint group": libbol.CheckpointGroup,
            "Object point group": libbol.Route,
            "Light param": libbol.LightParam,
            "Minigame param": libbol.MGEntry
        }

        for item, val in self.objecttypes.items():
            self.category_menu.addItem(item)

        self.category_menu.currentIndexChanged.connect(self.change_category)

    def change_category(self, index):
        if index > 0:
            item = self.category_menu.currentText()
            self.button_savetext.setDisabled(False)
            objecttype = self.objecttypes[item]

            if self.editor_widget is not None:
                self.editor_widget.deleteLater()
                self.editor_widget = None
            if self.created_object is not None:
                del self.created_object

            self.created_object = objecttype.new()

            if isinstance(self.created_object, (libbol.Checkpoint, libbol.EnemyPoint, libbol.RoutePoint)):
                self.group_edit.setDisabled(False)
                self.position_edit.setDisabled(False)
                self.group_edit.setText("0")
                self.position_edit.setText("-1")
            else:
                self.group_edit.setDisabled(True)
                self.position_edit.setDisabled(True)
                self.group_edit.clear()
                self.position_edit.clear()

            data_editor = choose_data_editor(self.created_object)
            if data_editor is not None:
                self.editor_widget = data_editor(self, self.created_object)
                self.editor_layout.setWidget(self.editor_widget)
                self.editor_widget.update_data()

        else:
            self.editor_widget.deleteLater()
            self.editor_widget = None
            del self.created_object
            self.created_object = None
            self.button_savetext.setDisabled(True)
            self.position_edit.setDisabled(True)
            self.group_edit.setDisabled(True)

class SpawnpointEditor(QMdiSubWindow):
    triggered = pyqtSignal(object)
    closing = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.centralwidget = QWidget(self)
        self.setWidget(self.centralwidget)
        self.entity = None
        self.resize(400, 200)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.verticalLayout = QVBoxLayout(self.centralwidget)

        self.position = QLineEdit(self.centralwidget)
        self.rotation = QLineEdit(self.centralwidget)

        self.button_savetext = QPushButton(self.centralwidget)
        self.button_savetext.setText("Set Data")
        self.button_savetext.setMaximumWidth(400)

        self.verticalLayout.addWidget(QLabel("startPos"))
        self.verticalLayout.addWidget(self.position)
        self.verticalLayout.addWidget(QLabel("startDir"))
        self.verticalLayout.addWidget(self.rotation)
        self.verticalLayout.addWidget(self.button_savetext)
        self.setWindowTitle("Edit startPos/Dir")

    def closeEvent(self, event):
        self.closing.emit()

    def get_pos_dir(self):
        pos = self.position.text().strip()
        direction = float(self.rotation.text().strip())

        if "," in pos:
            pos = [float(x.strip()) for x in pos.split(",")]
        else:
            pos = [float(x.strip()) for x in pos.split(" ")]

        assert len(pos) == 3

        return pos, direction
