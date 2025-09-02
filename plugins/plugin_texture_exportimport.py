import io
import os
import traceback

from PyQt6 import QtWidgets
from plugins.bw_texture_conv.bwtex import BW1Texture, BW2Texture, STRTOFORMAT
from collections import namedtuple
from typing import TYPE_CHECKING, cast
from lib.xmltypes.bw1 import Resource
from plugins.plugin_object_exportimport import LabeledWidget
from widgets.editor_widgets import open_error_dialog, open_message_dialog
import lib.lua.bwarchivelib as bwarchivelib
from lib.BattalionXMLLib import BattalionObject

if TYPE_CHECKING:
    import bw_editor


class PathAlreadyExists(QtWidgets.QDialog):
    def __init__(self, path):
        super().__init__()
        self.setWindowTitle("Warning")
        self.path = path
        self.layout = QtWidgets.QVBoxLayout(self)
        self.description = QtWidgets.QLabel(
            f"File {path} already exists.\nDo you want to overwrite it?", self)

        self.overwrite_all_check = QtWidgets.QCheckBox(self, text="Remember for all following conflicts.")

        self.layout.addWidget(self.description)
        self.layout.addWidget(self.overwrite_all_check)

        self.ok = QtWidgets.QPushButton(self, text="Yes")
        self.cancel = QtWidgets.QPushButton(self, text="No")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def get_level_name(self):
        return self.name_widget.widget.text()

    def remember(self):
        return self.overwrite_all_check.isChecked()

    def confirm(self):
        self.accept()

    def deny(self):
        self.reject()

class MultiError(QtWidgets.QDialog):
    def __init__(self, text):
        super().__init__()
        self.setWindowTitle("Warning")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.description = QtWidgets.QLabel(
            text, self)

        self.ignore = QtWidgets.QCheckBox(self, text="Ignore Following Errors")

        self.layout.addWidget(self.description)
        self.layout.addWidget(self.ignore)

        self.ok = QtWidgets.QPushButton(self, text="Yes")
        self.cancel = QtWidgets.QPushButton(self, text="No")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def get_level_name(self):
        return self.name_widget.widget.text()

    def remember(self):
        return self.ignore.isChecked()

    def confirm(self):
        self.accept()

    def deny(self):
        self.reject()


class Plugin(object):
    def __init__(self):
        self.name = "Texture Tool"
        self.actions = [("Export Textures", self.export_texture),
                        ("Import Textures", self.import_texture)]
        print("I have been initialized")

        self.texpath = None
        self.last_chosen_type = None

    def export_texture(self, editor: "bw_editor.LevelEditor"):
        objs = editor.get_selected_objs()

        is_bw1 = editor.file_menu.level_data.is_bw1()

        flatten = []
        textures = set()

        for obj in objs:
            if obj not in flatten:
                flatten.append(obj)

            for dep in obj.get_dependencies():
                if dep not in flatten:
                    flatten.append(dep)

        additional_textures = set()

        for obj in flatten:
            if obj.type == "cTextureResource":
                additional_textures.add(obj.mName.lower())

            if obj.type == "cNodeHierarchyResource":
                textures = editor.level_view.bwmodelhandler.models[obj.mName].all_textures
                for tex in textures:
                    additional_textures.add(tex.lower())

            elif obj.type == "cTequilaEffectResource":
                resource = editor.file_menu.resource_archive.get_resource(b"FEQT", obj.mName)
                if resource is None:
                    continue

                effects_file = io.StringIO(str(resource.data, encoding="ascii"))
                for line in effects_file:
                    line = line.strip()
                    result = line.split(" ", maxsplit=2)
                    if len(result) == 2:
                        command, arg = result
                        arg: str
                        if command == "Texture":
                            texname = arg.removesuffix(".ace")
                            additional_textures.add(texname.lower())

                        elif command == "Mesh":
                            modelname, _ = arg.rsplit(".", maxsplit=2)
                            textures = editor.level_view.bwmodelhandler.models[modelname].all_textures
                            for tex in textures:
                                additional_textures.add(tex.lower())

        chosen_path = QtWidgets.QFileDialog.getExistingDirectory(
            editor,
            "Choose Export Destination",
                    directory=self.texpath)

        if not chosen_path:
            return

        self.texpath = chosen_path

        overwrite = None

        written = 0
        skipped = 0

        for tex in additional_textures:
            resource = editor.file_menu.resource_archive.textures.get_texture(tex)
            data = io.BytesIO()
            resource.dump_to_file(data)
            data.seek(0)

            if is_bw1:
                bwtex = BW1Texture.from_file(data)
            else:
                bwtex = BW2Texture.from_file(data)

            settings = bwtex.header_to_string()
            outname = tex+"."+bwtex.fmt+"."+settings+".png"

            outpath = os.path.join(chosen_path, outname)

            if os.path.exists(outpath):
                dialog = PathAlreadyExists(outname)

                if overwrite is None:
                    result = dialog.exec()
                    if dialog.remember():
                        overwrite = result == True

                    if not result:  # We don't want to overwrite
                        skipped += 1
                        continue
                else:
                    if not overwrite:
                        skipped += 1
                        continue

            bwtex.mipmaps[0].save(outpath)
            written += 1

        open_message_dialog(f"Done!\n{written} texture(s) exported, {skipped} texture(s) skipped.", instructiontext="")

    def import_texture(self, editor: "bw_editor.LevelEditor"):
        filepaths, chosentype = QtWidgets.QFileDialog.getOpenFileNames(
            editor, "Open File",
            self.texpath,
            "Image Files (*.png; *.jpg);;All files (*)",
            self.last_chosen_type)

        update_textures = []
        ignore = False


        if filepaths:
            is_bw1 = editor.file_menu.level_data.is_bw1()

            name_limit = 0x10 if is_bw1 else 0x20

            for filepath in filepaths:
                try:
                    settings = os.path.basename(filepath).split(".")
                    name = settings.pop(0)

                    if len(name) > name_limit:
                        raise RuntimeError(f"Name too long! Please keep texture name below {name_limit} characters.")


                    fmt = None

                    if fmt is None:
                        if len(settings) > 2:
                            fmt = settings.pop(0)
                            if fmt not in STRTOFORMAT:
                                fmt = None
                        else:
                            fmt = None

                    resource = editor.file_menu.resource_archive.textures.get_texture(name)
                    basetex = None

                    if fmt is None and resource is not None:
                        data = io.BytesIO()
                        resource.dump_to_file(data)
                        data.seek(0)

                        if is_bw1:
                            basetex = BW1Texture.from_file(data, no_decode=True)
                        else:
                            basetex = BW2Texture.from_file(data, no_decode=True)

                        fmt = basetex.fmt
                    else:
                        fmt = "DXT1"

                    if len(settings) > 1:
                        gen_mipmap = settings[0].lower() == "mipmap"
                    else:
                        if basetex is not None:
                            gen_mipmap = len(basetex.mipmaps) > 1
                        else:
                            gen_mipmap = False

                    print("Converting to format", fmt)
                    if is_bw1:
                        tex = BW1Texture.from_path(path=filepath, name=name, fmt=fmt, autogenmipmaps=gen_mipmap)
                    else:
                        tex = BW2Texture.from_path(path=filepath, name=name, fmt=fmt, autogenmipmaps=gen_mipmap)

                    if 6 <= len(settings) <= 7:
                        try:
                            tex.header_from_string(".".join(settings))
                        except Exception as err:
                            print(f"Wasn't able to parse texture header settings: {err}")
                            if basetex is not None:
                                baseheader = basetex.header_to_string()
                                tex.header_from_string(baseheader)
                    elif basetex is not None:
                        baseheader = basetex.header_to_string()
                        tex.header_from_string(baseheader)

                    tmp = io.BytesIO()
                    tex.write(tmp)
                    tmp.seek(0)
                    
                    if is_bw1:
                        newresource = bwarchivelib.TextureBW1.from_file_headerless(tmp)
                    else:
                        newresource = bwarchivelib.TextureBW2.from_file_headerless(tmp)

                    if resource is not None:
                        editor.file_menu.resource_archive.delete_resource(resource)
                        editor.file_menu.resource_archive.add_resource(newresource)
                    else:
                        editor.file_menu.resource_archive.add_resource(newresource)
                        xmltext = f"""
                                <Object type="cTextureResource" id="550000000">
                                    <Attribute name="mName" type="cFxString8" elements="1">
                                        <Item>PLACEHOLDER</Item>
                                    </Attribute>
                                </Object>
                                """
                        texobj = BattalionObject.create_from_text(xmltext, editor.level_file, editor.preload_file)
                        texobj.choose_unique_id(editor.level_file, editor.preload_file)
                        texobj.mName = newresource.name
                        texobj.update_xml()

                        editor.level_file.add_object_new(texobj)
                    update_textures.append(newresource.name)
                except Exception as err:
                    traceback.print_exc()
                    print(f"Error appeared on {name}:\n{str(err)}")

                    if not ignore:
                        dialog = MultiError(
                            f"Error appeared on {name}:\n{str(err)}\n\nDo you want to continue?")
                        result = dialog.exec()
                        if result:
                            if dialog.remember():
                                ignore = True
                        else:
                            break

        if len(update_textures) > 0:
            editor.level_view.bwmodelhandler.textures.clear_cache(update_textures)
            editor.level_view.update_models(
                editor.file_menu.resource_archive,
                [],
                update_textures
            )

            editor.set_has_unsaved_changes(True)
            editor.leveldatatreeview.set_objects(editor.level_file, editor.preload_file,
                                                 remember_position=True)

            open_message_dialog(f"Done!", instructiontext="")

    def unload(self):
        print("I have been unloaded")
