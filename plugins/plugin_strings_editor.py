from collections import namedtuple
from functools import partial
import os
from importlib import reload
from typing import TYPE_CHECKING
import plugins.strings_editor.bw_strings_editor as strings_editor
from widgets.editor_widgets import open_error_dialog
if TYPE_CHECKING:
    import bw_editor


class Plugin(object):
    def __init__(self):
        self.name = "Strings Editor"
        self.actions = [("Open Strings Editor", self.open_editor),
                        ("Open Level Strings (English)", partial(self.open_editor_language, "English")),
                        ("Open Level Strings (Spanish)", partial(self.open_editor_language, "Spanish")),
                        ("Open Level Strings (French)", partial(self.open_editor_language, "French")),
                        ("Open Level Strings (German)", partial(self.open_editor_language, "German")),
                        ("Open Level Strings (Italian)", partial(self.open_editor_language, "Italian")),
                        ("Open Level Strings (Japanese)", partial(self.open_editor_language, "Japanese")),
                        ("Open Level Strings (British English)", partial(self.open_editor_language, "UK"))]
        self.strings_editor = None

    def open_editor(self, editor: "bw_editor.LevelEditor"):
        if (self.strings_editor is None
                or (self.strings_editor is not None
                    and not self.strings_editor.isVisible())):

            self.strings_editor = strings_editor.StringsEditorMainWindow()
            self.strings_editor.show()

    def open_editor_language(self, language, editor: "bw_editor.LevelEditor"):
        if language not in editor.file_menu.level_paths.stringpaths:
            open_error_dialog(f"Language {language} doesn't exist for this level!", editor)
        else:
            string_file = editor.file_menu.level_paths.stringpaths[language]

            self.open_editor(editor)
            base = editor.file_menu.current_path
            data_path = os.path.dirname(os.path.dirname(base))

            string_path = os.path.join(data_path, "Strings", string_file)
            if not os.path.exists(string_path):
                open_error_dialog(f"String file {string_path} has not been found!", editor)
            else:
                print(string_path)
                self.strings_editor.load_path(string_path)

    def before_save(self, editor):
        if self.strings_editor is not None and self.strings_editor.isVisible():
            self.strings_editor.button_save_strings()

    def unload(self):
        reload(strings_editor)
        del self.strings_editor
        print("I have been unloaded")
