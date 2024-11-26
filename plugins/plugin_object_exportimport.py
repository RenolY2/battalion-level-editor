import os
import gzip
import shutil
import PyQt6.QtWidgets as QtWidgets
from io import BytesIO


from PyQt6.QtWidgets import QDialog, QMessageBox
from collections import namedtuple

import lib.lua.bwarchivelib as bwarchivelib
from lib.lua.bwarchivelib import BattalionArchive
from lib.BattalionXMLLib import BattalionLevelFile, BattalionObject
from widgets.editor_widgets import open_error_dialog
from plugins.plugin_padding import YesNoQuestionDialog

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


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


class Plugin(object):
    def __init__(self):
        self.name = "Object Export/Import"
        self.actions = [("Quick Export", self.exportobject),
                        ("Quick Import", self.importobject)]
        print("I have been initialized")

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

        for objid, obj in re_export.objects.items():
            resource = False
            if obj.type == "cAnimationResource":
                resource = res.get_resource(b"MINA", obj.mName)
            elif obj.type == "cTequilaEffectResource":
                resource = res.get_resource(b"FEQT", obj.mName)
            elif obj.type == "cNodeHierarchyResource":
                resource = res.get_resource(b"LDOM", obj.mName)
            elif obj.type == "cGameScriptResource":
                resource = res.get_resource(b"PRCS", obj.mName)
            elif obj.type == "sSampleResource":
                resource = res.get_resource(b"HPSD", obj.mName)
            elif obj.type == "cTextureResource":
                resource = res.get_resource(b"DXTG", obj.mName)
                if resource is None:
                    resource = res.get_resource(b"TXET", obj.mName)

            if resource is not False:
                print(obj.type, obj.mName)
                resource.dump_to_directory(bundle_path)

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

            bundle.resolve_pointers(None)

            hashed_objects = {}
            for id, obj in editor.level_file.objects.items():
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
            if respath.endswith(".gz"):
                with gzip.open(respath, "rb") as f:
                    res = BattalionArchive.from_file(f)
            else:
                with open(respath, "rb") as f:
                    res = BattalionArchive.from_file(f)

            print("We gonna add:")
            for obj in to_add:
                assert not obj.is_preload(), "Preload Object Import not supported"

                if obj.calc_hash_recursive() in hashed_objects:
                    print(obj.name, "has already been added")
                else:
                    print(obj.name, "has not been added")
                    resource = None
                    if obj.type == "cAnimationResource":
                        resource = bwarchivelib.Animation.from_filepath(
                                        os.path.join(chosen_path,
                                        obj.mName+".anim"))
                    elif obj.type == "cTequilaEffectResource":
                        resource = bwarchivelib.Effect.from_filepath(
                                         os.path.join(chosen_path,
                                         obj.mName + ".txt"))
                    elif obj.type == "cNodeHierarchyResource":
                        resource = bwarchivelib.Model.from_filepath(
                            os.path.join(chosen_path,
                                         obj.mName + ".modl"))
                    elif obj.type == "cGameScriptResource":
                        resource = bwarchivelib.LuaScript.from_filepath(
                            os.path.join(chosen_path,
                                         obj.mName + ".luap"))
                    elif obj.type == "sSampleResource":
                        resource = bwarchivelib.Sound.from_filepath(
                            os.path.join(chosen_path,
                                         obj.mName + ".adp"))

                    elif obj.type == "cTextureResource":
                        if game == "bw2":
                            resource = bwarchivelib.TextureBW2.from_filepath(
                                        os.path.join(chosen_path,
                                        obj.mName + ".texture"))
                        else:
                            resource = bwarchivelib.TextureBW1.from_filepath(
                                os.path.join(chosen_path,
                                             obj.mName + ".texture"))

                    if resource is not None:
                        if isinstance(resource, bwarchivelib.LuaScript):
                            res.add_script(resource)
                        else:
                            res.add_resource(resource)

                    obj.choose_unique_id(editor.level_file, editor.preload_file)
                    editor.level_file.add_object_new(obj)

            res.sort_sections()
            tmp = BytesIO()
            res.write(tmp)
            tmp.seek(0)
            if respath.endswith(".gz"):
                with gzip.open(respath, "wb") as f:
                    f.write(tmp.getvalue())
            else:
                with open(respath, "wb") as f:
                    f.write(tmp.getvalue())
            editor.set_has_unsaved_changes(True)
            editor.leveldatatreeview.set_objects(editor.level_file, editor.preload_file,
                                                remember_position=True)
            editor.level_view.update_models(res)

            if len(roots) > 0:
                obj = roots[0]
                if obj.getmatrix() is not None:
                    editor.goto_object(obj)

            editor.level_view.do_redraw(force=True)

    def unload(self):
        print("I have been unloaded")
