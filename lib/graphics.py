import json
import numpy
from math import sin, cos
from OpenGL.GL import *
from OpenGL.GLU import *
from lib.vectors import Vector3

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bw_widgets import BolMapViewer

with open("lib/color_coding.json", "r") as f:
    object_colors = json.load(f)
    #colors_selection = colors_json["SelectionColor"]
    #colors_area  = colors_json["Areas"]


class Scene(object):
    def __init__(self):
        self.objects = {
            "generic": None,
            "cCamera": None
        }

        self.model = {
            "generic": None,
            "cCamera": None
        }

    def reset(self):
        for key in list(self.objects.keys()):
            del self.objects[key]
            self.objects[key] = ([], [])

    def set_model(self, type, model):
        self.model[type] = model


class Graphics(object):
    def __init__(self, renderwidget):
        self.rw: BolMapViewer = renderwidget

        self.scene = Scene()
        self.scene.set_model("generic", self.rw.models.cubev2)
        self.scene.set_model("cCamera", self.rw.models.camera)
        self._dirty = True

    def set_dirty(self):
        self.rw.models.cubev2.mtxdirty = True
        self.rw.models.camera.mtxdirty = True
        self._dirty = True

    def reset_dirty(self):
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def setup_ortho(self, width, height, offset_x, offset_z):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        zf = self.rw.zoom_factor
        # glOrtho(-6000.0, 6000.0, -6000.0, 6000.0, -3000.0, 2000.0)
        camera_width = width * zf
        camera_height = height * zf

        glOrtho(-camera_width / 2 - offset_x, camera_width / 2 - offset_x,
                -camera_height / 2 + offset_z, camera_height / 2 + offset_z, -120000.0, 80000.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def setup_perspective(self, width, height,):
        rw = self.rw
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75, width / height, 0.1, 4000.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        look_direction = Vector3(cos(rw.camera_horiz),
                                 sin(rw.camera_horiz),
                                 sin(rw.camera_vertical))
        # look_direction.unify()
        fac = 1.01 - abs(look_direction.z)
        # print(fac, look_direction.z, look_direction)

        gluLookAt(rw.offset_x, rw.offset_z, rw.camera_height,
                  rw.offset_x + look_direction.x * fac,
                  rw.offset_z + look_direction.y * fac,
                  rw.camera_height + look_direction.z,
                  0, 0, 1)

        rw.camera_direction = Vector3(look_direction.x * fac, look_direction.y * fac, look_direction.z)

    def render_select(self, objlist):
        rw = self.rw

        extradataarrays = {}
        for key in self.scene.objects:
            extradataarrays[key] = []


        if len(objlist) > 0xFFFF:
            raise RuntimeError("More than 64k objects, cannot select.")

        for i, obj in enumerate(objlist):
            colorid = (0x10000000 + (i << 12))
            if obj.type not in extradataarrays:
                extradataarrays["generic"].append(colorid)
            else:
                extradataarrays[obj.type].append(colorid)
        for key, model in self.scene.model.items():
            extradataarray = extradataarrays[key]
            extradata = numpy.array(extradataarray, dtype=numpy.uint32)
            model.bind_colorid(extradata)
            model.instancedrender()
            model.unbind()

        print("We queued up", len(objlist))

    def render_scene(self):
        rw = self.rw

        selected = rw.selected
        positions = rw.selected_positions

        glEnable(GL_CULL_FACE)
        # mtx = numpy.concatenate([obj.getmatrix().mtx for obj in self.level_file.objects_with_positions.values()])
        self.scene.reset()
        default_matrices, default_extradata = self.scene.objects["generic"]

        # self.models.cubev2.mtxdirty = True
        if self.is_dirty():
            for obj in rw.level_file.objects_with_positions.values():
                if obj.type in self.scene.objects:
                    mtx, extradata = self.scene.objects[obj.type]
                else:
                    mtx, extradata = default_matrices, default_extradata

                mtx.append(obj.getmatrix().mtx)
                value = 0
                if obj in selected:
                    extradata.append(255)
                else:
                    extradata.append(0)
                r, g, b, a = object_colors[obj.type]
                extradata.append(int(r * 255))
                extradata.append(int(g * 255))
                extradata.append(int(b * 255))

        # self.models.cubev2.mtxdirty = True

        drawn = 0
        for objtype, model in self.scene.model.items():
            mtx, extradata = self.scene.objects[objtype]
            if not mtx:
                mtx, extradata = None, None
            else:
                mtx = numpy.concatenate(mtx)
                extradata =  numpy.array(extradata, dtype=numpy.uint8)

            model.bind(mtx, extradata)
            model.instancedrender()
            model.unbind()