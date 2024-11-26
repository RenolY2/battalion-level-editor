import traceback
from io import StringIO
from itertools import chain
from math import acos, pi
import os
import sys

from PyQt6.QtGui import (QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence,
                         QAction, QShortcut)
from PyQt6.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit, QFileDialog, QScrollArea,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit)
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt6.QtCore import Qt
import PyQt6.QtGui as QtGui

from widgets.data_editor import choose_data_editor
from lib.BattalionXMLLib import BattalionObject
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class YesNoQuestionDialog(QtWidgets.QMessageBox):
    def __init__(self, parent, text, instructiontext):
        super().__init__(parent)
        self.setText(text)
        self.setInformativeText(instructiontext)
        self.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        self.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        self.setIcon(QtWidgets.QMessageBox.Icon.Question)
        self.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        self.setWindowTitle("Question")


class MessageDialog(QtWidgets.QMessageBox):
    def __init__(self, parent, text, instructiontext=None):
        super().__init__(parent)
        self.setText(text)
        if instructiontext is not None:
            self.setInformativeText(instructiontext)
        self.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes)
        self.setIcon(QtWidgets.QMessageBox.Icon.Information)
        self.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        self.setWindowTitle("Information")


def open_message_dialog(message, instructiontext=None, parent=None):
    messagebox = MessageDialog(parent, message, instructiontext)
    messagebox.exec()


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


class HelpWindow(QtWidgets.QMdiSubWindow):
    closing = pyqtSignal()

    def __init__(self, title, text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(800, 400)

        self.helptext = QtWidgets.QTextEdit(self)
        self.setWindowTitle(title)
        self.helptext.setReadOnly(True)
        self.helptext.setMarkdown(text)

        self.setWidget(self.helptext)

    def closeEvent(self, closeEvent: QtGui.QCloseEvent) -> None:
        self.closing.emit()


class BWObjectEditWindow(QMdiSubWindow):
    closing = pyqtSignal()
    opennewxml = pyqtSignal(str)
    saving = pyqtSignal(str)
    findobject = pyqtSignal(str)
    focusobj = pyqtSignal(str)

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
        self.help_button = QtWidgets.QPushButton(self)
        self.help_button.setText("Help")

        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.addWidget(self.help_button)
        self.help_button.pressed.connect(self.open_help)

        self.search = SearchBar(self)
        self.hlayout.addWidget(self.search)
        self._layout.addLayout(self.hlayout)
        self._layout.addWidget(self.textbox_xml)
        self._layout.addWidget(self.save_xml)
        self.central_widget.setLayout(self._layout)
        self.setWidget(self.central_widget)
        self.textbox_xml.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.textbox_xml.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.textbox_xml.customContextMenuRequested.connect(self.my_context_menu)
        self.gotoaction = QAction("Edit XML for ID", self)
        self.shortcut = QtGui.QShortcut("Ctrl+E", self)
        self.shortcut.setAutoRepeat(False)
        self.findaction = QAction("Find ID in Map", self)
        self.findaction.triggered.connect(self.find_object)

        self.find_shortcut = QtGui.QShortcut("Ctrl+F", self)
        self.find_shortcut.activated.connect(self.goto_find_box)

        self.shortcut.activated.connect(self.goto_id_action)

        self.gotoaction.triggered.connect(self.goto_id_action)
        self.search.find.connect(self.find_text)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        metrics = QFontMetrics(font)
        self.textbox_xml.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        self.textbox_xml.setFont(font)
        self.id = None
        self.type = None
        self.current_index = 0

        self.helpwindow = None

        #self.verticalLayout.addWidget(self.textbox_xml)
        self.unsaved_changes = False
        self.textbox_xml.textChanged.connect(self.set_unsaved)
        self.title = ""

        self._scrollbarstate = None

    def backup_scrollbar_state(self):
        self._scrollbarstate = self.textbox_xml.verticalScrollBar().value(), self.textbox_xml.horizontalScrollBar().value()

    def restore_scrollbar_state(self):
        vertical, horizontal = self._scrollbarstate
        self.textbox_xml.verticalScrollBar().setValue(vertical)
        self.textbox_xml.horizontalScrollBar().setValue(horizontal)

    def set_unsaved(self):
        self.unsaved_changes = True
        self.update_windowtitle()

    def close_help(self):
        self.helpwindow = None

    def open_help(self):
        if self.helpwindow is not None:
            self.helpwindow.setWindowState(
                self.helpwindow.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
            self.helpwindow.activateWindow()
            self.helpwindow.show()
            self.helpwindow.setFocus()
        else:
            try:
                with open("objecthelp/{0}.txt".format(self.type), "r") as f:
                    text = f.read()
            except FileNotFoundError:
                open_error_dialog(( "No help found for object type {}!"
                                    "\n\nHelp files can be added in the editor's objecthelp folder."
                                    "\nThe text files need to be named after the object type."
                                    "Example: cTroop.txt for the object type cTroop.").format(self.type), None)
            else:
                self.helpwindow = HelpWindow("Help for {}".format(self.type), text)
                self.helpwindow.closing.connect(self.close_help)
                self.helpwindow.show()

    def find_text(self, text):
        if text:
            textbox = self.textbox_xml.toPlainText().lower()
            cursor = self.textbox_xml.textCursor()
            result = textbox.find(text.lower(), cursor.position())
            if result == -1:
                result = textbox.find(text.lower())
            print("found", result)
            if result >= 0:
                cursor.setPosition(result)

                cursor.setPosition(result+len(text), QtGui.QTextCursor.MoveMode.KeepAnchor)
                self.textbox_xml.setTextCursor(cursor)
                self.textbox_xml.setFocus()
                print("moved")

    def goto_find_box(self):
        self.search.textinput.setFocus()

    def find_object(self):
        cursor = self.textbox_xml.textCursor()
        id = cursor.selectedText()
        self.findobject.emit(id)

    # Select object belonging to this window if window is activated
    def changeEvent(self, changeEvent: QtCore.QEvent) -> None:
        super().changeEvent(changeEvent)

        if changeEvent.type() == QtCore.QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.focusobj.emit(self.id)

    def action_save_xml(self):
        self.saving.emit(self.id)

    def my_context_menu(self, position):
        try:
            context_menu = self.textbox_xml.createStandardContextMenu()
            context_menu.addAction(self.gotoaction)
            self.gotoaction.setShortcut("Ctrl+E")
            context_menu.addAction(self.findaction)
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
        if self.helpwindow is not None:
            del self.helpwindow
        self.closing.emit()

    def set_content(self, bwobject):
        self.textbox_xml.setText(bwobject.tostring())
        self.id = bwobject.id
        self.type = bwobject.type
        self.title = bwobject.name
        self.unsaved_changes = False
        self.update_windowtitle()

    def update_windowtitle(self):
        if self.unsaved_changes:
            self.setWindowTitle(self.title +" [Unsaved Changes]")
        else:
            self.setWindowTitle(self.title)

    def reset_unsaved(self):
        self.unsaved_changes = False
        self.update_windowtitle()

    def get_content(self):
        return self.textbox_xml.toPlainText()




class AddBWObjectWindow(QtWidgets.QMainWindow):
    closing = pyqtSignal()
    addobject = pyqtSignal(str, bool)

    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))
        self.basewidget = QtWidgets.QWidget(self)
        self.setWindowTitle("Add Object")

        self.setCentralWidget(self.basewidget)
        self.explanation = QtWidgets.QLabel(("Insert the XML data of an object you want to add here. "
                                             "This does not automatically add object dependencies or resources if they don't exist already.\n"
                                             "Each press of 'Add Object' adds the object to the level with a new ID."))
        self.vlayout = QtWidgets.QVBoxLayout(self)
        self.basewidget.setLayout(self.vlayout)
        self.vlayout.addWidget(self.explanation)
        self.textbox_xml = QTextEdit(self.basewidget)


        #self.add_object_on_map = QtWidgets.QPushButton("Add Object On Map", self)
        self.add_object = QtWidgets.QPushButton("Add Object", self)
        self.add_object.pressed.connect(self.action_add_object)
        #self.add_object_on_map.setEnabled(False)

        self.vlayout.addWidget(self.textbox_xml)

        self.hlayout = QtWidgets.QHBoxLayout(self)
        #self.hlayout.addWidget(self.add_object_on_map)
        self.hlayout.addWidget(self.add_object)
        self.vlayout.addLayout(self.hlayout)

        self.textbox_xml.textChanged.connect(self.resetoffset)
        self.offsetx = 0
        self.offsety = 0
        self.donotreset = False

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        metrics = QFontMetrics(font)
        self.textbox_xml.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        self.textbox_xml.setFont(font)

    def resetoffset(self):
        if not self.donotreset:
            self.offsetx = 0
            self.offsety = 0

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.closing.emit()

    def action_add_object(self):
        content = self.textbox_xml.toPlainText()
        try:
            obj = BattalionObject.create_from_text(content, self.editor.level_file, self.editor.preload_file)
        except Exception as err:
            open_error_dialog("Couldn't add object:\n"+str(err), None)
            return

        oldid = obj.id
        obj.choose_unique_id(self.editor.level_file, self.editor.preload_file)
        newid = obj.id

        self.offsety += 1
        if self.offsety > 5:
            self.offsety = 0
            self.offsetx += 1
        mtx = obj.getmatrix()
        if mtx is not None:
            mtx.mtx[12] += self.offsetx*4
            mtx.mtx[14] -= self.offsety*4

        if obj.type == "cGameScriptResource" and obj.mName != "":
            if self.editor.lua_workbench.script_exists(obj.mName):
                number = 1
                while True:
                    newscriptname = "{0}_{1}".format(obj.mName, number)
                    if not self.editor.lua_workbench.script_exists(newscriptname):
                        obj.mName = newscriptname
                        break
                    else:
                        number += 1

            self.editor.lua_workbench.create_empty_if_not_exist(obj.mName)

        if obj.is_preload():
            self.editor.preload_file.add_object_new(obj)
        else:
            self.editor.level_file.add_object_new(obj)



        self.donotreset = True
        self.textbox_xml.setText(content.replace(oldid, newid))
        self.donotreset = False
        self.editor.leveldatatreeview.set_objects(self.editor.level_file, self.editor.preload_file, remember_position=True)
        self.editor.level_view.do_redraw(force=True)


class SearchBar(QtWidgets.QWidget):
    find = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.l = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.l)

        self.textinput = QtWidgets.QLineEdit(self)
        self.searchbutton = QtWidgets.QPushButton(self)
        self.searchbutton.setText("Find")
        self.l.addWidget(self.textinput)
        self.l.addWidget(self.searchbutton)
        self.searchbutton.pressed.connect(self.do_search)
        self.textinput.editingFinished.connect(self.do_search)

    def do_search(self):
        self.find.emit(self.textinput.text())


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
