

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
        self.categories = {
                        "sTroopBase": ObjectGroup("Troops"),
                        "cGroundVehicleBase": ObjectGroup("Ground Vehicles"),
                        "sAirVehicleBase": ObjectGroup("Air Vehicles"),
                        "cBuildingImpBase": ObjectGroup("Buildings"),
                        "sDestroyBase": ObjectGroup("Destroyable/Environment Objects"),
                        "sSceneryClusterBase": ObjectGroup("Trees/Vegetation"),
                        "cCameraBase": ObjectGroup("Cameras"),
                        "cObjectiveMarkerBase": ObjectGroup("Objective Markers"),
        }

        for objid, obj in editor.level_file.objects.items():
            if obj.type in self.categories:
                category = self.categories[obj.type]
                item = NamedItem(category, obj.name, obj)
                item.setText(2, "AAA")
                category.addChild(item)

        for category in self.categories.values():
            self.treewidget.addTopLevelItem(category)

        self.treewidget.itemSelectionChanged.connect(self.set_model_scene)

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
        self.actions = []#,
                        #("Unit Viewer Test", self.testfunc),
                        #("New Add Window", self.unitaddwindow),
                        #("Edit Window Mass Test", self.neweditwindowtest)]
        print("I have been initialized")
        self.opengl = None
        self.newaddwindow = None
        self.gizmowidget = None
        self.lua_find_window = None
        self.editwindows = []

    def unitaddwindow(self, editor: "bw_editor.LevelEditor"):
        print("hi")
        self.newaddwindow = NewAddWindow(editor)
        self.newaddwindow.show()

    def select_update(self, editor: "bw_editor.LevelEditor"):
        if self.main_window is not None and self.main_window.autoupdate_checkbox.isChecked():
            obj = editor.get_selected_obj()
            if obj is not None:
                QtWidgets.QApplication.setOverrideCursor(
                    QtCore.Qt.CursorShape.WaitCursor)
                self.main_window.change_object(obj)
                QtWidgets.QApplication.restoreOverrideCursor()

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
