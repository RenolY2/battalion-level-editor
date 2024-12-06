import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
import PyQt6.QtOpenGLWidgets as QtOpenGLWidgets
import PyQt6.QtOpenGL as QtOpengl
import math
from collections import namedtuple
from typing import TYPE_CHECKING
from OpenGL.GL import *
from OpenGL.GLU import *
from lib.BattalionXMLLib import BattalionObject
from timeit import default_timer

if TYPE_CHECKING:
    import bw_editor


class UnitViewer(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self,
                 parent,
                 editor: "bw_editor.LevelEditor",
                 width=None,
                 height=None,
                 angle=math.pi/4.0,
                 record_image=False):

        super().__init__(parent)
        self.time = default_timer()
        self.angle = 0
        #self.timer = QtCore.QTimer()
        #self.timer.setInterval(30)
        #self.timer.timeout.connect(self.render_loop)
        #self.timer.start()
        if height is not None:
            self.setFixedHeight(height)
        if width is not None:
            self.setFixedWidth(width)

        self.editor: "bw_editor.LevelEditor" = editor

        self.scene = []
        self.camera_lookat = (0, 0, 0)
        self.radius = 20
        self.camera_from_height = 1
        self.img = None
        self.angle = angle
        self.vertical_angle = 0.5
        self.avg = (0, 0, 0)
        self.zoom = 100
        self.left_pressed = False
        self.last_mouse_x = None
        self.last_mouse_y = None
        self.record_image = record_image

    def set_scene_single_model(self, modelname):
        self.reset_scene()
        self.add_to_scene(modelname,
                    [1.0, 0.0, 0.0, 0.0,
                      0.0, 1.0, 0.0, 0.0,
                      0.0, 0.0, 1.0, 0.0,
                      0.0, 0.0, 0.0, 1.0])

    def reset_scene(self):
        self.scene = []

    def add_to_scene(self, modelname, mtx):
        self.scene.append((modelname, mtx))

    def wheelEvent(self, event):
        wheel_delta = event.angleDelta().y()

        if self.editor.editorconfig is not None:
            invert = self.editor.editorconfig.getboolean("invertzoom")
            if not invert:
                wheel_delta = -1*wheel_delta

        if wheel_delta < 0:
            self.zoom -= 1
            if self.zoom <= 1:
                self.zoom == 1

        elif wheel_delta > 0:
            self.zoom += 1
            if self.zoom > 200:
                self.zoom = 200


        self.update()

    def recalculate_camera(self):
        avgx = 0
        avgy = 0
        avgz = 0

        for modelname, mtx in self.scene:
            model = self.editor.level_view.bwmodelhandler.models[modelname]
            midx = model.boundsphere[0]+mtx[12]
            midy = model.boundsphere[1]+mtx[13]
            midz = model.boundsphere[2]+mtx[14]
            avgx += midx
            avgy += midy
            avgz += midz
        if len(self.scene) > 0:
            avgx = avgx / len(self.scene)
            avgy = avgy / len(self.scene)
            avgz = avgz / len(self.scene)

        maxdistx = 0
        maxdisty = 0
        maxdistz = 0

        for modelname, mtx in self.scene:
            model = self.editor.level_view.bwmodelhandler.models[modelname]
            midx = model.boundsphere[0] + mtx[12]
            midy = model.boundsphere[1] + mtx[13]
            midz = model.boundsphere[2] + mtx[14]

            distx = abs(midx-avgx + model.boundsphereradius)
            disty = abs(midy-avgy + model.boundsphereradius)
            distz = abs(midz-avgz + model.boundsphereradius)

            if distx > maxdistx:
                maxdistx = distx
            if disty > maxdisty:
                maxdisty = disty
            if distz > maxdistz:
                maxdistz = distz
        self.avg = (avgx, avgy, avgz)
        radius = (maxdistx**2 + maxdisty**2 + maxdistz**2)**0.5

        self.camera_lookat = (0, 0, avgy)
        self.camera_from_height = avgy
        self.radius = radius*1.1

    def render_loop(self):
        if not self.isVisible():
            self.timer.stop()
        delta = default_timer() - self.time
        self.time = default_timer()
        self.angle = math.pi/4.0

        self.update()

    def paintGL(self) -> None:
        glClearColor(0.8, 0.8, 0.8, 0.0)
        # glClearColor(*self.backgroundcolor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        width, height = self.width(), self.height()


        self.setup_camera(width, height)
        self.set_camera(self.angle, self.radius)


        glActiveTexture(GL_TEXTURE0)
        glEnable(GL_TEXTURE_2D)

        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GEQUAL, 0.5)
        glDisable(GL_BLEND)

        glMultMatrixf([1.0, 0.0, 0.0, 0.0,
                      0.0, 0.0, 1.0, 0.0,
                      0.0, 1.0, 0.0, 0.0,
                      0.0, 0.0, 0.0, 1.0])

        for modelname, mtx in self.scene:
            glPushMatrix()
            mtx2 = mtx.copy()
            mtx2[12] -= self.avg[0]
            mtx2[14] -= self.avg[2]
            glMultMatrixf(mtx2)
            self.editor.level_view.bwmodelhandler.render_model_inplace(modelname)
            glPopMatrix()
        glFinish()
        if self.record_image:
            pixels = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)

            img = QtGui.QImage(pixels, width, height, QtGui.QImage.Format.Format_RGBA8888)
            img.mirror()
            self.img = img

    def setup_camera(self, width, height):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75, width / height, 0.1, 4000.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            print("Pressed")
            self.left_pressed = True
            self.last_mouse_x = event.pos().x()
            self.last_mouse_y = event.pos().y()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.left_pressed:
            delta_x = event.pos().x() - self.last_mouse_x
            delta_y = event.pos().y() - self.last_mouse_y
            print(delta_x, delta_y)
            self.angle += delta_x*0.02
            self.vertical_angle += delta_y*0.02
            self.update()

            self.last_mouse_x = event.pos().x()
            self.last_mouse_y = event.pos().y()

    def mouseReleaseEvent(self, event):
        self.left_pressed = False

    def set_camera(self, angle, radius):
        zoomlevel = (self.zoom/100.0)**3
        if zoomlevel < 0.01: zoomlevel = 0.01
        x = math.sin(angle)*radius*zoomlevel*math.cos(self.vertical_angle)
        y = math.cos(angle)*radius*zoomlevel*math.cos(self.vertical_angle)
        z = math.sin(self.vertical_angle)*radius*zoomlevel+self.camera_from_height
        gluLookAt(x, y, z,
                  self.camera_lookat[0], self.camera_lookat[1], self.camera_lookat[2],
                  0, 0, 1)

    @classmethod
    def screenshot_objects(cls, objects, editor):
        angle = math.pi / 4.0
        if len(objects) == 1:
            obj = objects[0]
            if obj.type == "cTroop":
                angle = -math.pi * (3 / 4)

        opengl = cls(editor, editor, width=256, height=256, angle=angle)

        temp_scene = []
        count = 0
        midx, midy, midz = 0, 0, 0
        for obj in objects:
            obj: BattalionObject
            mtx = obj.getmatrix()
            if mtx is not None:
                selectedmodel = obj.modelname
                height = obj.height
                currmtx = mtx.mtx.copy()
                currmtx[13] = obj.height
                if selectedmodel is not None:
                    temp_scene.append((selectedmodel, currmtx))
                    midx += currmtx[12]
                    midy += currmtx[13]
                    midz += currmtx[14]
                    count += 1

        opengl.reset_scene()

        if count > 0:
            avgx = midx / count
            avgy = midy / count
            avgz = midz / count

            for model, mtx in temp_scene:
                mtx[12] = mtx[12] - avgx
                mtx[13] = mtx[13] - avgy
                mtx[14] = mtx[14] - avgz
                if count == 1:
                    mtx[0] = 1.0
                    mtx[1] = 0.0
                    mtx[2] = 0.0
                    mtx[3] = 0.0

                    mtx[4] = 0.0
                    mtx[5] = 1.0
                    mtx[6] = 0.0
                    mtx[7] = 0.0

                    mtx[8] = 0.0
                    mtx[9] = 0.0
                    mtx[10] = 1.0
                    mtx[11] = 0.0

                opengl.add_to_scene(model, mtx)
            opengl.recalculate_camera()
        opengl.record_image = True
        opengl.show()
        opengl.hide()
        img = opengl.img
        opengl.destroy()
        del opengl

        return img
