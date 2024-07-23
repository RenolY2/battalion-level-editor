import os
from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QShortcut, QStatusBar, QLineEdit)
#from bw_editor import LevelEditor
from widgets.editor_widgets import catch_exception_with_dialog, open_error_dialog
from PyQt5.QtCore import Qt
import traceback
from lib.BattalionXMLLib import BattalionLevelFile, BattalionFilePaths
import gzip
from io import BytesIO

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor

class EditorFileMenu(QMenu):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.setTitle("File")

        self.last_chosen_type = None

        save_file_shortcut = QShortcut(Qt.CTRL + Qt.Key_S, self)
        save_file_shortcut.activated.connect(self.button_save_level)

        self.file_load_action = QAction("Load", self)
        self.save_file_action = QAction("Save", self)
        self.save_file_as_action = QAction("Save As", self)
        self.save_file_action.setShortcut("Ctrl+S")
        self.file_load_action.setShortcut("Ctrl+O")
        self.save_file_as_action.setShortcut("Ctrl+Alt+S")

        self.save_file_copy_as_action = QAction("Save Copy As", self)

        self.file_load_action.triggered.connect(self.button_load_level)
        self.save_file_action.triggered.connect(self.button_save_level)
        self.save_file_as_action.triggered.connect(self.button_save_level_as)
        self.save_file_copy_as_action.triggered.connect(self.button_save_level_copy_as)

        self.addAction(self.file_load_action)
        self.addAction(self.save_file_action)
        self.addAction(self.save_file_as_action)
        self.addAction(self.save_file_copy_as_action)


    def button_load_level(self, fpathoverride=None):
        if fpathoverride:
            filepath = fpathoverride
            chosentype = ""
        else:
            filepath, chosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.editor.pathsconfig["bol"],
                "XML files (*.xml; *.xml.gz);;All files (*)",
                self.last_chosen_type)

        if filepath:
            self.last_chosen_type = chosentype
            print("Resetting editor")
            self.editor.reset()
            print("Reset done")
            print("Chosen file type:", chosentype)
            if filepath.lower().endswith(".gz"):
                func_open = gzip.open
            else:
                func_open = open

            with func_open(filepath, "rb") as f:
                try:
                    #self.loaded_archive = Archive.from_file(f)
                    #root_name = self.loaded_archive.root.name
                    #coursename = find_file(self.loaded_archive.root, "_course.bol")
                    #bol_file = self.loaded_archive[root_name + "/" + coursename]
                    #bol_data = BOL.from_file(bol_file)
                    #self.setup_bol_file(bol_data, filepath)
                    #self.leveldatatreeview.set_objects(bol_data)
                    levelpaths = BattalionFilePaths(f)
                    base = os.path.dirname(filepath)
                    print(base, levelpaths.objectpath)
                    if levelpaths.objectpath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.objectpath), "rb") as g:
                            level_data = BattalionLevelFile(g)
                    else:
                        with open(os.path.join(base, levelpaths.objectpath), "rb") as g:
                            level_data = BattalionLevelFile(g)

                    if levelpaths.preloadpath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.preloadpath), "rb") as g:
                            preload_data = BattalionLevelFile(g)
                    else:
                        with open(os.path.join(base, levelpaths.preloadpath), "rb") as g:
                            preload_data = BattalionLevelFile(g)

                    level_data.resolve_pointers(preload_data)
                    preload_data.resolve_pointers(level_data)
                    for id, obj in preload_data.objects.items():
                        if obj.type == "cLevelSettings":
                            self.editor.level_view.waterheight = obj.mpRenderParams.mWaterHeight
                    
                    if levelpaths.resourcepath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.resourcepath), "rb") as g:
                            self.editor.level_view.reloadModels(g)
                    else:
                        with open(os.path.join(base, levelpaths.resourcepath), "rb") as g:
                            self.editor.level_view.reloadModels(g)
                            
                    if levelpaths.terrainpath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.terrainpath), "rb") as g:
                            self.editor.level_view.reloadTerrain(g)
                    else:
                        with open(os.path.join(base, levelpaths.terrainpath), "rb") as g:
                            self.editor.level_view.reloadTerrain(g)

                    self.editor.setup_level_file(level_data, filepath)
                    self.current_gen_path = filepath
                except Exception as error:
                    print("Error appeared while loading:", error)
                    traceback.print_exc()
                    open_error_dialog(str(error), self)
                    return

    @catch_exception_with_dialog
    def button_save_level(self, *args, **kwargs):
        if self.current_gen_path is not None:
            if self.loaded_archive is not None:
                assert self.loaded_archive_file is not None
                root_name = self.loaded_archive.root.name
                file = self.loaded_archive[root_name + "/" + self.loaded_archive_file]
                file.seek(0)

                self.level_file.write(file)

                with open(self.current_gen_path, "wb") as f:
                    self.loaded_archive.write_arc(f)

                self.set_has_unsaved_changes(False)
                self.statusbar.showMessage("Saved to {0}".format(self.current_gen_path))

            else:
                with open(self.current_gen_path, "wb") as f:
                    self.level_file.write(f)
                    self.set_has_unsaved_changes(False)

                    self.statusbar.showMessage("Saved to {0}".format(self.current_gen_path))
        else:
            self.button_save_level_as()

    def button_save_level_as(self, *args, **kwargs):
        self._button_save_level_as(True, *args, **kwargs)

    def button_save_level_copy_as(self, *args, **kwargs):
        self._button_save_level_as(False, *args, **kwargs)

    @catch_exception_with_dialog
    def _button_save_level_as(self, modify_current_path, *args, **kwargs):
        filepath, choosentype = QFileDialog.getSaveFileName(
            self, "Save File",
            self.pathsconfig["bol"],
            "MKDD Track Data (*.bol);;Archived files (*.arc);;All files (*)",
            self.last_chosen_type)

        if filepath:
            if choosentype == "Archived files (*.arc)" or filepath.endswith(".arc"):
                if self.loaded_archive is None or self.loaded_archive_file is None:
                    with open(filepath, "rb") as f:
                        self.loaded_archive = Archive.from_file(f)

                self.loaded_archive_file = find_file(self.loaded_archive.root, "_course.bol")
                root_name = self.loaded_archive.root.name
                file = self.loaded_archive[root_name + "/" + self.loaded_archive_file]
                file.seek(0)

                self.level_file.write(file)

                with open(filepath, "wb") as f:
                    self.loaded_archive.write_arc(f)

                self.set_has_unsaved_changes(False)
                self.statusbar.showMessage("Saved to {0}".format(filepath))
            else:
                with open(filepath, "wb") as f:
                    self.level_file.write(f)

                    self.set_has_unsaved_changes(False)

            self.pathsconfig["bol"] = filepath
            save_cfg(self.configuration)

            if modify_current_path:
                self.current_gen_path = filepath
                self.set_base_window_title(filepath)

            self.statusbar.showMessage("Saved to {0}".format(filepath))
