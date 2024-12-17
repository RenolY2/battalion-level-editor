import subprocess
import os
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
import bw_widgets
from widgets.menu.menu import Menu
from widgets.menu.plugin import PluginMenu
from widgets.filter_view import FilterViewMenu
from widgets.search_widget import SearchWidget
from widgets.editor_widgets import open_error_dialog
from typing import TYPE_CHECKING
from lib.game_visualizer import DebugInfoWIndow
from widgets.editor_widgets import open_message_dialog, open_yesno_box
from configuration import save_cfg
from widgets.lua_search_widgets import LuaFindWindow

if TYPE_CHECKING:
    import bw_editor


class EditorMenuBar(QtWidgets.QMenuBar):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor

        self.search_window = None
        self.debug_window = None
        self.lua_find_menu = None

        self.visibility_menu = FilterViewMenu(self)
        self.visibility_menu.filter_update.connect(self.editor.update_render)

        # ------ Collision Menu
        #self.collision_menu = Menu(self, "Geometry")
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
        self.search = self.misc_menu.add_action("Find Objects", self.open_search, "Ctrl+F")


        self.change_to_topdownview_action = self.misc_menu.add_action("Topdown View",
                                                                     self.editor.change_to_topdownview,
                                                                     "Ctrl+1")
        self.change_to_topdownview_action.setCheckable(True)
        self.change_to_topdownview_action.setChecked(True)

        self.change_to_3dview_action = self.misc_menu.add_action("3D View",
                                                                     self.editor.change_to_3dview,
                                                                     "Ctrl+2")
        self.change_to_3dview_action = QtGui.QAction("3D View", self)
        self.change_to_3dview_action.setCheckable(True)

        #self.choose_bco_area = QtWidgets.QAction("Highlight Collision Area (BCO)")

        self.dolphin_menu = Menu(self, "Dolphin (Experimental)")
        self.start_game_action = self.dolphin_menu.add_action("Start Game in Dolphin",
                                                              self.run_game)
        self.show_debug_info_action = self.dolphin_menu.add_action("Show Freelist Info",
                                                                   self.open_debug_window)
        self.hook_game_action = self.dolphin_menu.add_action("Enable Live Edit",
                                                            self.hook_game)
        self.hook_game_action.setToolTip("If enabled, edits positions/rotations of selected objects ingame.\nWarning: Some objects don't move ingame.")
        self.hook_game_action.setCheckable(True)
        self.hook_game_view_action = self.dolphin_menu.add_action("Enable Live View",
                                                            self.hook_game_visualize)
        self.hook_game_view_action.setToolTip(
            "If enabled, visualizes ingame positions in the game.\nObjects can be moved but the updated positions won't be saved in the xml. Some object don't move ingame.\nUse \"Apply Positions to Selected\" to apply live positions of selected objects to the xml data." )
        self.hook_game_view_action.setCheckable(True)

        self.apply_live_positions_action = self.dolphin_menu.add_action("Apply Live Positions to Selected",
                                                                self.apply_live_positions)

        self.lua_menu = Menu(self, "Lua")
        self.lua_open_find_action = self.lua_menu.add_action("Open Lua Script Search",
                                                             self.lua_open_find)
        self.lua_open_entity_init_action = self.lua_menu.add_action("Open EntityInitialise",
                                                                    self.lua_open_entity_initialise)
        self.lua_open_workdir_action = self.lua_menu.add_action("Open Lua Script Folder",
                                                                    self.lua_open_workdir)
        self.lua_menu.addSeparator()
        self.lua_reload_scripts_action = self.lua_menu.add_action("Reload Scripts from Resource",
                                                                    self.lua_reload_scripts)
        self.addAction(self.editor.file_menu.menuAction())
        self.addAction(self.visibility_menu.menuAction())
        #self.addAction(self.collision_menu.menuAction())
        self.addAction(self.misc_menu.menuAction())
        self.addAction(self.dolphin_menu.menuAction())
        self.addAction(self.lua_menu.menuAction())

        self.plugin_menu = PluginMenu(self)
        self.plugin_menu.load_plugins()
        self.plugin_menu.add_menu_actions()
        self.addAction(self.plugin_menu.menuAction())


        self.last_obj_select_pos = 0

    def lua_open_find(self):
        self.lua_find_menu = LuaFindWindow(None, self.editor.lua_workbench)
        self.lua_find_menu.show()

    def run_game(self):
        dolphin_path = self.editor.configuration["editor"].get("dolphin", fallback=None)
        if dolphin_path is None:
            open_message_dialog("Dolphin not found, please choose location of Dolphin's executable.")
            filepath, chosentype = QtWidgets.QFileDialog.getOpenFileName(
                self, "Choose Dolphin",
                "",
                "Dolphin executable (Dolphin.exe);;All files (*)",
                None)

            if filepath:
                self.editor.configuration["editor"]["dolphin"] = filepath
                save_cfg(self.editor.configuration)
                dolphin_path = filepath

        if dolphin_path is not None:
            data_folder = os.path.dirname(os.path.dirname(self.editor.file_menu.current_path))
            game_base_folder = os.path.dirname(os.path.dirname(data_folder))
            game_executable = os.path.join(game_base_folder, "sys", "main.dol")
            print(data_folder)
            print(game_base_folder)
            print(dolphin_path)
            print(game_executable)
            try:
                subprocess.Popen([dolphin_path, game_executable])
            except FileNotFoundError:
                if open_yesno_box("Dolphin not found.\nDo you want to choose a new location for Dolphin?"):
                    filepath, chosentype = QtWidgets.QFileDialog.getOpenFileName(
                        self, "Choose Dolphin",
                        "",
                        "Dolphin executable (Dolphin.exe);;All files (*)",
                        None)
                    if filepath:
                        self.editor.configuration["editor"]["dolphin"] = filepath
                        save_cfg(self.editor.configuration)
                        open_message_dialog("New Dolphin location chosen. Use 'Start Game in Dolphin' again.")
        else:
            open_error_dialog("No Dolphin path chosen, can't start Dolphin.")

    def lua_reload_scripts(self):
        msgbox = QtWidgets.QMessageBox()
        msgbox.setText("Reloading the scripts from the level's resource file will overwrite your current scripts!")
        msgbox.setInformativeText("Do you want to overwrite your current scripts?")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        msgbox.setWindowTitle("Warning")
        result = msgbox.exec()

        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            basepath = os.path.dirname(self.editor.current_gen_path)
            resname = self.editor.file_menu.level_paths.resourcepath
            self.editor.statusbar.showMessage("Reloading scripts...")

            print("reloading scripts from", os.path.join(basepath, resname))
            try:
                self.editor.lua_workbench.unpack_scripts(os.path.join(basepath, resname))
            except Exception as err:
                open_error_dialog(str(err), None)
            self.editor.statusbar.showMessage("Finished reloading scripts!")
            print("finished reloading")

    def lua_open_entity_initialise(self):
        self.editor.lua_workbench.open_script("EntityInitialise")

    def lua_open_workdir(self):
        print("Opening", self.editor.lua_workbench.workdir)
        os.startfile(self.editor.lua_workbench.workdir)

    def close_debug_window(self):
        self.debug_window = None

    def open_debug_window(self):
        if self.debug_window is None:
            self.debug_window = DebugInfoWIndow()
            self.debug_window.closing.connect(self.close_debug_window)
            self.debug_window.show()

    def apply_live_positions(self):
        if self.editor.dolphin.do_visualize():
            for obj in self.editor.level_view.selected:
                if obj.mtxoverride is not None and obj.getmatrix() is not None:
                    if hasattr(obj, "mStickToFloor"):
                        obj.mStickToFloor = False
                    if hasattr(obj, "mLockToSurface"):
                        obj.mLockToSurface = False

                    mtx = obj.getmatrix().mtx
                    for i in range(16):
                        mtx[i] = obj.mtxoverride[i]
                    obj.update_xml()

    def reset_hook(self):
        self.hook_game_action.setChecked(False)
        self.hook_game_view_action.setChecked(False)
        self.apply_live_positions_action.setEnabled(False)
        self.editor.dolphin.initialize(shutdown=True)
        self.editor.level_view.indicator.reset()
        self.editor.level_view.do_redraw(force=True)

    def reset_hook_with_error_message(self):
        self.reset_hook()
        open_error_dialog("Level was changed or the game has been closed. Dolphin hook has been shut down.", None)

    def hook_game(self):
        self.editor.level_view.selected = []
        self.editor.level_view.selected_positions = []
        self.editor.update_3d()
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
                self.editor.level_view.indicator.set_live_edit()
            else:
                open_error_dialog(failure, None)
                self.hook_game_action.setChecked(False)
                self.hook_game_view_action.setChecked(False)
                self.apply_live_positions_action.setEnabled(False)
                self.editor.level_view.indicator.reset()

            self.editor.level_view.do_redraw(force=True)
        else:
            self.editor.dolphin.initialize(shutdown=True)
            #for objid, obj in self.editor.level_file.objects_with_positions.items():
            self.hook_game_action.setChecked(False)
            self.hook_game_view_action.setChecked(False)
            self.apply_live_positions_action.setEnabled(False)
            self.editor.level_view.indicator.reset()
            for objid, obj in self.editor.level_file.objects_with_positions.items():
                obj.set_mtx_override(None)
            self.editor.level_view.do_redraw(force=True)
        self.editor.update_3d()

    def hook_game_visualize(self):
        self.editor.level_view.selected = []
        self.editor.level_view.selected_positions = []
        self.editor.update_3d()
        if not self.editor.dolphin.running or not self.editor.dolphin.visualize:
            failure = self.editor.dolphin.initialize(self.editor.level_file,
                                                     shutdowncallback=self.reset_hook_with_error_message)
            if not failure:
                self.editor.dolphin.visualize = True
                self.hook_game_action.setChecked(False)
                self.hook_game_view_action.setChecked(True)
                self.apply_live_positions_action.setEnabled(True)
                self.editor.level_view.indicator.set_live_view()
            else:
                open_error_dialog(failure, None)
                self.hook_game_action.setChecked(False)
                self.hook_game_view_action.setChecked(False)
                self.apply_live_positions_action.setEnabled(False)
                self.editor.level_view.indicator.reset()

            self.editor.level_view.do_redraw(force=True)
        else:
            self.editor.dolphin.initialize(shutdown=True)
            # for objid, obj in self.editor.level_file.objects_with_positions.items():

            self.hook_game_action.setChecked(False)
            self.hook_game_view_action.setChecked(False)
            self.apply_live_positions_action.setEnabled(False)
            self.editor.level_view.indicator.reset()
            for objid, obj in self.editor.level_file.objects_with_positions.items():
                obj.set_mtx_override(None)
            self.editor.level_view.do_redraw(force=True)
        self.editor.update_3d()

    def close_search(self):
        self.search_window = None

    def open_search(self):
        if self.search_window is not None:
            window = self.search_window
            window.setWindowState(window.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
            window.activateWindow()
        else:
            self.search_window = SearchWidget(self.editor)
            self.search_window.closing.connect(self.close_search)
        self.search_window.show()
        self.search_window.setFocus()

