import numpy
import PyQt6.QtWidgets as QtWidgets
from plugins.plugin_pfd_edit import PFDPluginButton
from collections import namedtuple
from typing import TYPE_CHECKING
from lib.render.model_renderingv2 import QuadDrawing, LineDrawing
from OpenGL.GL import *
from math import cos, sin, radians

if TYPE_CHECKING:
    import bw_editor
    import bw_widgets


class Matrix2x2(object):
    def __init__(self, a1, a2, b1, b2):
        self.mtx = numpy.array([(a1, a2, 0),
                                (b1, b2, 0),
                                (0, 0, 1)])


def matrix(a1, a2, b1, b2):
    return numpy.array([(a1, a2, 0),
                        (b1, b2, 0),
                        (0, 0, 1)])


def rotate(angle):
    return matrix(cos(angle), -sin(angle),
                     sin(angle), cos(angle))


def translate(x, y):
    mtx = matrix(1, 0, 0, 1)
    mtx[0][2] = x
    mtx[1][2] = y

    return mtx


def scale(x, y):
    return matrix(x, 0,
                0, y)


def get_pos(obj):
    if hasattr(obj, "mpPos"):
        if obj.mpPos is None:
            return 0, 0
        elif obj.mpPos.type == "cGUIVectorVector":
            return obj.mpPos.msVector.x, obj.mpPos.msVector.z
        else:
            return 0, 0
    else:
        return None, None


def get_rotation(obj):
    if hasattr(obj, "mpAngle"):
        if obj.mpAngle is None:
            return 0
        elif obj.mpAngle.type == "cGUINumberNumber":
            return obj.mpAngle.msNumber
        else:
            return 0
    else:
        return None


def get_scale(obj):
    if hasattr(obj, "mpScale"):
        if obj.mpScale is None:
            return 1, 1
        elif obj.mpScale.type == "cGUIScaleVector":
            return obj.mpScale.msVector.x, obj.mpScale.msVector.z
        else:
            return 1, 1
    else:
        return None, None


def recalculate_parents(obj):
    if obj._parent is None:
        return matrix(1, 0, 0, 1)
    if obj._parentmtx is None:
        obj._parentmtx = recalculate_parents(obj._parent)
    return obj._parentmtx @ obj._currmtx


def depth_traverse(obj, out, depth=0):
    if obj not in out:
        out.append((obj, depth))

    for child in obj._children:
        if child in out:
            break

        depth_traverse(child, out, depth+1)


def get_root(obj, visited=None):
    if visited is None:
        visited = set()

    if id(obj) in visited:
        return []

    visited.add(id(obj))

    if len(obj._parents) == 0:
        return [obj]
    else:
        parents = []
        for parent in obj._parents:
            for p in get_root(parent):
                if p not in parents:
                    parents.append(p)
        return parents


class Plugin(object):
    def __init__(self):
        self.name = "GUI Visualizer"
        self.actions = []
        self.guimode = False
        self.lines = LineDrawing()
        self.curr = 0
        self.calc_roots = []

    def testfunc(self, editor: "bw_editor.LevelEditor"):
        print("This is a test function")
        print("More")

    def plugin_init(self, editor):
        for obj in editor.file_menu.level_data.objects.values():
            if "cGUIPage" in obj.type:
                self.guimode = True

    def after_load(self, editor: "bw_editor.LevelEditor"):
        self.guimode = False

        for obj in editor.file_menu.level_data.objects.values():
            if "cGUIPage" in obj.type:
                self.guimode = True

    def unload(self):
        pass

    def render_gui(self, obj, selected, visited=None, mtx=None, depth=0):
        if visited is None:
            visited = set()

        if id(obj) in visited:
            return

        visited.add(id(obj))
        currmtx = obj._currmtx
        if mtx is not None:
            currmtx = mtx @ currmtx

        if hasattr(obj, "mpSize") and obj.mpSize is not None:
            if obj.mpSize.type == "cGUIVectorVector":
                size_x = obj.mpSize.msVector.x
                size_y = obj.mpSize.msVector.z
            else:
                size_x = 10
                size_y = 10

        else:
            size_x = 10
            size_y = 10

        points = [(0, 0, 1), (size_x, 0, 1), (size_x, size_y, 1), (0, size_y, 1)]
        transformed = [currmtx@p for p in points]

        if obj in selected:
            col = (1.0, 0.0, 0.0)
        else:
            val = 1.0 - (depth / 4)
            if val < 0:
                val = 0
            col = (val, val, val)

        for i in range(4):
            p1, p2, _ = transformed[i]
            if i == 0:
                last = 3
            else:
                last = i - 1

            p1_2, p2_2, _ = transformed[last]

            self.lines.add_line((p1, 100, p2), (p1_2, 100, p2_2), col)

        for child in obj._children:
            self.render_gui(child, selected, visited, currmtx, depth+1)

    def render_post(self, viewer: "bw_widgets.BolMapViewer"):
        if self.guimode:
            self.lines.reset_lines()

            for obj in viewer.level_file.objects.values():
                obj._parentmtx = None #matrix(0, 0, 0, 0)
                obj._parents = []
                obj._children = []

                transx, transy = get_pos(obj)
                rot = get_rotation(obj)
                scalex, scaley = get_scale(obj)

                mtx = matrix(1, 0, 0, 1)
                notable = False

                if transx is not None:
                    notable = True
                    mtx = mtx@translate(transx, transy)

                if rot is not None:
                    notable = True
                    mtx = mtx@rotate(radians(rot))

                if scalex is not None:
                    notable = True
                    mtx = mtx@scale(scalex, scaley)

                obj._currmtx = mtx
                obj._notable = notable

            for obj in viewer.level_file.objects.values():
                if obj._notable:
                    for obj2 in obj.references:
                        if obj2._notable:
                            #if obj2._parent is not None:
                            #    print("WARNING", obj2.name, "has two parents", obj.name, obj2._parent.name)
                            if obj2 not in obj._children:
                                obj._children.append(obj2)
                            if obj not in obj2._parents:
                                obj2._parents.append(obj)
            roots = []
            for obj in viewer.selected:
                root = get_root(obj)
                for r in root:
                    if r not in roots:
                        roots.append(r)

            if roots:
                self.roots.setText("GUI Parent Branches: {}".format(len(roots)))
                if self.curr >= len(roots):
                    self.curr = 0
                    self.currroots.setText("Current Branch: {}".format(self.curr+1))

                self.render_gui(roots[self.curr], viewer.selected)

            self.calc_roots = roots

            """for obj in viewer.selected:
                depth_traverse(obj, objs)

            for obj, depth in objs: 
                #  for obj in viewer.level_file.objects.values():
                if obj._notable:
                    if obj._parentmtx is not None:
                        obj._currmtx = obj._parentmtx@obj._currmtx
                    elif obj._parent is not None:
                        recalculate_parents(obj)
                        obj._currmtx = obj._parentmtx @ obj._currmtx"""

            glLineWidth(2.0)
            self.lines.bind()
            self.lines.render()
            self.lines.unbind()
            glLineWidth(1.0)

    def toggle_branch(self, editor: "bw_editor.LevelEditor"):
        self.curr += 1
        self.currroots.setText("Current Branch: {}".format(self.curr))
        editor.level_view.do_redraw()

    def setup_widget(self, editor: "bw_editor.LevelEditor", widget: "plugin.PluginWidgetEntry"):
        self.section = widget.add_widget(QtWidgets.QLabel(widget, text="BW2 GUI Rendering:"))

        self.button_add_point = widget.add_widget(PFDPluginButton(
            widget, text="Toggle GUI branch", editor=editor, func=self.toggle_branch,
            checkable=False))

        self.roots = widget.add_widget(QtWidgets.QLabel(widget, text="GUI Parent Branches: 0"))
        self.currroots = widget.add_widget(QtWidgets.QLabel(widget, text="Current Branch: -"))