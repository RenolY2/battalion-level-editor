import os
import sys
import traceback
from functools import partial
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
from PyQt6.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter, QApplication, QMdiSubWindow, QVBoxLayout,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QStatusBar, QLineEdit)
from PyQt6.QtGui import QAction, QShortcut
#from bw_editor import LevelEditor
from widgets.editor_widgets import catch_exception_with_dialog, open_error_dialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import traceback
from lib.BattalionXMLLib import BattalionLevelFile, BattalionFilePaths
import gzip
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect, QObject
from io import BytesIO

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class LoadingProgress(QObject):
    progressupdate = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.curr = 0

    def callback(self, scale, max, i):
        self.progressupdate.emit(int(self.curr + (i/max)*scale))
        QApplication.processEvents()

    def set(self, progress):
        self.curr = progress
        self.progressupdate.emit(int(self.curr))


class EditorFileMenu(QMenu):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.setTitle("File")

        self.last_chosen_type = None
        self.level_paths = None

        save_file_shortcut = QShortcut(Qt.Key.Key_Control + Qt.Key.Key_S, self)
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
        #self.addAction(self.save_file_as_action)
        #self.addAction(self.save_file_copy_as_action)
        self.is_loading = False

    def updatestatus(self, progress):
        self.editor.statusbar.showMessage("Loading: {0}%".format(progress))

    def loadingcallback(self, base, max, progress):
        print(progress)
        QApplication.processEvents()

    def button_load_level(self, fpathoverride=None):
        if fpathoverride:
            filepath = fpathoverride
            chosentype = ""
        else:
            filepath, chosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.editor.pathsconfig["xml"],
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
                    self.is_loading = True
                    levelpaths = BattalionFilePaths(f)
                    base = os.path.dirname(filepath)
                    print(base, levelpaths.objectpath)
                    progressbar = LoadingProgress()
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    progressbar.progressupdate.connect(self.updatestatus)
                    if levelpaths.objectpath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.objectpath), "rb") as g:
                            level_data = BattalionLevelFile(g, partial(progressbar.callback, 10))
                    else:
                        with open(os.path.join(base, levelpaths.objectpath), "rb") as g:
                            level_data = BattalionLevelFile(g, partial(progressbar.callback, 10))

                    progressbar.set(10)
                    if levelpaths.preloadpath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.preloadpath), "rb") as g:
                            preload_data = BattalionLevelFile(g, partial(progressbar.callback, 10))
                    else:
                        with open(os.path.join(base, levelpaths.preloadpath), "rb") as g:
                            preload_data = BattalionLevelFile(g, partial(progressbar.callback, 10))

                    progressbar.set(20)
                    level_data.resolve_pointers(preload_data)
                    preload_data.resolve_pointers(level_data)

                    for id, obj in preload_data.objects.items():
                        if obj.type == "cLevelSettings":
                            self.editor.level_view.waterheight = obj.mpRenderParams.mWaterHeight
                    progressbar.set(30)

                    if levelpaths.resourcepath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.resourcepath), "rb") as g:
                            self.editor.level_view.reloadModels(g, partial(progressbar.callback, 30))
                    else:
                        with open(os.path.join(base, levelpaths.resourcepath), "rb") as g:
                            self.editor.level_view.reloadModels(g, partial(progressbar.callback, 30))
                    progressbar.set(60)

                    if levelpaths.terrainpath.endswith(".gz"):
                        with gzip.open(os.path.join(base, levelpaths.terrainpath), "rb") as g:
                            self.editor.level_view.reloadTerrain(g, partial(progressbar.callback, 30))
                    else:
                        with open(os.path.join(base, levelpaths.terrainpath), "rb") as g:
                            self.editor.level_view.reloadTerrain(g, partial(progressbar.callback, 30))
                    progressbar.set(100)

                    self.level_paths = levelpaths
                    self.level_data = level_data
                    self.preload_data = preload_data
                    self.editor.setup_level_file(level_data, preload_data, filepath)
                    self.current_gen_path = filepath

                    # In testing the cursor didn't want to change back unless you moved the cursor
                    # off the window and back so we'll do this
                    self.is_loading = False
                    QApplication.restoreOverrideCursor()
                    QApplication.processEvents()
                    QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
                    QApplication.processEvents()
                    QApplication.restoreOverrideCursor()
                    QApplication.processEvents()

                    self.editor.pathsconfig["xml"] = filepath
                    self.editor.setCursor(QtGui.QCursor(Qt.CursorShape.ArrowCursor))
                    cursor = QtGui.QCursor()
                    cursor.setShape(Qt.CursorShape.ArrowCursor)
                    pos = cursor.pos()
                    """widgets = []
                    widget_at = QApplication.widgetAt(pos)

                    while widget_at:
                        widgets.append(widget_at)

                        # Make widget invisible to further enquiries
                        widget_at.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
                        widget_at = QApplication.widgetAt(pos)

                    # Restore attribute
                    for widget in widgets:
                        widget.setCursor(cursor)
                        widget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)"""

                    QApplication.processEvents()
                except Exception as error:
                    self.is_loading = False
                    print("Error appeared while loading:", error)
                    traceback.print_exc()
                    open_error_dialog(str(error), self)
                    return

    @catch_exception_with_dialog
    def button_save_level(self, *args, **kwargs):
        if self.level_paths is not None:
            levelpaths = self.level_paths
            progressbar = LoadingProgress()
            progressbar.progressupdate.connect(self.updatestatus)

            base = os.path.dirname(self.current_gen_path)
            progressbar.set(0)

            for id, window in self.editor.pik_control.edit_windows.items():
                try:
                    self.editor.pik_control.save_object_data(id, mass_save=True)
                except Exception as err:
                    self.editor.pik_control.activate_window(id)
                    open_error_dialog("Error while saving object {0}: \n{1}\nFix the error or close the object's edit window, then try saving again.".format(id, str(err)), None)
                    self.editor.level_view.do_redraw(force=True)
                    self.editor.leveldatatreeview.updatenames()
                    return

            self.editor.level_view.do_redraw(force=True)
            self.editor.leveldatatreeview.updatenames()
            progressbar.set(5)
            for object in self.level_data.objects.values():
                object.update_xml()

            progressbar.set(20)

            for object in self.preload_data.objects.values():
                object.update_xml()
            progressbar.set(30)

            tmp = BytesIO()
            print("Writing level data to temp file...")
            self.level_data.write(tmp)
            progressbar.set(70)
            tmp2 = BytesIO()

            print("Writing preload data to temp file...")
            self.preload_data.write(tmp2)

            if levelpaths.objectpath.endswith(".gz"):
                with gzip.open(os.path.join(base, levelpaths.objectpath), "wb") as g:
                    g.write(tmp.getvalue())
                    if self.level_paths.objectfilepadding is not None:
                        if g.tell() < self.level_paths.objectfilepadding:
                            g.write(b"\x00"*(self.level_paths.objectfilepadding - g.tell()))
            else:
                with open(os.path.join(base, levelpaths.objectpath), "wb") as g:
                    g.write(tmp.getvalue())
                    if self.level_paths.objectfilepadding is not None:
                        if g.tell() < self.level_paths.objectfilepadding:
                            g.write(b" "*(self.level_paths.objectfilepadding - g.tell()))

            progressbar.set(90)

            if levelpaths.preloadpath.endswith(".gz"):
                with gzip.open(os.path.join(base, levelpaths.preloadpath), "wb") as g:
                    g.write(tmp2.getvalue())
                    if self.level_paths.preloadpadding is not None:
                        if g.tell() < self.level_paths.preloadpadding:
                            g.write(b"\x00"*(self.level_paths.preloadpadding - g.tell()))
            else:
                with open(os.path.join(base, levelpaths.preloadpath), "wb") as g:
                    g.write(tmp2.getvalue())
                    if self.level_paths.preloadpadding is not None:
                        if g.tell() < self.level_paths.preloadpadding:
                            g.write(b" "*(self.level_paths.preloadpadding - g.tell()))

            print("Done!")
            progressbar.set(100)
            self.editor.set_has_unsaved_changes(False)
        #else:
        #    self.button_save_level_as()

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
