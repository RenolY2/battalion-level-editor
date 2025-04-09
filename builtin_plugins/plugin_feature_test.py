import os
import math
import enum
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
import typing

from typing import TYPE_CHECKING
from widgets.graphics_widgets import UnitViewer
from widgets.tree_view import ObjectGroup, NamedItem
from lib.BattalionXMLLib import BattalionObject, BattalionLevelFile
from editor_controls import MouseMode
from plugins.plugin_object_exportimport import Plugin as ObjectExportImportPlugin
from lib.bw_types import BWMatrix
from lib.vectors import Vector3

if TYPE_CHECKING:
    import bw_editor
    import bw_widgets


class AddObjectMode(enum.Enum):
    NONE = 0
    EXISTING = 1
    IMPORT = 2
    XML = 3


class ObjectGroupInstancer(ObjectGroup):
    def __init__(self, name, xmlpath):
        super().__init__(name)
        with open(xmlpath, "r") as f:
            data = f.read()

        self.base_obj = BattalionObject.create_from_text(data, None, None)


class NamedItemInstancer(NamedItem):
    def __init__(self, parent, name, obj, base=None):
        self.base = base
        self.name = name
        self.bound_to: BattalionObject
        super().__init__(parent, name, obj)

    def update_name_original(self):
        self.setText(0, self.bound_to.name)
        self.setText(1, self.bound_to.extra_detail_name())

    def update_name(self):
        if self.base is None:
            self.setText(0, self.name)
            self.setText(1, self.bound_to.extra_detail_name())
        else:
            self.update_name_original()

    def create_instance(self, level_data, preload_data):
        if self.base is None:
            obj = self.bound_to.clone_object(level_data, preload_data)
            obj._level = level_data

            return obj
        else:
            obj: BattalionObject = self.base.clone_object(level_data, preload_data)
            obj.mBase = self.bound_to
            obj._level = level_data
            obj.update_xml()

            return obj


class AddExistingObject(QtWidgets.QSplitter):
    signal_addobj = QtCore.pyqtSignal(str)
    mode_change = QtCore.pyqtSignal(AddObjectMode)

    def __init__(self, parent, editor: "bw_editor.LevelEditor"):
        super().__init__(parent)
        self.editor = editor

        self.treewidget = QtWidgets.QTreeWidget(self)
        self.viewer = UnitViewer(self, editor)
        self.viewer.setMinimumWidth(100)
        self.treewidget.resize(self.width()//2, self.treewidget.height())

        self.addWidget(self.treewidget)
        self.addWidget(self.viewer)
        self.treewidget.setColumnCount(2)
        self.treewidget.setHeaderLabels(["Objects", "Info"])
        self.spawn: NamedItemInstancer = None

        bw1path = "resources/basetemplates/BW1/"
        bw2path = "resources/basetemplates/BW2/"

        if self.editor.file_menu.level_data.is_bw1():
            self.categories: typing.Dict[str, ObjectGroupInstancer] = {
                "sTroopBase": ObjectGroupInstancer("Troops", bw1path+"cTroop.xml"),
                "cGroundVehicleBase": ObjectGroupInstancer("Ground Vehicles", bw1path+"cGroundVehicle.xml"),
                "sAirVehicleBase": ObjectGroupInstancer("Air Vehicles", bw1path+"cAirVehicle.xml"),
                "cBuildingImpBase": ObjectGroupInstancer("Buildings", bw1path+"cBuilding.xml"),
                "cCapturePointBase": ObjectGroupInstancer("Capture Points", bw1path+"cCapturePoint.xml"),
                "sDestroyBase": ObjectGroupInstancer("Destroyable/Environment Objects", bw1path+"cDestroyableObject.xml"),
                "sSceneryClusterBase": ObjectGroupInstancer("Trees/Vegetation", bw1path+"cSceneryCluster.xml"),
                "cCameraBase": ObjectGroupInstancer("Cameras", bw1path+"cCamera.xml"),
                "cObjectiveMarkerBase": ObjectGroupInstancer("Objective Markers", bw1path+"cObjectiveMarker.xml"),
                "sPickupBase": ObjectGroupInstancer("Pickups", bw1path+"cPickupReflected.xml")
            }
        else:
            self.categories: typing.Dict[str, ObjectGroupInstancer] = {
                "sTroopBase": ObjectGroupInstancer("Troops", bw2path+"cTroop.xml"),
                "cGroundVehicleBase": ObjectGroupInstancer("Ground Vehicles", bw2path+"cGroundVehicle.xml"),
                "sAirVehicleBase": ObjectGroupInstancer("Air Vehicles", bw2path+"cAirVehicle.xml"),
                "cWaterVehicleBase": ObjectGroupInstancer("Water Vehicles", bw2path+"cWaterVehicle.xml"),
                "cBuildingImpBase": ObjectGroupInstancer("Buildings", bw2path+"cBuilding.xml"),
                "cCapturePointBase": ObjectGroupInstancer("Capture Points", bw2path+"cCapturePoint.xml"),
                "sDestroyBase": ObjectGroupInstancer("Destroyable/Environment Objects", bw2path+"cDestroyableObject.xml"),
                "sSceneryClusterBase": ObjectGroupInstancer("Trees/Vegetation", bw2path+"cSceneryCluster.xml"),
                "cCameraBase": ObjectGroupInstancer("Cameras", bw2path+"cCamera.xml"),
                "cObjectiveMarkerBase": ObjectGroupInstancer("Objective Markers", bw2path+"cObjectiveMarker.xml"),
                "sPickupBase": ObjectGroupInstancer("Pickups", bw2path+"cPickupReflected.xml")
            }

        for objid, obj in editor.level_file.objects.items():
            if obj.type in self.categories:
                category = self.categories[obj.type]
                item = NamedItemInstancer(category, obj.name, obj, category.base_obj)
                item.setText(2, "AAA")
                category.addChild(item)

        for category in self.categories.values():
            self.treewidget.addTopLevelItem(category)

        for name, xmlname in (("Map Zone", "cMapZone.xml"),
                              ("Waypoint", "cWaypoint.xml")):
            xmlpath = bw1path+xmlname if self.editor.file_menu.level_data.is_bw1() else bw2path+xmlname
            obj = BattalionObject.create_from_path(bw1path + xmlname, None, None)
            item = NamedItemInstancer(self.treewidget, name, obj, None)
            self.treewidget.addTopLevelItem(item)

        self.treewidget.itemSelectionChanged.connect(self.set_model_scene)
        self.treewidget.itemDoubleClicked.connect(self.set_spawn_obj)

    def set_spawn_obj(self, result):
        if isinstance(result, NamedItemInstancer):
            self.editor.level_view.text_display.set_text(
                "AddObject",
                "Now adding {}\nHold Shift to place multiple.\nPress ESC to cancel.".format(result.text(0)))
            self.editor.level_view.mouse_mode.set_mode(MouseMode.ADD_OBJECT)
            self.spawn = result

            self.mode_change.emit(AddObjectMode.EXISTING)
            self.editor.activateWindow()

    def spawn_object(self, point) -> BattalionObject:
        if self.spawn is not None:
            level_data = self.editor.file_menu.level_data
            preload_data = self.editor.file_menu.preload_data
            newobj: BattalionObject = self.spawn.create_instance(level_data, preload_data)
            newobj.updatemodelname()
            mtx = newobj.getmatrix()
            if mtx is not None:
                mtx.reset_rotation()
                mtx.rotate_y(-self.editor.level_view.camera_horiz - self.viewer.angle - math.pi/2)
                mtx.set_position(point.x, point.z, point.y)
            level_data.add_object_new(newobj)
            self.editor.leveldatatreeview.set_objects(self.editor.level_file, self.editor.preload_file,
                                                      remember_position=True)
            self.editor.update_3d()
            self.editor.level_view.do_redraw(force=True)
            self.editor.set_has_unsaved_changes(True)

            return newobj

    def set_model_scene(self):
        curritem = self.treewidget.selectedItems()
        if len(curritem) > 0:
            item = curritem[0]

            self.viewer.reset_scene()
            if item.bound_to is not None:
                if item.bound_to.modelname is not None:
                    self.viewer.set_scene_single_model(item.bound_to.modelname)
                    self.viewer.recalculate_camera()
            self.viewer.update()


class DirectoryList(QtWidgets.QListWidget):
    directory_change = QtCore.pyqtSignal(str)

    def __init__(self, parent, basepath):
        super().__init__(parent)
        self.foldericon = load_icon("resources/Folder-32x32.png")
        self.basepath = basepath
        self.currpath = basepath
        self.level = 0

        dirs = self.get_directory_listing(basepath)
        self.set_directory_listing(dirs)
        self.itemDoubleClicked.connect(self.change_dir)

    def change_dir(self, item):
        if item.text() == "..":
            currpath = os.path.dirname(self.currpath)
            self.currpath = currpath
            self.level -= 1
            dirs = self.get_directory_listing(currpath)
            self.set_directory_listing(dirs)

        else:
            dir = item.text()
            currpath =  os.path.join(self.currpath, dir)
            self.currpath = currpath
            self.level += 1
            dirs = self.get_directory_listing(currpath)
            self.set_directory_listing(dirs)

        self.directory_change.emit(self.currpath)

    def set_directory_listing(self, dirs):
        self.clear()

        if self.level > 0:
            up_level = QtWidgets.QListWidgetItem(self)
            up_level.setText("..")
            self.addItem(up_level)

        for dir in dirs:
            diritem = QtWidgets.QListWidgetItem(self)
            diritem.setIcon(self.foldericon)
            diritem.setText(dir)
            self.addItem(diritem)

    def get_directory_listing(self, path):
        dirs = []

        for entry in os.listdir(path):
            bundle_path = os.path.join(path, entry, "bundle.xml")
            if not os.path.exists(bundle_path) and os.path.isdir(os.path.join(path, entry)):
                dirs.append(entry)

        dirs.sort()

        return dirs


def load_icon(imagepath: str) -> QtGui.QIcon | None:
    if not os.path.exists(imagepath):
        return None

    try:
        image = QtGui.QImage(imagepath)
    except Exception as err:
        icon = None
    else:
        pixmap = QtGui.QPixmap.fromImage(image)
        icon = QtGui.QIcon(pixmap)

    return icon


class ItemWithPath(QtWidgets.QListWidgetItem):
    def __init__(self, parent, path: str):
        super().__init__(parent)
        self.path = path


class ImportObject(QtWidgets.QWidget):
    mode_change = QtCore.pyqtSignal(AddObjectMode)

    def __init__(self, parent, editor: "bw_editor.LevelEditor"):
        super().__init__(parent)
        self.editor = editor
        self.layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.layout)

        game = "bw1" if editor.level_file.is_bw1() else "bw2"
        dirpath = os.path.join("battalion_objects", game)

        self.dir_list = DirectoryList(self, dirpath)
        self.layout.addWidget(self.dir_list)

        self.list = QtWidgets.QListWidget(self)
        self.list.setIconSize(QtCore.QSize(128, 128))
        self.layout.addWidget(self.list)
        self.no_icon = load_icon("battalion_objects/no_icon.png")

        assert self.no_icon is not None, "battalion_objects/no_icon.png is missing"

        self.layout.setStretch(0, 1)
        self.layout.setStretch(1, 3)
        self.populate_items(dirpath)

        self.dir_list.directory_change.connect(lambda x: self.populate_items(x))
        self.list.itemDoubleClicked.connect(self.import_object)
        self.current_bundle = None

    def populate_items(self, dirpath):
        self.list.clear()
        for entry in os.listdir(dirpath):
            bundle_path = os.path.join(dirpath, entry, "bundle.xml")
            preview_path = os.path.join(dirpath, entry, "preview.png")

            if os.path.exists(bundle_path):
                item = ItemWithPath(self.list, os.path.join(dirpath, entry))
                item.setText(entry)

                icon = load_icon(preview_path)
                if icon is None:
                    icon = self.no_icon

                item.setIcon(icon)

    def import_object(self):
        item: ItemWithPath = self.list.currentItem()

        with open(os.path.join(item.path, "bundle.xml"), "r") as f:
            level = BattalionLevelFile(f)

        if len(level.objects_with_positions) == 0:
            ObjectExportImportPlugin.import_bundle(self.editor, item.path)
            self.current_bundle = None
        else:
            self.editor.level_view.text_display.set_text(
                "AddObject",
                "Now importing {}\nClick on terrain to choose import location.\nHold shift to import multiple times.\nPress ESC to cancel.".format(item.text()))
            self.editor.level_view.mouse_mode.set_mode(MouseMode.ADD_OBJECT)
            self.mode_change.emit(AddObjectMode.IMPORT)
            self.current_bundle = item.path
            self.editor.activateWindow()


class NewAddWindow(QtWidgets.QMdiSubWindow):
    closing = QtCore.pyqtSignal()

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setWindowTitle("Choose Object")
        self.resize(900, 500)

        self.vertical = QtWidgets.QVBoxLayout()
        self.verticalHolder = QtWidgets.QWidget(self)
        self.verticalHolder.setLayout(self.vertical)
        self.tabs = QtWidgets.QTabWidget(self)
        #self.addxml = AddBWObjectWindow(self, editor)
        self.importobj: ImportObject = ImportObject(self, editor)
        self.addexistingoject: AddExistingObject = AddExistingObject(self, editor)
        self.tabs.addTab(self.addexistingoject, "Add Existing Object")
        self.tabs.addTab(self.importobj, "Import External Object")
        #self.tabs.addTab(self.addxml, "Add XML Object")

        self.vertical.addWidget(self.tabs)
        self.add_object = QtWidgets.QPushButton("Add Object", self)
        self.add_object.pressed.connect(self.action_add_object)
        self.vertical.addWidget(self.add_object)

        self.tabs.currentChanged.connect(self.change_button_text)
        self.setWidget(self.verticalHolder)

        self.current_mode = AddObjectMode.NONE
        self.importobj.mode_change.connect(self.change_mode)
        self.addexistingoject.mode_change.connect(self.change_mode)

    def change_mode(self, mode):
        self.current_mode = mode

    def reset_mode(self):
        self.change_mode(AddObjectMode.NONE)

    def change_button_text(self, index):
        if index == 0:
            self.add_object.setText("Add Object")
        elif index == 1:
            self.add_object.setText("Import Object")
        else:
            raise RuntimeError(f"Unknown index {index}")

    def action_add_object(self):
        index = self.tabs.currentIndex()
        if index == 0:
            item = self.addexistingoject.treewidget.currentItem()
            self.addexistingoject.set_spawn_obj(item)
        elif index == 1:
            self.importobj.import_object()

    def closeEvent(self, closeEvent: typing.Optional[QtGui.QCloseEvent]) -> None:
        self.closing.emit()


class Plugin(object):
    def __init__(self):
        self.name = "Feature Test"
        self.actions = []#,
                        #("Unit Viewer Test", self.testfunc),
                        #,
                        #("Edit Window Mass Test", self.neweditwindowtest)]
        print("I have been initialized")
        self.opengl = None
        self.newaddwindow: NewAddWindow|None = None
        self.gizmowidget = None
        self.lua_find_window = None
        self.editwindows = []

        self.last_obj = None

    def cancel_mode(self, editor: "bw_editor.LevelEditor"):
        self.cancel_mode_manual(editor.level_view)

    def cancel_mode_manual(self, level_view: "bw_widgets.BolMapViewer"):
        level_view.mouse_mode.set_mode(MouseMode.NONE)
        level_view.text_display.set_text("AddObject", "")
        self.last_obj = None
        if self.newaddwindow is not None:
            self.newaddwindow.change_mode(AddObjectMode.NONE)

    def handle_close_window(self):
        self.cancel_mode(self.newaddwindow.editor)
        self.newaddwindow = None

    def terrain_click_2d(self, viewer, point):
        self.terrain_click_3d(viewer, None, point)

    def terrain_click_3d(self, viewer: "bw_widgets.BolMapViewer", ray, point):
        if self.newaddwindow is not None and viewer.mouse_mode.active(MouseMode.ADD_OBJECT):
            if self.newaddwindow.current_mode == AddObjectMode.EXISTING:
                self.newaddwindow.addexistingoject: AddExistingObject
                obj = self.newaddwindow.addexistingoject.spawn_object(point)
                if self.last_obj is not None:
                    if obj.type == "cWaypoint" and self.last_obj.type == "cWaypoint":
                        self.last_obj.NextWP = obj

                self.last_obj = obj

                if not viewer.shift_is_pressed:
                    print("CANCELLING")
                    self.cancel_mode_manual(viewer)
                else:
                    print("NOT CANCELLING")
            else:
                editor: bw_editor.LevelEditor = self.newaddwindow.editor
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)

                objects: list[BattalionObject] = ObjectExportImportPlugin.import_bundle(
                    editor,
                    self.newaddwindow.importobj.current_bundle,
                    go_to_object=False,
                    show_info=not viewer.shift_is_pressed
                )


                # Calculate mid point of all objects.
                mid = Vector3(0, 0, 0)
                count = 0

                for obj in objects:

                    mtx: BWMatrix = obj.getmatrix()
                    if mtx is not None:
                        print(obj.name, mtx.x, mtx.y, mtx.z)
                        mid.x += mtx.x
                        mid.y += mtx.y
                        mid.z += mtx.z
                        count += 1

                if count > 0:
                    mid.x /= count
                    mid.y /= count
                    mid.z /= count
                print("MIDPOINT", mid)
                diff: Vector3 = Vector3(point.x, point.z, point.y) - mid
                print("DIFFERENCE", diff)
                for obj in objects:
                    mtx: BWMatrix = obj.getmatrix()
                    if mtx is not None:
                        mtx.set_position(mtx.x+diff.x, mtx.y+diff.y, mtx.z+diff.z)
                        print(obj.name, "has moved to", mtx.x, mtx.y, mtx.z)

                editor.level_view.do_redraw(force=True)
                QtWidgets.QApplication.restoreOverrideCursor()
                if not viewer.shift_is_pressed:
                    self.cancel_mode_manual(viewer)

    def key_press(self, editor, key):
        if key == QtCore.Qt.Key.Key_Escape:
            self.cancel_mode_manual(editor.level_view)

    def open_add_window(self, editor: "bw_editor.LevelEditor"):
        if self.newaddwindow is not None:
            self.newaddwindow.activateWindow()
        else:
            self.newaddwindow = NewAddWindow(editor)
            self.newaddwindow.closing.connect(self.handle_close_window)
            self.newaddwindow.show()

    def testfunc(self, editor: "bw_editor.LevelEditor"):
        print("This is a test function")
        print("More")
        img = UnitViewer.screenshot_objects(editor.level_view.selected, editor)
        img.save("test.png")
        """angle = math.pi / 4.0
        if len(editor.level_view.selected) == 1:
            obj = editor.level_view.selected[0]
            if obj.type == "cTroop":
                angle = -math.pi *(3/4)

        self.opengl = UnitViewer(editor, editor, width=256, height=256, angle=angle)

        positions = [] 
        bwterrain = editor.level_view.bwterrain
        waterheight = editor.level_view.waterheight



        temp_scene = []
        count = 0
        midx, midy, midz = 0, 0, 0
        for obj in editor.level_view.selected:
            obj: BattalionObject
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
        self.opengl.reset_scene()
        if count > 0:
            avgx = midx/count
            avgy = midy/count
            avgz = midz/count

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

                self.opengl.add_to_scene(model, mtx)
            self.opengl.recalculate_camera()
        self.opengl.record_image = True
        self.opengl.show()
        self.opengl.hide()
        img = self.opengl.img
        img.save("test.png")
        self.opengl.destroy()
        del self.opengl"""
        #self.opengl.show()
        #self.opengl.update()



    def unload(self):
        print("I have been unloaded")
