import PyQt5.QtWidgets as QtWidgets

import bw_widgets
from widgets.filter_view import FilterViewMenu

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class Menu(QtWidgets.QMenu):
    def __init__(self, parent, name):
        super().__init__(parent)
        self.setTitle(name)
        self.actions = []

    def add_action(self, name, func=None, shortcut=None):
        action = QtWidgets.QAction(name, self)
        if func is not None:
            action.triggered.connect(func)
        if shortcut is not None:
            action.setShortcut(shortcut)

        self.actions.append(action)
        return action


class EditorMenuBar(QtWidgets.QMenuBar):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor

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
        self.rotation_mode = self.misc_menu.addAction("Rotate Positions around Pivot")
        self.rotation_mode.setCheckable(True)
        self.rotation_mode.setChecked(True)


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

        self.addAction(self.editor.file_menu.menuAction())
        self.addAction(self.visibility_menu.menuAction())
        self.addAction(self.collision_menu.menuAction())
        self.addAction(self.misc_menu.menuAction())


        self.last_obj_select_pos = 0