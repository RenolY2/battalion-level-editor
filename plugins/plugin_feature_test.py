
import math
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore



import typing
from typing import TYPE_CHECKING
from widgets.graphics_widgets import UnitViewer
from widgets.tree_view import ObjectGroup, NamedItem
from lib.BattalionXMLLib import BattalionObject, BattalionLevelFile


if TYPE_CHECKING:
    import bw_editor


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
            self.spawn = result

    def spawn_object(self, point):
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


class ImportObject(QtWidgets.QWidget):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        self.setLayout(self.layout)


class AddBWObjectWindow(QtWidgets.QWidget):
    closing = QtCore.pyqtSignal()
    addobject = QtCore.pyqtSignal(str, bool)

    def __init__(self, parent, editor):
        super().__init__(parent)
        #self.editor: bw_editor.LevelEditor = editor
        self.resize(900, 500)
        self.setMinimumSize(QtCore.QSize(300, 300))

        self.explanation = QtWidgets.QLabel(("Insert the XML data of an object you want to add here. "
                                             "This does not automatically add object dependencies or resources if they don't exist already.\n"
                                             "Each press of 'Add Object' adds the object to the level with a new ID."))
        self.vlayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.vlayout)
        self.vlayout.addWidget(self.explanation)
        self.textbox_xml = QtWidgets.QTextEdit(self)


        #self.add_object_on_map = QtWidgets.QPushButton("Add Object On Map", self)

        #self.add_object_on_map.setEnabled(False)

        self.vlayout.addWidget(self.textbox_xml)

        self.hlayout = QtWidgets.QHBoxLayout(self)
        #self.hlayout.addWidget(self.add_object_on_map)

        self.vlayout.addLayout(self.hlayout)

        self.textbox_xml.textChanged.connect(self.resetoffset)
        self.offsetx = 0
        self.offsety = 0
        self.donotreset = False

        font = QtGui.QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        metrics = QtGui.QFontMetrics(font)
        self.textbox_xml.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        self.textbox_xml.setFont(font)

    def resetoffset(self):
        if not self.donotreset:
            self.offsetx = 0
            self.offsety = 0

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.closing.emit()

    def action_add_object(self):
        content = self.textbox_xml.toPlainText()
        try:
            obj = BattalionObject.create_from_text(content, self.editor.level_file, self.editor.preload_file)
        except Exception as err:
            open_error_dialog("Couldn't add object:\n"+str(err), None)
            return

        oldid = obj.id
        obj.choose_unique_id(self.editor.level_file, self.editor.preload_file)
        newid = obj.id

        self.offsety += 1
        if self.offsety > 5:
            self.offsety = 0
            self.offsetx += 1
        mtx = obj.getmatrix()
        if mtx is not None:
            mtx.mtx[12] += self.offsetx*4
            mtx.mtx[14] -= self.offsety*4

        if obj.type == "cGameScriptResource" and obj.mName != "":
            if self.editor.lua_workbench.script_exists(obj.mName):
                number = 1
                while True:
                    newscriptname = "{0}_{1}".format(obj.mName, number)
                    if not self.editor.lua_workbench.script_exists(newscriptname):
                        obj.mName = newscriptname
                        break
                    else:
                        number += 1

            self.editor.lua_workbench.create_empty_if_not_exist(obj.mName)

        if obj.is_preload():
            self.editor.preload_file.add_object_new(obj)
        else:
            self.editor.level_file.add_object_new(obj)


        self.donotreset = True
        self.textbox_xml.setText(content.replace(oldid, newid))
        self.donotreset = False
        self.editor.leveldatatreeview.set_objects(self.editor.level_file, self.editor.preload_file, remember_position=True)
        self.editor.level_view.do_redraw(force=True)


class NewAddWindow(QtWidgets.QMdiSubWindow):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.resize(900, 500)

        self.vertical = QtWidgets.QVBoxLayout()
        self.verticalHolder = QtWidgets.QWidget(self)
        self.verticalHolder.setLayout(self.vertical)
        self.tabs = QtWidgets.QTabWidget(self)
        self.addxml = AddBWObjectWindow(self, editor)
        self.importobj = ImportObject(self, editor)
        self.addexistinboject = AddExistingObject(self, editor)
        self.tabs.addTab(self.addexistinboject, "Add Existing Object")
        self.tabs.addTab(self.importobj, "Import External Object")
        self.tabs.addTab(self.addxml, "Add XML Object")

        self.vertical.addWidget(self.tabs)
        self.add_object = QtWidgets.QPushButton("Add Object", self)
        self.add_object.pressed.connect(self.action_add_object)
        self.vertical.addWidget(self.add_object)


        self.setWidget(self.verticalHolder)

    def action_add_object(self):
        print("Current index:", self.tabs.currentIndex())


class Plugin(object):
    def __init__(self):
        self.name = "Feature Test"
        self.actions = [("New Add Window", self.unitaddwindow)]#,
                        #("Unit Viewer Test", self.testfunc),
                        #,
                        #("Edit Window Mass Test", self.neweditwindowtest)]
        print("I have been initialized")
        self.opengl = None
        self.newaddwindow = None
        self.gizmowidget = None
        self.lua_find_window = None
        self.editwindows = []

    def terrain_click_3d(self, viewer, ray, point):
        if self.newaddwindow is not None:
            self.newaddwindow.addexistinboject: AddExistingObject
            self.newaddwindow.addexistinboject.spawn_object(point)

    def unitaddwindow(self, editor: "bw_editor.LevelEditor"):
        print("hi")
        self.newaddwindow = NewAddWindow(editor)
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
