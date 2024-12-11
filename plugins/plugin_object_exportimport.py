import os
import gzip
import shutil
import PyQt6.QtWidgets as QtWidgets
from io import BytesIO
from pathlib import Path
from collections import UserDict
import traceback

from PyQt6.QtWidgets import QDialog, QMessageBox
from collections import namedtuple

import lib.lua.bwarchivelib as bwarchivelib
from lib.lua.bwarchivelib import BattalionArchive
from lib.BattalionXMLLib import BattalionLevelFile, BattalionObject
from widgets.editor_widgets import open_error_dialog, open_message_dialog
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


class ExportSettings(QDialog):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.layout = QtWidgets.QVBoxLayout(self)
        self.name_widget = LabeledWidget(self, "Object Bundle name:",
                                         QtWidgets.QLineEdit)
        self.include_passengers = QtWidgets.QCheckBox(self, text="Include Passengers")
        self.include_mpscript = QtWidgets.QCheckBox(self, text="Include MpScript")
        self.clear_instance_flags = QtWidgets.QCheckBox(self, text="Clear Instance Flags")

        self.layout.addWidget(self.name_widget)
        self.layout.addWidget(self.include_passengers)
        self.layout.addWidget(self.include_mpscript)
        self.layout.addWidget(self.clear_instance_flags)

        self.ok = QtWidgets.QPushButton(self, text="OK")
        self.cancel = QtWidgets.QPushButton(self, text="Cancel")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def get_name(self):
        return self.name_widget.widget.text()

    def confirm(self):
        self.name_widget.widget: QtWidgets.QLineEdit
        bundlename = self.name_widget.widget.text()

        if "/" in bundlename or "\\" in bundlename:
            open_error_dialog("Invalid characters in bundle name!", self)
            return

        folderpath = os.path.join(self.path, bundlename)

        if os.path.exists(folderpath):
            msgbox = YesNoQuestionDialog(self,
                                         "The Object bundle name already exists.",
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


class Plugin(object):
    def __init__(self):
        self.name = "Object Export/Import"
        self.actions = [("Quick Export", self.exportobject),
                        ("Quick Import", self.importobject),
                        ("Remove Objects and Assets", self.remove_selected_object)]
        print("I have been initialized")

    def remove_selected_object(self, editor: "bw_editor.LevelEditor"):
        deleted = set()
        parent = {}

        texture_lookup = {}
        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cTextureResource":
                texture_lookup[obj.mName.lower()] = obj

        for objid, obj in editor.level_file.objects.items():
            for ref in obj.references:
                if ref.id not in parent:
                    parent[ref.id] = []

                parent[ref.id].append(obj.id)

            if obj.type == "cNodeHierarchyResource":
                textures = editor.level_view.bwmodelhandler.models[obj.mName].all_textures
                for texname in textures:
                    texobj = texture_lookup.get(texname.lower(), None)
                    if texobj is not None:
                        if texobj.id not in parent:
                            parent[texobj.id] = []

                        parent[texobj.id].append(obj.id)
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

        for obj in editor.level_view.selected:
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
        a = dialog.exec()
        if not a:
            return

        include_passenger = dialog.include_passengers.isChecked()
        include_mpscript = dialog.include_mpscript.isChecked()
        reset_instance_flags = dialog.clear_instance_flags.isChecked()
        bundle_name = dialog.get_name()

        bundle_path = os.path.join(basepath, bundle_name)
        print(include_passenger, include_mpscript)
        skip = []
        if not include_passenger:
            skip.append("mPassenger")
        if not include_mpscript:
            skip.append("mpScript")

        selected = editor.level_view.selected
        export = BattalionLevelFile()
        to_be_exported = []
        selected_ids = []

        for obj in selected:
            obj: BattalionObject

            for dep in obj.get_dependencies(skip=skip):
                if dep not in to_be_exported:
                    to_be_exported.append(dep)

            if obj not in to_be_exported:
                to_be_exported.append(obj)
                selected_ids.append(obj.id)

        for obj in to_be_exported:
            export.add_object_new(obj)

        texture_lookup = {}
        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cTextureResource":
                texture_lookup[obj.mName.lower()] = obj

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
        respath = os.path.join(base, editor.file_menu.level_paths.resourcepath)
        if respath.endswith(".gz"):
            with gzip.open(respath, "rb") as f:
                res = BattalionArchive.from_file(f)
        else:
            with open(respath, "rb") as f:
                res = BattalionArchive.from_file(f)

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

        open_message_dialog(f"{len(re_export.objects)} XML object(s) and {resource_count} resource(s) have been exported for '{bundle_name}'!",
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
            with open(os.path.join(chosen_path, "bundle.xml"), "rb") as f:
                bundle = BattalionLevelFile(f)
            bundlename = os.path.basename(chosen_path)
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

            for dirpath, dirnames, filenames in os.walk(chosen_path):
                for fname in filenames:
                    files[fname] = os.path.join(dirpath, fname)

            update_models = []
            update_textures = []

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

            res.sort_sections()

            editor.set_has_unsaved_changes(True)
            editor.leveldatatreeview.set_objects(editor.level_file, editor.preload_file,
                                                remember_position=True)
            editor.level_view.update_models(res, force_update_models=update_models, force_update_textures=update_textures)

            if to_be_added_count > 0:
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

            open_message_dialog(f"{to_be_added_count} new object(s) and {resources_count} new resource(s) added for '{bundlename}'!",
                                instructiontext=instructions,
                                parent=editor)

    def unload(self):
        print("I have been unloaded")
