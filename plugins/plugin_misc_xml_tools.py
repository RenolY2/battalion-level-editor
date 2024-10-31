from collections import namedtuple
from typing import TYPE_CHECKING

import xml.etree.ElementTree as etree

if TYPE_CHECKING:
    import bw_editor


def move_object_to_start(tree, objects):
    for obj in objects:
        assert not obj.deleted

    for i, v in enumerate(objects):
        tree.remove(v._node)
        tree.insert(i, v._node)


class Plugin(object):
    def __init__(self):
        self.name = "Misc XML Tools"
        self.actions = [("Move Selected Objects to Start of XML", self.movetostart),
                        ("Move Selected Objects and Dependencies to Start of XML", self.movetostart_dependencies)]
        print("I have been initialized")

    def movetostart(self, editor: "bw_editor.LevelEditor"):
        print(editor.level_view.selected)
        objs = []
        for obj in editor.level_view.selected:
            if obj in editor.preload_file.objects:
                print("Skipping", obj.name, "because of being a preload object")
            else:
                objs.append(obj)
        print("moving objects", objs)
        move_object_to_start(editor.level_file._root, objs)

    def movetostart_dependencies(self, editor: "bw_editor.LevelEditor"):
        print(editor.level_view.selected)
        objs = []
        for obj in editor.level_view.selected:
            if obj in editor.preload_file.objects:
                print("Skipping", obj.name, "because of being a preload object")
            else:
                if obj not in objs:
                    objs.append(obj)
                for obj in obj.get_dependencies():
                    if obj not in objs:
                        objs.append(obj)
        print(objs)

        print("moving objects", objs)
        move_object_to_start(editor.level_file._root, objs)
        

    def unload(self):
        print("I have been unloaded")
