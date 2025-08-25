import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from dataclasses import dataclass
from collections import namedtuple
from typing import TYPE_CHECKING
from math import ceil, floor
from OpenGL.GL import *
import struct
#from lib.bw.texture import OpenGLTexture
from lib.model_rendering import TexturedMesh
from PIL import Image
from lib.vectors import Vector3, Line
from lib.bw.texture import OpenGLTexture
from io import BytesIO
from timeit import default_timer
import timeit
from functools import partial
from lib.render.model_renderingv2 import QuadDrawing, LineDrawing
from editor_controls import MouseMode
from widgets.edit_window import IntegerInput, ColorView
from widgets.editor_widgets import open_yesno_box, open_message_dialog


def round_to_multiple(val, val2, upwards=False):
    if upwards:
        return ceil(val/val2)*val2
    else:
        return floor(val/val2)*val2

def make_getter(getobj, attr, index=None):
    def get():
        obj = getobj()
        print("Object?", obj)
        if obj is not None:
            val = getattr(obj, attr)
            print("hey", val)
            if isinstance(val, list):
                return val[index]
            else:
                return val
        return 0

    return get


def make_setter(getobj, attr, index=None):
    def changed(newval):
        obj = getobj()
        if obj is not None:
            val = getattr(obj, attr)
            if isinstance(val, list):
                val[index] = newval
            else:
                setattr(obj, attr, newval)

    return changed


class DoubleEdit(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, get_value, color_vals):
        super().__init__(parent)
        self.vector_layout = QtWidgets.QHBoxLayout(self)
        self.vector_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.vector_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.vector_layout)
        self.edits = []
        color = ColorView(self)
        color.change_color(*color_vals)
        self.vector_layout.addWidget(color)
        for i in ("priority", "flags"):
            getter = make_getter(get_value, i)
            setter = make_setter(get_value, i)

            labeled_widget = QtWidgets.QWidget(self)


            label_layout = QtWidgets.QHBoxLayout(labeled_widget)
            labeled_widget.setLayout(label_layout)
            label_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

            label = QtWidgets.QLabel(i, self)
            decimal_edit = IntegerInput(self, "sUInt8", getter, setter)

            label_layout.addWidget(label)
            label_layout.addWidget(decimal_edit)

            self.edits.append(decimal_edit)
            self.vector_layout.addWidget(labeled_widget)

            decimal_edit.changed.connect(lambda: self.changed.emit())

    def get_searchable_values(self):
        return [x.text() for x in self.edits]

    def update_value(self) -> None:
        for edit in self.edits:
            edit.update_value()


if TYPE_CHECKING:
    import bw_editor
    import widgets.menu.plugin as plugin
    import bw_widgets


class LinksFull(Exception):
    pass

@dataclass
class PathfindPoint:
    x: int
    y: int
    neighbours: list["Link"]
    type = "PathfindPoint"
    modelname = None
    customname = None
    pathgroup: "RenderGroup" = None
    lua_name = None
    id = None

    def __hash__(self):
        return id(self)

    @classmethod
    def new(cls, x, y):
        return cls(x, y, [Link(None, None) for i in range(4)])

    def get_island(self):
        visited = []
        to_be_visited = [self]
        while to_be_visited:
            next_visit = to_be_visited.pop(0)
            if next_visit._visited:
                continue

            visited.append(next_visit)
            next_visit._visited = True
            for link in next_visit.neighbours:
                if link.exists() and not link.point._visited:
                    to_be_visited.append(link.point)

        return visited

    def connect(self, other, prio=None, flags=None):
        for link in self.neighbours:
            if other is link.point:
                return

        for link in other.neighbours:
            assert self is not link.point

        start_link = self.get_empty_link()
        other_link = other.get_empty_link()

        if start_link is None:
            raise LinksFull("Cannot connect: This point is full!")
        if other_link is None:
            raise LinksFull("Cannot connect: Other point is full!")

        dist = int(((self.x - other.x)**2 + (self.y - other.y)**2)**0.5)
        value = 64 if prio is None else prio
        flags = 0 if flags is None else flags


        edge = PathEdge(dist, value, flags)
        start_link.point = other
        start_link.edge = edge
        other_link.point = self
        other_link.edge = edge

        self.set_dirty()
        other.set_dirty()

    def set_dirty(self):
        if self.pathgroup is not None:
            self.pathgroup.dirty = True

    def get_empty_link(self):
        for link in self.neighbours:
            if not link.exists():
                return link
        return None

    def init(self, x, y, values, points: list["PathfindPoint"], edges: list["PathEdge"]):
        self.x = x
        self.y = y
        self.neighbours = []

        for i in range(4):
            point_index = values[i*2]
            edge_index = values[i*2+1]
            assert (point_index == 2**16-1) == (edge_index == 2**16-1)
            if point_index == 2**16-1:
                link = Link(None, None)
            else:
                link = Link(points[point_index], edges[edge_index])

            self.neighbours.append(link)

    def remove_neighbour(self, point):
        for link in self.neighbours:
            if link.point is point:
                link_point = link.point
                link.clear()
                link_point.remove_neighbour(self)
                self.set_dirty()

    def add_position(self, deltax, deltay, deltaz):
        self.x += deltax
        self.y += deltaz
        self.set_dirty()
        for edge in self.neighbours:
            if edge.exists():
                edge.point.set_dirty()

    def getmatrix(self):
        return None

    def getposition(self):
        return self.x, 0, self.y

    def setposition(self, x, y, z):
        self.x = x
        self.y = z
        self.set_dirty()
        for edge in self.neighbours:
            if edge.exists():
                edge.point.set_dirty()

    def calculate_height(self, bwterrain, water):
        return 0


@dataclass
class PathEdge:
    distance: int
    priority: int  # higher = lower prio?
    flags: int  # 1 = water, 4 = through an object, etc

    def pack(self):
        return self.distance, self.priority, self.flags

    def set(self, a, b, c):
        self.distance, self.priority, self.flags = a,b,c


@dataclass
class Link:
    point: PathfindPoint
    edge: PathEdge

    def exists(self):
        return self.point is not None

    def set(self, point, edge):
        self.point = point
        self.edge = edge

    def clear(self):
        self.point = None
        self.edge = None


class PFD(object):
    def __init__(self):
        self.pathpoints = []
        self.gradient_map = bytearray(0 for i in range(512*512))

    def init_map(self, val):
        for i in range(512*512):
            self.gradient_map[i] = val

    def set_map_val(self, x, y, val):
        self.gradient_map[x+y*512] = val

    def get_map_val(self, x, y):
        return self.gradient_map[x+y*512]

    @classmethod
    def from_file(cls, f):
        pfd = cls()
        pfd.gradient_map = bytearray(0 for i in range(512*512))
        count1, count2 = struct.unpack(">HH", f.read(4))
        print(count1, "points", count2, "edges")
        pfd.point_data = point_data = f.read(count1 * 0x14)
        pfd.edge_data = edge_data = f.read(count2 * 0x3)
        data3 = f.read(0x40000)

        pathpoints = [PathfindPoint(0, 0, []) for i in range(count1)]
        edges = [PathEdge(0, 0, 0) for i in range(count2)]
        pfd.pathpoints = []

        for i in range(count1):
            x, y = struct.unpack_from(">HH", point_data, i*0x14)
            values = struct.unpack_from(">HHHHHHHH", point_data, i*0x14+4)
            pathpoint = pathpoints[i]

            x = (x / 2.0) - 2048
            y = (y / 2.0) - 2048

            pathpoint.init(x, y, values, pathpoints, edges)
            pfd.pathpoints.append(pathpoint)

        for i in range(count2):
            distance, b, c = struct.unpack_from(">BBB", edge_data, i * 0x3)
            edge = edges[i]
            edge.distance, edge.priority, edge.flags = distance, b, c

        for x in range(512):
            for y in range(512):
                val = data3[x + y * 512]
                if x < 256:
                    x = x * 2
                else:
                    x = (x - 256) * 2 + 1
                pfd.gradient_map[x+y*512] = val

        return pfd

    def write(self, f):
        edges = []
        edges_pack = []
        print("Start")
        for i, point in enumerate(self.pathpoints):
            point._index = i
        print("Indexed points")
        for i, point in enumerate(self.pathpoints):
            for link in point.neighbours:
                if link.exists():
                    if hasattr(link.edge, "_index"):
                        continue

                    link.edge.distance = min(255, int(((link.point.x-point.x)**2 + (link.point.y-point.y)**2)**0.5))
                    #packed = link.edge.pack()
                    packed = (point._index, link.point._index) if point._index < link.point._index else (link.point._index, point._index)

                    edges_pack.append(packed)
                    link.edge._index = len(edges)
                    edges.append(link.edge)
        print("Indexed edges")
        f.write(struct.pack(">HH", len(self.pathpoints), len(edges)))
        for point in self.pathpoints:
            x = max(0, min(8192, int((point.x + 2048) * 2)))
            y = max(0, min(8192, int((point.y + 2048) * 2)))
            f.write(struct.pack(">HH",
                                x, y))
            indices = []
            for link in point.neighbours:
                if link.exists():
                    indices.append(link.point._index)
                    indices.append(link.edge._index)
                else:
                    indices.append(2**16-1)
                    indices.append(2**16-1)

            f.write(struct.pack(">HHHHHHHH",
                                *indices))
        print("Written points")
        for edge in edges:
            f.write(struct.pack("BBB", edge.distance, edge.priority, edge.flags))
        print("Written edges")
        print("Written", len(self.pathpoints), "points and", len(edges), "edges")
        values = bytearray(0 for i in range(512*512))
        for x in range(512):
            for y in range(512):
                val = self.gradient_map[x+y*512]
                if x % 2 == 0:
                    x = x // 2
                else:
                    x = (x-1)//2 + 256
                values[x + y*512] = val

        f.write(values)
        print("Written gradient map")


class RenderGroupDistributor(object):
    def __init__(self, groupcount, buffer=256):
        self.groups = [RenderGroup() for i in range(groupcount)]

        self._count = 0
        self._buffer = buffer
        self._curr_group: RenderGroup = None

    def reset(self):
        for group in self.groups:
            group.reset()

    def choose_next_group(self):
        groups = [group for group in self.groups]
        groups.sort(key=lambda x: x.size())

        return groups[0]

    def add_point(self, point: PathfindPoint):
        assert point.pathgroup is None

        if self._curr_group is not None:
            if self._count < self._buffer:
                self._curr_group.add_point(point)
                self._count += 1
            else:
                self._curr_group = self.choose_next_group()
                self._curr_group.add_point(point)
                self._count = 1
        else:
            self._curr_group = self.choose_next_group()
            self._curr_group.add_point(point)
            self._count = 1

    def render(self):
        for group in self.groups:
            group.render()


COLORS = ((1.0, 1.0, 1.0),
        (1.0, 0.1, 0.1),
        (0.1, 1.0, 0.1),
        (0.1, 0.1, 1.0))

COLORS2 = ((0.8, 0.8, 0.8),
          (1.0, 0.5, 0.5),
          (0.5, 1.0, 0.5),
          (0.5, 0.5, 1.0))


class RenderGroup(object):
    def __init__(self):
        self.points = []
        self.quads = QuadDrawing()
        self.lines = LineDrawing()

        self.dirty = True

    def remove_point(self, point):
        self.points.remove(point)
        self.dirty = True

    def reset(self):
        self.points = []
        self.quads.reset()
        self.lines.reset_lines()
        self.dirty = True

    def render(self):
        if len(self.points) == 0:
            return

        if self.dirty:
            self.quads.reset()
            self.lines.reset_lines()

            for point in self.points:
                x = point.x
                y = point.y
                size = 0.5
                h = None  # viewer.bwterrain.check_height_interpolate(x, y)
                if h is None:
                    h = 100
                self.quads.add_quad((x + size, h + 1, y + size),
                                    (x - size, h + 1, y + size),
                                    (x - size, h + 1, y - size),
                                    (x + size, h + 1, y - size),
                                    (1.0, 0.4, 0.4))

                for i, link in enumerate(point.neighbours):
                    if link.exists():

                        start = (x, h, y)
                        end_x = link.point.x
                        end_y = link.point.y
                        h2 = None  # viewer.bwterrain.check_height_interpolate(end_x, end_y)
                        if h2 is None:
                            h2 = 100

                        end = ((x + end_x) / 2.0, (h + h2) / 2.0 + 0.5, (y + end_y) / 2.0)
                        self.lines.add_line(start, end, COLORS2[i])

            self.dirty = False

        self.quads.bind()
        self.quads.render()
        self.quads.unbind()
        glLineWidth(2.0)
        self.lines.bind()
        self.lines.render()
        self.lines.unbind()
        glLineWidth(1.0)

    def add_point(self, point: PathfindPoint):
        self.points.append(point)
        point.pathgroup = self
        self.dirty = True

    def size(self):
        return len(self.points)


class Material(object):
    def __init__(self, tex, diffuse=None):
        self.tex = tex
        self.diffuse = diffuse


class PFDPluginButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        self.editor = kwargs["editor"]
        self.func = kwargs["func"]
        del kwargs["editor"]
        del kwargs["func"]

        super().__init__(*args, **kwargs)

        self.pressed.connect(self.call_func)

    def call_func(self):
        self.func(self.editor)


class Plugin(object):
    def __init__(self):
        self.name = "PFD Research"
        self.actions = [("Load Image", self.testfunc),
                        ("Load Current PFD", self.load_currpfd),
                        ("Gradient Generation Test", self.gen_gradient_map)]
        print("I have been initialized")
        self.texture: OpenGLTexture = None
        self.model: TexturedMesh = None
        self.last_path = None
        self.do_update = False
        self.pfd: PFD = None
        self.curr = None
        self.pos = None
        self.raycast = None
        self.quads = QuadDrawing()
        self.selected_quads = QuadDrawing()
        self.selected_points = []
        self.lines = LineDrawing()
        self.MODE_ADD_PATHPOINT = None
        self.gradient_path = None
        self.pfd_path = None

        self.render_distributor = RenderGroupDistributor(32, buffer=128)

        self.dirty = True

        self.hit_tiles = []

        self.last_point = None
        self.visual_points = []
        self.start_point = None
        self.end_point = None
        self.edge_template = PathEdge(0, 0, 0)

    def gen_gradient_map(self, editor: "bw_editor.LevelEditor"):
        check_height = editor.level_view.bwterrain.check_height_interpolate
        res = 512.0
        step = 4096/res

        start_x = -2048 - 2*step
        start_y = -2048

        #img_data = Image.new("RGB", (int(res), int(res)), color=(255, 255, 255))
        self.pfd.init_map(0xFF)

        for obj in editor.file_menu.preload_data.objects.values():
            if obj.type == "cLevelSettings":
                settings = obj
                break
        else:
            raise RuntimeError("cLevelSettings not found")
        waterheight = editor.level_view.waterheight
        boundary = settings.mMapScreenLimits

        boundary_start_x = boundary.mMatrix.x - boundary.mSize.x/2.0
        boundary_start_z = boundary.mMatrix.z - boundary.mSize.z / 2.0
        boundary_end_x = boundary.mMatrix.x + boundary.mSize.x / 2.0
        boundary_end_z = boundary.mMatrix.z + boundary.mSize.z / 2.0
        print(boundary_start_x)

        def calc_gradient(x, y):
            curr = (start_x + x * step, start_y + y * step)
            curr_up = (start_x + (x + 1) * step, start_y + y * step)
            curr_right = (start_x + x * step, start_y + (y + 1) * step)
            curr_upright = (start_x + (x+1) * step, start_y + (y + 1) * step)

            curr_height = check_height(*curr)
            up_height = check_height(*curr_up)
            right_height = check_height(*curr_right)
            upright_height = check_height(*curr_upright)

            if curr_height is None or curr_height < waterheight:
                curr_height = 0
            if up_height is None:
                up_height = curr_height
            if right_height is None:
                right_height = curr_height
            if right_height is None:
                right_height = curr_height

        for x in range(int(res)):
            for y in range(int(res)):
                curr = (start_x + x*step, start_y + y*step)
                curr_up = (start_x + (x+1)*step, start_y + y*step)
                curr_right = (start_x + x*step, start_y + (y+1)*step)
                curr_upright = (start_x + (x + 1) * step, start_y + (y + 1) * step)
                if (not boundary_start_x <= curr[0] <= boundary_end_x
                        or not boundary_start_z <= curr[1] <= boundary_end_z):
                    continue

                curr_height = check_height(*curr)
                up_height = check_height(*curr_up)
                right_height = check_height(*curr_right)
                upright_height = check_height(*curr_upright)

                if curr_height is None or curr_height < waterheight:
                    curr_height = 0
                    #img_data.putpixel((x, y), (0xAA, 0xAA, 0xAA))
                    self.pfd.set_map_val(x, y, 0xAA)
                    continue
                if up_height is None:
                    up_height = curr_height
                if right_height is None:
                    right_height = curr_height
                if curr_upright is None:
                    curr_upright = curr_height

                gradient_up = abs(curr_height - up_height)/step
                gradient_right = abs(curr_height - right_height)/step
                gradient_upright = abs(curr_height - upright_height)/step
                gradient = max(gradient_up, gradient_right, gradient_upright)
                v = max(0, min(int((round(gradient, 1)-0.1) *300), 255))

                self.pfd.set_map_val(x, y, v)

    def testfunc(self, editor: "bw_editor.LevelEditor"):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(editor,
                                                        "Choose PNG",
                                                        self.last_path,
                                                        "Image (*.png);;All (*)")
        self.pfd = None
        if self.texture is not None:
            self.texture.img_data = Image.open(path)
            self.do_update = True

    def load_currpfd(self, editor: "bw_editor.LevelEditor", message=True):
        path = editor.file_menu.get_pfd_path()

        if path:
            with open(path, "rb") as f:
                editor.pfd = PFD.from_file(f)
                self.pfd = editor.pfd
                self.render_distributor.reset()
                for point in self.pfd.pathpoints:
                    self.render_distributor.add_point(point)
                self.dirty = True
            """self.texture.img_data = Image.new("RGB", (8192+1, 8192+1), color=(128, 128, 128))
            editor.level_view.overlay_texture.img_data = self.texture.img_data
            img = self.texture.img_data
            for point in self.pfd.pathpoints:
                x, y = point.x, point.y
                img.putpixel((x, y), (255, 0, 0))

            self.do_update = True
            self.curr = None"""
            editor.level_view.do_redraw()
            if message:
                open_message_dialog("Loaded!", parent=editor)

    def load_pfd(self, editor: "bw_editor.LevelEditor"):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(editor,
                                                        "Choose PFD",
                                                        self.last_path,
                                                        "BW1 Pathfinding Data (*.pfd);;All (*)")

        if path:
            with open(path, "rb") as f:
                editor.pfd = PFD.from_file(f)
                self.dirty = True
                self.pfd = editor.pfd
            editor.level_view.do_redraw()
            """self.texture.img_data = Image.new("RGB", (8192+1, 8192+1))
            img = self.texture.img_data
            for point in self.pfd.pathpoints:
                x, y = point.x, point.y
                img.putpixel((x, 8192 - y), (255, 0, 0))"""
            open_message_dialog("Loaded!", parent=editor)
            #self.do_update = True
            #self.curr = None

    def save_currpfd(self, editor, message=True):
        path = editor.file_menu.get_pfd_path()

        if path:
            tmp = BytesIO()
            self.pfd.write(tmp)
            with open(path, "wb") as f:
                f.write(tmp.getvalue())
            if message:
                open_message_dialog("Saved!", parent=editor)

    def cancel_mode(self, editor):
        print("Cancelled")
        editor.level_view.text_display.set_text("PFD", " ")
        editor.level_view.text_display.set_text("PFD", "")
        editor.level_view.text_display.update()
        self.visual_points = []

    def buttonaction_add_point(self, editor: "bw_editor.LevelEditor"):
        print("Adding point")
        assert self.MODE_ADD_PATHPOINT is not None
        if not editor.level_view.mouse_mode.plugin_active(self.MODE_ADD_PATHPOINT):
            print("Enabled path point mode")
            editor.level_view.mouse_mode.set_plugin_mode(self.MODE_ADD_PATHPOINT)
            editor.level_view.text_display.set_text("PFD", "Pathfinding: Left Mouse Button to place points.\nESC to cancel.")
        else:
            print("Disabled path point mode")
            editor.level_view.mouse_mode.set_mode(MouseMode.NONE)
            self.cancel_mode(editor)

    def buttonaction_delete_point(self, editor: "bw_editor.LevelEditor"):
        self.delete_selected_points(editor)

    def buttonaction_connect_points(self, editor: "bw_editor.LevelEditor"):
        print("Connecting point")
        assert self.MODE_CONNECT_PATHPOINT is not None
        if not editor.level_view.mouse_mode.plugin_active(self.MODE_CONNECT_PATHPOINT):
            self.last_point = None
            editor.level_view.mouse_mode.set_plugin_mode(self.MODE_CONNECT_PATHPOINT)
            editor.level_view.text_display.set_text("PFD",
                                                    ("Pathfinding: Left Mouse Button to connect points.\n"
                                                     "If Continuous, next point will be connected to last selected point.\n"
                                                     "ESC to cancel."))
        else:
            editor.level_view.mouse_mode.set_mode(MouseMode.NONE)
            self.cancel_mode(editor)

    def buttonaction_disconnect_points(self, editor: "bw_editor.LevelEditor"):
        assert self.MODE_DISCONNECT_PATHPOINT is not None
        if not editor.level_view.mouse_mode.plugin_active(self.MODE_DISCONNECT_PATHPOINT):
            self.last_point = None
            editor.level_view.mouse_mode.set_plugin_mode(self.MODE_DISCONNECT_PATHPOINT)
            editor.level_view.text_display.set_text("PFD",
                                                    ("Pathfinding: Left Mouse Button to disconnect points.\n"
                                                     "If Continuous, next point will be disconnected to last selected point.\n"
                                                     "ESC to cancel."))
        else:
            editor.level_view.mouse_mode.set_mode(MouseMode.NONE)
            self.cancel_mode(editor)

    def buttonaction_disconnect_selection(self, editor: "bw_editor.LevelEditor"):
        if self.pfd is not None:
            for point in self.selected_points:
                point: PathfindPoint
                for link in point.neighbours:
                    if link.exists() and link.point in self.selected_points:
                        point.remove_neighbour(link.point)

    def initialize_pfd_from_terrain(self, editor: "bw_editor.LevelEditor"):
        if not open_yesno_box("This will generate a new pathfinding grid from the terrain.\nAll current data will be replaced.",
                              "Do you want to continue?"):
            return

        self.pfd = PFD()
        size = int(4096/8.0)
        grid = [[None for z in range(size)] for x in range(size)]
        mode_grid = [[None for z in range(size)] for x in range(size)]
        start_x = -2048
        start_y = -2048

        check_height = editor.level_view.bwterrain.check_height_interpolate
        step = 2

        waterheight = editor.level_view.waterheight

        def calc_gradient(x, y):
            curr = (x, y)
            curr_up = (x, y+step)
            curr_right = (x+step, y)

            curr_height = check_height(*curr)
            up_height = check_height(*curr_up)
            right_height = check_height(*curr_right)

            if curr_height is None or curr_height < waterheight:
                curr_height = 0
            if up_height is None:
                up_height = curr_height
            if right_height is None:
                right_height = curr_height

            gradient_up = abs(curr_height - up_height) / step
            gradient_right = abs(curr_height - right_height) / step
            gradient = max(gradient_up, gradient_right)
            return gradient

        for x in range(size):
            for y in range(size):
                curr_x = start_x + x * 8.0
                curr_y = start_y + y * 8.0

                mode = None

                height = editor.level_view.bwterrain.check_height(curr_x, curr_y)
                if height is None:
                    mode = 0  # very sparse or dont
                elif height < waterheight:
                    mode = 1  # sparse
                else:
                    gradient = calc_gradient(curr_x, curr_y)
                    if gradient < 0.45:
                        mode = 2  # normal
                    else:
                        mode = 3

                mode_grid[x][y] = mode

                point = PathfindPoint.new(curr_x, curr_y)

                if mode == 0:
                    pass
                elif mode == 1:
                    if x % 4 == 0 and y % 4 == 0:
                        grid[x][y] = point
                elif mode == 2:
                    grid[x][y] = point
                elif mode == 3:
                    pass

        self.pfd.pathpoints = []
        self.render_distributor.reset()
        for x in range(size):
            for y in range(size):
                if grid[x][y] is not None:
                    self.pfd.pathpoints.append(grid[x][y])
                    self.render_distributor.add_point(grid[x][y])

        for x in range(size):
            for y in range(size):
                curr = grid[x][y]
                if curr is None:
                    continue
                mode = mode_grid[x][y]

                if mode == 1:
                    maxrange = 8
                else:
                    maxrange = 3

                for i in range(1, maxrange):
                    if x + i < size and grid[x][y] is not None and grid[x + i][y] is not None and mode_grid[x + i][y] in (1,2):
                        if mode_grid[x][y] == 1 or mode_grid[x+i][y] == 1:
                            grid[x][y].connect(grid[x + i][y], flags=1)
                        else:
                            grid[x][y].connect(grid[x + i][y])
                        break

                for i in range(1, maxrange):
                    if y + i < size and grid[x][y] is not None and grid[x][y+i] is not None and mode_grid[x][y+i] in (1,2):
                        if mode_grid[x][y] == 1 or mode_grid[x + i][y] == 1:
                            grid[x][y].connect(grid[x][y+i], flags=1)
                        else:
                            grid[x][y].connect(grid[x][y+i])
                        break

        delete_candidates = []
        checked = [point for point in self.pfd.pathpoints]
        for point in checked:
            point._visited = False

        while checked:
            point = checked[0]
            island = point.get_island()
            for point in island:
                checked.remove(point)
                if len(island) < 40:
                    delete_candidates.append(point)
        print("removed", len(delete_candidates))
        for point in delete_candidates:
            point.pathgroup.remove_point(point)
            self.pfd.pathpoints.remove(point)

        editor.level_view.do_redraw()
        print("Added points", len(self.pfd.pathpoints))
        open_message_dialog("Initialized New PFD!", parent=editor)

    def buttonaction_connect_points_grid(self, editor: "bw_editor.LevelEditor"):
        print("Connecting point")

    def buttonaction_make_grid(self, editor: "bw_editor.LevelEditor"):
        assert self.MODE_MAKE_PATH_GRID is not None
        if not editor.level_view.mouse_mode.plugin_active(self.MODE_MAKE_PATH_GRID):
            self.start_point = None
            self.end_point = None
            editor.level_view.mouse_mode.set_plugin_mode(self.MODE_MAKE_PATH_GRID)
            editor.level_view.text_display.set_text("PFD",
                                                    ("Pathfinding: Click+Drag to create grid of points.\n"
                                                     "ESC to cancel."))
        else:
            editor.level_view.mouse_mode.set_mode(MouseMode.NONE)
            self.cancel_mode(editor)

    def world_click_select_start(self, editor: "bw_widgets.BolMapViewer", start_x, start_z):
        if editor.mouse_mode.plugin_active(self.MODE_MAKE_PATH_GRID):
            self.start_point = (start_x, start_z)

    def world_click_select_continue(self, editor: "bw_widgets.BolMapViewer", end_x, end_z):
        if not self.hide_pfd.isChecked():
            return

        if editor.mouse_mode.plugin_active(self.MODE_MAKE_PATH_GRID):
            print("aaa")
            self.end_point = (end_x, end_z)
            spacing = self.get_spacing()
            start_x = round_to_multiple(min(self.start_point[0], end_x), spacing, upwards=True)
            start_z = round_to_multiple(min(self.start_point[1], end_z), spacing, upwards=True)
            end_x = round_to_multiple(max(self.start_point[0], end_x), spacing, upwards=True)
            end_z = round_to_multiple(max(self.start_point[1], end_z), spacing, upwards=True)


            size_x = int((end_x-start_x)/spacing)
            size_z = int((end_z-start_z)/spacing)

            points = []
            for x in range(size_x):
                for z in range(size_z):
                    points.append((start_x + x * spacing, start_z + z * spacing))
            self.visual_points = points
            editor.do_redraw()

    def get_spacing(self):
        index = self.spacing_choice.currentIndex()
        return [4.0, 8.0, 16.0, 32.0][index]

    def get_limited_area_from_selected(self, tolerance):
        smallest_x = None
        smallest_z = None
        biggest_x = None
        biggest_z = None

        for point in self.selected_points:
            if smallest_x is None:
                smallest_x = point.x
                smallest_z = point.z
                biggest_x = point.x
                biggest_z = point.z
            else:
                if point.x < smallest_x: smallest_x = point.x
                if point.x > biggest_x: biggest_x = point.x
                if point.z < smallest_z: smallest_z = point.z
                if point.z > biggest_z: biggest_z = point.z

        smallest_x -= tolerance
        smallest_z -= tolerance
        biggest_x += tolerance
        biggest_z += tolerance

        return smallest_x, smallest_z, biggest_x, biggest_z

    def get_limited_points(self, area):
        smallest_x, smallest_z, biggest_x, biggest_z = area

        result = []

        for point in self.pfd.pathpoints:
            if smallest_x <= point.x <= biggest_x and smallest_z <= point.y <= biggest_z:
                result.append(point)

        return result

    def get_closest_point(self, x, z, tolerance, limit=None):
        result = []
        if limit:
            point_list = limit
        else:
            point_list = self.pfd.pathpoints

        for point in point_list:
            diff_x = abs(x - point.x)
            diff_z = abs(z - point.y)
            if diff_x + diff_z < tolerance:
                result.append((point, diff_x+diff_z))

        if result:
            result.sort(key=lambda x: x[1])
            return result[0][0]
        else:
            return None

    def world_click_select_box(self, editor: "bw_editor.LevelEditor",
                               select_start_x, select_start_z,
                               select_end_x, select_end_z):
        if not self.hide_pfd.isChecked():
            return

        if self.pfd is not None:
            if editor.mouse_mode.plugin_active(self.MODE_MAKE_PATH_GRID):
                self.visual_points = []
                spacing = self.get_spacing()
                start_x = round_to_multiple(min(select_start_x, select_end_x), spacing, upwards=True)
                start_z = round_to_multiple(min(select_start_z, select_end_z), spacing, upwards=True)
                end_x = round_to_multiple(max(select_start_x, select_end_x), spacing, upwards=True)
                end_z = round_to_multiple(max(select_start_z, select_end_z), spacing, upwards=True)

                tolerance = spacing*2
                check_area = self.get_limited_points((start_x-tolerance, start_z-tolerance, end_x+tolerance, end_z+tolerance))

                size_x = int((end_x - start_x) / spacing)
                size_z = int((end_z - start_z) / spacing)

                grid = [[None for z in range(size_z)] for x in range(size_x)]
                print(size_x, size_z, "SIZE", start_x, start_z, end_x, end_z)
                points = []
                for x in range(size_x):
                    for z in range(size_z):
                        point = self.get_closest_point(start_x + x*spacing, start_z + z*spacing, spacing, check_area)

                        if point is None:
                            point = PathfindPoint.new(start_x + x*spacing, start_z + z*spacing)
                            self.pfd.pathpoints.append(point)
                            self.render_distributor.add_point(point)

                        grid[x][z] = point

                for x in range(size_x):
                    for z in range(size_z):
                        this_point = grid[x][z]

                        if z < size_z-1:
                            up = grid[x][z+1]
                            try:
                                this_point.connect(up)
                            except Exception as err:
                                print(err)
                                pass

                        if x < size_x - 1:
                            right = grid[x + 1][z]

                            try:
                                this_point.connect(right)
                            except Exception as err:
                                print(err)





            if editor.mouse_mode.active(MouseMode.NONE):
                results = []
                for i, point in enumerate(self.pfd.pathpoints):
                    if (select_start_x <= point.x <= select_end_x and select_start_z <= point.y <= select_end_z):
                        results.append(point)

                if results:
                    print("PFD selected", len(results))
                    self.add_selection_list(editor, results, append=editor.shift_is_pressed)

                else:
                    self.clear_selection(editor)
                self.dirty = True

                if len(self.selected_points) == 1:
                    self.edge1_edit.update_value()
                    self.edge2_edit.update_value()
                    self.edge3_edit.update_value()
                    self.edge4_edit.update_value()

    def setup_widget(self, editor: "bw_editor.LevelEditor", widget: "plugin.PluginWidgetEntry"):
        print("Setting up widget...")
        self.section = widget.add_widget(QtWidgets.QLabel(widget, text="BW1 Pathfind Data (PFD) Tools:"))


        self.button_add_point = widget.add_widget(PFDPluginButton(
            widget, text="Add Path Point", editor=editor, func=self.buttonaction_add_point))
        self.button_delete_point = widget.add_widget(PFDPluginButton(
            widget, text="Delete Path Point", editor=editor, func=self.buttonaction_delete_point))
        self.button_connect_point = widget.add_widget(PFDPluginButton(
            widget, text="Connect Points", editor=editor, func=self.buttonaction_connect_points))
        self.button_disconnect_point = widget.add_widget(PFDPluginButton(
            widget, text="Disconnect Points", editor=editor, func=self.buttonaction_disconnect_points))
        self.continuous = widget.add_widget(QtWidgets.QCheckBox(widget, text="Continuous Connect/Disconnect"))
        self.button_disconnect_point_selection = widget.add_widget(PFDPluginButton(
            widget, text="Disconnect Selection", editor=editor, func=self.buttonaction_disconnect_selection))
        self.button_connect_point.setToolTip("Enables Connect Mode. Click on points to connect them together.")
        self.button_disconnect_point.setToolTip("Enables Disconnect Mode. Click on points to disconnect them.")
        self.button_disconnect_point_selection.setToolTip("Disconnects selected points from each other.")


        self.button_make_grid = widget.add_widget(PFDPluginButton(
            widget, text="Draw Grid", editor=editor, func=self.buttonaction_make_grid))
        self.spacing_choice: QtWidgets.QComboBox = widget.add_widget(QtWidgets.QComboBox(
            widget
        ))
        self.spacing_choice.addItem("Grid Spacing: Tiny (Obstacles)")
        self.spacing_choice.addItem("Grid Spacing: Small (Default)")
        self.spacing_choice.addItem("Grid Spacing: Medium (Sparse)")
        self.spacing_choice.addItem("Grid Spacing: Large (Water)")
        self.spacing_choice.setCurrentIndex(1)

        """self.pfdinfo = widget.add_widget(QtWidgets.QLabel(widget))
        self.current_index = widget.add_widget(QtWidgets.QLabel(widget))
        self.current_coords = widget.add_widget(QtWidgets.QLabel(widget))
        self.current_y = widget.add_widget(QtWidgets.QLabel(widget))

        self.current_val1 = widget.add_widget(QtWidgets.QLabel(widget))
        self.current_val2 = widget.add_widget(QtWidgets.QLabel(widget))


        self.current_val4 = widget.add_widget(QtWidgets.QLabel(widget))
        self.current_val5 = widget.add_widget(QtWidgets.QLabel(widget))
        self.current_unk6 = widget.add_widget(QtWidgets.QLabel(widget))"""
        self.edge1_edit = widget.add_widget(DoubleEdit(widget,
                                                       partial(self.get_edge, 0),
                                                       (255, 255, 255, 255)))
        self.edge2_edit = widget.add_widget(DoubleEdit(widget,
                                                       partial(self.get_edge, 1),
                                                       (255, 0, 0, 255)))
        self.edge3_edit = widget.add_widget(DoubleEdit(widget,
                                                       partial(self.get_edge, 2),
                                                       (0, 255, 0, 255)))
        self.edge4_edit = widget.add_widget(DoubleEdit(widget,
                                                       partial(self.get_edge, 3),
                                                       (0, 0, 255, 255)))

        self.button_load_pfd = widget.add_widget(PFDPluginButton(
            widget, text="Load Current PFD", editor=editor, func=self.load_currpfd))

        self.button_load_pfd = widget.add_widget(PFDPluginButton(
            widget, text="Save Current PFD", editor=editor, func=self.save_currpfd))
        self.button_init_pfd = widget.add_widget(PFDPluginButton(
            widget, text="Initialize New PFD", editor=editor, func=self.initialize_pfd_from_terrain))

        pfd1 = QtWidgets.QWidget(widget)
        layout1 = QtWidgets.QHBoxLayout(pfd1)
        layout1.setContentsMargins(0, 0, 0, 0)
        pfd1.setLayout(layout1)

        pfd2 = QtWidgets.QWidget(widget)
        layout2 = QtWidgets.QHBoxLayout(pfd2)
        layout2.setContentsMargins(0, 0, 0, 0)
        pfd2.setLayout(layout2)

        self.button_load_pfd = PFDPluginButton(
            pfd1, text="Load PFD From File", editor=editor, func=self.buttonaction_load_pfd_file)
        self.button_save_pfd =PFDPluginButton(
            pfd1, text="Save PFD To File", editor=editor, func=self.buttonaction_save_pfd_file)
        self.button_load_gradient = PFDPluginButton(
            pfd2, text="Load Gradient Map From PNG", editor=editor, func=self.buttonaction_load_gradient)
        self.button_save_gradient = PFDPluginButton(
            pfd2, text="Save Gradient Map To PNG", editor=editor, func=self.buttonaction_save_gradient)



        layout1.addWidget(self.button_load_pfd)
        layout1.addWidget(self.button_save_pfd)
        layout2.addWidget(self.button_load_gradient)
        layout2.addWidget(self.button_save_gradient)

        widget.add_widget(pfd1)
        widget.add_widget(pfd2)

        self.button_regen_gradient = widget.add_widget(PFDPluginButton(
            widget, text="Regenerate PFD Gradient", editor=editor, func=self.gen_gradient_map
        ))
        self.button_regen_gradient.setToolTip("Regenerates PFD Gradient from Terrain.There may be issues!")

        self.hide_pfd: QtWidgets.QCheckBox = widget.add_widget(QtWidgets.QCheckBox(
            widget, text="Show Pathfinding Points"
        ))
        self.only_select_pathfind: QtWidgets.QCheckBox = widget.add_widget(QtWidgets.QCheckBox(
            widget, text="Only Select Pathfind Points"
        ))

        self.only_select_pathfind.toggled.connect(partial(self.set_select_ignore, editor))
        self.only_select_pathfind.setToolTip("If checked, disables selecting other map objects besides pathfinding points.")

        self.hide_pfd.toggled.connect(partial(self.toggle_visible, editor))
        self.hide_pfd.toggle()
        widget.add_text("Mass Set Edge Data:")
        self.mass_set_template = widget.add_widget(DoubleEdit(widget,
                                                       lambda: self.edge_template,
                                                       (0, 0, 255, 0)))

        pfd3 = QtWidgets.QWidget(widget)
        layout3 = QtWidgets.QHBoxLayout(pfd3)
        layout3.setContentsMargins(0, 0, 0, 0)
        pfd3.setLayout(layout2)

        self.mass_set = PFDPluginButton(
            pfd2, text="Mass Set Priority", editor=editor, func=self.buttonaction_mass_set)

        self.mass_set_2 = PFDPluginButton(
            pfd2, text="Mass Set Flags", editor=editor, func=self.buttonaction_mass_set_2)

        layout3.addWidget(self.mass_set)
        layout3.addWidget(self.mass_set_2)
        widget.add_widget(pfd3)

        self.bake_wp = widget.add_widget(PFDPluginButton(
            widget, text="Bake Selected Waypoint Path to PFD", editor=editor, func=self.buttonaction_waypoint)
        )

    def set_select_ignore(self, editor):
        editor.level_view.ignore_selection = self.only_select_pathfind.isChecked()

    def buttonaction_mass_set(self, editor):
        for point in self.selected_points:
            for link in point.neighbours:
                if link.exists and link.point in self.selected_points:
                    link.edge.priority = self.edge_template.priority
    
    def buttonaction_mass_set_2(self, editor):
        for point in self.selected_points:
            for link in point.neighbours:
                if link.exists and link.point in self.selected_points:
                    link.edge.flags = self.edge_template.flags

    def toggle_visible(self, editor):
        self.clear_selection(editor.level_view)
        editor.level_view.do_redraw()

    def before_save(self, editor):
        if self.pfd is not None:
            self.save_currpfd(editor, message=False)

    def after_load(self, editor):
        if self.pfd is not None:
            self.load_currpfd(editor, message=False)

    def get_edge(self, i):
        if len(self.selected_points) == 1:
            point = self.selected_points[0]
            link = point.neighbours[i]
            if link.exists():
                print("OGEY", link.edge)
                return link.edge

        return None

    def terrain_click_3d(self, editor, ray, pos):
        print("CLICKED", pos)
        #self.pos = pos
        self.raycast = ray
        self.pos = pos + Vector3(0, 0, 2)

        swp = ray.swapped_yz()
        #print("time", timeit.timeit(lambda: editor.bwterrain.ray_collide(swp), number=250)/250.0)

    def add_selection(self,  editor: "bw_widgets.BolMapViewer", obj, append=True):
        if append:
            if obj not in self.selected_points:
                self.selected_points.append(obj)
                editor.selected_misc.append(obj)
                editor.selected_positions.append(obj)
            else:

                self.selected_points.remove(obj)
                editor.selected_misc.remove(obj)
                editor.selected_positions.remove(obj)
        else:
            self.selected_points = [obj]
            editor.selected_misc = [obj]
            editor.selected_positions = [obj]

        editor.parent().parent().update_3d()

    def add_selection_list(self,  editor: "bw_widgets.BolMapViewer", objlist, append=True):
        if append:
            for obj in objlist:
                if obj not in self.selected_points:
                    self.selected_points.append(obj)
                    editor.selected_misc.append(obj)
                    editor.selected_positions.append(obj)
        else:
            self.selected_points = [obj for obj in objlist]
            editor.selected_misc = [obj for obj in objlist]
            editor.selected_positions = [obj for obj in objlist]

        editor.parent().parent().update_3d()

    def clear_selection(self, editor: "bw_widgets.BolMapViewer"):
        try:
            for obj in self.selected_points:
                editor.selected_misc.remove(obj)
                editor.selected_positions.remove(obj)
        except ValueError:
            pass

        self.selected_points = []
        self.selected_quads.reset()
        editor.parent().parent().update_3d()

    def delete_selected_points(self, editor):
        if self.pfd is not None:
            for point in self.selected_points:
                point.pathgroup.remove_point(point)
                for link in point.neighbours:
                    if link.exists():
                        link.point.remove_neighbour(point)
                        if link.exists():
                            link.point.set_dirty()
                self.pfd.pathpoints.remove(point)

            self.dirty = True
            self.clear_selection(editor.level_view)

    def raycast_3d(self, editor: "bw_widgets.BolMapViewer", ray):
        return
        self.raycast = ray
        swapped = ray.swapped_yz()
        self.hit_tiles = []
        """hit = [editor.bwterrain.chunk_group]
        while hit:
            nextitem = hit.pop(0)
            if nextitem.aabb.ray_hits_box(swapped):
                self.hit_tiles.append(nextitem)
                if hasattr(nextitem, "items"): 
                    hit.extend(nextitem.items)"""

        result = editor.bwterrain.ray_collide(swapped)
        if result:
            point, d = result
            point.swap_yz()
            self.pos = point + Vector3(0, 0, 2)

    def world_click(self, editor: "bw_widgets.BolMapViewer", x, y):
        pfd = getattr(editor, "pfd", None)
        if pfd is not None:
            self.pfd = pfd
        scale = 3 * editor.zoom_factor
        line = Line(Vector3(x, 100, y), Vector3(0, -1, 0))
        print("Did we hit gizmo?", editor.gizmo.collide(line, scale, False, True, True))

        hit, _ = editor.gizmo.collide(line, scale, False, True, True)

        if not self.hide_pfd.isChecked():
            return

        if self.pfd is not None and not hit:
            if editor.mouse_mode.plugin_active(self.MODE_ADD_PATHPOINT):
                point = PathfindPoint.new(x, y)
                self.pfd: PFD
                self.pfd.pathpoints.append(point)
                self.render_distributor.add_point(point)

            elif (editor.mouse_mode.plugin_active(self.MODE_CONNECT_PATHPOINT) or
                  editor.mouse_mode.plugin_active(self.MODE_DISCONNECT_PATHPOINT)):

                results = []
                for i, point in enumerate(self.pfd.pathpoints):
                    diffx = abs(point.x - x)
                    diffy = abs(point.y - y)
                    if diffx < 1 and diffy < 1:
                        results.append((max(diffx, diffy), i))

                if results:
                    results.sort(key=lambda x: x[0])
                    point = self.pfd.pathpoints[results[0][1]]
                    self.selected_points = [point]
                    if self.last_point is None:
                        self.last_point = point
                    else:
                        if editor.mouse_mode.plugin_active(self.MODE_CONNECT_PATHPOINT):
                            self.last_point.connect(point)
                        elif editor.mouse_mode.plugin_active(self.MODE_DISCONNECT_PATHPOINT):
                            self.last_point.remove_neighbour(point)

                        if self.continuous.isChecked():
                            self.last_point = point
                        else:
                            self.last_point = None
            elif editor.mouse_mode.active(MouseMode.NONE):
                results = []
                for i, point in enumerate(self.pfd.pathpoints):
                    diffx = abs(point.x-x)
                    diffy = abs(point.y-y)
                    if diffx < 1 and diffy < 1:
                        results.append((max(diffx, diffy), i))

                if results:
                    results.sort(key=lambda x: x[0])
                    i = results[0][1]
                    self.curr = i
                    point = self.pfd.pathpoints[i]
                    self.add_selection(editor, point, append=editor.shift_is_pressed)

                    #self.pfdinfo.setText("Count1: {} Count2: {}".format(self.pfd.count1, self.pfd.count2))
                    """self.current_index.setText("Index: {}".format(i))
                    self.current_coords.setText("Pos: x:{} y:{}".format(point.x, point.y))
                    neighbours = []
                    col = ["W", "R", "G", "B"]
                    for j, link in enumerate(point.neighbours):
                        if link.exists():
                            neighbours.append(f"Link{col[j]}: x:{link.point.x} y:{link.point.y} edge: {[link.edge.distance, link.edge.priority, link.edge.flags]}")
                    self.current_val1.setText("\n".join(neighbours))"""
                    #self.current_val2.setText("{} {} {} {}".format(*point.values[4:8]))
                    self.dirty = True
                else:
                    self.clear_selection(editor)

                if len(self.selected_points) == 1:
                    self.edge1_edit.update_value()
                    self.edge2_edit.update_value()
                    self.edge3_edit.update_value()
                    self.edge4_edit.update_value()

        print("heya", x, y)

    def buttonaction_load_gradient(self, editor):
        path = self.gradient_path if self.gradient_path else editor.pathsconfig["xml"].replace(".xml", "_Gradient.png")

        filepath, chosentype = QtWidgets.QFileDialog.getOpenFileName(
            editor, "Open File",
            path,
            "B&W Gradient (*.png);;All files (*)",
            None)

        if filepath:
            img = Image.open(filepath)
            pixels = img.load()
            for x in range(512):
                for y in range(512):
                    vals = pixels[x,y]
                    self.pfd.set_map_val(x, 511-y, vals[0])


    def buttonaction_save_gradient(self, editor):
        path = self.gradient_path if self.gradient_path else editor.pathsconfig["xml"].replace(".xml", "_Gradient.png")

        filepath, chosentype = QtWidgets.QFileDialog.getSaveFileName(
            editor, "Save File",
            path,
            "B&W Gradient (*.png);;All files (*)",
            None)

        if filepath:
            img = Image.new("RGB", (512, 512), color=(255, 255, 255))
            pixels = img.load()
            for x in range(512):
                for y in range(512):
                    val = self.pfd.get_map_val(x,y)
                    pixels[x,511-y] = (val, val, val)

            img.save(filepath)
            self.gradient_path = filepath


    def buttonaction_load_pfd_file(self, editor):
        path = self.pfd_path if self.gradient_path else editor.pathsconfig["xml"].replace(".xml", ".pfd")

        filepath, chosentype = QtWidgets.QFileDialog.getOpenFileName(
            editor, "Open File",
            path,
            "BW1 Pathfinding Data (*.pfd);;All files (*)",
            None)

        if filepath:
            with open(filepath, "rb") as f:
                editor.pfd = PFD.from_file(f)
                self.pfd = editor.pfd
                self.render_distributor.reset()
                for point in self.pfd.pathpoints:
                    self.render_distributor.add_point(point)
                self.dirty = True
            """self.texture.img_data = Image.new("RGB", (8192+1, 8192+1), color=(128, 128, 128))
            editor.level_view.overlay_texture.img_data = self.texture.img_data
            img = self.texture.img_data
            for point in self.pfd.pathpoints:
                x, y = point.x, point.y
                img.putpixel((x, y), (255, 0, 0))

            self.do_update = True
            self.curr = None"""
            editor.level_view.do_redraw()
            self.pfd_path = filepath
            open_message_dialog("Loaded!", parent=editor)

    def buttonaction_save_pfd_file(self, editor):
        path = self.pfd_path if self.gradient_path else editor.pathsconfig["xml"].replace(".xml", ".pfd")

        filepath, chosentype = QtWidgets.QFileDialog.getSaveFileName(
            editor, "Save File",
            path,
            "BW1 Pathfinding Data (*.pfd);;All files (*)",
            None)

        if filepath:
            tmp = BytesIO()
            self.pfd.write(tmp)
            with open(filepath, "wb") as f:
                f.write(tmp.getvalue())
            self.pfd_path = filepath
            open_message_dialog("Saved!", parent=editor)

    def test_intersect(self, p1_x, p1_y, p2_x, p2_y, p3_x, p3_y, p4_x, p4_y):
        if (p1_x == p2_x and p1_y == p2_y) or (p3_x == p4_x and p3_y == p4_y):
            return False, False, False

        denom = (p4_y - p3_y) * (p2_x - p1_x) - (p4_x - p3_x)*(p2_y - p1_y)
        if denom == 0:
            return False, False, False

        ua = ((p4_x - p3_x) * (p1_y - p3_y) - (p4_y - p3_y) * (p1_x - p3_x)) / denom
        ub = ((p2_x - p1_x) * (p1_y - p3_y) - (p2_y - p1_y) * (p1_x - p3_x)) / denom
        if 0 <= ua <= 1.0 and 0 <= ub <= 1.0:
            return ua, p1_x + ua*(p2_x - p1_x), p1_y + ua*(p2_y - p1_y)
        else:
            return False, False, False

    def buttonaction_waypoint(self, editor: "bw_editor.LevelEditor"):
        point = editor.get_selected_obj()
        for id, obj in editor.level_file.objects.items():
            if obj.type == "cWaypoint":
                if hasattr(obj, "_backref"):
                    del obj._backref

        if point is not None and point.type == "cWaypoint":
            for id, obj in editor.level_file.objects.items():
                if obj.type == "cWaypoint" and obj.NextWP is not None:
                    obj.NextWP._backref = obj

            root = point
            while hasattr(root, "_backref"):
                root = root._backref

            self.bake_waypoint_to_pfd(root)

    def bake_waypoint_to_pfd(self, point):
        traverse = [point]
        visited = []
        point_pairs = []
        next_next = point.NextWP
        #point_pairs.append((start_mat.x, start_mat.z, next_mat.x, next_mat.z))
        #print(point_pairs)
        while traverse:
            next_point = traverse.pop(0)
            visited.append(next_point)
            next_next = next_point.NextWP
            if next_next is not None:
                start_mat = next_point.getmatrix()
                next_mat = next_next.getmatrix()

                point_pairs.append((start_mat.x, start_mat.z, next_mat.x, next_mat.z))
                if next_next not in visited:
                    traverse.append(next_next)

        overlaps = 0
        for x1, y1, x2, y2 in point_pairs:
            p = self.get_closest_point(x1, y1, tolerance=2)
            if p is not None:
                overlaps += 1
        if overlaps > 3:
            if not open_yesno_box(f"The path has a lot of overlap with existing PFD points. ({overlaps})",
                              "Are you sure you want to continue?"):
                return

        print("Testing intersections...", len(point_pairs))
        last = None
        for x1, y1, x2, y2 in point_pairs:
            intersections = []
            checked = {}
            for point in self.pfd.pathpoints:
                for link in point.neighbours:
                    if link.exists():
                        if link.point in checked:
                            continue
                        checked[point] = True
                        dist, x, y = self.test_intersect(x1, y1, x2, y2, point.x, point.y, link.point.x, link.point.y)

                        if dist is not False and dist > 0:

                            intersections.append((dist, x, y, point, link))

            print("intersections", len(intersections))
            intersections.sort(key=lambda x: x[0])
            if last is None:
                last = PathfindPoint.new(x1, y1)
            newpoints = [last]


            for d, x, y, point, link in intersections:
                intersection_point = PathfindPoint.new(x, y)
                other = link.point
                point.remove_neighbour(other)
                point.connect(intersection_point, prio=0)
                intersection_point.connect(other, prio=0)
                last.connect(intersection_point, prio=0)
                last = intersection_point
                newpoints.append(intersection_point)
            end = PathfindPoint.new(x2, y2)
            newpoints.append(end)
            last.connect(end, prio=0)
            last = end

            for point in newpoints:
                if point.pathgroup is None:
                    self.pfd.pathpoints.append(point)
                    self.render_distributor.add_point(point)


    def render_post(self, viewer: "bw_widgets.BolMapViewer"):
        self.hide_pfd: QtWidgets.QCheckBox
        if not self.hide_pfd.isChecked():
            return

        """for meshindex, mesh in viewer.bwterrain.meshes.items():
            for tile in mesh:
                glBegin(GL_TRIANGLE_FAN)
                quad = tile.lod_quad
                glColor4f(1.0, 0.5, 1, 1)
                glVertex3f(quad.p1.x, quad.p1.z, quad.p1.y+100)
                glColor4f(0.0, 0.5, 1, 1)
                glVertex3f(quad.p2.x, quad.p2.z, quad.p2.y+100)
                glColor4f(0.0, 0.5, 1, 1)
                glVertex3f(quad.p4.x, quad.p4.z, quad.p4.y+100)
                glColor4f(0.0, 1.0, 1, 1)
                glVertex3f(quad.p3.x, quad.p3.z, quad.p3.y+100)
                glEnd()"""

        if self.pos is not None and False:
            x, y, z = self.pos.x, self.pos.y, self.pos.z
            #glDisable(GL_DEPTH_TEST)
            glColor4f(1.0, 0.5, 1, 1)
            glLineWidth(2.0)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(x - 2, y - 2, z)
            glVertex3f(x + 2, y - 2, z)
            glVertex3f(x + 2, y + 2, z)
            glVertex3f(x - 2, y + 2, z)
            glEnd()
            #glEnable(GL_DEPTH_TEST)

        if self.raycast is not None:
            glBegin(GL_LINES)
            glColor4f(0.0, 0.5, 1, 1)
            glVertex3f(self.raycast.origin.x, self.raycast.origin.y, self.raycast.origin.z)
            end = self.raycast.origin + self.raycast.direction*1000
            glColor4f(1.0, 0.5, 1, 1)
            glVertex3f(end.x, end.y, end.z)
            glEnd()

        """for chunk in viewer.bwterrain.chunk_groups:
            if hasattr(chunk, "hit") and chunk.hit:
                glColor4f(1.0, 0, 0, 1)

                for quad in chunk.aabb.quads:

                    glBegin(GL_LINE_LOOP)
                    glVertex3f(quad.tri1.origin.x, quad.tri1.origin.z, quad.tri1.origin.y)
                    glVertex3f(quad.tri1.p2.x, quad.tri1.p2.z, quad.tri1.p2.y)
                    glVertex3f(quad.tri1.p3.x, quad.tri1.p3.z, quad.tri1.p3.y)
                    glEnd()
                    glBegin(GL_LINE_LOOP)
                    glVertex3f(quad.tri2.origin.x, quad.tri2.origin.z, quad.tri2.origin.y)
                    glVertex3f(quad.tri2.p2.x, quad.tri2.p2.z, quad.tri2.p2.y)
                    glVertex3f(quad.tri2.p3.x, quad.tri2.p3.z, quad.tri2.p3.y)
                    glEnd()"""

        for tile in self.hit_tiles:
            glColor4f(1.0, 1, 0, 1)
            for quad in tile.aabb.quads:

                glBegin(GL_LINE_LOOP)
                glVertex3f(quad.tri1.origin.x, quad.tri1.origin.z, quad.tri1.origin.y)
                glVertex3f(quad.tri1.p2.x, quad.tri1.p2.z, quad.tri1.p2.y)
                glVertex3f(quad.tri1.p3.x, quad.tri1.p3.z, quad.tri1.p3.y)
                glEnd()
                glBegin(GL_LINE_LOOP)
                glVertex3f(quad.tri2.origin.x, quad.tri2.origin.z, quad.tri2.origin.y)
                glVertex3f(quad.tri2.p2.x, quad.tri2.p2.z, quad.tri2.p2.y)
                glVertex3f(quad.tri2.p3.x, quad.tri2.p3.z, quad.tri2.p3.y)
                glEnd()

        if True or self.dirty:
            self.quads.reset()
            self.lines.reset_lines()
            self.selected_quads.reset()

            for pointx, pointy in self.visual_points:
                size = 0.5
                h = 100
                x = pointx
                y = pointy
                self.quads.add_quad((x + size, h + 1, y + size),
                                     (x - size, h + 1, y + size),
                                     (x - size, h + 1, y - size),
                                     (x + size, h + 1, y - size),
                                     (1.0, 0.0, 0.0))

            if self.pfd is not None:
                for point in self.selected_points:

                    x = point.x
                    y = point.y
                    size = 0.5
                    h = None #viewer.bwterrain.check_height_interpolate(x, y)
                    if h is None:
                        h = 100
                    self.selected_quads.add_quad((x + size, h+1, y + size),
                                        (x - size, h+1, y + size),
                                        (x - size, h+1, y - size),
                                        (x + size, h+1, y - size),
                                        (1.0, 0.0, 0.0))

                    for i, link in enumerate(point.neighbours):
                        if link.exists():


                            start = (x, 100, y)
                            end_x = link.point.x
                            end_y = link.point.y

                            h2 = None #viewer.bwterrain.check_height_interpolate(end_x, end_y)
                            if h2 is None:
                                h2 = 100

                            end = ((x+end_x)/2.0, (h+h2)/2+0.5, (y+end_y)/2.0)
                            self.lines.add_line(start, end, COLORS[i])
            self.dirty = True

        glDisable(GL_DEPTH_TEST)
        # glActiveTexture(GL_TEXTURE0)
        # glBindTexture(GL_TEXTURE_2D, self.texture.id)

        glDisable(GL_ALPHA_TEST)
        glEnable(GL_BLEND)

        self.render_distributor.render()

        self.quads.bind()
        self.quads.render()
        self.quads.unbind()

        self.selected_quads.bind()
        self.selected_quads.render()
        self.selected_quads.unbind()
        glLineWidth(2.0)
        self.lines.bind()
        self.lines.render()
        self.lines.unbind()
        glLineWidth(1.0)
        glEnable(GL_ALPHA_TEST)
        glDisable(GL_BLEND)

        glEnable(GL_DEPTH_TEST)

        return



        if self.texture is None:
            self.texture = OpenGLTexture.create_dummy(64, 64)



        if False and self.texture is None:
            print("Remaking...")
            self.texture = OpenGLTexture.create_dummy(64, 64)
            #self.texture.img_data = Image.open(r"C:\Users\User\Documents\Modding\BattalionWars\PFDTool\C1_Bonus.pfd.png")

            with open(r"C:\Users\User\Documents\Tmp\C3_XDay.pfd", "rb") as f:
                self.pfd = PFD.from_file(f)

            for i in range(len(self.pfd.map)):
                if self.pfd.map[i] not in (0xAA, 0xFF):
                    self.pfd.map[i] = 0xFF

            with open(r"D:\Wii games\BattWars\P-G8WP\files\Data\CompoundFiles\C3_XDay.pfd", "wb") as f:
                self.pfd.write(f)

            if True:
                self.texture.img_data = Image.new("RGB", (8192+1, 8192+1), color=(128, 128, 128))
                #self.texture.img_data = Image.new("RGB", (512, 512))
                viewer.overlay_texture.img_data = self.texture.img_data

                img = self.texture.img_data
                for point in self.pfd.pathpoints:
                    x, y = point.x, point.y
                    img.putpixel((x, y), (255, 0, 0))
                #for x in range(0, 512):
                #    for y in range(0, 512):
                #        img.putpixel((x,y), (x//2, y//2, 0))
                viewer.overlay_texture.update()
            else:
                self.texture.img_data = Image.new("RGB", (512, 512), color=(128, 128, 128))
                # self.texture.img_data = Image.new("RGB", (512, 512))
                viewer.overlay_texture.img_data = self.texture.img_data
                img = self.texture.img_data

                for x in range(512):
                    for y in range(512):
                        val = self.pfd.data3[x+y*512]
                        if x < 256:
                            x = x*2
                        else:
                            x = (x-256)*2+1
                        #y = 511-y
                        if x - 3 > 0:
                            img.putpixel((x-3, y), (val, val, val))
                self.texture.img_data.save("pfdimg.png")
                viewer.overlay_texture.update()
            """
            self.texture.mag_filter = GL_NEAREST
            self.texture.init()
            material = Material(self.texture.id, (1.0, 1.0, 1.0, 0.9))

            self.model = TexturedMesh(material)
            self.model.vertex_texcoords = [(0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0)]

            extent = 2048

            self.model.vertex_positions = [(-extent, -extent, 0),
                                           (extent, -extent, 0),
                                           (-extent, extent, 0),
                                           (extent, extent, 0)]

            self.model.triangles = [((0, 0), (1, 1), (2, 2)), ((2, 2), (1, 1), (3, 3))]"""

        else:
            if self.do_update:
                viewer.overlay_texture.update()
                print("About to update...")
                self.texture.update()
                self.do_update = False
                print("Updated..")

            glDisable(GL_DEPTH_TEST)
            #glActiveTexture(GL_TEXTURE0)
            #glBindTexture(GL_TEXTURE_2D, self.texture.id)

            glDisable(GL_ALPHA_TEST)
            glEnable(GL_BLEND)

            #self.model.render()

            if self.curr is not None:
                point = self.pfd.pathpoints[self.curr]
                x, y = (point.x/2.0)-2048, (point.y/2.0)-2048
                glColor4f(0.5, 0.5, 1, 1)
                glLineWidth(2.0)
                glBegin(GL_TRIANGLE_FAN)
                glVertex3f(x-2, y-2, 0)
                glVertex3f(x+2, y-2, 0)
                glVertex3f(x+2, y+2, 0)
                glVertex3f(x-2, y+2, 0)
                glEnd()

                color = [(1.0, 0.0, 0.0, 1.0),
                         (0.0, 1.0, 0.0, 1.0),
                         (0.0, 0.0, 1.0, 1.0),
                         (0.0, 0.0, 0.0, 1.0)]

                glBegin(GL_LINES)
                for i, link in enumerate(point.neighbours):
                    if link.exists():
                        glColor4f(*color[i])
                        point2 = link.point
                        x2, y2 = (point2.x / 2.0) - 2048, (point2.y / 2.0) - 2048
                        glVertex3f(x, y, 0)
                        glVertex3f(x2, y2, 0)
                glEnd()


            glEnable(GL_ALPHA_TEST)
            glDisable(GL_BLEND)

            glEnable(GL_DEPTH_TEST)

    def plugin_init(self, editor: "bw_editor.LevelEditor"):
        self.MODE_ADD_PATHPOINT = editor.level_view.mouse_mode.add_plugin_mode("PFD_ADD")
        self.MODE_CONNECT_PATHPOINT = editor.level_view.mouse_mode.add_plugin_mode("PFD_CONNECT")
        self.MODE_DISCONNECT_PATHPOINT = editor.level_view.mouse_mode.add_plugin_mode("PFD_DISCONNECT")
        self.MODE_MAKE_PATH_GRID = editor.level_view.mouse_mode.add_plugin_mode("PFD_GRID")

        editor.level_view.mouse_mode.plugin_set_change_from_callback(
            self.MODE_ADD_PATHPOINT,
            partial(self.cancel_mode, editor))
        editor.level_view.mouse_mode.plugin_set_change_from_callback(
            self.MODE_CONNECT_PATHPOINT,
            partial(self.cancel_mode, editor))
        editor.level_view.mouse_mode.plugin_set_change_from_callback(
            self.MODE_DISCONNECT_PATHPOINT,
            partial(self.cancel_mode, editor))

        editor.level_view.mouse_mode.plugin_set_change_from_callback(
            self.MODE_MAKE_PATH_GRID,
            partial(self.cancel_mode, editor))

    def unload(self):
        print("unload...")
        self.texture = None
        """if self.texture is not None and self.texture.id is not None:
            glDeleteTextures(1, self.texture.id)
        self.texture = None"""
