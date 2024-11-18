import os
import struct
import numpy
import shutil
from PIL import Image, ImageDraw, ImageOps
import sys
import traceback
from functools import partial
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from PyQt6.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter, QApplication, QMdiSubWindow, QVBoxLayout,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QStatusBar, QLineEdit)
from PyQt6.QtGui import QAction, QShortcut
#from bw_editor import LevelEditor
from widgets.editor_widgets import catch_exception_with_dialog, open_error_dialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import traceback
from lib.BattalionXMLLib import BattalionLevelFile, BattalionFilePaths, BattalionObject
import gzip
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect, QObject
from io import BytesIO
from lib.lua.luaworkshop import LuaWorkbench

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor
    from lib.bw_terrain import BWTerrainV2


class LoadingProgress(QObject):
    progressupdate = pyqtSignal(str, int)

    def __init__(self, text):
        super().__init__()
        self.curr = 0
        self.text = text

    def callback(self, scale, max, i):
        self.progressupdate.emit(self.text, int(self.curr + (i/max)*scale))
        QApplication.processEvents()

    def set(self, progress):
        self.curr = progress
        self.progressupdate.emit(self.text, int(self.curr))


class EditorFileMenu(QMenu):
    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.setTitle("File")

        self.last_chosen_type = None
        self.level_paths = None
        self.current_path = None

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

    def updatestatus(self, text, progress):
        self.editor.statusbar.showMessage("{1}: {0}%".format(progress, text))

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
                "XML files (*.xml);;All files (*)",
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

            self.editor.menubar.plugin_menu.execute_event("before_load")

            with func_open(filepath, "rb") as f:
                try:
                    self.editor.level_view.stop_redrawing()
                    self.is_loading = True
                    levelpaths = BattalionFilePaths(f)
                    if levelpaths.objectpath is None:
                        raise RuntimeError("Wrong XML loaded!\nMake sure you are loading the level's main XML file without Level or Preload in the name.")


                    base = os.path.dirname(filepath)
                    print(base, levelpaths.objectpath)
                    progressbar = LoadingProgress("Loading")
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

                    del self.editor.lua_workbench
                    self.editor.lua_workbench = LuaWorkbench(filepath+"_lua")
                    if not self.editor.lua_workbench.is_initialized():
                        respath = os.path.join(base, levelpaths.resourcepath)
                        try:
                            self.editor.lua_workbench.unpack_scripts(respath)
                        except Exception as err:
                            open_error_dialog(str(err)+"\nPress OK to continue. Script decompilation will be skipped.",
                                              None)

                    if self.editor.lua_workbench.is_initialized():
                        self.editor.lua_workbench.read_entity_initialization()

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
                    self.current_path = filepath
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

                    self.editor.read_entityinit_and_update()

                    QApplication.processEvents()
                    self.editor.level_view.start_redrawing()

                    self.editor.menubar.plugin_menu.execute_event("after_load")

                except Exception as error:
                    self.editor.level_view.start_redrawing()
                    self.is_loading = False
                    print("Error appeared while loading:", error)
                    traceback.print_exc()
                    open_error_dialog(str(error), self)
                    return

    @catch_exception_with_dialog
    def button_save_level(self, *args, **kwargs):
        try:
            self.editor.level_view.stop_redrawing()
            if self.level_paths is not None:
                levelpaths = self.level_paths
                progressbar = LoadingProgress("Saving")
                progressbar.progressupdate.connect(self.updatestatus)

                base = os.path.dirname(self.current_gen_path)
                fname = os.path.basename(self.current_gen_path)
                progressbar.set(0)

                for id, window in self.editor.pik_control.edit_windows.items():
                    try:
                        self.editor.pik_control.update_editwindow_position(id)
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
                self.editor.level_view.selected_positions = []
                for obj in self.editor.level_view.selected:
                    if obj.getmatrix() is not None:
                        self.editor.level_view.selected_positions.append(obj.getmatrix())
                progressbar.set(10)

                if self.editor.editorconfig.getboolean("regenerate_pf2", fallback=False):
                    regenerate_waypoints = self.editor.editorconfig.getboolean("regenerate_waypoints", fallback=False)
                    try:
                        pf2path = os.path.join(base, fname.replace("xml", "pf2"))
                        pf2 = PF2(pf2path)
                    except FileNotFoundError:
                        pass
                    else:
                        pf2.update_boundary(self.level_data,
                                            os.path.join(base, fname.replace(".xml", "")),
                                            self.editor.level_view.bwterrain,
                                            self.editor.level_view.waterheight,
                                            regenerate_waypoints)
                        pf2.save(pf2path)
                else:
                    print("Skipping PF2..")

                progressbar.set(20)
                if (self.editor.editorconfig.getboolean("recompile_lua", fallback=True)
                    and self.editor.lua_workbench.is_initialized()):
                    try:
                        respath = os.path.join(base, levelpaths.resourcepath)
                        self.editor.lua_workbench.repack_scripts(respath,
                                                                 respath,
                                                                 scripts=[x.mName for x in self.level_data.scripts.values()]
                                                                 )
                    except Exception as err:
                        traceback.print_exc()
                        msgbox = QtWidgets.QMessageBox()
                        msgbox.setText(
                            "An error appeared during compilation:\n\n"+str(err))
                        msgbox.setInformativeText("Do you want to continue saving? This will skip compilation of Lua scripts.")
                        msgbox.setStandardButtons(
                            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                        #msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
                        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                        msgbox.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
                        msgbox.setWindowTitle("Warning")
                        result = msgbox.exec()

                        if result == QtWidgets.QMessageBox.StandardButton.No:
                            return

                progressbar.set(25)
                for object in self.preload_data.objects.values():
                    object.update_xml()
                progressbar.set(30)


                print("Sorting XML nodes...")
                self.level_data.sort_nodes()

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
                    """if self.level_paths.objectfilepadding is not None:
                        with open(os.path.join(base, levelpaths.objectpath), "r+b") as g:
                            g.seek(0, 2)
                            if g.tell() < self.level_paths.objectfilepadding:
                                g.write(b"\x00"*(self.level_paths.objectfilepadding - g.tell()))"""
                else:
                    with open(os.path.join(base, levelpaths.objectpath), "wb") as g:
                        g.write(tmp.getvalue())
                        if self.level_paths.objectfilepadding is not None:
                            if g.tell() < self.level_paths.objectfilepadding:
                                g.write(b" "*(self.level_paths.objectfilepadding - g.tell()))

                            else:
                                open_error_dialog(
                                    f"Level XML has exceeded Padding! "
                                    f"({g.tell()} vs {self.level_paths.objectfilepadding})\n"
                                    "If you need padding, you have to update the padding to a higher value.\n"
                                    "If you are using save states, you have to restart the game normally and set a new savestate.",
                                    self
                                )

                progressbar.set(90)

                if levelpaths.preloadpath.endswith(".gz"):
                    with gzip.open(os.path.join(base, levelpaths.preloadpath), "wb") as g:
                        g.write(tmp2.getvalue())
                    """if self.level_paths.preloadpadding is not None:
                        with open(os.path.join(base, levelpaths.preloadpath), "ab") as g:
                            g.seek(0, 2)
                            if g.tell() < self.level_paths.preloadpadding:
                                g.write(b"\x00"*(self.level_paths.preloadpadding - g.tell()))"""
                else:
                    with open(os.path.join(base, levelpaths.preloadpath), "wb") as g:
                        g.write(tmp2.getvalue())
                        if self.level_paths.preloadpadding is not None:
                            if g.tell() < self.level_paths.preloadpadding:
                                g.write(b" "*(self.level_paths.preloadpadding - g.tell()))
                            else:
                                open_error_dialog(
                                    f"Preload XML has exceeded Padding! "
                                    f"({g.tell()} vs {self.level_paths.objectfilepadding})\n"
                                    "If you need padding, you have to update the padding to a higher value.\n"
                                    "If you are using save states, you have to restart the game and set a new savestate.",
                                    self
                                )

                tmp = BytesIO()
                self.level_paths.write(tmp)

                with open(self.current_path, "wb") as f:
                    f.write(tmp.getvalue())

                print("Done!")
                progressbar.set(100)
                self.editor.level_view.start_redrawing()
                self.editor.set_has_unsaved_changes(False)
            #else:
            #    self.button_save_level_as()
        except Exception as err:
            self.editor.level_view.start_redrawing()
            raise

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


class PF2(object):
    def __init__(self, path):
        self.data = [[None for y in range(512)] for x in range(512)]

        with open(path, "rb") as f:
            for i in range(512*512):
                x = (i) % 512
                y = (i) // 512
                if x < 256:
                    x *= 2
                else:
                    x = x - 256
                    x *= 2
                    x += 1

                tilevalue = f.read(6)
                self.data[x][y] = [v for v in tilevalue]

            self.rest = f.read()

    def update_boundary(self, level_file: BattalionLevelFile, basepath, terrain: 'BWTerrainV2', waterheight, regenerate_waypoints=False):
        try:
            missionboundary = Image.open(basepath+"_boundary.png")
            if missionboundary.height != 512 or missionboundary.width != 512:
                raise RuntimeError("Incorrect width")
            missionboundary = ImageOps.flip(missionboundary)
        except:
            print(basepath + "_boundary.png", "not found. Starting with a blank boundary map.")
            missionboundary = Image.new("RGB", (512, 512))
        drawboundary = ImageDraw.Draw(missionboundary)

        try:
            ford = Image.open(basepath+"_ford.png")
            if ford.height != 512 or ford.width != 512:
                raise RuntimeError("Incorrect width")
            ford = ImageOps.flip(ford)
        except:
            print(basepath+"_ford.png", "not found. Starting with a blank ford map.")
            ford = Image.new("RGB", (512, 512))
        drawford = ImageDraw.Draw(ford)

        replace_data = False
        try:
            nogo = Image.open(basepath+"_nogo.png")
            if nogo.height != 512 or nogo.width != 512:
                raise RuntimeError("Incorrect width")
            nogo = ImageOps.flip(nogo)
            replace_data = True
        except:
            print(basepath + "_nogo.png", "not found. Starting with a blank No-Go map.")
            nogo = Image.new("RGB", (512, 512))
        drawnogo = ImageDraw.Draw(nogo)

        if regenerate_waypoints:
            replace_data = True

        temptarget = Image.new("RGB", (512, 512))
        temptarget.paste((0, 0, 0), (0,0,512,512))
        tempdrawtarget = ImageDraw.Draw(temptarget)

        offsetx = 2
        val = 0x1
        for id, object in level_file.objects_with_positions.items():
            if (regenerate_waypoints and object.type == "cWaypoint"
                    and (object.Flags & 0x8 or object.Flags & 0x40 or object.Flags & 0x80)):
                mtx = object.getmatrix().mtx
                x, y, z = mtx[12:15]
                img_x = (x + 2048) / 8.0
                img_y = (z + 2048) / 8.0
                rad = 1
                drawnogo.point([img_x+offsetx, img_y], fill=(val,val, val))
            elif object.type == "cMapZone" or object.type == "cDamageZone":
                mtx = object.getmatrix().mtx
                x,y,z = mtx[12:15]
                img_x = (x+2048)/8.0
                img_y = (z+2048)/8.0

                mymtx = mtx.reshape((4, 4), order="F")

                temp_drawing = False
                intended_target = None

                if object.type == "cDamageZone":
                    if object.mFlags & 1:
                        temptarget.paste((0, 0, 0), (0, 0, 512, 512))
                        drawtarget = tempdrawtarget
                        intended_target = drawnogo
                        temp_drawing = True
                    else:
                        drawtarget = drawnogo
                elif object.mZoneType == "ZONETYPE_MISSIONBOUNDARY":
                    drawtarget = drawboundary
                elif object.mZoneType == "ZONETYPE_FORD":
                    drawtarget = drawford
                elif object.mZoneType == "ZONETYPE_NOGOAREA":
                    if object.mFlags & 1:
                        temptarget.paste((0, 0, 0), (0, 0, 512, 512))
                        drawtarget = tempdrawtarget
                        intended_target = drawnogo
                        temp_drawing = True
                    else:
                        drawtarget = drawnogo
                else:
                    drawtarget = None

                if drawtarget is not None:
                    if object.mRadius > 0:
                        rad = object.mRadius / 8.0

                        if temp_drawing:
                            aabb_min_x = max(0, int(img_x-rad+offsetx))
                            aabb_min_y = max(0, int(img_y - rad))
                            aabb_max_x = min(511, int(img_x + rad + offsetx))
                            aabb_max_y = min(511, int(img_y + rad))


                        drawtarget.ellipse((img_x-rad+offsetx, img_y-rad, img_x+rad+offsetx, img_y+rad), outline=(0xF0, 0xF0, 0xF0), fill=(0xF0, 0xF0, 0xF0))
                    if object.mSize.x != 0 and object.mSize.z != 0:
                        sizex, sizey, sizez = object.mSize.x/2.0, object.mSize.y/2.0, object.mSize.z/2.0

                        corner1 = mymtx.dot(numpy.array([-sizex, 0, -sizez, 1]))
                        corner2 = mymtx.dot(numpy.array([-sizex, 0, sizez, 1]))
                        corner3 = mymtx.dot(numpy.array([sizex, 0, sizez, 1]))
                        corner4 = mymtx.dot(numpy.array([sizex, 0, -sizez, 1]))



                        points = []
                        for p in [corner1, corner2, corner3, corner4]:
                            points.append(((p[0]+2048)/8.0+offsetx, (p[2]+2048)/8.0))

                        if temp_drawing:
                            aabb_min_x = max(0, min(int(p[0]) for p in points))
                            aabb_min_y = max(0, min(int(p[1]) for p in points))
                            aabb_max_x = min(511, max(int(p[0]) for p in points))
                            aabb_max_y = min(511, max(int(p[1]) for p in points))

                        drawtarget.polygon(points, (0xF0, 0xF0, 0xF0), (0xF0, 0xF0, 0xF0))

                if temp_drawing:
                    box_height = object.mSize.y
                    for imgx in range(aabb_min_x, aabb_max_x+1):
                        for imgy in range(aabb_min_y, aabb_max_y+1):
                            color = temptarget.getpixel((imgx, imgy))
                            if color[0] > 128:
                                terrheight = terrain.pointdata[imgx*2][imgy*2]
                                if terrheight is None:
                                    intended_target.point([imgx, imgy], fill=color)
                                else:
                                    terr2height = terrain.pointdata[imgx*2+1][imgy*2]
                                    terr3height = terrain.pointdata[imgx * 2+1][imgy * 2+1]
                                    terr4height = terrain.pointdata[imgx * 2][imgy * 2 + 1]
                                    count = 1
                                    for h in (terr2height, terr3height, terr4height):
                                        if h is not None:
                                            count += 1
                                            terrheight += h
                                    terrheight = terrheight/count
                                    if y-box_height/2.0 <= terrheight <= y+box_height/2.0:
                                        intended_target.point([imgx, imgy], fill=color)

        for i in range(512*512):
            x = (i) % 512
            y = (i) // 512
            if x < 256:
                x *= 2
            else:
                x = x - 256
                x *= 2
                x += 1

            # NOGO
            val = nogo.getpixel((x, y))
            if replace_data:
                self.data[x][y][0] = val[0]
            else:
                self.data[x][y][0] = val[0] + (self.data[x][y][0]&0xF)

            # FORD
            val = ford.getpixel((x, y))
            self.data[x][y][1] = val[0]

            # MISSION BOUNDARY
            val = missionboundary.getpixel((x,y))
            self.data[x][y][2] = val[0]

        #ImageOps.flip(nogo).save("nogotest.png")
        #ImageOps.flip(missionboundary).save("missionboundarytest.png")
        #ImageOps.flip(ford).save("fordtest.png")


    def save(self, path):
        with open(path, "wb") as f:
            for i in range(512*512):
                x = (i) % 512
                y = (i) // 512
                if x < 256:
                    x *= 2
                else:
                    x = x - 256
                    x *= 2
                    x += 1
                values = self.data[x][y]
                f.write(struct.pack("BBBBBB", *values))
            f.write(self.rest)
            print("Updated PF2 written to", path)
        #shutil.copy(path, r"E:\Modding\Video Game Modding\battalion-tools\PF2\test.pf2")