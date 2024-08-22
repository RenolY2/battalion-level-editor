import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
import bw_widgets
from widgets.menu.menu import Menu
from widgets.filter_view import FilterViewMenu
from widgets.search_widget import SearchWidget
from widgets.editor_widgets import open_error_dialog
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class EditorMenuBar(QtWidgets.QMenuBar):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor

        self.search_window = None

        self.visibility_menu = FilterViewMenu(self)
        self.visibility_menu.filter_update.connect(self.editor.update_render)

        # ------ Collision Menu
        self.collision_menu = Menu(self, "Geometry")
        """self.collision_load_action = QtWidgets.QAction("Load OBJ", self)
        self.collision_load_action.triggered.connect(self.editor.button_load_collision)
        self.collision_menu.addAction(self.collision_load_action)
        self.collision_load_grid_action = QtWidgets.QAction("Load BCO", self)
        self.collision_load_grid_action.triggered.connect(self.editor.button_load_collision_bco)
        self.collision_menu.addAction(self.collision_load_grid_action)
        self.collision_load_bmd_action = QtWidgets.QAction("Load BMD", self)
        self.collision_load_bmd_action.triggered.connect(self.editor.button_load_collision_bmd)
        self.collision_menu.addAction(self.collision_load_bmd_action)"""

        # Misc
        self.misc_menu = Menu(self, "Misc")
        #self.rotation_mode = self.misc_menu.addAction("Rotate Positions around Pivot")
        #self.rotation_mode.setCheckable(True)
        #self.rotation_mode.setChecked(True)
        self.search = self.misc_menu.addAction("Find Objects", self.open_search, "Ctrl+F")


        self.change_to_topdownview_action = self.misc_menu.addAction("Topdown View",
                                                                     self.editor.change_to_topdownview,
                                                                     "Ctrl+1")
        self.change_to_topdownview_action.setCheckable(True)
        self.change_to_topdownview_action.setChecked(True)

        self.change_to_3dview_action = self.misc_menu.addAction("3D View",
                                                                     self.editor.change_to_3dview,
                                                                     "Ctrl+2")
        self.change_to_3dview_action = QtWidgets.QAction("3D View", self)
        self.change_to_3dview_action.setCheckable(True)

        #self.choose_bco_area = QtWidgets.QAction("Highlight Collision Area (BCO)")

        self.dolphin_menu = Menu(self, "Dolphin (Experimental)")
        self.hook_game_action = self.dolphin_menu.addAction("Enable Live Edit",
                                                            self.hook_game)
        self.hook_game_action.setCheckable(True)
        self.hook_game_view_action = self.dolphin_menu.addAction("Enable Live View",
                                                            self.hook_game_visualize)
        self.hook_game_view_action.setCheckable(True)

        self.apply_live_positions_action = self.dolphin_menu.addAction("Apply Live Positions to Selected",
                                                                self.apply_live_positions)


        self.addAction(self.editor.file_menu.menuAction())
        self.addAction(self.visibility_menu.menuAction())
        self.addAction(self.collision_menu.menuAction())
        self.addAction(self.misc_menu.menuAction())
        self.addAction(self.dolphin_menu.menuAction())

        self.last_obj_select_pos = 0

    def apply_live_positions(self):
        if self.editor.dolphin.do_visualize():
            for obj in self.editor.level_view.selected:
                if obj.mtxoverride is not None and obj.getmatrix() is not None:
                    mtx = obj.getmatrix().mtx
                    for i in range(16):
                        mtx[i] = obj.mtxoverride[i]

    def reset_hook(self):
        self.hook_game_action.setChecked(False)
        self.hook_game_view_action.setChecked(False)
        self.apply_live_positions_action.setEnabled(False)
        self.editor.dolphin.initialize(shutdown=True)


    def reset_hook_with_error_message(self):
        self.reset_hook()
        open_error_dialog("Level or game change detected! Dolphin hook has been shut down.", None)

    def hook_game(self):
        if not self.editor.dolphin.running or self.editor.dolphin.visualize:
            self.editor.dolphin.running = False
            for objid, obj in self.editor.level_file.objects_with_positions.items():
                obj.set_mtx_override(None)
            failure = self.editor.dolphin.initialize(self.editor.level_file,
                                                     shutdowncallback=self.reset_hook_with_error_message)
            if not failure:
                self.editor.dolphin.visualize = False
                self.hook_game_action.setChecked(True)
                self.hook_game_view_action.setChecked(False)
                self.apply_live_positions_action.setEnabled(False)
            else:
                open_error_dialog(failure, None)
                self.hook_game_action.setChecked(False)
                self.hook_game_view_action.setChecked(False)
                self.apply_live_positions_action.setEnabled(False)

            self.editor.level_view.do_redraw(force=True)
        else:
            self.editor.dolphin.initialize(shutdown=True)
            #for objid, obj in self.editor.level_file.objects_with_positions.items():
            self.hook_game_action.setChecked(False)
            self.hook_game_view_action.setChecked(False)
            self.apply_live_positions_action.setEnabled(False)
            for objid, obj in self.editor.level_file.objects_with_positions.items():
                obj.set_mtx_override(None)
            self.editor.level_view.do_redraw(force=True)

    def hook_game_visualize(self):
        if not self.editor.dolphin.running or not self.editor.dolphin.visualize:
            failure = self.editor.dolphin.initialize(self.editor.level_file,
                                                     shutdowncallback=self.reset_hook_with_error_message)
            if not failure:
                self.editor.dolphin.visualize = True
                self.hook_game_action.setChecked(False)
                self.hook_game_view_action.setChecked(True)
                self.apply_live_positions_action.setEnabled(True)
            else:
                open_error_dialog(failure, None)
                self.hook_game_action.setChecked(False)
                self.hook_game_view_action.setChecked(False)
                self.apply_live_positions_action.setEnabled(False)
            self.editor.level_view.do_redraw(force=True)
        else:
            self.editor.dolphin.initialize(shutdown=True)
            # for objid, obj in self.editor.level_file.objects_with_positions.items():

            self.hook_game_action.setChecked(False)
            self.hook_game_view_action.setChecked(False)
            self.apply_live_positions_action.setEnabled(False)
            for objid, obj in self.editor.level_file.objects_with_positions.items():
                obj.set_mtx_override(None)
            self.editor.level_view.do_redraw(force=True)
    
    def close_search(self):
        self.search_window = None

    def open_search(self):
        if self.search_window is not None:
            window = self.search_window
            window.setWindowState(window.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            window.activateWindow()
        else:
            self.search_window = SearchWidget(self.editor)
            self.search_window.closing.connect(self.close_search)
        self.search_window.show()

