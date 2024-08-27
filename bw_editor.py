import cProfile
import pstats
import traceback
import os
from timeit import default_timer
from copy import deepcopy
from io import TextIOWrapper, BytesIO, StringIO
from math import sin, cos, atan2
import json
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit)
from PyQt5.QtGui import QMouseEvent, QImage
import PyQt5.QtGui as QtGui

import opengltext
import py_obj
from lib.vectors import Vector3
from widgets.menu.menubar import EditorMenuBar
from widgets.editor_widgets import catch_exception
from widgets.editor_widgets import AddPikObjectWindow
from widgets.tree_view import LevelDataTreeView
import widgets.tree_view as tree_view
from configuration import read_config, make_default_config, save_cfg

import bw_widgets # as mkddwidgets
from widgets.side_widget import PikminSideWidget
from widgets.editor_widgets import open_error_dialog, catch_exception_with_dialog
from bw_widgets import BolMapViewer, MODE_TOPDOWN

from lib.model_rendering import TexturedModel, CollisionModel, Minimap

from lib.dolreader import DolFile, read_float, write_float, read_load_immediate_r0, write_load_immediate_r0, UnmappedAddress
from widgets.file_select import FileSelect
from PyQt5.QtWidgets import QTreeWidgetItem
from lib.game_visualizer import Game

from widgets.menu.file_menu import EditorFileMenu
PIKMIN2GEN = "Generator files (defaultgen.txt;initgen.txt;plantsgen.txt;*.txt)"


def get_treeitem(root:QTreeWidgetItem, obj):
    for i in range(root.childCount()):
        child = root.child(i)
        if child.bound_to == obj:
            return child
    return None


class LevelEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.level_file = None

        self.file_menu = EditorFileMenu(self)

        self.setup_ui()
        self.setCursor(Qt.ArrowCursor)
        try:
            self.configuration = read_config()
            print("Config file loaded")
        except FileNotFoundError as e:
            print("No config file found, creating default config...")
            self.configuration = make_default_config()

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

        self.addobjectwindow_last_selected = None

        self.loaded_archive = None
        self.loaded_archive_file = None
        self.last_position_clicked = []

        self.analyzer_window = None

        self._dontselectfromtree = False

        self.dolphin = Game()
        self.level_view.dolphin = self.dolphin
        self.last_chosen_type = ""

    def save_filter_settings(self):
        self.menubar.visibility_menu.save(self.configuration)
        save_cfg(self.configuration)

    def eventFilter(self, a0: 'QObject', a1: 'QEvent') -> bool:
        super().eventFilter(a0, a1)
        if a1 == QtCore.QEvent.MouseMove:
            pass

    @catch_exception
    def reset(self):
        self.menubar.reset_hook()
        self.last_position_clicked = []
        self.loaded_archive = None
        self.loaded_archive_file = None
        self.history.reset()
        self.object_to_be_added = None
        self.level_view.reset(keep_collision=True)

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
            self.setWindowTitle("Battalion Level Editor - "+name)
        else:
            self.setWindowTitle("Battalion Level Editor")

    def set_has_unsaved_changes(self, hasunsavedchanges):
        if hasunsavedchanges and not self._user_made_change:
            self._user_made_change = True

            if self._window_title != "":
                self.setWindowTitle("Battalion Level Editor [Unsaved Changes] - " + self._window_title)
            else:
                self.setWindowTitle("Battalion Level Editor [Unsaved Changes] ")
        elif not hasunsavedchanges and self._user_made_change:
            self._user_made_change = False
            if self._window_title != "":
                self.setWindowTitle("Battalion Level Editor - " + self._window_title)
            else:
                self.setWindowTitle("Battalion Level Editor")

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
        else:
            self.pik_control.action_open_edit_object()

    def tree_select_arrowkey(self):
        current = self.leveldatatreeview.selectedItems()
        if len(current) == 1:
            self.tree_select_object(current[0])

    def tree_select_object(self, item):
        """if self._dontselectfromtree:
            #print("hmm")
            #self._dontselectfromtree = False
            return"""

        print("Selected:", item)
        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []
        if hasattr(item, "bound_to"):
            self.level_view.selected = [item.bound_to]

        self.level_view.gizmo.move_to_average(self.level_view.selected,
                                              self.level_view.bwterrain,
                                              self.level_view.waterheight,
                                              self.dolphin.do_visualize())
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
        self.leveldatatreeview = LevelDataTreeView(self.centralwidget)
        #self.leveldatatreeview.itemClicked.connect(self.tree_select_object)
        self.leveldatatreeview.itemDoubleClicked.connect(self.do_goto_action)
        self.leveldatatreeview.itemSelectionChanged.connect(self.tree_select_arrowkey)

        self.level_view = BolMapViewer(self.centralwidget)

        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.addWidget(self.leveldatatreeview)
        self.horizontalLayout.addWidget(self.level_view)
        self.leveldatatreeview.resize(200, self.leveldatatreeview.height())
        spacerItem = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        #self.horizontalLayout.addItem(spacerItem)

        self.pik_control = PikminSideWidget(self)
        self.horizontalLayout.addWidget(self.pik_control)

        QtWidgets.QShortcut(Qt.Key_G, self).activated.connect(self.action_ground_objects)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_A, self).activated.connect(self.shortcut_open_add_item_window)
        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_E, self).activated.connect(self.action_open_edit)
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

    def connect_actions(self):
        self.level_view.select_update.connect(self.action_update_info)
        self.level_view.select_update.connect(self.select_from_3d_to_treeview)
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

        delete_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.action_delete_objects)

        undo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Z), self)
        undo_shortcut.activated.connect(self.action_undo)

        redo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Y), self)
        redo_shortcut.activated.connect(self.action_redo)

        self.level_view.rotate_current.connect(self.action_rotate_object)
        self.leveldatatreeview.select_all.connect(self.select_all_of_group)
        self.leveldatatreeview.reverse.connect(self.reverse_all_of_group)
        self.leveldatatreeview.duplicate.connect(self.duplicate_group)
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

    def duplicate_group(self, item):
        group = item.bound_to
        if isinstance(group, libbol.EnemyPointGroup):
            new_id = len(self.level_file.enemypointgroups.groups)
            new_group = group.copy_group(new_id)
            self.level_file.enemypointgroups.groups.append(new_group)

            self.leveldatatreeview.set_objects(self.level_file)
            self.update_3d()
            self.set_has_unsaved_changes(True)

    def reverse_all_of_group(self, item):
        group = item.bound_to
        if isinstance(group, libbol.CheckpointGroup):
            group.points.reverse()
            for point in group.points:
                start = point.start
                point.start = point.end
                point.end = start
        elif isinstance(group, libbol.EnemyPointGroup):
            group.points.reverse()
        elif isinstance(group, libbol.Route):
            group.points.reverse()

        self.leveldatatreeview.set_objects(self.level_file)
        self.update_3d()

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

    def action_open_rotationedit_window(self):
        if self.edit_spawn_window is None:
            self.edit_spawn_window = mkdd_widgets.SpawnpointEditor()
            self.edit_spawn_window.position.setText("{0}, {1}, {2}".format(
                self.pikmin_gen_file.startpos_x, self.pikmin_gen_file.startpos_y, self.pikmin_gen_file.startpos_z
            ))
            self.edit_spawn_window.rotation.setText(str(self.pikmin_gen_file.startdir))
            self.edit_spawn_window.closing.connect(self.action_close_edit_startpos_window)
            self.edit_spawn_window.button_savetext.pressed.connect(self.action_save_startpos)
            self.edit_spawn_window.show()

    #@catch_exception


    def load_optional_3d_file(self, additional_files, bmdfile, collisionfile):
        choice, pos = FileSelect.open_file_list(self, additional_files,
                                                "Select additional file to load", startat=0)

        if choice.endswith("(3D Model)"):
            alternative_mesh = load_textured_bmd(bmdfile)
            with open("lib/temp/temp.obj", "r") as f:
                verts, faces, normals = py_obj.read_obj(f)

            self.setup_collision(verts, faces, bmdfile, alternative_mesh)

        elif choice.endswith("(3D Collision)"):
            bco_coll = RacetrackCollision()
            verts = []
            faces = []

            with open(collisionfile, "rb") as f:
                bco_coll.load_file(f)

            for vert in bco_coll.vertices:
                verts.append(vert)

            for v1, v2, v3, collision_type, rest in bco_coll.triangles:
                faces.append(((v1 + 1, None), (v2 + 1, None), (v3 + 1, None)))
            model = CollisionModel(bco_coll)
            self.setup_collision(verts, faces, collisionfile, alternative_mesh=model)

    def load_optional_3d_file_arc(self, additional_files, bmdfile, collisionfile, arcfilepath):
        choice, pos = FileSelect.open_file_list(self, additional_files,
                                                "Select additional file to load", startat=0)

        if choice.endswith("(3D Model)"):
            with open("lib/temp/temp.bmd", "wb") as f:
                f.write(bmdfile.getvalue())

            bmdpath = "lib/temp/temp.bmd"
            alternative_mesh = load_textured_bmd(bmdpath)
            with open("lib/temp/temp.obj", "r") as f:
                verts, faces, normals = py_obj.read_obj(f)

            self.setup_collision(verts, faces, arcfilepath, alternative_mesh)

        elif choice.endswith("(3D Collision)"):
            bco_coll = RacetrackCollision()
            verts = []
            faces = []

            bco_coll.load_file(collisionfile)

            for vert in bco_coll.vertices:
                verts.append(vert)

            for v1, v2, v3, collision_type, rest in bco_coll.triangles:
                faces.append(((v1 + 1, None), (v2 + 1, None), (v3 + 1, None)))
            model = CollisionModel(bco_coll)
            self.setup_collision(verts, faces, arcfilepath, alternative_mesh=model)

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
    def button_add_item_window_save(self):
        print("ohai")
        if self.add_object_window is not None:
            self.object_to_be_added = self.add_object_window.get_content()
            if self.object_to_be_added is None:
                return

            obj = self.object_to_be_added[0]

            if isinstance(obj, (libbol.EnemyPointGroup, libbol.CheckpointGroup, libbol.Route,
                                                    libbol.LightParam, libbol.MGEntry)):
                if isinstance(obj, libbol.EnemyPointGroup):
                    self.level_file.enemypointgroups.groups.append(obj)
                elif isinstance(obj, libbol.CheckpointGroup):
                    self.level_file.checkpoints.groups.append(obj)
                elif isinstance(obj, libbol.Route):
                    self.level_file.routes.append(obj)
                elif isinstance(obj, libbol.LightParam):
                    self.level_file.lightparams.append(obj)
                elif isinstance(obj, libbol.MGEntry):
                    self.level_file.lightparams.append(obj)

                self.addobjectwindow_last_selected_category = self.add_object_window.category_menu.currentIndex()
                self.object_to_be_added = None
                self.add_object_window.destroy()
                self.add_object_window = None
                self.leveldatatreeview.set_objects(self.level_file)

            elif self.object_to_be_added is not None:
                self.addobjectwindow_last_selected_category = self.add_object_window.category_menu.currentIndex()
                self.pik_control.button_add_object.setChecked(True)
                #self.pik_control.button_move_object.setChecked(False)
                self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_ADDWP)
                self.add_object_window.destroy()
                self.add_object_window = None
                #self.pikmin_gen_view.setContextMenuPolicy(Qt.DefaultContextMenu)

    @catch_exception
    def button_add_item_window_close(self):
        # self.add_object_window.destroy()
        print("Hmmm")
        self.add_object_window = None
        self.pik_control.button_add_object.setChecked(False)
        self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_NONE)

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
        for i in range(len(self.level_view.selected_positions)):
            for j in range(len(self.level_view.selected_positions)):
                pos = self.level_view.selected_positions
                if i != j and pos[i] == pos[j]:
                    print("What the fuck")
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

        if event.key() == Qt.Key_Escape:
            self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_NONE)
            self.pik_control.button_add_object.setChecked(False)
            #self.pik_control.button_move_object.setChecked(False)
            if self.add_object_window is not None:
                self.add_object_window.close()

        if event.key() == Qt.Key_Shift:
            self.level_view.shift_is_pressed = True
        elif event.key() == Qt.Key_R:
            self.level_view.rotation_is_pressed = True
        elif event.key() == Qt.Key_H:
            self.level_view.change_height_is_pressed = True

        if event.key() == Qt.Key_W:
            self.level_view.MOVE_FORWARD = 1
        elif event.key() == Qt.Key_S:
            self.level_view.MOVE_BACKWARD = 1
        elif event.key() == Qt.Key_A:
            self.level_view.MOVE_LEFT = 1
        elif event.key() == Qt.Key_D:
            self.level_view.MOVE_RIGHT = 1
        elif event.key() == Qt.Key_Q:
            self.level_view.MOVE_UP = 1
        elif event.key() == Qt.Key_E:
            self.level_view.MOVE_DOWN = 1

        if event.key() == Qt.Key_Plus:
            self.level_view.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.level_view.zoom_out()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.level_view.shift_is_pressed = False
        elif event.key() == Qt.Key_R:
            self.level_view.rotation_is_pressed = False
        elif event.key() == Qt.Key_H:
            self.level_view.change_height_is_pressed = False

        if event.key() == Qt.Key_W:
            self.level_view.MOVE_FORWARD = 0
        elif event.key() == Qt.Key_S:
            self.level_view.MOVE_BACKWARD = 0
        elif event.key() == Qt.Key_A:
            self.level_view.MOVE_LEFT = 0
        elif event.key() == Qt.Key_D:
            self.level_view.MOVE_RIGHT = 0
        elif event.key() == Qt.Key_Q:
            self.level_view.MOVE_UP = 0
        elif event.key() == Qt.Key_E:
            self.level_view.MOVE_DOWN = 0

    def action_rotate_object(self, deltarotation):
        #obj.set_rotation((None, round(angle, 6), None))
        for mtx in self.level_view.selected_positions:
            if deltarotation.y != 0:
                mtx.rotate_y(deltarotation.y)
        """for rot in self.level_view.selected_rotations:
            if deltarotation.x != 0:
                rot.rotate_around_y(deltarotation.x)
            elif deltarotation.y != 0:
                rot.rotate_around_z(deltarotation.y)
            elif deltarotation.z != 0:
                rot.rotate_around_x(deltarotation.z)"""

        #if self.rotation_mode.isChecked():
        if True:
            middle = self.level_view.gizmo.position

            for mtx in self.level_view.selected_positions:
                position = Vector3(mtx.x, mtx.y, mtx.z)
                diff = position - middle
                diff.y = 0.0

                length = diff.norm()
                if length > 0:
                    diff.normalize()
                    angle = atan2(diff.x, diff.z)
                    angle += deltarotation.y
                    position.x = middle.x + length * sin(angle)
                    position.z = middle.z + length * cos(angle)
                    mtx.mtx[12] = position.x
                    mtx.mtx[14] = position.z

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
        self.level_view.gizmo.move_to_average(self.level_view.selected,
                                              self.level_view.bwterrain,
                                              self.level_view.waterheight,
                                              self.dolphin.do_visualize())
        self.set_has_unsaved_changes(True)
        self.level_view.do_redraw()

    def action_delete_objects(self):
        tobedeleted = []

        self.level_file.delete_objects(self.level_view.selected)
        self.preload_file.delete_objects(self.level_view.selected)
        for obj in self.level_view.selected:
            obj.delete()

        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []

        self.pik_control.reset_info()
        self.leveldatatreeview.set_objects(self.level_file, self.preload_file)
        self.level_view.gizmo.hidden = True
        #self.pikmin_gen_view.update()
        self.level_view.do_redraw(force=True)
        self.set_has_unsaved_changes(True)

    @catch_exception
    def action_undo(self):
        if not self.dolphin.do_visualize():
            state = self.history.history_undo()
            if state is None:
                print("reached end of undo history")
            else:
                for obj, mtx, overridemtx in state:
                    currmtx = obj.getmatrix()
                    if currmtx is not None:
                        for i in range(16):
                            currmtx.mtx[i] = mtx[i]
                        obj.update_xml()
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
                for obj, mtx, overridemtx in state:
                    currmtx = obj.getmatrix()
                    if currmtx is not None:
                        for i in range(16):
                            currmtx.mtx[i] = mtx[i]
                        obj.update_xml()
                if len(state) > 0:
                    self.level_view.do_redraw(force=True)
                    self.set_has_unsaved_changes(True)
                    self.update_3d()

    def update_3d(self):
        self.level_view.gizmo.move_to_average(self.level_view.selected,
                                              self.level_view.bwterrain,
                                              self.level_view.waterheight,
                                              self.dolphin.do_visualize())
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

    @catch_exception
    def mapview_showcontextmenu(self, position):
        context_menu = QMenu(self)
        action = QAction("Copy Coordinates", self)
        action.triggered.connect(self.action_copy_coords_to_clipboard)
        context_menu.addAction(action)
        context_menu.exec(self.mapToGlobal(position))
        context_menu.destroy()

    def action_copy_coords_to_clipboard(self):
        if self.current_coordinates is not None:
            QApplication.clipboard().setText(", ".join(str(x) for x in self.current_coordinates))

    def action_update_position(self, event, pos):
        self.current_coordinates = pos
        self.statusbar.showMessage(str(pos))

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
        if self.top == len(self.history):
            return None

        item = self.history[self.top]
        self.top += 1
        return item


class EditorLevelPositionsHistory(EditorHistory):
    def __init__(self, historysize, editor):
        super().__init__(historysize)
        self.editor: LevelEditor = editor

    def stash_record(self, objects):
        record = []
        for obj in objects:
            bwmtx = obj.getmatrix()
            if bwmtx is not None:
                mtx = bwmtx.mtx.copy()
                if obj.mtxoverride is not None:
                    overridemtx = obj.mtxoverride.copy()
                else:
                    overridemtx = None

                record.append((obj, mtx, overridemtx))

        return record

    def stash_selected(self):
        return self.stash_record(self.editor.level_view.selected)

    def record_stash(self, stash):
        if len(stash) > 0 and not self.editor.dolphin.do_visualize():
            self.add(stash)

    def record(self, objects):
        record = self.stash_record(objects)
        if len(record) > 0 and not self.editor.dolphin.do_visualize():
            self.add(record)

    def record_selected(self):
        objects = self.editor.level_view.selected
        self.record(objects)


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


if __name__ == "__main__":
    #with cProfile.Profile() as pr:
    if True:
        pr = None
        #import sys
        import platform
        import argparse
        from PyQt5.QtCore import QLocale

        QLocale.setDefault(QLocale(QLocale.English))

        sys.excepthook = except_hook

        parser = argparse.ArgumentParser()
        """parser.add_argument("--inputgen", default=None,
                            help="Path to generator file to be loaded.")
        parser.add_argument("--collision", default=None,
                            help="Path to collision to be loaded.")
        parser.add_argument("--waterbox", default=None,
                            help="Path to waterbox file to be loaded.")"""

        parser.add_argument("filepath", default=None, help="Path to level to be loaded.", nargs="?")

        args = parser.parse_args()

        app = QApplication(sys.argv)

        if platform.system() == "Windows":
            import ctypes
            myappid = 'P2GeneratorsEditor'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        #with open("log.txt", "w") as f:
        if True:
            #sys.stdout = f
            #sys.stderr = f
            print("Python version: ", sys.version)
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