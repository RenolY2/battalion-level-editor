from collections import namedtuple
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class Plugin(object):
    def __init__(self):
        self.name = "Example Plugin"
        self.actions = [("Test", self.testfunc)]
        print("I have been initialized")

    def testfunc(self, editor: "bw_editor.LevelEditor"):
        print("This is a test function")
        print("More")

    def unload(self):
        print("I have been unloaded")
