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

from widgets.data_editor import choose_data_editor


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


class BWObjectEditWindow(QMdiSubWindow):
    closing = pyqtSignal()
    opennewxml = pyqtSignal(str)
    saving = pyqtSignal(str)

    def __init__(self, id):
        super().__init__()
        self.id = id
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))

        self.central_widget = QtWidgets.QWidget(self)
        self._layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.textbox_xml = QTextEdit(self.central_widget)
        self.save_xml = QtWidgets.QPushButton("Save", self.central_widget)
        self.save_xml.setShortcut("Ctrl+S")
        self.save_xml.pressed.connect(self.action_save_xml)

        self._layout.addWidget(self.textbox_xml)
        self._layout.addWidget(self.save_xml)

        self.central_widget.setLayout(self._layout)
        self.setWidget(self.central_widget)
        self.textbox_xml.setLineWrapMode(QTextEdit.NoWrap)
        self.textbox_xml.setContextMenuPolicy(Qt.CustomContextMenu)
        self.textbox_xml.customContextMenuRequested.connect(self.my_context_menu)
        self.gotoaction = QAction("Edit XML for ID", self)
        self.shortcut = QtWidgets.QShortcut("Ctrl+E", self)
        self.shortcut.setAutoRepeat(False)
        self.shortcut.activated.connect(self.goto_id_action)

        self.gotoaction.triggered.connect(self.goto_id_action)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        metrics = QFontMetrics(font)
        self.textbox_xml.setTabStopWidth(4 * metrics.width(' '))
        self.textbox_xml.setFont(font)
        self.id = None

        #self.verticalLayout.addWidget(self.textbox_xml)

    def action_save_xml(self):
        self.saving.emit(self.id)

    def my_context_menu(self, position):
        try:
            context_menu = self.textbox_xml.createStandardContextMenu()
            context_menu.addAction(self.gotoaction)
            self.gotoaction.setShortcut("Ctrl+E")
            context_menu.exec(self.mapToGlobal(position))
            context_menu.destroy()
            del context_menu
            #self.context_menu.exec(event.globalPos())
            #return super().contextMenuEvent(event)
        except:
            traceback.print_exc()

    def goto_id_action(self):
        cursor = self.textbox_xml.textCursor()
        id = cursor.selectedText()
        self.opennewxml.emit(id)

    def closeEvent(self, event):
        self.closing.emit()

    def set_content(self, bwobject):
        self.textbox_xml.setText(bwobject.tostring())
        self.id = bwobject.id
        self.setWindowTitle(bwobject.name)

    def get_content(self):
        return self.textbox_xml.toPlainText()


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
