from io import BytesIO
from PyQt6 import QtWidgets, QtGui
from collections import namedtuple

from widgets.editor_widgets import open_error_dialog

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class YesNoQuestionDialog(QtWidgets.QMessageBox):
    def __init__(self, parent, text, instructiontext):
        super().__init__(parent)
        self.setText(text)
        self.setInformativeText(instructiontext)
        self.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        self.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        self.setIcon(QtWidgets.QMessageBox.Icon.Question)
        self.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        self.setWindowTitle("Question")


class MessageDialog(QtWidgets.QMessageBox):
    def __init__(self, parent, text, instructiontext):
        super().__init__(parent)
        self.setText(text)
        self.setInformativeText(instructiontext)
        self.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes)
        self.setIcon(QtWidgets.QMessageBox.Icon.Information)
        self.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        self.setWindowTitle("Information")


class PaddingDialog(QtWidgets.QInputDialog):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setInputMode(QtWidgets.QInputDialog.InputMode.IntInput)
        self.setIntValue(5)
        self.setIntRange(0, 25)
        self.setLabelText("Padding will fill up the XML file up to a specific size.\n"
                          "This can help with testing mods more quickly using Dolphin save states\n"
                          "Enter padding percentage (0 for no padding):")
        self.setWindowTitle(text)


class Plugin(object):
    def __init__(self):
        self.name = "Padding"
        self.actions = [("Set Preload XML Padding", self.pad_preload),
                        ("Set Level XML Padding", self.pad_object),
                        ("Toggle gzip Compression", self.toggle_gzip)]

    def toggle_gzip(self, editor: "bw_editor.LevelEditor", confirm=False):
        if not editor.level_file.bw2:
            open_error_dialog("BW1 does not use gzip compression. No toggling necessary.", editor)
            return

        path = editor.file_menu.level_paths.objectpath
        result = editor.file_menu.level_paths._tree.findall("level/objectfiles")

        text = "Gzip compression for this level is"

        node = result[0]
        print(node[0].attrib["name"])

        decompress = False

        if path.endswith(".gz"):
            path = path.replace(".gz", "")
            text += " enabled."
            actiontext = "Do you want to turn compression off?\n(Will take action on saving!)"
            decompress = True
        else:
            path = path+".gz"
            text += " disabled."
            actiontext = "Do you want to turn compression on?\n(Will take action on saving!)"

        if not confirm:
            msgbox = YesNoQuestionDialog(editor, text, actiontext)

            result = msgbox.exec()
        else:
            result = QtWidgets.QMessageBox.StandardButton.Yes

        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            if decompress:
                editor.file_menu.level_paths.set_uncompressed()
            else:
                editor.file_menu.level_paths.set_compressed()

            editor.set_has_unsaved_changes(True)

    def pad_preload(self, editor: "bw_editor.LevelEditor"):
        inputdialog = PaddingDialog(editor, "Preload XML Padding")

        if inputdialog.exec():
            value = inputdialog.intValue()
            if value == 0:
                editor.file_menu.level_paths.clear_preload_padding()
            else:
                tmp = BytesIO()
                editor.preload_file.write(tmp)
                size = len(tmp.getbuffer())
                padding = int(size*(1+value/100.0))
                editor.file_menu.level_paths.set_preload_padding(padding)
                editor.set_has_unsaved_changes(True)
                print("Padding has been set to", padding, "bytes.")
                msgbox = MessageDialog(editor,
                                       (f"Padding has been set to {padding} bytes.\n"
                                        f"A headroom of {padding-size} bytes over unpadded ({size} bytes)."),
                                       "")
                msgbox.exec()

                if editor.file_menu.level_paths.objectpath.endswith(".gz"):
                    msgbox = YesNoQuestionDialog(editor,
                                                 "Level files are compressed! Padding won't be used.",
                                                 ("Do you want to decompress the level files and use padding? "
                                                  "(Will take action on saving!)"))

                    result = msgbox.exec()
                    if result == QtWidgets.QMessageBox.StandardButton.Yes:
                        self.toggle_gzip(editor, confirm=True)

    def pad_object(self, editor: "bw_editor.LevelEditor"):
        inputdialog = PaddingDialog(editor, "Level XML Padding")

        if inputdialog.exec():
            value = inputdialog.intValue()
            if value == 0:
                editor.file_menu.level_paths.clear_object_padding()
            else:
                tmp = BytesIO()
                editor.level_file.write(tmp)
                size = len(tmp.getbuffer())
                padding = int(size*(1+value/100.0))
                editor.file_menu.level_paths.set_object_padding(padding)
                editor.set_has_unsaved_changes(True)
                print("Padding has been set to", padding, "bytes.")
                msgbox = MessageDialog(editor,
                                       (f"Padding has been set to {padding} bytes.\n"
                                        f"A headroom of {padding-size} bytes over unpadded ({size} bytes)."),
                                       "")
                msgbox.exec()

                print("Padding has been set to", padding, "bytes.")

                if editor.file_menu.level_paths.objectpath.endswith(".gz"):
                    msgbox = YesNoQuestionDialog(editor,
                                                 "Level files are compressed! Padding won't be used.",
                                                 ("Do you want to decompress the level files and use padding? "
                                                  "(Will take action on saving!)"))

                    result = msgbox.exec()
                    if result == QtWidgets.QMessageBox.StandardButton.Yes:
                        self.toggle_gzip(editor, confirm=True)

    def unload(self):
        print("I have been unloaded")
