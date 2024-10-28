import os
from collections import namedtuple
from typing import TYPE_CHECKING


from plugins.plugin_misc_tools import open_yesno_box

if TYPE_CHECKING:
    import bw_editor


class Plugin(object):
    def __init__(self):
        self.name = "Misc Lua Tools"
        self.actions = [("Clear Out Scripts", self.clear_lua),
                        ("Clear EntityInitialise", self.clear_entityinitialise)]
        print("I have been initialized")

    def clear_lua(self, editor: "bw_editor.LevelEditor"):
        yes = open_yesno_box("This will clear all lua scripts and make them do nothing.",
                             "Are you sure?")
        if yes:
            for script in editor.lua_workbench.current_scripts():
                path = os.path.join(editor.lua_workbench.workdir,
                                    script+".lua")

                if script != "EntityInitialise":
                    startline = None
                    with open(path, "r") as f:
                        for line in f:
                            if line.startswith("function"):
                                startline = line
                                break
                    assert startline is not None, "Line that starts with 'function' must exist."
                    with open(path, "w") as f:
                        f.write(startline)
                        f.write("\n\nend")
            print("Cleared Lua Scripts")

    def clear_entityinitialise(self, editor: "bw_editor.LevelEditor"):
        yes = open_yesno_box("This will clear the entire list of defined entity names in EntityInitialise.lua",
                       "Are you sure?")

        if yes:
            editor.lua_workbench.entityinit.reflection_ids = {}
            editor.lua_workbench.write_entity_initialization()
            print("Cleared EntityInitialise.lua")

    def unload(self):
        print("I have been unloaded")
