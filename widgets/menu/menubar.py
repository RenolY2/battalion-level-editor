import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
import bw_widgets
from widgets.menu.menu import Menu
from widgets.filter_view import FilterViewMenu
from widgets.search_widget import SearchWidget
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

        self.addAction(self.editor.file_menu.menuAction())
        self.addAction(self.visibility_menu.menuAction())
        self.addAction(self.collision_menu.menuAction())
        self.addAction(self.misc_menu.menuAction())
        self.addAction(self.dolphin_menu.menuAction())

        self.last_obj_select_pos = 0
    
    def hook_game(self):
        self.editor.dolphin.initialize()
    
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

