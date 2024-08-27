from functools import partial

from PyQt6.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence, QAction, QShortcut
from PyQt6.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit)
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt6.QtCore import Qt
from widgets.data_editor import choose_data_editor
from widgets.editor_widgets import BWObjectEditWindow, AddBWObjectWindow, open_error_dialog
from lib.BattalionXMLLib import BattalionObject
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class PikminSideWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parent = args[0]

        self.parent: bw_editor.LevelEditor = parent
        self.setMaximumSize(QSize(700, 1500))
        self.setMinimumWidth(300)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(9)

        self.verticalLayout.setObjectName("verticalLayout")

        self.button_add_object = QPushButton("Add Object", parent)
        self.button_add_object.pressed.connect(self.open_add_window)
        self.button_remove_object = QPushButton("Remove Object(s)", parent)
        #self.button_ground_object = QPushButton("Ground Object(s)", parent)
        #self.button_move_object = QPushButton(parent)
        self.button_edit_object = QPushButton("Edit Object", parent)
        self.button_clone_object = QPushButton("Clone Object", parent)
        self.button_clone_object.setToolTip("Clones selected objects and their passengers, then selects them.")

        #self.button_add_object.setDisabled(True)
        #self.button_remove_object.setDisabled(True)
        self.button_add_object.setToolTip("Hotkey: Ctrl+A")
        self.button_remove_object.setToolTip("Hotkey: Delete")
        #self.button_ground_object.setToolTip("Hotkey: G")

        self.button_remove_object.setEnabled(True)
        #self.button_ground_object.setEnabled(False)
        self.button_add_object.setEnabled(True)

        self.button_edit_object.pressed.connect(self.action_open_edit_object)
        self.button_add_object.setCheckable(True)
        self.button_clone_object.pressed.connect(self.clone_object)

        self.verticalLayout.addWidget(self.button_add_object)
        self.verticalLayout.addWidget(self.button_remove_object)
        #self.verticalLayout.addWidget(self.button_ground_object)
        self.verticalLayout.addWidget(self.button_edit_object)
        self.verticalLayout.addWidget(self.button_clone_object)
        self.verticalLayout.addStretch(20)

        self.name_label = QLabel(parent)
        self.name_label.setFont(font)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumSize(self.name_label.width(), 30)
        #self.identifier_label = QLabel(parent)
        #self.identifier_label.setFont(font)
        #self.identifier_label.setMinimumSize(self.name_label.width(), 50)
        #self.identifier_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.verticalLayout.addWidget(self.name_label)
        #self.verticalLayout.addWidget(self.identifier_label)

        #self.verticalLayout.addStretch(10)
        self.comment_label = QLabel(parent)
        self.comment_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.comment_label.setWordWrap(True)
        self.comment_label.setFont(font)
        self.verticalLayout.addWidget(self.comment_label)
        #self.verticalLayout.addStretch(500)

        self.objectlist = []

        self.object_data_edit = None
        self.edit_windows = {}

        self.reset_info()
        self.add_window = None

    def _copy_object(self, obj, offsetx, offsetz):
        content = obj.tostring()
        level_file = self.parent.level_file
        preload = self.parent.preload_file
        obj = BattalionObject.create_from_text(content, level_file, preload)
        obj.choose_unique_id(level_file, preload)
        newid = obj.id


        mtx = obj.getmatrix()
        if mtx is not None:
            mtx.mtx[12] += offsetx
            mtx.mtx[14] += offsetz

        if obj.is_preload():
            preload.add_object_new(obj)
        else:
            level_file.add_object_new(obj)

        return obj

    def clone_object(self):
        clonelist = [x for x in self.parent.level_view.selected]

        # Do not clone selected grunts who are already passengers because passengers will get cloned anyway
        for obj in self.parent.level_view.selected:
            if hasattr(obj, "mPassenger"):
                for passenger in obj.mPassenger:
                    if passenger is not None and passenger in clonelist:
                        clonelist.remove(passenger)
        newclones = []
        for obj in clonelist:
            clone = self._copy_object(obj, 5, 5)
            newclones.append(clone)
            if hasattr(obj, "mPassenger"):
                for i, v in enumerate(clone.mPassenger):
                    if v is not None:
                        clone.mPassenger[i] = self._copy_object(clone.mPassenger[i], 5, 5)
                        newclones.append(clone.mPassenger[i])

        self.parent.level_view.do_select(newclones)
        self.parent.leveldatatreeview.set_objects(self.parent.level_file, self.parent.preload_file)
        self.parent.update_3d()
        self.parent.level_view.do_redraw(force=True)
        self.set_objectlist(newclones)

    def select_obj(self, id):
        if id in self.parent.level_file.objects_with_positions:
            obj = self.parent.level_file.objects_with_positions[id]
            self.parent.level_view.selected = [obj]
            self.parent.level_view.select_update.emit()
            self.parent.level_view.do_redraw(force=True)

    def handle_close(self, field):
        setattr(self, field, None)

    def open_add_window(self):
        if self.add_window is not None:
            self.add_window.setWindowState(
                self.add_window.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
            self.add_window.activateWindow()
            self.add_window.show()
            self.add_window.setFocus()
        else:
            self.add_window = AddBWObjectWindow(self.parent)
            self.add_window.closing.connect(partial(self.handle_close, "add_window"))
            self.add_window.show()

    def goto_object(self, id):
        if id in self.parent.level_file.objects_with_positions:
            obj = self.parent.level_file.objects_with_positions[id]
            self.parent.level_view.selected = [obj]
            self.parent.goto_object(obj)
            self.parent.level_view.select_update.emit()
            self.parent.level_view.do_redraw(force=True)

    def open_new_window(self, id):
        if id in self.parent.level_file.objects:
            obj = self.parent.level_file.objects[id]
        elif id in self.parent.preload_file.objects:
            obj = self.parent.preload_file.objects[id]
        else:
            obj = None

        if obj is not None:
            offset = (len(self.edit_windows) % 15) * 25
            if obj.id in self.edit_windows:
                window = self.edit_windows[obj.id]
                window.setWindowState(window.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
                window.activateWindow()
                window.show()
            else:
                window = BWObjectEditWindow(obj.id)
                window.opennewxml.connect(self.open_new_window)
                window.focusobj.connect(self.select_obj)
                window.findobject.connect(self.goto_object)
                window.move(window.x() + offset, window.y() + offset)
                self.edit_windows[obj.id] = window

                def remove_window(id):
                    del self.edit_windows[id]

                window.saving.connect(self.save_object_data)
                window.closing.connect(partial(remove_window, obj.id))
                window.set_content(obj)
                window.show()

    def action_open_edit_object(self):
        selected = self.parent.level_view.selected

        if len(selected) >= 1:
            for i, v in enumerate(selected):
                offset = (len(self.edit_windows) %15)*25
                obj = selected[i]
                if obj.id in self.edit_windows:
                    window = self.edit_windows[obj.id]
                    window.setWindowState(window.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
                    window.activateWindow()
                    window.show()
                else:
                    window = BWObjectEditWindow(obj.id)
                    window.opennewxml.connect(self.open_new_window)
                    window.findobject.connect(self.goto_object)
                    window.focusobj.connect(self.select_obj)
                    window.move(window.x()+offset, window.y()+offset)
                    self.edit_windows[obj.id] = window

                    def remove_window(id):
                        del self.edit_windows[id]
                    window.saving.connect(self.save_object_data)
                    window.closing.connect(partial(remove_window, obj.id))
                    window.set_content(obj)
                    window.show()

    def activate_window(self, id):
        if id in self.edit_windows:
            window = self.edit_windows[id]
            window.setWindowState(
                window.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
            window.activateWindow()
            window.show()

    def save_object_data(self, id, mass_save=False):
        content = self.edit_windows[id].get_content()
        obj = None
        if id in self.parent.level_file.objects:
            obj = self.parent.level_file.objects[id]
        elif id in self.parent.preload_file.objects:
            obj = self.parent.preload_file.objects[id]

        if not mass_save:
            if obj is not None:
                try:
                    obj.update_object_from_text(content, self.parent.level_file, self.parent.preload_file)
                except Exception as err:
                    open_error_dialog(str(err), None)
                self.parent.level_view.do_redraw(force=True)
            self.parent.leveldatatreeview.updatenames()
        else:
            if obj is not None:
                obj.update_object_from_text(content, self.parent.level_file, self.parent.preload_file)

    def _make_labeled_lineedit(self, lineedit, label):
        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        layout = QHBoxLayout()
        label = QLabel(label, self)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineedit)
        return layout

    def reset_info(self, info="None selected"):
        self.name_label.setText(info)
        #self.identifier_label.setText("")
        self.comment_label.setText("")

        if self.object_data_edit is not None:
            self.object_data_edit.deleteLater()
            del self.object_data_edit
            self.object_data_edit = None

        self.objectlist = []

    def update_info(self):
        if self.object_data_edit is not None:
            self.object_data_edit.update_data()

    def set_info(self, obj, update3d, usedby=[]):
        if usedby:
            self.name_label.setText("Selected: {}\nUsed by: {}".format(obj.type,
                                    ", ".join(usedby)))
        else:
            if obj.customname is not None:
                self.name_label.setText("Selected: {} ({}, {})".format(obj.type, obj.customname, obj.id))
            else:
                self.name_label.setText("Selected: {} ({})".format(obj.type, obj.id))
        #self.identifier_label.setText(obj.get_identifier())
        if self.object_data_edit is not None:
            #self.verticalLayout.removeWidget(self.object_data_edit)
            self.object_data_edit.deleteLater()
            del self.object_data_edit
            self.object_data_edit = None
            print("should be removed")

        editor = choose_data_editor(obj)
        if editor is not None:

            self.object_data_edit = editor(self, obj)
            self.verticalLayout.addWidget(self.object_data_edit)
            self.object_data_edit.emit_3d_update.connect(update3d)

        self.objectlist = []
        self.comment_label.setText("")

    def set_objectlist(self, objs):
        self.objectlist = []
        objectnames = []

        for obj in objs:
            if len(objectnames) < 25:
                if obj.customname is not None:
                    objectnames.append("{0} ({1}, {2})".format(obj.type, obj.customname,  obj.id))
                else:
                    objectnames.append("{0} ({1})".format(obj.type, obj.id))
                """if obj.customname is not None:
                    objectnames.append("{0} ({1}, {2})".format(obj.customname, obj.type, obj.id))
                else:
                    objectnames.append(obj.name)"""
            self.objectlist.append(obj)

        objectnames.sort()
        if len(objs) > 0:
            text = "Selected objects:\n" + (", ".join(objectnames))
            diff = len(objs) - len(objectnames)
            if diff == 1:
                text += "\nAnd {0} more object".format(diff)
            elif diff > 1:
                text += "\nAnd {0} more objects".format(diff)

        else:
            text = ""

        self.comment_label.setText(text)


