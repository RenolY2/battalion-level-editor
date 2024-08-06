import PyQt5.QtWidgets as QtWidgets

import bw_widgets

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class EditorMenuBar(QtWidgets.QMenuBar):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor

        self.visibility_menu = bw_widgets.FilterViewMenu(self)
        self.visibility_menu.filter_update.connect(self.editor.update_render)

        # ------ Collision Menu
        self.collision_menu = QtWidgets.QMenu(self)
        self.collision_menu.setTitle("Geometry")
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
        self.misc_menu = QtWidgets.QMenu(self)
        self.misc_menu.setTitle("Misc")
        # self.spawnpoint_action = QAction("Set startPos/Dir", self)
        # self.spawnpoint_action.triggered.connect(self.action_open_rotationedit_window)
        # self.misc_menu.addAction(self.spawnpoint_action)
        self.rotation_mode = QtWidgets.QAction("Rotate Positions around Pivot", self)
        self.rotation_mode.setCheckable(True)
        self.rotation_mode.setChecked(True)
        # self.goto_action.triggered.connect(self.do_goto_action)
        # self.goto_action.setShortcut("Ctrl+G")
        self.misc_menu.addAction(self.rotation_mode)
        self.analyze_action = QtWidgets.QAction("Analyze for common mistakes", self)
        self.analyze_action.triggered.connect(self.editor.analyze_for_mistakes)
        self.misc_menu.addAction(self.analyze_action)

        self.change_to_topdownview_action = QtWidgets.QAction("Topdown View", self)
        self.change_to_topdownview_action.triggered.connect(self.editor.change_to_topdownview)
        self.misc_menu.addAction(self.change_to_topdownview_action)
        self.change_to_topdownview_action.setCheckable(True)
        self.change_to_topdownview_action.setChecked(True)
        self.change_to_topdownview_action.setShortcut("Ctrl+1")

        self.change_to_3dview_action = QtWidgets.QAction("3D View", self)
        self.change_to_3dview_action.triggered.connect(self.editor.change_to_3dview)
        self.misc_menu.addAction(self.change_to_3dview_action)
        self.change_to_3dview_action.setCheckable(True)
        self.change_to_3dview_action.setShortcut("Ctrl+2")

        self.choose_bco_area = QtWidgets.QAction("Highlight Collision Area (BCO)")

        self.addAction(self.editor.file_menu.menuAction())
        self.addAction(self.visibility_menu.menuAction())
        self.addAction(self.collision_menu.menuAction())
        self.addAction(self.misc_menu.menuAction())


        self.last_obj_select_pos = 0