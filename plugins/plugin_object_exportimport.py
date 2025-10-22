import io
import os
import gzip
import shutil
import PyQt6.QtWidgets as QtWidgets
from io import BytesIO
from pathlib import Path
from collections import UserDict
import traceback
from widgets.menu.file_menu import LoadingBar
from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication
from collections import namedtuple

import lib.lua.bwarchivelib as bwarchivelib
from lib.lua.bwarchivelib import BattalionArchive
from lib.BattalionXMLLib import BattalionLevelFile, BattalionObject
from widgets.editor_widgets import open_error_dialog, open_message_dialog, open_yesno_box
from widgets.graphics_widgets import UnitViewer
from plugins.plugin_padding import YesNoQuestionDialog

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class CaseInsensitiveDict(UserDict):
    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, item):
        return super().__getitem__(item.lower())


def replace_references(obj, replacement_map):
    for attr_node in obj._node:
        if attr_node.tag in ("Pointer", "Resource"):
            pointers = getattr(obj, attr_node.attrib["name"])
            if isinstance(pointers, list):
                for i in range(len(pointers)):
                    if pointers[i] is not None:
                        if pointers[i].id in replacement_map:
                            pointers[i] = replacement_map[pointers[i].id]
            else:
                if pointers is not None and pointers.id in replacement_map:
                    setattr(obj, attr_node.attrib["name"], replacement_map[pointers.id])


class LabeledWidget(QtWidgets.QWidget):
    def __init__(self, parent, text, widget, text_right=False):
        super().__init__(parent)

        self.layout = QtWidgets.QHBoxLayout(self)
        self.text_label = QtWidgets.QLabel(text=text)
        self.widget = widget(self)

        if not text_right:
            self.layout.addWidget(self.text_label)
            self.layout.addWidget(self.widget)
        else:
            self.layout.addWidget(self.widget)
            self.layout.addWidget(self.text_label)


def os_walk(path):
    for entry in os.listdir(path):
        fullpath = os.path.join(path, entry)
        if os.path.isdir(fullpath):
            if os.path.exists(os.path.join(fullpath, "bundle.xml")):
                continue

            yield fullpath
            yield from os_walk(fullpath)




class CategorySelection(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.setEditable(True)

    def fill_category(self, path):
        paths = []
        """for dirpath, dirnames, filenames in os.walk(path):
            for dir in dirnames:
                fullpath = os.path.join(dirpath, dir)
                if not os.path.exists(os.path.join(fullpath, "bundle.xml")):
                    paths.append(fullpath)"""
        for dirpath in os_walk(path):
            paths.append(os.path.relpath(dirpath, path))

        paths.sort()
        self.addItem("--NONE--")
        self.addItems(paths)

    def get_category(self):
        if self.currentText() == "--NONE--":
            return None
        else:
            result = self.currentText().strip()
            if result:
                return result
            else:
                return None


class ExportSettingsFullLevel(QDialog):
    def __init__(self, path, levelname):
        super().__init__()
        self.setWindowTitle("Mass Object Export")
        self.path = path
        self.bundle_path = None
        self.layout = QtWidgets.QVBoxLayout(self)
        self.name_widget = LabeledWidget(self, "Level Name",
                                         QtWidgets.QLineEdit)
        self.name_widget.widget.setText(levelname)
        self.include_passengers = QtWidgets.QCheckBox(self, text="Include Passengers")
        self.clear_instance_flags = QtWidgets.QCheckBox(self, text="Clear Instance Flags")

        self.layout.addWidget(self.name_widget)
        self.layout.addWidget(self.include_passengers)
        self.layout.addWidget(self.clear_instance_flags)

        self.ok = QtWidgets.QPushButton(self, text="OK")
        self.cancel = QtWidgets.QPushButton(self, text="Cancel")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def get_level_name(self):
        return self.name_widget.widget.text()

    def confirm(self):
        self.name_widget.widget: QtWidgets.QLineEdit
        levelname = self.name_widget.widget.text()

        if "/" in levelname or "\\" in levelname:
            open_error_dialog("Invalid characters in level name!", self)
            return

        folderpath = os.path.join(self.path, levelname)
        print(folderpath)
        if os.path.exists(folderpath) and os.path.isdir(folderpath):
            msgbox = YesNoQuestionDialog(self,
                                         f"The level name is already in use at path: \n{folderpath}",
                                         "Do you still want to use it? (files in the existing folder may be overwritten)")
            result = msgbox.exec()
            if result == QMessageBox.StandardButton.Yes:
                self.accept()
        elif os.path.exists(folderpath) and os.path.isfile(folderpath):
            open_error_dialog("Level name is used by a file. Please use a different name.", None)
        else:
            self.accept()

    def deny(self):
        self.reject()




class ExportSettings(QDialog):
    def __init__(self, path):
        super().__init__()
        self.setWindowTitle("Object Export")
        self.path = path
        self.bundle_path = None
        self.layout = QtWidgets.QVBoxLayout(self)
        self.name_widget = LabeledWidget(self, "Object Bundle name:",
                                         QtWidgets.QLineEdit)
        self.category_widget = LabeledWidget(self, "Category:",
                                             CategorySelection)
        self.include_passengers = QtWidgets.QCheckBox(self, text="Include Passengers")
        #self.include_mpscript = QtWidgets.QCheckBox(self, text="Include MpScript")
        self.include_startwaypoint = QtWidgets.QCheckBox(self, text="Include Start Waypoint")
        self.clear_instance_flags = QtWidgets.QCheckBox(self, text="Clear Instance Flags")

        self.layout.addWidget(self.name_widget)
        self.layout.addWidget(self.category_widget)
        self.layout.addWidget(self.include_passengers)
        #self.layout.addWidget(self.include_mpscript)
        self.layout.addWidget(self.include_startwaypoint)
        self.layout.addWidget(self.clear_instance_flags)

        self.ok = QtWidgets.QPushButton(self, text="OK")
        self.cancel = QtWidgets.QPushButton(self, text="Cancel")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def set_current_category(self, category):
        if category is not None:
            self.category_widget.widget: CategorySelection
            self.category_widget.widget.setCurrentText(category)

    def fill_category(self, path):
        self.category_widget.widget.fill_category(path)

    def get_name(self):
        return self.name_widget.widget.text()

    def confirm(self):
        self.name_widget.widget: QtWidgets.QLineEdit
        bundlename = self.name_widget.widget.text()

        if "/" in bundlename or "\\" in bundlename:
            open_error_dialog("Invalid characters in bundle name!", self)
            return

        self.category_widget.widget: CategorySelection
        path = self.category_widget.widget.get_category()
        if path is None:
            folderpath = os.path.join(self.path, bundlename)
        else:
            full_category_path = os.path.join(self.path, path)
            if os.path.exists(
                    os.path.join(full_category_path, "bundle.xml")
            ):
                open_error_dialog("An object uses this category name! Please choose a different category name.", self)
                return

            try:
                os.makedirs(full_category_path, exist_ok=True)
            except Exception as error:
                open_error_dialog(f"Unable to create category: \n{str(error)}", self)
                return

            folderpath = os.path.join(full_category_path, bundlename)

        self.bundle_path = folderpath
        print(folderpath, "SAVE PATH")
        if os.path.exists(folderpath):
            msgbox = YesNoQuestionDialog(self,
                                         f"The Object bundle name already exists at path: \n{folderpath}",
                                         "Do you want to replace it? (All files in the existing bundle will be deleted!)")
            result = msgbox.exec()
            if result == QMessageBox.StandardButton.Yes:
                for fname in os.listdir(folderpath):
                    path = os.path.join(folderpath, fname)
                    os.remove(path)
                self.accept()
        else:
            self.accept()

    def deny(self):
        self.reject()


class DeleteSettings(QDialog):
    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle("Delete Objects")
        self.delete_passengers = QtWidgets.QCheckBox(self, text="Delete Passengers")
        self.delete_mpscript = QtWidgets.QCheckBox(self, text="Delete Script")
        self.delete_objects_of_base = QtWidgets.QCheckBox(self, text="Delete Object's Base And Other Instances Of Object")
        self.remove_initialisation_entry = QtWidgets.QCheckBox(self, text="Remove From EntityInitialise")

        self.text = QtWidgets.QLabel("This will delete the selected objects and also remove the dependencies and resources if those aren't used by other objects. If object bases are selected, all instances of the object base will also be deleted.")
        self.text.setWordWrap(True)
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.delete_passengers)
        self.layout.addWidget(self.delete_mpscript)
        self.layout.addWidget(self.delete_objects_of_base)
        #self.delete_objects_of_base.setToolTip("If only objects are selected, this will also mark the object's bases for deletion.")
        self.layout.addWidget(self.remove_initialisation_entry)
        self.remove_initialisation_entry.setChecked(True)

        self.ok = QtWidgets.QPushButton(self, text="OK")
        self.cancel = QtWidgets.QPushButton(self, text="Cancel")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def confirm(self):
        self.accept()

    def deny(self):
        self.reject()


def get_all_parents(objid, parents, end_ids=None):
    if end_ids is None:
        end_ids = set()

    if objid not in parents:
        return []

    all_parents = []
    to_visit = [x for x in parents[objid]]
    visited = set()

    while to_visit:
        parent = to_visit.pop(0)
        if parent not in visited and parent not in end_ids:
            all_parents.append(parent)
            visited.add(parent)
            if parent in parents:
                to_visit.extend(parents[parent])

    return all_parents


def get_sound_name(obj):
    if obj.type not in ("cAmbientAreaPointSoundBox",
                        "cAmbientAreaPointSoundSphere"):
        return None

    soundbase = obj.mSoundBase
    if soundbase is None:
        soundbase = obj.mLoopingSoundBase
        if soundbase is None:
            return None

    sound_name = None
    for sample in soundbase.mSample:
        if sample is not None:
            sound_name = sample.mName
            break

    return sound_name


class Plugin(object):
    def __init__(self):
        self.name = "Object Export/Import"
        self.actions = [("Quick Export", self.exportobject),
                        ("Mass Export", self.export_all_level_objects),
                        ("Quick Import", self.importobject),
                        ("Remove Objects and Assets", self.remove_selected_object),
                        ("Delete Loose Textures", self.select_loose_assets)]
        print("I have been initialized")
        self.last_category = None
        
    def after_load(self, editor):
        self.last_category = None

    def select_loose_assets(self, editor: "bw_editor.LevelEditor"):
        texture_lookup = {}
        mesh_lookup = {}
        parent = {}

        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cTextureResource":
                texture_lookup[obj.mName.lower()] = obj

        terrain = editor.level_view.bwterrain
        for mat in terrain.materials:
            for tex in (mat.mat1, mat.mat2):
                obj = texture_lookup[tex]
                if obj.id not in parent:
                    parent[obj.id] = ["Terrain"]

        for objid, obj in editor.level_file.objects.items():
            for ref in obj.references:
                if ref.id not in parent:
                    parent[ref.id] = []

                parent[ref.id].append(obj.id)

            if obj.type == "cNodeHierarchyResource":
                mesh_lookup[obj.mName.lower()] = obj
                textures = editor.level_view.bwmodelhandler.models[obj.mName].all_textures
                for texname in textures:
                    texobj = texture_lookup.get(texname.lower(), None)
                    if texobj is not None:
                        if texobj.id not in parent:
                            parent[texobj.id] = []

                        parent[texobj.id].append(obj.id)

            if obj.type == "cTequilaEffectResource":
                resource = editor.file_menu.resource_archive.get_resource(b"FEQT", obj.mName)
                effects_file = io.StringIO(str(resource.data, encoding="ascii"))
                for line in effects_file:
                    line = line.strip()
                    result = line.split(" ", maxsplit=2)
                    if len(result) == 2:
                        command, arg = result
                        arg: str
                        if command == "Texture":
                            texname = arg.removesuffix(".ace")
                            texobj = texture_lookup.get(texname.lower())
                            if texobj is not None:
                                if texobj.id not in parent:
                                    parent[texobj.id] = []

                                parent[texobj.id].append(obj.id)
                            else:
                                print("Warning: Special Effect", obj.mName, "({})".format(obj.id), "references non-existing texture", texname)

                        elif command == "Mesh":
                            modelname, _ = arg.rsplit(".", maxsplit=2)
                            modelobj = mesh_lookup.get(modelname.lower())
                            if modelobj is not None:
                                if modelobj.id not in parent:
                                    parent[modelobj.id] = []

                                parent[modelobj.id].append(obj.id)
                            else:
                                print("Warning: Special Effect", obj.mName, "({})".format(obj.id), "references non-existing model", modelname)
        print("Listing Orphaned Textures...")
        selected = []
        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cTextureResource" and (obj.id not in parent or not parent[obj.id]):
                print(obj.type, obj.name)
                selected.append(obj)
        print("done...")

        editor.level_view.selected = []
        editor.level_view.selected_positions = []
        editor.level_view.selected_rotations = []

        for obj in selected:
            editor.level_view.selected.append(obj)
            mtx = obj.getmatrix()
            if mtx is not None:
                editor.level_view.selected_positions.append(mtx)

        editor.update_3d()
        editor.level_view.do_redraw(forceselected=True)
        editor.level_view.select_update.emit()

        result = open_yesno_box(f"Selected {len(selected)} texture(s). Check console for which textures were selected.", "Do you want to delete them?")
        if result:
            self.remove_selected_object(editor)


    def remove_selected_object(self, editor: "bw_editor.LevelEditor"):
        deleted = set()
        parent = {}

        texture_lookup = {}
        mesh_lookup = {}
        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cTextureResource":
                texture_lookup[obj.mName.lower()] = obj

        for objid, obj in editor.level_file.objects.items():
            for ref in obj.references:
                if ref.id not in parent:
                    parent[ref.id] = []

                parent[ref.id].append(obj.id)

            if obj.type == "cNodeHierarchyResource":
                mesh_lookup[obj.mName.lower()] = obj
                textures = editor.level_view.bwmodelhandler.models[obj.mName].all_textures
                for texname in textures:
                    texobj = texture_lookup.get(texname.lower(), None)
                    if texobj is not None:
                        if texobj.id not in parent:
                            parent[texobj.id] = []

                        parent[texobj.id].append(obj.id)

            if obj.type == "cTequilaEffectResource":
                resource = editor.file_menu.resource_archive.get_resource(b"FEQT", obj.mName)
                effects_file = io.StringIO(str(resource.data, encoding="ascii"))
                for line in effects_file:
                    line = line.strip()
                    result = line.split(" ", maxsplit=2)
                    if len(result) == 2:
                        command, arg = result
                        arg: str
                        if command == "Texture":
                            texname = arg.removesuffix(".ace")
                            texobj = texture_lookup.get(texname.lower())
                            if texobj is not None:
                                if texobj.id not in parent:
                                    parent[texobj.id] = []

                                parent[texobj.id].append(obj.id)
                            else:
                                print("Warning: Special Effect", obj.mName,"references non-existing texture", texname)

                        elif command == "Mesh":
                            modelname, _ = arg.rsplit(".", maxsplit=2)
                            modelobj = mesh_lookup.get(modelname.lower())
                            if modelobj is not None:
                                if modelobj.id not in parent:
                                    parent[modelobj.id] = []

                                parent[modelobj.id].append(obj.id)
                            else:
                                print("Warning: Special Effect", obj.mName,"references non-existing model", modelname)


        dialog = DeleteSettings()
        a = dialog.exec()
        if not a:
            return

        skip = []
        if not dialog.delete_passengers.isChecked():
            skip.append("mPassenger")

        if not dialog.delete_mpscript.isChecked():
            skip.append("mpScript")

        deletion_candidates = []
        deletion_candidates.extend(editor.level_view.selected)

        if dialog.delete_objects_of_base.isChecked():
            for obj in deletion_candidates:
                if hasattr(obj, "mBase") and obj.mBase is not None:
                    deletion_candidates.append(obj.mBase)

        bases = set()
        for obj in deletion_candidates:
            bases.add(obj.id)

        for objid, obj in editor.level_file.objects.items():
            if hasattr(obj, "mBase") and obj.mBase is not None:
                if obj.mBase.id in bases:
                    deletion_candidates.append(obj)

        extended_set = []
        extended_set.extend(editor.level_view.selected)
        if dialog.delete_passengers.isChecked():
            for obj in deletion_candidates:
                if hasattr(obj, "mPassenger"):
                    for passenger in obj.mPassenger:
                        if passenger is not None:
                            extended_set.append(passenger)

        for obj in extended_set:
            deleted.add(obj.id)
            for obj_dep in obj.get_dependencies(skip=skip):
                if obj_dep not in deletion_candidates:
                    deletion_candidates.append(obj_dep)

        for candidate in deletion_candidates:
            if candidate.id in deleted:
                pass  # Already guaranteed to be deleted
            else:
                parents = parent.get(candidate.id, None)
                if parents is not None:
                    to_be_deleted = True
                    for parentid in get_all_parents(candidate.id, parent, deleted):
                        obj = editor.level_file.objects[parentid]
                        if obj not in deletion_candidates:
                            to_be_deleted = False
                    if to_be_deleted:
                        deleted.add(candidate.id)
                else:
                    deleted.add(candidate.id)



        to_be_deleted = []
        res = editor.file_menu.resource_archive
        for objid in deleted:
            obj = editor.level_file.objects[objid]
            to_be_deleted.append(obj)

            if obj.type == "cAnimationResource":
                resource = res.get_resource(b"MINA", obj.mName)
            elif obj.type == "cTequilaEffectResource":
                resource = res.get_resource(b"FEQT", obj.mName)
            elif obj.type == "cNodeHierarchyResource":
                resource = res.get_resource(b"LDOM", obj.mName)
            elif obj.type == "cGameScriptResource":
                resource = res.get_script(obj.mName)
            elif obj.type == "sSampleResource":
                resource = res.get_resource(b"HPSD", obj.mName)
            elif obj.type == "cTextureResource":
                resource = res.get_resource(b"DXTG", obj.mName)
                if resource is None:
                    resource = res.get_resource(b"TXET", obj.mName)


        lua_deletions, resources = 0, 0

        if dialog.remove_initialisation_entry:
            for objid in deleted:
                if objid in editor.lua_workbench.entityinit.reflection_ids:
                    print("deleting entityinit entry for", objid)
                    editor.lua_workbench.entityinit.delete_name(objid)
                    lua_deletions += 1
            editor.lua_workbench.write_entity_initialization()


        for obj in to_be_deleted:
            resource = None
            if obj.type == "cAnimationResource":
                resource = res.get_resource(b"MINA", obj.mName)
            elif obj.type == "cTequilaEffectResource":
                resource = res.get_resource(b"FEQT", obj.mName)
            elif obj.type == "cNodeHierarchyResource":
                resource = res.get_resource(b"LDOM", obj.mName)
            elif obj.type == "cGameScriptResource":
                resource = res.get_script(obj.mName)
            elif obj.type == "sSampleResource":
                resource = res.get_resource(b"HPSD", obj.mName)
            elif obj.type == "cTextureResource":
                resource = res.get_resource(b"DXTG", obj.mName)
                if resource is None:
                    resource = res.get_resource(b"TXET", obj.mName)

            if resource is not None:
                pass
                print("deleting resource", resource)
                res.delete_resource(resource)
                resources += 1
        for obj in to_be_deleted:
            print("deleting", obj.name)
        editor.delete_objects(to_be_deleted)
        editor.set_has_unsaved_changes(True)
        open_message_dialog("Operation successful!",
                            f"Removed {len(to_be_deleted)} object(s), {resources} resource(s) and {lua_deletions} EntityInitialise entries", None)

    def initiate_object_folder(self, editor):
        try:
            os.mkdir(
                os.path.join(
                    editor.get_editor_folder(),
                    "battalion_objects")
            )
        except:
            pass

        try:
            os.mkdir(
                os.path.join(
                    editor.get_editor_folder(),
                    "battalion_objects",
                    "bw1")
            )
        except:
            pass

        try:
            os.mkdir(
                os.path.join(
                    editor.get_editor_folder(),
                    "battalion_objects",
                    "bw2")
            )
        except:
            pass

    def exportobject(self, editor: "bw_editor.LevelEditor"):
        self.initiate_object_folder(editor)

        if editor.level_file.bw2:
            game = "bw2"
        else:
            game = "bw1"

        basepath = os.path.join(
            editor.get_editor_folder(),
            "battalion_objects",
            game)

        dialog = ExportSettings(basepath)
        dialog.fill_category(basepath)
        dialog.set_current_category(self.last_category)
        a = dialog.exec()
        self.last_category = dialog.category_widget.widget.get_category()
        if not a:
            return

        include_passenger = dialog.include_passengers.isChecked()
        include_mpscript = False #dialog.include_mpscript.isChecked()
        reset_instance_flags = dialog.clear_instance_flags.isChecked()
        include_startwaypoint = dialog.include_startwaypoint.isChecked()
        bundle_name = dialog.get_name()
        bundle_path = dialog.bundle_path  # os.path.join(basepath, bundle_name)

        selected = editor.level_view.selected

        try:
            self.export_objects(selected,
                                editor,
                                include_passenger,
                                include_mpscript,
                                reset_instance_flags,
                                include_startwaypoint,
                                bundle_path)
        except Exception as err:
            traceback.print_exc()
            errormsg = (f"An error appeared during object export: \n"
                        f"{str(err)}\n"
                        f"Check console log for more details.\nThe exported object '{bundle_name}' might be incomplete.")
            open_error_dialog(errormsg, None)

    def export_all_level_objects(self, editor: "bw_editor.LevelEditor"):
        self.initiate_object_folder(editor)

        if editor.level_file.bw2:
            game = "bw2"
        else:
            game = "bw1"

        basepath = os.path.join(
            editor.get_editor_folder(),
            "battalion_objects",
            game)

        level_name = os.path.basename(editor.pathsconfig["xml"]).removesuffix(".xml")
        dialog = ExportSettingsFullLevel(basepath, level_name)

        a = dialog.exec()
        if not a:
            return

        level_folder = os.path.join(basepath, level_name)
        level_name = dialog.get_level_name()
        try:
            os.mkdir(level_folder)
        except FileExistsError:
            print(level_folder, "already exists")

        include_passenger = dialog.include_passengers.isChecked()
        reset_instance_flags = dialog.clear_instance_flags.isChecked()

        categories = {
            "cAirVehicle": "Air Vehicles",
            "cGroundVehicle": "Ground Vehicles",
            "cTroop": "Troops",
            "cWaterVehicle": "Water Vehicles",
            "cBuilding": "Buildings",
            "cCapturePoint": "Capture Points",
            "cDestroyableObject": "Environment Objects",
            "cSceneryCluster": "Scenery Objects",
            "cMorphingBuilding": "Morphing Buildings",
            "cAmbientAreaPointSoundBox": "Environment Sounds",
            "cAmbientAreaPointSoundSphere": "Environment Sounds",
        }

        total_work_objects = set()
        for objid, object in editor.file_menu.level_data.objects_with_positions.items():
            if object.type in categories:
                if object.type in (
                        "cMorphingBuilding",
                        "cAmbientAreaPointSoundBox",
                        "cAmbientAreaPointSoundSphere"):
                    represent_id = object.id
                else:
                    represent_id = object.mBase.id

                total_work_objects.add(represent_id)


        total = len(total_work_objects)
        object_represented = []

        loading_bar = LoadingBar(editor)
        loading_bar.setWindowTitle("Exporting...")
        loading_bar.show()

        failed_export = False

        i = 0
        for objid, object in editor.file_menu.level_data.objects_with_positions.items():
            if object.type in categories:
                category_folder = os.path.join(level_folder,
                                               categories[object.type])

                try:
                    os.mkdir(category_folder)
                except FileExistsError:
                    pass

                if object.type in (
                        "cMorphingBuilding",
                        "cAmbientAreaPointSoundBox",
                        "cAmbientAreaPointSoundSphere"):
                    represent_id = object.id
                else:
                    represent_id = object.mBase.id

                if represent_id in object_represented:
                    continue  # Object has already been represented

                name = ""
                allegiance = object.faction
                if allegiance is not None:
                    name += allegiance + "_"

                if object.modelname is not None:
                    name += object.modelname + "_" + object.id
                elif object.type in ("cAmbientAreaPointSoundBox", "cAmbientAreaPointSoundSphere"):
                    sound_name = get_sound_name(object)
                    if sound_name is not None:
                        name += sound_name + "_" + object.id
                    else:
                        name += object.type + "_" + object.id
                else:
                    name += object.type + "_" + object.id

                print("exporting", object.name)

                try:
                    self.export_objects(
                        [object],
                        editor,
                        include_passenger,
                        False,
                        reset_instance_flags,
                        False,
                        os.path.join(category_folder, name),
                        showinfo=False
                    )
                except Exception as err:
                    print("Error on object", object.name)

                    traceback.print_exc()

                    failed_export = True

                    msgbox = YesNoQuestionDialog(editor,
                        f"Error appeared during export of {object.name}.\n{str(err)}",
                             "Object might be incomplete. Do you want to continue export?")
                    if msgbox.exec() != QMessageBox.StandardButton.Yes:
                        loading_bar.force_close()
                        break

                loading_bar.progress = (i/total)
                QApplication.processEvents()
                object_represented.append(represent_id)
                i += 1

        loading_bar.force_close()
        instructiontext = "Some objects weren't exported correctly." if failed_export else ""
        open_message_dialog(f"Done! {i} object(s) exported to {level_name}.", instructiontext=instructiontext)

    def export_objects(self,
                       selected,
                       editor,
                       include_passenger,
                       include_mpscript,
                       reset_instance_flags,
                       include_startwaypoint,
                       bundle_path,
                       showinfo=True):

            print(include_passenger, include_mpscript)
            skip = []
            if not include_passenger:
                skip.append("mPassenger")
            if not include_mpscript:
                skip.append("mpScript")
            if not include_startwaypoint:
                skip.append("mStartWaypoint")

            print("Skipping...", skip)
            export = BattalionLevelFile()
            to_be_exported = []
            selected_ids = []

            script_stuff_skipped = 0

            for obj in selected:
                obj: BattalionObject
                if obj.type in ("cGameScriptResource", "cGlobalScriptEntity", "cInitialisationScriptEntity"):
                    script_stuff_skipped += 1
                    continue

                for dep in obj.get_dependencies(skip=skip):
                    if dep not in to_be_exported:
                        to_be_exported.append(dep)

                if obj not in to_be_exported:
                    to_be_exported.append(obj)
                    selected_ids.append(obj.id)

            if len(selected) == script_stuff_skipped:
                open_error_dialog("Exporting Lua scripts is not supported!", None)
                return

            for obj in to_be_exported:
                obj.update_xml()
                export.add_object_new(obj)

            texture_lookup = {}
            mesh_lookup = {}
            destroy_lookup = {}
            for objid, obj in editor.level_file.objects.items():
                if obj.type == "cTextureResource":
                    texture_lookup[obj.mName.lower()] = obj
                elif obj.type == "cNodeHierarchyResource":
                    mesh_lookup[obj.mName.lower()] = obj
                elif obj.type == "cDestroyableObject":
                    if obj.mBase is not None and obj.mBase.Model is not None:
                        modelname = obj.mBase.Model.mName
                        destroy_lookup[modelname] = obj

            additional_meshes = []

            # Scan special effects for texture and mesh references which
            # we will add to the list of objects/assets to be exported
            for obj in to_be_exported:
                if obj.type == "cTequilaEffectResource":
                    resource = editor.file_menu.resource_archive.get_resource(b"FEQT", obj.mName)
                    effects_file = io.StringIO(str(resource.data, encoding="ascii"))
                    for line in effects_file:
                        line = line.strip()
                        result = line.split(" ", maxsplit=2)
                        if len(result) == 2:
                            command, arg = result
                            arg: str
                            if command == "Texture":
                                texname = arg.removesuffix(".ace")
                                texobj = texture_lookup.get(texname.lower())
                                if texobj is not None:
                                    if texobj.id not in export.objects:
                                        export.add_object_new(texobj)
                                else:
                                    print("Warning: Special Effect", obj.mName,"references non-existing texture", texname)

                            elif command == "Mesh":
                                modelname, _ = arg.rsplit(".", maxsplit=2)
                                modelobj = mesh_lookup.get(modelname.lower())
                                if modelobj is not None:
                                    if modelobj not in to_be_exported and modelobj.id not in export.objects:
                                        additional_meshes.append(modelobj)
                                        export.add_object_new(modelobj)

                                        # Add in the place holder destroyable objects
                                        destroy_obj = destroy_lookup[modelname]
                                        if destroy_obj not in to_be_exported:
                                            export.add_object_new(destroy_obj)
                                            selected_ids.append(destroy_obj.id)

                                        for dep in destroy_obj.get_dependencies(skip=skip):
                                            if dep not in to_be_exported:
                                                export.add_object_new(dep)

                                else:
                                    print("Warning: Special Effect", obj.mName,"references non-existing mesh", modelname)

            to_be_exported.extend(additional_meshes)

            additional_textures = []
            for obj in to_be_exported:
                if obj.type == "cNodeHierarchyResource":
                    modelname = obj.mName

                    textures = editor.level_view.bwmodelhandler.models[modelname].all_textures
                    for texname in textures:
                        if texname.lower() in texture_lookup:
                            texobj = texture_lookup[texname.lower()]
                            if texobj.id not in export.objects:
                                export.add_object_new(texobj)
                        else:
                            texresource = editor.file_menu.resource_archive.textures.get_texture(texname)
                            if texresource is not None:
                                print("Texture", texname, "is in res archive but not in xml! Recreating TextureResource.")
                                xmltext = f"""
                                <Object type="cTextureResource" id="550000000">
                                    <Attribute name="mName" type="cFxString8" elements="1">
                                        <Item>PLACEHOLDER</Item>
                                    </Attribute>
                                </Object>
                                """
                                texobj = BattalionObject.create_from_text(xmltext, editor.level_file, editor.preload_file)
                                texobj.choose_unique_id(export, editor.preload_file)
                                texobj.mName = texresource.name
                                texobj.update_xml()

                                export.add_object_new(texobj)


            # Doing a re-export to have a new set of objects we can modify without affecting
            # the objects in the editor
            tmp = BytesIO()
            export.write(tmp)
            tmp.seek(0)

            re_export = BattalionLevelFile(tmp)

            for objid, obj in re_export.objects.items():
                if obj.id in selected_ids:
                    obj._node.attrib["isroot"] = "1"
                else:
                    if "isroot" in obj._node.attrib:
                        del obj._node.attrib["isroot"]

                if not include_passenger:
                    if hasattr(obj, "mPassenger"):
                        print("skipping passenger", obj.name, obj.mPassenger)
                        passengernode = obj._node.find("Pointer[@name='mPassenger']")
                        for node in passengernode:
                            node.text = "0"

                        for i in range(len(obj.mPassenger)):
                            print("skipping passenger", obj.name, obj.mPassenger[i])
                            obj.mPassenger[i] = None

                if not include_startwaypoint:
                    if hasattr(obj, "mStartWaypoint"):
                        noderesults = obj._node.find("Pointer[@name='mStartWaypoint']")
                        for node in noderesults:
                            node.text = "0"

                        obj.mStartWaypoint = None

                if not include_mpscript:
                    if hasattr(obj, "mpScript"):
                        scriptnode = obj._node.find("Resource[@name='mpScript']")
                        for node in scriptnode:
                            node.text = "0"

                        obj.mpScript = None

                if reset_instance_flags:
                    if hasattr(obj, "mUnitInstanceFlags"):
                        obj.mUnitInstanceFlags = 0

            re_export.resolve_pointers(other=None)
            for objid, obj in re_export.objects.items():
                obj.update_xml()

            try:
                os.mkdir(bundle_path)
            except:
                pass

            with open(os.path.join(bundle_path, "bundle.xml"), "wb") as f:
                re_export.write(f)

            base = os.path.dirname(editor.file_menu.current_path)
            res = editor.file_menu.resource_archive

            resource_count = 0

            for objid, obj in re_export.objects.items():
                resource = False
                respath = None

                if obj.type == "cAnimationResource":
                    resource = res.get_resource(b"MINA", obj.mName)
                    respath = os.path.join(bundle_path, "Animations")
                elif obj.type == "cTequilaEffectResource":
                    resource = res.get_resource(b"FEQT", obj.mName)
                    respath = os.path.join(bundle_path, "SpecialEffects")
                elif obj.type == "cNodeHierarchyResource":
                    resource = res.get_resource(b"LDOM", obj.mName)
                    respath = os.path.join(bundle_path, "Models")
                elif obj.type == "cGameScriptResource":
                    resource = res.get_resource(b"PRCS", obj.mName)
                    respath = os.path.join(bundle_path, "Scripts")
                elif obj.type == "sSampleResource":
                    resource = res.get_resource(b"HPSD", obj.mName)
                    respath = os.path.join(bundle_path, "Sounds")
                elif obj.type == "cTextureResource":
                    resource = res.get_resource(b"DXTG", obj.mName)
                    if resource is None:
                        resource = res.get_resource(b"TXET", obj.mName)

                    respath = os.path.join(bundle_path, "Textures")

                if resource is not False:
                    print(obj.type, obj.mName)
                    resource_count += 1
                    Path(respath).mkdir(parents=True, exist_ok=True)
                    print(respath)
                    resource.dump_to_directory(respath)
                    
            try:
                preview = UnitViewer.screenshot_objects(selected, editor)
                preview.save(os.path.join(bundle_path, "preview.png"))
            except Exception as err:
                traceback.print_exc()
                open_error_dialog(f"Wasn't able to create a preview render: \n{str(err)}\nCheck console log for more details.", None)

            if showinfo:
                message = f"{len(re_export.objects)} XML object(s) and {resource_count} resource(s) have been exported for '{os.path.basename(bundle_path)}'!"
                if script_stuff_skipped > 0:
                    message += f"{script_stuff_skipped} script objects have been skipped."
                open_message_dialog(message,
                                    parent=editor)



    def importobject(self, editor: "bw_editor.LevelEditor"):
        self.initiate_object_folder(editor)

        if editor.level_file.bw2:
            game = "bw2"
        else:
            game = "bw1"

        basepath = os.path.join(
            editor.get_editor_folder(),
            "battalion_objects",
            game)

        chosen_path = QtWidgets.QFileDialog.getExistingDirectory(editor, "Choose the Object to Import", directory=basepath)
        if chosen_path:
            self.import_bundle(editor, chosen_path)

    @staticmethod
    def import_bundle(editor: "bw_editor.LevelEditor", bundlepath, go_to_object=True, show_info=True):
        if editor.level_file.bw2:
            game = "bw2"
        else:
            game = "bw1"

        with open(os.path.join(bundlepath, "bundle.xml"), "rb") as f:
            bundle = BattalionLevelFile(f)
        bundlename = os.path.basename(bundlepath)
        bundle.resolve_pointers(None)

        hashed_objects = {}
        for id, obj in editor.level_file.objects.items():
            if obj.type == "cSeatBase":
                # Do not reuse existing seatbases
                continue
            else:
                hash = obj.calc_hash_recursive()
                hashed_objects[hash] = obj

        reference_remap = {}
        for id, obj in bundle.objects.items():
            hash = obj.calc_hash_recursive()
            if hash in hashed_objects:
                print(obj.name, "will be remaped to", hashed_objects[hash].name)
                reference_remap[obj.id] = hashed_objects[hash]

        for id, obj in bundle.objects.items():
            replace_references(obj, reference_remap)

        visited = []
        to_visit = []
        roots = []
        for id, obj in bundle.objects.items():
            if "isroot" in obj._node.attrib:
                del obj._node.attrib["isroot"]
                print("root", obj)
                to_visit.append(obj)
                roots.append(obj)

        while len(to_visit) > 0:
            next = to_visit.pop(0)
            if next not in visited:
                visited.append(next)
            for ref in next.references:
                if ref not in visited:
                    to_visit.append(ref)

        to_add = []
        for id, obj in bundle.objects.items():
            if obj in visited or obj.type == "cTextureResource":
                to_add.append(obj)

        base = os.path.dirname(editor.file_menu.current_path)
        respath = os.path.join(base, editor.file_menu.level_paths.resourcepath)
        res = editor.file_menu.resource_archive

        print("We gonna add:")
        already_exist_count = 0
        to_be_added_count = 0
        resources_count = 0
        resources_replaced_count = 0

        files = CaseInsensitiveDict()

        for dirpath, dirnames, filenames in os.walk(bundlepath):
            for fname in filenames:
                files[fname] = os.path.join(dirpath, fname)

        update_models = []
        update_textures = []
        objects_actually_added = []

        for obj in to_add:
            assert not obj.is_preload(), "Preload Object Import not supported"

            if obj.calc_hash_recursive() in hashed_objects:
                print(obj.name, "has already been added")

                resource = None
                if obj.type == "cAnimationResource":
                    resource = bwarchivelib.Animation.from_filepath(files[obj.mName + ".anim"])
                elif obj.type == "cTequilaEffectResource":
                    resource = bwarchivelib.Effect.from_filepath(files[obj.mName + ".txt"])
                elif obj.type == "cNodeHierarchyResource":
                    resource = bwarchivelib.Model.from_filepath(files[obj.mName + ".modl"])
                    update_models.append(obj.mName)
                elif obj.type == "cGameScriptResource":
                    resource = bwarchivelib.LuaScript.from_filepath(files[obj.mName + ".luap"])
                elif obj.type == "sSampleResource":
                    resource = bwarchivelib.Sound.from_filepath(files[obj.mName + ".adp"])
                elif obj.type == "cTextureResource":
                    if game == "bw2":
                        resource = bwarchivelib.TextureBW2.from_filepath(files[obj.mName + ".texture"])
                    else:
                        resource = bwarchivelib.TextureBW1.from_filepath(files[obj.mName + ".texture"])
                    update_textures.append(obj.mName)

                if resource is not None:
                    resources_replaced_count += 1

                    if isinstance(resource, bwarchivelib.LuaScript):
                        res.delete_script(resource.name)
                        res.add_script(resource)
                    else:
                        existing_res = res.get_resource(resource.secname, resource.name)
                        if existing_res is not None:
                            res.delete_resource(existing_res)

                        res.add_resource(resource)

            else:
                print(obj.name, "will be added")
                to_be_added_count += 1
                resource = None
                if obj.type == "cAnimationResource":
                    resource = bwarchivelib.Animation.from_filepath(files[obj.mName+".anim"])
                elif obj.type == "cTequilaEffectResource":
                    resource = bwarchivelib.Effect.from_filepath(files[obj.mName+".txt"])
                elif obj.type == "cNodeHierarchyResource":
                    resource = bwarchivelib.Model.from_filepath(files[obj.mName+".modl"])
                elif obj.type == "cGameScriptResource":
                    resource = bwarchivelib.LuaScript.from_filepath(files[obj.mName+".luap"])
                elif obj.type == "sSampleResource":
                    resource = bwarchivelib.Sound.from_filepath(files[obj.mName+".adp"])
                elif obj.type == "cTextureResource":
                    if game == "bw2":
                        resource = bwarchivelib.TextureBW2.from_filepath(files[obj.mName+".texture"])
                    else:
                        resource = bwarchivelib.TextureBW1.from_filepath(files[obj.mName+".texture"])

                if resource is not None:
                    resources_count += 1
                    if isinstance(resource, bwarchivelib.LuaScript):
                        res.add_script(resource)
                    else:
                        res.add_resource(resource)

                obj.choose_unique_id(editor.level_file, editor.preload_file)
                editor.level_file.add_object_new(obj)
                objects_actually_added.append(obj)

        res.sort_sections()

        editor.set_has_unsaved_changes(True)
        editor.leveldatatreeview.set_objects(editor.level_file, editor.preload_file,
                                            remember_position=True)
        editor.level_view.update_models(res, force_update_models=update_models, force_update_textures=update_textures)


        if go_to_object and to_be_added_count > 0:
            if len(roots) > 0:
                obj = roots[0]
                if obj.getmatrix() is not None:
                    editor.goto_object(obj)

        if len(update_textures) > 0:
            editor.level_view.bwmodelhandler.textures.clear_cache(update_textures)

        editor.level_view.do_redraw(force=True)

        instructions = None
        if to_be_added_count == 0:
            instructions = "Objects from this bundle probably already exist in this level!"

        if resources_replaced_count > 0:
            if instructions is None:
                instructions = ""
            else:
                instructions += "\n"

            instructions += f"{resources_replaced_count} existing resource(s) have been replaced."

        if show_info:
            open_message_dialog(f"{to_be_added_count} new object(s) and {resources_count} new resource(s) added for '{bundlename}'!",
                                instructiontext=instructions,
                                parent=editor)

        return objects_actually_added

    def unload(self):
        print("I have been unloaded")
