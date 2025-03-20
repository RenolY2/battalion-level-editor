from functools import partial

from PyQt6.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence, QAction, QShortcut
from PyQt6.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit)
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt6.QtCore import Qt
import PyQt6.QtGui as QtGui
from widgets.data_editor import choose_data_editor
from widgets.editor_widgets import BWObjectEditWindow, AddBWObjectWindow, open_error_dialog
from lib.BattalionXMLLib import BattalionObject
import typing
from typing import TYPE_CHECKING
from lib.bw_types import BWMatrix
from plugins.plugin_feature_test import NewEditWindow

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

        self.button_set_spawnmatrix = QPushButton("Set SpawnMatrix")
        self.button_set_spawnmatrix.setToolTip("Sets the spawn matrix of selected objects to the main position matrix. Spawn matrices are primarily used for XML-based respawning.")
        self.button_set_spawnmatrix.pressed.connect(self.set_spawn_matrix)
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

        self.button_set_level = QtWidgets.QPushButton("Reset Vertical Rotation")
        self.button_set_level.setToolTip("If object has been rotated along th")
        self.button_set_level.pressed.connect(self.action_clear_vertical_rotation)

        self.verticalLayout.addWidget(self.button_add_object)
        self.verticalLayout.addWidget(self.button_remove_object)
        #self.verticalLayout.addWidget(self.button_ground_object)
        self.verticalLayout.addWidget(self.button_edit_object)
        self.verticalLayout.addWidget(self.button_clone_object)
        self.verticalLayout.addWidget(QtWidgets.QSplitter(self))
        self.verticalLayout.addWidget(self.button_set_spawnmatrix)
        self.verticalLayout.addWidget(self.button_set_level)
        self.verticalLayout.addStretch()

        self.name_label = QLabel(parent)
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        policy = self.scroll_area.sizePolicy()
        policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        self.scroll_area.setSizePolicy(policy)
        self.scroll_area_content = QtWidgets.QWidget(self.scroll_area)

        self.scroll_layout = QVBoxLayout(self.scroll_area_content)
        self.scroll_area_content.setLayout(self.scroll_layout)
        self.comment_label = QLabel(self.scroll_area_content)
        self.comment_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.comment_label.setWordWrap(True)
        self.comment_label.setFont(font)


        #self.scroll_area.setWidget(self.comment_label)
        self.scroll_layout.addWidget(self.comment_label)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_area_content)
        self.verticalLayout.addWidget(self.scroll_area)
        #self.verticalLayout.addStretch(500)

        self.objectlist = []

        self.object_data_edit = None
        #self.edit_windows: typing.Dict[str, BWObjectEditWindow] = {}

        self.reset_info()
        self.add_window = None

        self.main_window = None
        self.editwindows = []
        self.parent.level_view.select_update.connect(self.update_main_edit_window)

    def update_main_edit_window(self):
        if self.main_window is not None:
            obj = self.parent.get_selected_obj()
            if obj is not None:
                QtWidgets.QApplication.setOverrideCursor(
                    QtCore.Qt.CursorShape.WaitCursor)
                self.main_window.change_object(obj)
                QtWidgets.QApplication.restoreOverrideCursor()

    def set_comment_label(self, text):
        self.comment_label.setText(text)

    def action_clear_vertical_rotation(self):
        if self.parent.dolphin.do_visualize():
            for obj in self.parent.level_view.selected:
                if obj.mtxoverride is not None:
                    BWMatrix.vertical_reset(obj.mtxoverride)
        else:
            for mtx in self.parent.level_view.selected_positions:
                BWMatrix.vertical_reset(mtx.mtx)

        self.parent.level_view.do_redraw(forceselected=True)
        self.parent.set_has_unsaved_changes(True)
        self.parent.pik_control.update_info()

    def close_all_windows(self):
        for window in self.editwindows:
            window.close()

        self.editwindows = []

    def set_spawn_matrix(self):
        for obj in self.parent.level_view.selected:
            if hasattr(obj, "spawnMatrix") and hasattr(obj, "Mat"):
                for i in range(16):
                    obj.spawnMatrix.mtx[i] = obj.Mat.mtx[i]
        self.parent.level_view.do_redraw()
        self.parent.set_has_unsaved_changes(True)

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

        if obj.type == "cGameScriptResource" and obj.mName != "":
            number = 1
            while True:
                newscriptname = "{0}_{1}".format(obj.mName, number)
                if not self.parent.lua_workbench.script_exists(newscriptname):
                    obj.mName = newscriptname
                    break
                else:
                    number += 1

            self.parent.lua_workbench.create_empty_if_not_exist(obj.mName)


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
        self.parent.leveldatatreeview.set_objects(self.parent.level_file, self.parent.preload_file, remember_position=True)
        self.parent.update_3d()
        self.parent.level_view.do_redraw(force=True)
        self.set_objectlist(newclones)
        self.parent.set_has_unsaved_changes(True)

    def select_obj(self, id):
        if id in self.parent.level_file.objects_with_positions:
            obj = self.parent.level_file.objects_with_positions[id]
            self.parent.level_view.selected = [obj]
            self.parent.level_view.selected_positions = [obj.getmatrix()]

            self.parent.update_3d()
            self.parent.level_view.select_update.emit()
            self.parent.level_view.do_redraw(force=True)

            if id in self.edit_windows and obj.getmatrix() is not None and not self.edit_windows[id].unsaved_changes:
                self.update_editwindow_position(id)

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
            mtx = obj.getmatrix()
            if mtx is not None:
                self.parent.level_view.selected_positions = [mtx]
                self.parent.level_view.gizmo.move_to_average(self.parent.level_view.selected,
                                                      self.parent.level_view.bwterrain,
                                                      self.parent.level_view.waterheight,
                                                      self.parent.dolphin.do_visualize())
            else:
                self.parent.level_view.selected_positions = []

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

    def make_window(self, editor, currobj, make_main=False):
        for window in self.editwindows:
            if window.object == currobj:
                window.activate()
                break
        else:
            editwindow = NewEditWindow(None, currobj, editor, self.make_window)
            editwindow.show()
            self.editwindows.append(editwindow)

            def handle_close():
                self.editwindows.remove(editwindow)
                if self.main_window is editwindow:
                    self.main_window = None

            if make_main:
                if self.main_window is None:
                    self.main_window = editwindow

            editwindow.closing.connect(handle_close)

    def action_open_edit_object(self):
        selected = self.parent.level_view.selected

        if len(selected) >= 1:
            for i, v in enumerate(selected):
                self.make_window(self.parent, v, make_main=True)


                continue
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

    def update_editwindow_position(self, id):
        obj = None
        if id in self.parent.level_file.objects:
            obj = self.parent.level_file.objects[id]

        if obj is None:
            return

        content = self.edit_windows[id].get_content()
        currobj = BattalionObject.create_from_text(content, self.parent.level_file, self.parent.preload_file)

        if currobj.getmatrix() is not None:
            assert currobj.getmatrix() is not None and obj.getmatrix() is not None

            for i in range(16):
                currobj.getmatrix().mtx[i] = obj.getmatrix().mtx[i]
            currobj.update_xml()
            unsaved = self.edit_windows[id].unsaved_changes
            self.edit_windows[id].backup_scrollbar_state()
            self.edit_windows[id].set_content(currobj)
            self.edit_windows[id].restore_scrollbar_state()
            self.edit_windows[id].unsaved_changes = unsaved

    def save_object_data(self, id, mass_save=False):

        content = self.edit_windows[id].get_content()
        obj = None
        if id in self.parent.level_file.objects:
            obj = self.parent.level_file.objects[id]
        elif id in self.parent.preload_file.objects:
            obj = self.parent.preload_file.objects[id]

        if obj.type == "cGameScriptResource":
            old_script_name = obj.mName

        if not mass_save:
            if obj is not None:
                try:
                    obj.update_object_from_text(content, self.parent.level_file, self.parent.preload_file)

                    if obj.type == "cGameScriptResource":
                        if self.parent.lua_workbench.script_exists(old_script_name):
                            if obj.mName != "" and not self.parent.lua_workbench.script_exists(obj.mName):
                                scripts = [x.mName for x in self.parent.level_file.scripts]
                                if scripts.count(old_script_name) > 1:
                                    self.parent.lua_workbench.create_empty_if_not_exist(obj.mName)
                                else:
                                    self.parent.lua_workbench.rename(old_script_name, obj.mName)
                        else:
                            self.parent.lua_workbench.create_empty_if_not_exist(obj.mName)

                except Exception as err:
                    open_error_dialog(str(err), None)
                else:
                    self.edit_windows[id].reset_unsaved()

                self.parent.level_view.do_redraw(force=True)
            self.parent.leveldatatreeview.updatenames()
            for obj in self.parent.level_view.selected:
                if obj.getmatrix() is not None:
                    self.parent.level_view.selected_positions.append(obj.getmatrix())
            self.parent.update_3d()
            self.parent.set_has_unsaved_changes(True)
        else:
            if obj is not None:
                obj.update_object_from_text(content, self.parent.level_file, self.parent.preload_file)

                if obj.type == "cGameScriptResource":
                    if self.parent.lua_workbench.script_exists(old_script_name):
                        if obj.mName != "" and not self.parent.lua_workbench.script_exists(obj.mName):
                            scripts = [x.mName for x in self.parent.level_file.scripts]
                            if scripts.count(old_script_name) > 1:
                                self.parent.lua_workbench.create_empty_if_not_exist(obj.mName)
                            else:
                                self.parent.lua_workbench.rename(old_script_name, obj.mName)
                    else:
                        self.parent.lua_workbench.create_empty_if_not_exist(obj.mName)

                self.edit_windows[id].reset_unsaved()
                self.parent.level_view.selected_positions = []


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
        self.set_comment_label("")

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
                text = "Selected: \n{} ({}, {})".format(obj.type, obj.customname, obj.id)
            else:
                text = "Selected: \n{} ({})".format(obj.type, obj.id)

            if hasattr(obj, "mBase") and obj.mBase is not None:
                text += f"\nBase: {obj.mBase.name}"
                if obj.modelname is not None:
                    text += f"\nModel: {obj.modelname}"

            self.name_label.setText(text)



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
        self.set_comment_label("")
        if obj.lua_name:
            self.set_comment_label("Lua name:\n{}".format(obj.lua_name))

    def set_objectlist(self, objs):
        self.objectlist = []
        objectnames = []

        lua_names = []

        for obj in objs:
            if len(objectnames) < 20:
                if obj.customname is not None:
                    objectnames.append("{0} ({1}, {2})".format(obj.type, obj.customname,  obj.id))
                else:
                    objectnames.append("{0} ({1})".format(obj.type, obj.id))
                """if obj.customname is not None:
                    objectnames.append("{0} ({1}, {2})".format(obj.customname, obj.type, obj.id))
                else:
                    objectnames.append(obj.name)"""
            if obj.lua_name:
                lua_names.append(obj.lua_name)
            self.objectlist.append(obj)

        objectnames.sort()
        if len(objs) > 0:
            text = "Selected objects:\n" + ("\n".join(objectnames))
            diff = len(objs) - len(objectnames)
            if diff == 1:
                text += "\nAnd {0} more object".format(diff)
            elif diff > 1:
                text += "\nAnd {0} more objects".format(diff)
        else:
            text = ""

        if len(lua_names) > 0:
            if len(lua_names) > 20:
                part = lua_names[:20]
                rest = len(lua_names) - 20
            else:
                part = lua_names
                rest = 0

            text += "\n\nSelected Lua names:\n"+("\n".join(part))
            if rest == 1:
                text += "\nAnd 1 more object"
            elif rest > 1:
                text += "\nAnd {0} more objects".format(rest)

        self.set_comment_label(text)


