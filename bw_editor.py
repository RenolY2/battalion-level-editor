import cProfile
import pstats
import traceback
__version__ = '2.3.0.0'

import os
import multiprocessing
from timeit import default_timer
from copy import deepcopy
from dataclasses import dataclass
from itertools import chain
from io import TextIOWrapper, BytesIO, StringIO
from math import sin, cos, atan2, pi
import json
import enum
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from PyQt6.QtCore import Qt
from plugins.plugin_pfd_edit import PathfindPoint
from PyQt6.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QApplication, QStatusBar, QLineEdit)
from PyQt6.QtGui import QMouseEvent, QImage, QAction
import PyQt6.QtGui as QtGui
import numpy
import opengltext
import py_obj
from lib.lua.luaworkshop import LuaWorkbench
from lib.bw_types import BWMatrix
from lib.vectors import Vector3
from widgets.menu.menubar import EditorMenuBar
from widgets.editor_widgets import catch_exception
from widgets.editor_widgets import AddPikObjectWindow
from widgets.tree_view import LevelDataTreeView
import widgets.tree_view as tree_view
from configuration import read_config, make_default_config, save_cfg
from widgets.editor_widgets import open_yesno_box
from widgets.menu.plugin import PluginHandler
from widgets.lua_search_widgets import LuaSearchResultItem
from widgets.qtutils import VerticalWidget
from widgets.editor_widgets import SearchBarReset

import bw_widgets # as mkddwidgets
from widgets.side_widget import PikminSideWidget
from widgets.editor_widgets import open_error_dialog, catch_exception_with_dialog
from bw_widgets import BolMapViewer, MODE_TOPDOWN

from lib.model_rendering import TexturedModel, CollisionModel, Minimap

from lib.dolreader import DolFile, read_float, write_float, read_load_immediate_r0, write_load_immediate_r0, UnmappedAddress
from widgets.file_select import FileSelect
from PyQt6.QtWidgets import QTreeWidgetItem
from lib.game_visualizer import Game
from lib.BattalionXMLLib import BattalionObject

from widgets.menu.file_menu import EditorFileMenu
from widgets.graphics_widgets import UnitViewer

import typing
if typing.TYPE_CHECKING:
    from widgets.menu.plugin import PluginHandler


def get_treeitem(root: QTreeWidgetItem, obj):
    for i in range(root.childCount()):
        child = root.child(i)
        if child.bound_to == obj:
            return child
    return None


EDITOR_ROOT = os.path.dirname(__file__)


class LevelEditor(QMainWindow):
    def __init__(self):
        super().__init__()

        try:
            self.configuration = read_config()
            print("Config file loaded")
        except FileNotFoundError as e:
            print("No config file found, creating default config...")
            self.configuration = make_default_config()

        self.level_file = None
        self.plugin_handler = PluginHandler()
        self.hotreload_timer = QtCore.QTimer()
        self.hotreload_timer.setInterval(1000)
        self.hotreload_timer.timeout.connect(lambda: self.plugin_handler.hot_reload(self))
        self.hotreload_timer.start()

        self.installEventFilter(self)
        self.file_menu = EditorFileMenu(self)
        self.mini_model_viewer = UnitViewer(self, self, angle=0)
        self.setup_ui()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.lua_workbench: LuaWorkbench = None

        self.plugin_handler.load_plugins()
        self.plugin_handler.add_menu_actions(self)
        self.plugin_handler.add_plugin_widgets(self)

        if self.plugin_handler.plugin_sidewidget.is_empty():
            self.plugin_handler.plugin_sidewidget.setFixedSize(0, 0)
            self.horizontalLayout.setStretchFactor(0, 2)
            self.horizontalLayout.setStretchFactor(1, 3)
            self.horizontalLayout.setStretchFactor(3, 2)
            self.horizontalLayout.setSizes([self.leveldatatreeview.width(),
                                            self.level_view.width(),
                                            0,
                                            self.pik_control.width()])

        self.level_view.level_file = self.level_file
        self.level_view.set_editorconfig(self.configuration["editor"])
        self.level_view.visibility_menu = self.menubar.visibility_menu
        self.menubar.visibility_menu.filter_update.connect(self.level_view.graphics.set_dirty)
        self.menubar.visibility_menu.filter_update.connect(self.save_filter_settings)
        self.menubar.visibility_menu.restore(self.configuration)

        self.pathsconfig = self.configuration["default paths"]
        self.editorconfig = self.configuration["editor"]
        self.current_gen_path = None

        self.current_coordinates = None
        self.editing_windows = {}
        self.add_object_window = None
        self.object_to_be_added = None

        self.history = EditorLevelPositionsHistory(100, self)
        self.level_view.history = self.history
        self.edit_spawn_window = None

        self._window_title = ""
        self._user_made_change = False
        self._justupdatingselectedobject = False
        self.copypaste_obj = None

        self.addobjectwindow_last_selected = None

        self.loaded_archive = None
        self.loaded_archive_file = None
        self.last_position_clicked = []

        self.analyzer_window = None

        self._dontselectfromtree = False

        self.dolphin = Game()
        self.level_view.dolphin = self.dolphin
        self.last_chosen_type = ""

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.read_entityinit_if_changed)
        self.timer.start()

        self.plugin_handler.execute_event("load", self)

    def get_selected_obj(self) -> BattalionObject:
        if len(self.level_view.selected) == 1:
            return self.level_view.selected[0]
        else:
            return None

    def get_selected_objs(self, type_filter=None) -> list[BattalionObject]:
        if type_filter is None:
            return self.level_view.selected
        else:
            filtered = filter(lambda x: x.type == type_filter,
                              self.level_view.selected)

            return list(filtered)

    def get_level_object_by_id(self, id):
        if id in self.level_file.objects:
            return self.level_file.objects[id]

        if id in self.preload_file.objects:
            return self.preload_file.objects[id]

        return None

    def get_editor_folder(self):
        return EDITOR_ROOT

    def read_entityinit_if_changed(self):
        if self.level_file is None or self.level_file.objects is None:
            return

        if self.lua_workbench.is_initialized():
            if self.lua_workbench.did_file_change("EntityInitialise"):
                print("detected change to EntityInitialise.lua, re-reading file.")
                self.read_entityinit_and_update()
                self.lua_workbench.record_file_change("EntityInitialise")

    def read_entityinit_and_update(self):
        currentids = set(x for x in self.lua_workbench.entityinit.reflection_ids.keys())

        self.lua_workbench.read_entity_initialization()
        for id, name in self.lua_workbench.entityinit.reflection_ids.items():
            if id in self.level_file.objects:
                print("updating lua name for", id)
                obj = self.level_file.objects[id]
                obj.lua_name = name
            if id in currentids:
                currentids.remove(id)

        for id in currentids:
            if id in self.level_file.objects:
                print("removing lua name for", id)
                obj = self.level_file.objects[id]
                obj.lua_name = ""

        print("Finished reading")

    def save_filter_settings(self):
        self.menubar.visibility_menu.save(self.configuration)
        save_cfg(self.configuration)

    def eventFilter(self, object, event) -> bool:
        result = super().eventFilter(object, event)
        if (event.type() == QtCore.QEvent.Type.KeyRelease):
            if event.key() == Qt.Key.Key_Shift:
                self.level_view.shift_is_pressed = False

            if event.key() == Qt.Key.Key_W:
                self.level_view.MOVE_FORWARD = 0
            elif event.key() == Qt.Key.Key_S:
                self.level_view.MOVE_BACKWARD = 0
            elif event.key() == Qt.Key.Key_A:
                self.level_view.MOVE_LEFT = 0
            elif event.key() == Qt.Key.Key_D:
                self.level_view.MOVE_RIGHT = 0
            elif event.key() == Qt.Key.Key_Q:
                self.level_view.MOVE_UP = 0
            elif event.key() == Qt.Key.Key_E:
                self.level_view.MOVE_DOWN = 0
        return result

    def changeEvent(self, changeEvent: QtCore.QEvent) -> None:
        super().changeEvent(changeEvent)

        if changeEvent.type() == QtCore.QEvent.Type.ActivationChange:
            print("activation status change", self, self.isActiveWindow())
            if not self.isActiveWindow():
                self.level_view.selectionbox_projected_coords = None
                self.level_view.selectionbox_start = self.level_view.selectionbox_end = None
                self.level_view.shift_is_pressed = False
                self.level_view.MOVE_UP = 0
                self.level_view.MOVE_DOWN = 0
                self.level_view.MOVE_LEFT = 0
                self.level_view.MOVE_RIGHT = 0
                self.level_view.SPEEDUP = 0
                self.level_view.MOVE_FORWARD = 0
                self.level_view.MOVE_BACKWARD = 0

                self.update_3d()

    @catch_exception
    def reset(self):
        self.copypaste_obj = None
        self.menubar.reset_hook()
        self.last_position_clicked = []
        self.loaded_archive = None
        self.loaded_archive_file = None
        self.history.reset()
        self.object_to_be_added = None
        self.level_view.reset(keep_collision=True)
        self.mini_model_viewer.reset_scene()

        self.pik_control.close_all_windows()
        self.current_coordinates = None
        for key, val in self.editing_windows.items():
            val.destroy()

        self.editing_windows = {}

        if self.add_object_window is not None:
            self.add_object_window.destroy()
            self.add_object_window = None

        if self.edit_spawn_window is not None:
            self.edit_spawn_window.destroy()
            self.edit_spawn_window = None

        self.current_gen_path = None
        self.pik_control.reset_info()
        self.pik_control.button_add_object.setChecked(False)

        #self.pik_control.button_move_object.setChecked(False)
        self._window_title = ""
        self._user_made_change = False


        self.addobjectwindow_last_selected = None
        self.addobjectwindow_last_selected_category = None

    def set_base_window_title(self, name):
        self._window_title = name
        if name != "":
            self.setWindowTitle("Battalion Level Editor v{0} - ".format(__version__)+name)
        else:
            self.setWindowTitle("Battalion Level Editor v{0}".format(__version__))

    def set_has_unsaved_changes(self, hasunsavedchanges):
        if hasunsavedchanges and not self._user_made_change:
            self._user_made_change = True

            if self._window_title != "":
                self.setWindowTitle("Battalion Level Editor v{0} [Unsaved Changes] - ".format(__version__) + self._window_title)
            else:
                self.setWindowTitle("Battalion Level Editor v{0} [Unsaved Changes] ".format(__version__))
        elif not hasunsavedchanges and self._user_made_change:
            self._user_made_change = False
            if self._window_title != "":
                self.setWindowTitle("Battalion Level Editor v{0} - ".format(__version__) + self._window_title)
            else:
                self.setWindowTitle("Battalion Level Editor v{0}".format(__version__))

    def goto_object(self, obj):
        if self.dolphin.do_visualize():
            mtx = obj.mtxoverride
            x, y, z = mtx[12:15]
        else:
            bwmatrix = obj.getmatrix()
            x, y, z = bwmatrix.mtx[12:15]
            height = obj.calculate_height(self.level_view.bwterrain, self.level_view.waterheight)
            if height is not None:
                y = height
        print(x, y, z)

        if self.level_view.mode == MODE_TOPDOWN:
            self.level_view.offset_z = z
            self.level_view.offset_x = -x
        else:
            look = self.level_view.camera_direction.copy()

            fac = 100
            self.level_view.offset_z = (z - look.y * fac)
            self.level_view.offset_x = x - look.x * fac
            self.level_view.camera_height = y - look.z * fac
        print("teleported to object")
        self.level_view.do_redraw()

    @catch_exception_with_dialog
    def do_goto_action(self, item, index):
        if isinstance(item, LuaSearchResultItem):
            lua_script_name = item.script.removesuffix(".lua")
            self.lua_workbench.open_script(lua_script_name)
        else:
            print(item, index)
            self.tree_select_object(item)
            print(self.level_view.selected_positions)
            obj = item.bound_to
            bwmatrix = None

            if obj is None:
                return

            bwmatrix = obj.getmatrix()

            if bwmatrix is not None:
               self.goto_object(obj)
            elif obj.type == "cGameScriptResource" and obj.mName != "":
                self.lua_workbench.open_script(obj.mName)
            elif (obj.type in ("cGlobalScriptEntity", "cInitialisationScriptEntity")
                  and obj.mpScript is not None
                  and obj.mpScript.mName != ""):
                self.lua_workbench.open_script(obj.mpScript.mName)
            else:
                self.pik_control.action_open_edit_object()

    def tree_select_arrowkey(self):
        current = self.leveldatatreeview.selectedItems()
        if len(current) == 1:
            self.tree_select_object(current[0])

    def tree_search_action(self, text):
        txt = text.lower().strip()

        def search_func(obj):
            obj_text = obj.tostring().lower()
            in_model = obj.modelname is not None and txt in obj.modelname.lower()
            customname = obj.customname is not None and txt in obj.customname.lower()
            return txt in obj_text or in_model or customname

        self.leveldatatreeview.set_objects(
            self.level_file,
            self.preload_file,
            remember_position=True,
            filter_func=search_func
        )

    def tree_clear(self):
        self.leveldatatreeview.set_objects(
            self.level_file,
            self.preload_file,
            remember_position=True
        )

    def tree_select_object(self, item):
        """if self._dontselectfromtree:
            #print("hmm")
            #self._dontselectfromtree = False
            return"""

        print("Selected:", item)
        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []
        if hasattr(item, "bound_to") and item.bound_to is not None:
            self.level_view.selected = [item.bound_to]
            mtx = item.bound_to.getmatrix()
            if mtx is not None:
                self.level_view.selected_positions.append(mtx)

        self.level_view.center_gizmo(self.dolphin.do_visualize())
        self.update_3d()
        self.level_view.do_redraw(forceselected=True)
        self.level_view.select_update.emit()

    def setup_ui(self):
        self.resize(1000, 800)
        self.set_base_window_title("")

        self.menubar = EditorMenuBar(self)
        self.setMenuBar(self.menubar)

        #self.centralwidget = QWidget(self)
        #self.centralwidget.setObjectName("centralwidget")

        self.horizontalLayout = QSplitter()
        self.centralwidget = self.horizontalLayout
        self.setCentralWidget(self.horizontalLayout)


        self.tree_search = SearchBarReset(self.centralwidget)
        self.tree_search.searchbutton.setToolTip(
            "Searches for objects, whose XML content, model name or custom name matches the search term in a case insensitive way."
        )
        self.tree_search.reset.connect(self.tree_clear)
        self.tree_search.find.connect(self.tree_search_action)
        margin = self.tree_search.l.contentsMargins()
        self.tree_search.l.setContentsMargins(margin.left(), 0, margin.right(), 0)
        self.leveldatatreeview = LevelDataTreeView(self.centralwidget)
        #self.leveldatatreeview.itemClicked.connect(self.tree_select_object)
        self.leveldatatreeview.itemDoubleClicked.connect(self.do_goto_action)
        self.leveldatatreeview.itemSelectionChanged.connect(self.tree_select_arrowkey)

        self.tree_and_search = VerticalWidget(self.centralwidget, self.tree_search, self.leveldatatreeview)

        self.level_view = BolMapViewer(self.plugin_handler, self.centralwidget)

        self.horizontalLayout.setObjectName("horizontalLayout")
        self.vertical_holder = QSplitter(self)
        self.vertical_holder.setOrientation(Qt.Orientation.Vertical)
        self.left_side = QVBoxLayout(self.vertical_holder)
        self.vertical_holder.addWidget(self.tree_and_search)
        self.vertical_holder.addWidget(self.mini_model_viewer)


        self.horizontalLayout.addWidget(self.vertical_holder)# Widget(self.leveldatatreeview)
        self.horizontalLayout.addWidget(self.level_view)
        plugin_sidewidget = self.plugin_handler.create_plugin_sidewidget(self.centralwidget)
        self.horizontalLayout.addWidget(plugin_sidewidget)


        self.leveldatatreeview.resize(200, self.leveldatatreeview.height())
        spacerItem = QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        #self.horizontalLayout.addItem(spacerItem)

        self.pik_control = PikminSideWidget(self)
        self.horizontalLayout.addWidget(self.pik_control)
        #QtGui.QShortcut(Qt.Key.Key_G, self).activated.connect(self.action_ground_objects)
        self.add_shortcut = QtGui.QShortcut("Ctrl+A", self)
        self.add_shortcut.activated.connect(self.shortcut_open_add_item_window)
        self.edit_shortcut = QtGui.QShortcut("Ctrl+E", self)
        self.edit_shortcut.activated.connect(self.action_open_edit)
        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.connect_actions()



    def action_hook_into_dolphion(self):
        error = self.dolphin.initialize()
        if error != "":
            open_error_dialog(error, self)

    def action_load_minimap_image(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["minimap_png"],
            "Image (*.png);;All files (*)")

        if filepath:
            self.level_view.minimap.set_texture(filepath)

            self.pathsconfig["minimap_png"] = filepath
            save_cfg(self.configuration)

    def analyze_for_mistakes(self):
        if self.analyzer_window is not None:
            self.analyzer_window.destroy()
            self.analyzer_window = None

        self.analyzer_window = ErrorAnalyzer(self.level_file)
        self.analyzer_window.show()

    def update_render(self):
        self.level_view.do_redraw()

    def change_to_topdownview(self):
        self.level_view.change_from_3d_to_topdown()
        self.menubar.change_to_topdownview_action.setChecked(True)
        self.menubar.change_to_3dview_action.setChecked(False)

    def change_to_3dview(self):
        self.level_view.change_from_topdown_to_3d()
        self.menubar.change_to_topdownview_action.setChecked(False)
        self.menubar.change_to_3dview_action.setChecked(True)
        self.statusbar.clearMessage()

    def update_model_viewer(self):
        temp_scene = []
        count = 0
        editor = self
        midx, midy, midz = 0, 0, 0
        self.mini_model_viewer.reset_scene()

        if len(editor.level_view.selected) == 1:
            obj = editor.level_view.selected[0]
            self.mini_model_viewer.angle = pi/4.0
            if obj.getmatrix() is None and obj.modelname is not None:
                self.mini_model_viewer.set_scene_single_model(obj.modelname)
            elif obj.type == "cNodeHierarchyResource":
                self.mini_model_viewer.set_scene_single_model(obj.mName)
            elif obj.type == "cTextureResource":
                self.mini_model_viewer.set_scene_texture(obj.mName)
                self.mini_model_viewer.angle = 0
            elif obj.type == "cGUITextureWidget" and obj.mpTexture is not None:
                self.mini_model_viewer.set_scene_texture(obj.mpTexture.mName)
                self.mini_model_viewer.angle = 0
            elif obj.type == "sSpriteBasetype":
                if obj.texture is not None:
                    self.mini_model_viewer.set_scene_texture(obj.texture.mName)
                    self.mini_model_viewer.angle = 0
            elif obj.type == "cSprite":
                if obj.mBase is not None and obj.mBase.texture is not None:
                    self.mini_model_viewer.set_scene_texture(obj.mBase.texture.mName)
                    self.mini_model_viewer.angle = 0

        for obj in editor.level_view.selected:
            obj
            mtx = obj.getmatrix()
            if mtx is not None:
                selectedmodel = obj.modelname
                height = obj.height
                currmtx = mtx.mtx.copy()
                currmtx[13] = obj.height
                if selectedmodel is not None:
                    temp_scene.append((selectedmodel, currmtx))
                    midx += currmtx[12]
                    midy += currmtx[13]
                    midz += currmtx[14]
                    count += 1

        if count > 0:
            avgx = midx / count
            avgy = midy / count
            avgz = midz / count

            for model, mtx in temp_scene:
                mtx[12] = mtx[12] - avgx
                mtx[13] = mtx[13] - avgy
                mtx[14] = mtx[14] - avgz
                if count == 1:
                    mtx[0] = 1.0
                    mtx[1] = 0.0
                    mtx[2] = 0.0
                    mtx[3] = 0.0

                    mtx[4] = 0.0
                    mtx[5] = 1.0
                    mtx[6] = 0.0
                    mtx[7] = 0.0

                    mtx[8] = 0.0
                    mtx[9] = 0.0
                    mtx[10] = 1.0
                    mtx[11] = 0.0

                self.mini_model_viewer.add_to_scene(model, mtx)

            angle = pi / 4.0
            if len(editor.level_view.selected) == 1:
                obj = editor.level_view.selected[0]
                if obj.type == "cTroop":
                    angle = -pi * (3 / 4)

                if obj.type == "cTextureResource":
                    angle = 0
            self.mini_model_viewer.angle = angle
        self.mini_model_viewer.recalculate_camera()
        self.mini_model_viewer.update()

    def connect_actions(self):
        self.level_view.select_update.connect(self.action_update_info)
        self.level_view.select_update.connect(self.select_from_3d_to_treeview)
        self.level_view.select_update.connect(self.update_model_viewer)
        self.level_view.select_update.connect(lambda: self.plugin_handler.execute_event("select_update", self))
        #self.pik_control.lineedit_coordinatex.textChanged.connect(self.create_field_edit_action("coordinatex"))
        #self.pik_control.lineedit_coordinatey.textChanged.connect(self.create_field_edit_action("coordinatey"))
        #self.pik_control.lineedit_coordinatez.textChanged.connect(self.create_field_edit_action("coordinatez"))

        #self.pik_control.lineedit_rotationx.textChanged.connect(self.create_field_edit_action("rotationx"))
        #self.pik_control.lineedit_rotationy.textChanged.connect(self.create_field_edit_action("rotationy"))
        #self.pik_control.lineedit_rotationz.textChanged.connect(self.create_field_edit_action("rotationz"))

        self.level_view.position_update.connect(self.action_update_position)

        self.level_view.customContextMenuRequested.connect(self.mapview_showcontextmenu)

        #self.pik_control.button_add_object.pressed.connect(self.button_open_add_item_window)
        #self.pik_control.button_move_object.pressed.connect(self.button_move_objects)
        self.level_view.move_points.connect(self.action_move_objects)
        self.level_view.height_update.connect(self.action_change_object_heights)
        self.level_view.create_waypoint.connect(self.action_add_object)
        self.level_view.create_waypoint_3d.connect(self.action_add_object_3d)
        #self.pik_control.button_ground_object.pressed.connect(self.action_ground_objects)
        self.pik_control.button_remove_object.pressed.connect(self.action_delete_objects)

        delete_shortcut = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.activated.connect(self.action_delete_objects)
        self.delete_shortcut = delete_shortcut

        undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.action_undo)

        redo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.action_redo)

        self.level_view.rotate_current.connect(self.action_rotate_object)
        self.leveldatatreeview.select_all.connect(self.select_all_of_group)
        #self.leveldatatreeview.reverse.connect(self.reverse_all_of_group)
        #self.leveldatatreeview.duplicate.connect(self.duplicate_group)
        self.leveldatatreeview.split.connect(self.split_group)
        self.leveldatatreeview.split_checkpoint.connect(self.split_group_checkpoint)

    def split_group_checkpoint(self, group_item, item):
        group = group_item.bound_to
        point = item.bound_to

        if point == group.points[-1]:
            return

        """# Get an unused link to connect the groups with
        new_link = self.level_file.enemypointgroups.new_link_id()
        if new_link >= 2**14:
            raise RuntimeError("Too many links, cannot create more")
        """

        # Get new hopefully unused group id
        new_id = self.level_file.checkpoints.new_group_id()
        new_group = group.copy_group_after(new_id, point)
        self.level_file.checkpoints.groups.append(new_group)
        group.remove_after(point)
        new_group.prevlinks = [group.grouplink, -1, -1, -1]
        new_group.nextlinks = deepcopy(group.nextgroup)
        group.nextgroup = [new_group.grouplink, -1, -1, -1]

        self.leveldatatreeview.set_objects(self.level_file)
        self.update_3d()
        self.set_has_unsaved_changes(True)

    def split_group(self, group_item, item):
        group = group_item.bound_to
        point = item.bound_to

        if point == group.points[-1]:
            return

        # Get an unused link to connect the groups with
        new_link = self.level_file.enemypointgroups.new_link_id()
        if new_link >= 2**14:
            raise RuntimeError("Too many links, cannot create more")

        # Get new hopefully unused group id
        new_id = self.level_file.enemypointgroups.new_group_id()
        new_group = group.copy_group_after(new_id, point)
        self.level_file.enemypointgroups.groups.append(new_group)
        group.remove_after(point)

        group.points[-1].link = new_group.points[0].link = new_link

        self.leveldatatreeview.set_objects(self.level_file)
        self.update_3d()
        self.set_has_unsaved_changes(True)

    def select_all_of_group(self, item):
        group = item.bound_to
        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []
        for point in group.points:
            self.level_view.selected.append(point)

            if isinstance(group, libbol.CheckpointGroup):
                self.level_view.selected_positions.append(point.start)
                self.level_view.selected_positions.append(point.end)
            else:
                self.level_view.selected_positions.append(point.position)
        self.update_3d()

    def setup_level_file(self, level_file, preload_file, filepath):
        self.level_view.graphics.render_everything_once = True
        self.level_file = level_file
        self.preload_file = preload_file
        self.level_view.level_file = self.level_file
        # self.pikmin_gen_view.update()
        self.leveldatatreeview.set_objects(level_file, preload_file)
        self.level_view.do_redraw(force=True)

        print("File loaded")
        # self.bw_map_screen.update()
        # path_parts = path.split(filepath)
        self.set_base_window_title(filepath)
        self.pathsconfig["xml"] = filepath
        save_cfg(self.configuration)
        self.current_gen_path = filepath

    def button_load_collision(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "Collision (*.obj);;All files (*)")

            if not filepath:
                return

            with open(filepath, "r") as f:
                verts, faces, normals = py_obj.read_obj(f)
            alternative_mesh = TexturedModel.from_obj_path(filepath, rotate=True)

            self.setup_collision(verts, faces, filepath, alternative_mesh)

        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)

    def setup_collision(self, verts, faces, filepath, alternative_mesh=None):
        self.level_view.set_collision(verts, faces, alternative_mesh)
        self.pathsconfig["collision"] = filepath
        save_cfg(self.configuration)

    def action_close_edit_startpos_window(self):
        self.edit_spawn_window.destroy()
        self.edit_spawn_window = None

    @catch_exception_with_dialog
    def action_save_startpos(self):
        pos, direction = self.edit_spawn_window.get_pos_dir()
        self.pikmin_gen_file.startpos_x = pos[0]
        self.pikmin_gen_file.startpos_y = pos[1]
        self.pikmin_gen_file.startpos_z = pos[2]
        self.pikmin_gen_file.startdir = direction

        #self.pikmin_gen_view.update()
        self.pikmin_gen_view.do_redraw()
        self.set_has_unsaved_changes(True)

    """def button_open_add_item_window(self):
        if self.add_object_window is None:
            self.add_object_window = AddPikObjectWindow()
            self.add_object_window.button_savetext.pressed.connect(self.button_add_item_window_save)
            self.add_object_window.closing.connect(self.button_add_item_window_close)
            print("hmmm")
            if self.addobjectwindow_last_selected is not None:
                self.add_object_window.category_menu.setCurrentIndex(self.addobjectwindow_last_selected_category)
                self.add_object_window.template_menu.setCurrentIndex(self.addobjectwindow_last_selected)

            self.add_object_window.show()

        elif self.level_view.mousemode == mkdd_widgets.MOUSE_MODE_ADDWP:
            self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_NONE)
            self.pik_control.button_add_object.setChecked(False)"""

    def shortcut_open_add_item_window(self):
        self.pik_control.button_add_object.pressed.emit()
        """if self.add_object_window is None:
            self.add_object_window = AddPikObjectWindow()
            self.add_object_window.button_savetext.pressed.connect(self.button_add_item_window_save)
            self.add_object_window.closing.connect(self.button_add_item_window_close)
            print("object")
            if self.addobjectwindow_last_selected is not None:
                self.add_object_window.category_menu.setCurrentIndex(self.addobjectwindow_last_selected_category)
                self.add_object_window.template_menu.setCurrentIndex(self.addobjectwindow_last_selected)


            self.add_object_window.show()"""

    @catch_exception
    def action_add_object(self, x, z):
        y = 0
        object, group, position = self.object_to_be_added
        #if self.editorconfig.getboolean("GroundObjectsWhenAdding") is True:
        if isinstance(object, libbol.Checkpoint):
            y = object.start.y
        else:
            if self.level_view.collision is not None:
                y_collided = self.level_view.collision.collide_ray_downwards(x, z)
                if y_collided is not None:
                    y = y_collided

        self.action_add_object_3d(x, y, z)

    @catch_exception
    def action_add_object_3d(self, x, y, z):
        object, group, position = self.object_to_be_added
        if position is not None and position < 0:
            position = 99999999 # this forces insertion at the end of the list

        if isinstance(object, libbol.Checkpoint):
            if len(self.last_position_clicked) == 1:
                placeobject = deepcopy(object)

                x1, y1, z1 = self.last_position_clicked[0]
                placeobject.start.x = x1
                placeobject.start.y = y1
                placeobject.start.z = z1

                placeobject.end.x = x
                placeobject.end.y = y
                placeobject.end.z = z
                self.last_position_clicked = []
                self.level_file.checkpoints.groups[group].points.insert(position, placeobject)
                self.level_view.do_redraw()
                self.set_has_unsaved_changes(True)
                self.leveldatatreeview.set_objects(self.level_file)
            else:
                self.last_position_clicked = [(x, y, z)]

        else:
            placeobject = deepcopy(object)
            placeobject.position.x = x
            placeobject.position.y = y
            placeobject.position.z = z

            if isinstance(object, libbol.EnemyPoint):
                placeobject.group = group
                self.level_file.enemypointgroups.groups[group].points.insert(position, placeobject)
            elif isinstance(object, libbol.RoutePoint):
                self.level_file.routes[group].points.insert(position, placeobject)
            elif isinstance(object, libbol.MapObject):
                self.level_file.objects.objects.append(placeobject)
            elif isinstance(object, libbol.KartStartPoint):
                self.level_file.kartpoints.positions.append(placeobject)
            elif isinstance(object, libbol.JugemPoint):
                self.level_file.respawnpoints.append(placeobject)
            elif isinstance(object, libbol.Area):
                self.level_file.areas.areas.append(placeobject)
            elif isinstance(object, libbol.Camera):
                self.level_file.cameras.append(placeobject)
            else:
                raise RuntimeError("Unknown object type {0}".format(type(object)))

            self.level_view.do_redraw()
            self.leveldatatreeview.set_objects(self.level_file)
            self.set_has_unsaved_changes(True)



    @catch_exception
    def action_move_objects(self, deltax, deltay, deltaz):
        """for i in range(len(self.level_view.selected_positions)):
            for j in range(len(self.level_view.selected_positions)):
                pos = self.level_view.selected_positions
                if i != j and pos[i] == pos[j]:
                    print("What the fuck")"""
        if self.dolphin.running and self.dolphin.do_visualize():
            for obj in self.level_view.selected:
                if obj.mtxoverride is not None:
                    obj.mtxoverride[12] += deltax
                    obj.mtxoverride[13] += deltay
                    obj.mtxoverride[14] += deltaz
        else:
            for mtx in self.level_view.selected_positions:
                """obj.x += deltax
                obj.z += deltaz
                obj.x = round(obj.x, 6)
                obj.z = round(obj.z, 6)
                obj.position_x = obj.x
                obj.position_z = obj.z
                obj.offset_x = 0
                obj.offset_z = 0
    
                if self.editorconfig.getboolean("GroundObjectsWhenMoving") is True:
                    if self.pikmin_gen_view.collision is not None:
                        y = self.pikmin_gen_view.collision.collide_ray_downwards(obj.x, obj.z)
                        obj.y = obj.position_y = round(y, 6)
                        obj.offset_y = 0"""
                mtx.add_position(deltax, deltay, deltaz)



        #if len(self.pikmin_gen_view.selected) == 1:
        #    obj = self.pikmin_gen_view.selected[0]
        #    self.pik_control.set_info(obj, obj.position, obj.rotation)

        #self.pikmin_gen_view.update()
        self.level_view.do_redraw(forceselected=True)
        self.pik_control.update_info()
        self.set_has_unsaved_changes(True)


    @catch_exception
    def action_change_object_heights(self, deltay):
        for obj in self.pikmin_gen_view.selected:
            obj.y += deltay
            obj.y = round(obj.y, 6)
            obj.position_y = obj.y
            obj.offset_y = 0

        if len(self.pikmin_gen_view.selected) == 1:
            obj = self.pikmin_gen_view.selected[0]
            self.pik_control.set_info(obj, (obj.x, obj.y, obj.z), obj.get_rotation())

        #self.pikmin_gen_view.update()
        self.pikmin_gen_view.do_redraw()
        self.set_has_unsaved_changes(True)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key.Key_Shift:
            self.level_view.shift_is_pressed = True
        elif event.key() == Qt.Key.Key_R:
            self.level_view.rotation_is_pressed = True
        elif event.key() == Qt.Key.Key_H:
            self.level_view.change_height_is_pressed = True

        if event.key() == Qt.Key.Key_W:
            self.level_view.MOVE_FORWARD = 1
        elif event.key() == Qt.Key.Key_S:
            self.level_view.MOVE_BACKWARD = 1
        elif event.key() == Qt.Key.Key_A:
            self.level_view.MOVE_LEFT = 1
        elif event.key() == Qt.Key.Key_D:
            self.level_view.MOVE_RIGHT = 1
        elif event.key() == Qt.Key.Key_Q:
            self.level_view.MOVE_UP = 1
        elif event.key() == Qt.Key.Key_E:
            self.level_view.MOVE_DOWN = 1

        if event.key() == Qt.Key.Key_Plus:
            self.level_view.zoom_in()
        elif event.key() == Qt.Key.Key_Minus:
            self.level_view.zoom_out()

        self.plugin_handler.execute_event("key_press", self, event.key())

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key.Key_Shift:
            self.level_view.shift_is_pressed = False
        elif event.key() == Qt.Key.Key_R:
            self.level_view.rotation_is_pressed = False
        elif event.key() == Qt.Key.Key_H:
            self.level_view.change_height_is_pressed = False

        if event.key() == Qt.Key.Key_W:
            self.level_view.MOVE_FORWARD = 0
        elif event.key() == Qt.Key.Key_S:
            self.level_view.MOVE_BACKWARD = 0
        elif event.key() == Qt.Key.Key_A:
            self.level_view.MOVE_LEFT = 0
        elif event.key() == Qt.Key.Key_D:
            self.level_view.MOVE_RIGHT = 0
        elif event.key() == Qt.Key.Key_Q:
            self.level_view.MOVE_UP = 0
        elif event.key() == Qt.Key.Key_E:
            self.level_view.MOVE_DOWN = 0

        self.plugin_handler.execute_event("key_release", self, event.key())

    def focusOutEvent(self, a0) -> None:
        super().focusOutEvent(a0)
        #self.level_view.shift_is_pressed = False
        self.level_view.MOVE_FORWARD = 0
        self.level_view.MOVE_BACKWARD = 0
        self.level_view.MOVE_LEFT = 0
        self.level_view.MOVE_RIGHT = 0
        self.level_view.MOVE_UP = 0
        self.level_view.MOVE_DOWN = 0

    def action_rotate_object(self, deltarotation):
        #obj.set_rotation((None, round(angle, 6), None))
        if self.dolphin.do_visualize():
            for obj in self.level_view.selected:
                if obj.mtxoverride is not None:
                    if deltarotation.x != 0:
                        BWMatrix.static_rotate_x(obj.mtxoverride, deltarotation.x)
                    if deltarotation.y != 0:
                        BWMatrix.static_rotate_y(obj.mtxoverride, deltarotation.y)
                    if deltarotation.z != 0:
                        BWMatrix.static_rotate_z(obj.mtxoverride, deltarotation.z)
        else:
            for mtx in self.level_view.selected_positions:
                if hasattr(mtx, "mtx"):
                    if deltarotation.x != 0:
                        BWMatrix.static_rotate_x(mtx.mtx, deltarotation.x)
                    if deltarotation.y != 0:
                        mtx.rotate_y(deltarotation.y)
                    if deltarotation.z != 0:
                        BWMatrix.static_rotate_z(mtx.mtx, deltarotation.z)

        #if self.rotation_mode.isChecked():
        if True:
            middle = self.level_view.gizmo.position


            for obj in chain(self.level_view.selected, self.level_view.selected_misc):
                if obj.getmatrix() is not None:
                    if self.dolphin.do_visualize() and obj.mtxoverride is not None:
                        mtx = obj.mtxoverride
                    else:
                        mtx = obj.getmatrix().mtx
                    position = Vector3(mtx[12], mtx[13], mtx[14])
                elif obj.getposition() is not None:
                    position = Vector3(*obj.getposition())
                    mtx = None

                else:
                    position = None
                    mtx = None

                if position is not None:
                    diff = position - middle
                    diff.y = 0.0

                    length = diff.norm()
                    if length > 0:
                        diff.normalize()
                        angle = atan2(diff.x, diff.z)
                        angle += deltarotation.y
                        position.x = middle.x + length * sin(angle)
                        position.z = middle.z + length * cos(angle)

                    if mtx is not None:
                        mtx[12] = position.x
                        mtx[14] = position.z
                    else:
                        obj.setposition(position.x, position.y, position.z)

        #self.pikmin_gen_view.update()
        self.level_view.do_redraw(forceselected=True)
        self.set_has_unsaved_changes(True)
        self.pik_control.update_info()

    def action_ground_objects(self):
        for pos in self.level_view.selected_positions:
            if self.level_view.collision is None:
                return None
            height = self.level_view.collision.collide_ray_closest(pos.x, pos.z, pos.y)

            if height is not None:
                pos.y = height

        self.pik_control.update_info()
        self.level_view.center_gizmo(self.dolphin.do_visualize())
        self.set_has_unsaved_changes(True)
        self.level_view.do_redraw()

    def delete_objects(self, objects):
        self.level_file.delete_objects(objects)
        self.preload_file.delete_objects(objects)
        for obj in objects:
            obj.delete()

        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []

        self.pik_control.reset_info()
        self.leveldatatreeview.set_objects(self.level_file, self.preload_file, remember_position=True)
        self.level_view.gizmo.hidden = True
        # self.pikmin_gen_view.update()
        self.level_view.do_redraw(force=True)
        self.set_has_unsaved_changes(True)

    def action_delete_objects(self):
        objcount = len(self.level_view.selected)
        if objcount == 0:
            pass
        elif objcount > 0:
            if objcount == 1:
                text = "1 object selected."
                description = "Do you want to delete it?"
            else:
                text = f"{objcount} objects selected."
                description = "Do you want to delete them?"

            result = open_yesno_box(text, description)
            if result:
                self.delete_objects(self.level_view.selected)

        self.plugin_handler.execute_event("delete_press", self)

    @catch_exception
    def action_undo(self):
        if not self.dolphin.do_visualize():
            state = self.history.history_undo()
            if state is None:
                print("reached end of undo history")
            else:
                for entry in state:
                    entry: HistoryEntry
                    entry.restore()

                if len(state) > 0:
                    self.level_view.do_redraw(force=True)
                    self.set_has_unsaved_changes(True)
                    self.update_3d()

    @catch_exception
    def action_redo(self):
        if not self.dolphin.do_visualize():
            state = self.history.history_redo()
            if state is None:
                print("reached end of undo history")
            else:
                for entry in state:
                    entry: HistoryEntry
                    entry.restore()
                if len(state) > 0:
                    self.level_view.do_redraw(force=True)
                    self.set_has_unsaved_changes(True)
                    self.update_3d()

    def update_3d(self):
        if not hasattr(self, "dolphin"):
            self.level_view.center_gizmo(False)
        else:
            self.level_view.center_gizmo(self.dolphin.do_visualize())
        self.level_view.do_redraw()

    def select_from_3d_to_treeview(self):
        if self.level_file is not None:
            selected = self.level_view.selected
            if len(selected) == 1:
                currentobj = selected[0]
                item = None
                """if isinstance(currentobj, libbol.EnemyPoint):
                    for i in range(self.leveldatatreeview.enemyroutes.childCount()):
                        child = self.leveldatatreeview.enemyroutes.child(i)
                        item = get_treeitem(child, currentobj)
                        if item is not None:
                            break"""


                #assert item is not None
                if item is not None:
                    #self._dontselectfromtree = True
                    self.leveldatatreeview.setCurrentItem(item)

    @catch_exception
    def action_update_info(self):
        if self.level_file is not None:
            selected = self.level_view.selected
            if len(selected) == 1:
                currentobj = selected[0]
                """if isinstance(currentobj, Route):
                    objects = []
                    index = self.level_file.routes.index(currentobj)
                    for object in self.level_file.objects.objects:
                        if object.pathid == index:
                            objects.append(get_full_name(object.objectid))
                    for i, camera in enumerate(self.level_file.cameras):
                        if camera.route == index:
                            objects.append("Camera {0}".format(i))

                    self.pik_control.set_info(currentobj, self.update_3d, objects)
                else:"""
                self.pik_control.set_info(currentobj, self.update_3d)

                self.pik_control.update_info()
            else:
                self.pik_control.reset_info("{0} objects selected".format(len(self.level_view.selected)))
                self.pik_control.set_objectlist(selected)

    def closeEvent(self, event:QtGui.QCloseEvent):
        if self._user_made_change:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setText(
                "You have unsaved changes!")
            msgbox.setInformativeText("Are you sure you want to quit? Unsaved changes will be lost!")
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
            msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msgbox.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
            msgbox.setWindowTitle("Warning")
            result = msgbox.exec()
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                super().closeEvent(event)
            else:
                event.ignore()

    @catch_exception
    def mapview_showcontextmenu(self, position):
        if self.level_view.is_topdown():
            context_menu = QMenu(self)
            action = QAction("Copy Coordinates", self)
            action.triggered.connect(self.action_copy_coords_to_clipboard)
            context_menu.addAction(action)
            context_menu.exec(self.level_view.mapToGlobal(position))
            context_menu.destroy()

    def action_copy_coords_to_clipboard(self):
        if self.current_coordinates is not None:
            QApplication.clipboard().setText(", ".join(str(x) for x in self.current_coordinates))

    def action_update_position(self, event, pos):
        self.current_coordinates = pos
        self.statusbar.showMessage("({}, {}, {})".format(*pos))

    def action_open_edit(self):
        if self.pik_control.button_edit_object.isEnabled():
            self.pik_control.button_edit_object.pressed.emit()


class EditorHistory(object):
    def __init__(self, historysize):
        self.history = []
        self.top = 0
        self.historysize = historysize

    def reset(self):
        del self.history
        self.history = []
        self.top = 0

    def _add_history(self, entry):
        if self.top == len(self.history):
            self.history.append(entry)
            self.top += 1
        else:
            for i in range(len(self.history) - self.top):
                self.history.pop()
            self.history.append(entry)
            self.top += 1
            assert len(self.history) == self.top

        if len(self.history) > self.historysize:
            for i in range(len(self.history) - self.historysize):
                self.history.pop(0)
                self.top -= 1

    def add(self, entry):
        self._add_history(entry)

    def history_undo(self):
        if self.top == 0:
            return None

        self.top -= 1
        return self.history[self.top]

    def history_redo(self):
        if self.top >= len(self.history)-1:
            return None

        self.top += 1
        item = self.history[self.top]

        return item


@dataclass
class HistoryEntry:
    obj: object #BattalionObject
    data1: object
    data2: object

    def restore(self):
        pass
    #matrix: numpy.array
    #override: numpy.array


@dataclass
class HistoryEntryBW(HistoryEntry):
    obj: BattalionObject
    data1: numpy.array
    data2: numpy.array

    def restore(self):
        currmtx = self.obj.getmatrix()
        if currmtx is not None:
            for i in range(16):
                currmtx.mtx[i] = self.data1[i]
            self.obj.update_xml()

    @classmethod
    def backup(cls, obj):
        bwmtx = obj.getmatrix()
        mtx = bwmtx.mtx.copy()
        if obj.mtxoverride is not None:
            overridemtx = obj.mtxoverride.copy()
        else:
            overridemtx = None

        return cls(obj, mtx, overridemtx)

@dataclass
class HistoryEntryPFD:
    obj: PathfindPoint
    data1: tuple
    data2: tuple

    def restore(self):
        self.obj.setposition(*self.data1)

    @classmethod
    def backup(cls, obj):
        return cls(obj, obj.getposition(), None)

@dataclass
class ActionStep:
    prev: list
    curr: list


class EditorLevelPositionsHistory(EditorHistory):
    def __init__(self, historysize, editor):
        super().__init__(historysize)
        self.editor: LevelEditor = editor
        self.history: list[HistoryEntry]

    def stash_record(self, objects):
        record = []
        for obj in objects:
            bwmtx = obj.getmatrix()
            if bwmtx is not None:
                entry = HistoryEntryBW.backup(obj)
                record.append(entry)
            elif obj.getposition() is not None:
                entry = HistoryEntryPFD.backup(obj)
                record.append(entry)

        return record

    def create_updated_record(self, record: list[HistoryEntry]):
        newrecord = self.stash_record(
            entry.obj for entry in record
        )

        return newrecord

    def stash_selected(self):
        return self.stash_record(
            chain(self.editor.level_view.selected, self.editor.level_view.selected_misc))

    def record_stash(self, stash):
        if len(stash) > 0 and not self.editor.dolphin.do_visualize():
            current = self.create_updated_record(stash)
            self.add(ActionStep(stash, current))

    def print_state(self):
        indicators = ["  " for x in range(self.historysize)]
        indicators[self.top] = " v"
        indices = [str(x).rjust(2, " ") for x in range(self.historysize)]

        print(" ".join(indicators))
        print(" ".join(indices))

    def history_undo(self):
        if not self.history:
            return None

        if self.top > 0:
            self.top -= 1

        state = self.history[self.top].prev

        self.print_state()
        return state

    def history_redo(self):
        if self.top >= len(self.history):
            return None

        state = self.history[self.top].curr
        self.top += 1

        self.print_state()
        return state


import sys
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

def f8_alt(x):
    return "%14.9f" % x

def splitnowhitespace(line):
    line = line.strip().split(" ")
    while line.count("") > 0:
        line.remove("")

    return line


class Logger(object):
    def __init__(self, stdout, logfile):
        self.terminal = stdout
        self.log = logfile

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()



if __name__ == "__main__":
    multiprocessing.freeze_support()
    #with cProfile.Profile() as pr:
    if True:
        pr = None
        #import sys
        import platform
        import argparse
        from PyQt6.QtCore import QLocale
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtCore import Qt

        QLocale.setDefault(QLocale(QLocale.Language.English))

        sys.excepthook = except_hook

        parser = argparse.ArgumentParser()

        parser.add_argument("filepath", default=None, help="Path to level to be loaded.", nargs="?")

        args = parser.parse_args()
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
        app = QApplication(sys.argv)

        try:
            configuration = read_config()
        except FileNotFoundError as e:
            darkmode = False
        else:
            darkmode = configuration["editor"].getboolean("dark_mode", fallback=True)

        if darkmode:
            app.setStyle('Fusion')
            palette = QPalette()

            for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
                palette.setColor(group, QPalette.ColorRole.Window, QColor(53, 53, 53))
                palette.setColor(group, QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
                palette.setColor(group, QPalette.ColorRole.Base, QColor(35, 35, 35))
                palette.setColor(group, QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
                palette.setColor(group, QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
                palette.setColor(group, QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
                palette.setColor(group, QPalette.ColorRole.Text, Qt.GlobalColor.white)
                palette.setColor(group, QPalette.ColorRole.Button, QColor(53, 53, 53))
                palette.setColor(group, QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
                palette.setColor(group, QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
                palette.setColor(group, QPalette.ColorRole.Link, QColor(42, 130, 218))
                palette.setColor(group, QPalette.ColorRole.Highlight, QColor(42, 130, 218))
                palette.setColor(group, QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

            app.setStyleSheet("QToolTip { color: #000000; background-color: #FFFFFF; border: 0px; }")

            # This disables a weird white outline used when e.g. a menu element was disabled
            # Example: "Apply Live Positions to Selected"
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Light, QColor(35, 35, 35))

            app.setPalette(palette)

        if platform.system() == "Windows":
            import ctypes
            myappid = 'BWEditor'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        with open("editor_log.txt", "w") as f:
            logger = Logger(sys.stdout, f)
            loggererr = Logger(sys.stderr, f)
            sys.stdout = logger
            sys.stderr = loggererr
            print("Python version: ", sys.version)
            print("BW Editor Version: ", __version__)
            editor_gui = LevelEditor()
            editor_gui.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
            # Debugging

            editor_gui.show()
            if args.filepath is not None:
                editor_gui.file_menu.button_load_level(args.filepath)
            err_code = app.exec()

        if pr is not None:
            for sortedby in ("ncalls", "tottime", "cumtime"):
                statsname = "stats_{0}.txt".format(sortedby)
                statsmorename = "statsmore_{0}.txt".format(sortedby)

                with open(statsname, "w") as f:
                    stats = pstats.Stats(pr, stream=f)
                    stats.f8 = f8_alt
                    stats.sort_stats(sortedby)
                    stats.print_stats(200)
                    stats.print_callees(200)
                    stats.print_callers(200)
                    """a = pr.create_stats()
                    print(a)
                    pr.sort_stats("calls")
                    pr.print_stats()
                    pr.print_callers()"""

                with open(statsname, "r") as f:
                    with open(statsmorename, "w") as g:
                        noprocess = True

                        for line in f:
                            parts = splitnowhitespace(line)
                            if parts:
                                if noprocess:
                                    if parts[0] == "ncalls":
                                        noprocess = False
                                else:
                                    ncalls, tottime = parts[0], parts[1]
                                    if "/" in ncalls:
                                        ncalls = ncalls.split("/")[0]
                                    cumtime = parts[3]
                                    parts[2] = "{:.7f}".format(float(tottime)/float(ncalls))
                                    parts[4] = "{:.7f}".format(float(cumtime)/float(ncalls))

                                    linestart = g.tell()
                                    tab = 16

                                    """g.write(parts[0])
                                    g.write(((g.tell()-linestart+tab)%tab)*" ")
                                    g.write(parts[1])
                                    g.write(((g.tell() - linestart+tab) % tab) * " ")
                                    g.write(parts[2])
                                    g.write(((g.tell() - linestart+tab) % tab) * " ")
                                    g.write(parts[3])
                                    g.write(((g.tell() - linestart+tab) % tab) * " ")"""
                                    g.write(parts[0])
                                    g.write((tab - (g.tell() - linestart) % tab) * " ")
                                    g.write(parts[1])
                                    g.write((tab - (g.tell() - linestart) % tab) * " ")
                                    g.write(parts[2])
                                    g.write((tab - (g.tell() - linestart) % tab) * " ")
                                    g.write(parts[3])
                                    g.write((tab - (g.tell() - linestart) % tab) * " ")
                                    g.write(parts[4])
                                    g.write((tab - (g.tell() - linestart) % tab) * " ")
                                    g.write(" ".join(parts[5:]))

                                    #g.write("\t\t\t".join(parts))
                                    g.write("\n")
                            elif noprocess == False:
                                break







    sys.exit(err_code)