import json
import numpy
from math import sin, cos
from OpenGL.GL import *
from OpenGL.GLU import *
from lib.vectors import Vector3

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bw_widgets import BolMapViewer
    from widgets.filter_view import FilterViewMenu

with open("lib/color_coding.json", "r") as f:
    object_colors = json.load(f)
    #colors_selection = colors_json["SelectionColor"]
    #colors_area  = colors_json["Areas"]


def lerp(x0, x1, y0, y1, val):
    if val < x0:
        return y0
    elif val > x1:
        return y1
    else:
        return (y0*(x1-val)+y1*(val-x0))/(x1-x0)


class Scene(object):
    def __init__(self):
        self.objects = {}
        self.model = {}

        self.modelinstances = {}
        self.renderedmodels = []

    def add_matrix(self, modelname, mtx):
        if modelname not in self.modelinstances:
            self.renderedmodels.append(modelname)
            self.modelinstances[modelname] = [mtx]
        else:
            self.modelinstances[modelname].append(mtx)

    def fullreset(self):
        self.renderedmodels = []

    def reset(self):
        for key in list(self.objects.keys()):
            del self.objects[key]
            self.objects[key] = ([], [])
        del self.modelinstances
        self.modelinstances = {}

    def set_model(self, type, model):
        self.objects[type] = None
        self.model[type] = model


class Graphics(object):
    def __init__(self, renderwidget):
        self.rw: BolMapViewer = renderwidget

        self.scene = Scene()
        self.scene.set_model("generic", self.rw.models.cubev2)
        self.scene.set_model("cCamera", self.rw.models.camera)

        self.models_scene = []

        self._dirty = True

        self.render_everything_once = True

    def set_dirty(self):
        self.rw.models.cubev2.mtxdirty = True
        self.rw.models.camera.mtxdirty = True
        self.rw.models.billboard.mtxdirty = True
        for model in self.rw.bwmodelhandler.instancemodels.values():
            model.mtxdirty = True

        self._dirty = True

    def set_dirty_limited(self, modelnames):
        self.rw.models.cubev2.mtxdirty = True
        self.rw.models.camera.mtxdirty = True
        self.rw.models.billboard.mtxdirty = True
        for modelname in modelnames:
            model = self.rw.bwmodelhandler.instancemodels[modelname]
            model.mtxdirty = True

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
        vismenu = self.rw.visibility_menu

        extradataarrays = {}
        for key in self.scene.objects:
            extradataarrays[key] = []

        if len(objlist) > 0xFFFF:
            raise RuntimeError("More than 64k objects, cannot select.")

        for i, obj in enumerate(objlist):
            if vismenu.object_visible(obj.type):
                colorid = (0x10000100 + (i << 12))
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
        globalmtx = None
        globalextradata = None

        globalsetting = 0
        if self.rw.is_topdown():
            globalsetting |= 1
        vismenu: FilterViewMenu = self.rw.visibility_menu
        visible = vismenu.object_visible
        visible3d = vismenu.object_3d_visible

        empty = False
        #self.set_dirty()
        if self.is_dirty():
            self.scene.fullreset()
            globalmtx = []
            globalextradata = []

            self.models_scene = []

            bwterrain = self.rw.bwterrain
            waterheight = self.rw.waterheight
            empty = True
            for obj in rw.level_file.objects_with_positions.values():
                if not visible(obj.type):
                    continue
                empty = False

                if obj.type in self.scene.objects:
                    mtx, extradata = self.scene.objects[obj.type]
                else:
                    mtx, extradata = default_matrices, default_extradata

                currmtx = obj.getmatrix().mtx.copy()
                height = obj.calculate_height(bwterrain, self.rw.waterheight)
                if height is not None:
                    currmtx[13] = height

                obj.height = currmtx[13]

                mtx.append(currmtx)
                iconoffset = obj.iconoffset

                modelname = obj._modelname
                if modelname is not None and visible3d(obj.type):
                    self.scene.add_matrix(modelname, currmtx)

                flag = 0
                if obj in selected:
                    flag |= 1
                extradata.append(flag)

                r, g, b, a = object_colors[obj.type]
                extradata.append(int(r * 255))
                extradata.append(int(g * 255))
                extradata.append(int(b * 255))

                if iconoffset is not None:
                    globalmtx.append(currmtx)
                    flag = 0
                    if obj in selected:
                        flag |= 1

                    globalextradata.append(flag)
                    x,y = iconoffset
                    globalextradata.append(int(x))
                    globalextradata.append(int(y))
                    globalextradata.append(int(b * 255))
            self.reset_dirty()

        # self.models.cubev2.mtxdirty = True

        drawn = 0
        for objtype, model in self.scene.model.items():
            if not visible(objtype):
                continue

            mtx, extradata = self.scene.objects[objtype]

            if empty:
                mtx = numpy.array([], dtype=numpy.uint8)
                extradata = numpy.array([], dtype=numpy.uint8)
            elif not mtx:
                mtx, extradata = None, None
            else:
                mtx = numpy.concatenate(mtx)
                extradata = numpy.array(extradata, dtype=numpy.uint8)

            model.bind(mtx, extradata)
            coloruniform = model.program.getuniformlocation("selectioncolor")
            glUniform4f(coloruniform, *object_colors["SelectionColor"])
            model.instancedrender()
            model.unbind()


        glDisable(GL_CULL_FACE)

        glEnable(GL_TEXTURE_2D)
        glActiveTexture(GL_TEXTURE0)
        rw.models.billboard.maintex.bind()
        glActiveTexture(GL_TEXTURE1)
        rw.models.billboard.outlinetex.bind()

        if globalmtx is None:
            rw.models.billboard.bind(None, None)
        elif len(globalmtx) == 0:
            rw.models.billboard.bind(numpy.array(globalmtx, dtype=numpy.uint8),
                                     numpy.array(globalextradata, dtype=numpy.uint8))
        else:
            rw.models.billboard.bind(numpy.concatenate(globalmtx),
                                     numpy.array(globalextradata, dtype=numpy.uint8))
        texuniform = rw.models.billboard.program.getuniformlocation("tex")
        outlinetexuniform = rw.models.billboard.program.getuniformlocation("outlinetex")
        coloruniform = rw.models.billboard.program.getuniformlocation("selectioncolor")

        glUniform1i(texuniform, 0)
        glUniform1i(outlinetexuniform, 1)
        glUniform4f(coloruniform, *object_colors["SelectionColor"])

        mtxuniform = rw.models.billboard.program.getuniformlocation("mvmtx")
        projuniform = rw.models.billboard.program.getuniformlocation("proj")
        glUniformMatrix4fv(mtxuniform, 1, False, glGetFloatv(GL_MODELVIEW_MATRIX))
        glUniformMatrix4fv(projuniform, 1, False, glGetFloatv(GL_PROJECTION_MATRIX))

        globaluniform = rw.models.billboard.program.getuniformlocation("globalsetting")
        glUniform1i(globaluniform, globalsetting)

        zoomscale = lerp(0.28, 0.64, 1.0, 2.8, self.rw.zoom_factor)
        #zoomuniform =
        print(self.rw.zoom_factor, zoomscale)
        facuniform = rw.models.billboard.program.getuniformlocation("scalefactor")
        glUniform1f(facuniform, zoomscale)
        rw.models.billboard.instancedrender()
        rw.models.billboard.unbind()
        glActiveTexture(GL_TEXTURE0)
        glDisable(GL_TEXTURE_2D)
        glActiveTexture(GL_TEXTURE1)
        glDisable(GL_TEXTURE_2D)
        glUseProgram(0)
        glBindTexture(GL_TEXTURE_2D, 0)

        glEnable(GL_CULL_FACE)

        glActiveTexture(GL_TEXTURE0)
        glEnable(GL_TEXTURE_2D)

        cam_x, cam_z = rw.cam_x, rw.cam_z

        if self.render_everything_once:
            for mtx, x, z, modelname in self.models_scene:
                rw.bwmodelhandler.rendermodel(modelname, mtx, rw.bwterrain, 0)
            self.render_everything_once = False

        for meshname in self.scene.renderedmodels:
            if meshname in self.scene.modelinstances:
                mtxlist = self.scene.modelinstances[meshname]
                if not mtxlist:
                    mtx, extradata = None, None
                else:
                    mtx = numpy.concatenate(mtxlist)
            else:
                mtx, extradata = None, None

            #if len(mtx) > 0:
            model = self.rw.bwmodelhandler.instancemodels[meshname]
            model.bind(mtx, numpy.array([], dtype=numpy.uint8))
            model.instancedrender(self.rw.bwmodelhandler.textures)
            model.unbind()
        """else:
            inrange = []
            for mtx, x, z, modelname in self.models_scene:
                if abs(cam_x - x) < 1000 and abs(cam_z - z) < 1000:
                    dist = (cam_x - x)**2 + (cam_z - z)**2
                    inrange.append((modelname, mtx, dist))

            inrange.sort(key=lambda x: x[2])
            for i, v in enumerate(inrange):
                if i > 400:
                    break

                rw.bwmodelhandler.rendermodel(v[0], v[1], rw.bwterrain, 0)"""

