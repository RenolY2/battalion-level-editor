from math import sin, cos
from OpenGL.GL import *
from OpenGL.GLU import *
from lib.vectors import Vector3

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bw_widgets import BolMapViewer


class Graphics(object):
    def __init__(self, renderwidget):
        self.renderwidget: BolMapViewer = renderwidget

    def setup_ortho(self, width, height, offset_x, offset_z):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        zf = self.renderwidget.zoom_factor
        # glOrtho(-6000.0, 6000.0, -6000.0, 6000.0, -3000.0, 2000.0)
        camera_width = width * zf
        camera_height = height * zf

        glOrtho(-camera_width / 2 - offset_x, camera_width / 2 - offset_x,
                -camera_height / 2 + offset_z, camera_height / 2 + offset_z, -120000.0, 80000.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def setup_perspective(self, width, height,):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75, width / height, 0.1, 4000.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        look_direction = Vector3(cos(self.renderwidget.camera_horiz),
                                 sin(self.renderwidget.camera_horiz),
                                 sin(self.renderwidget.camera_vertical))
        # look_direction.unify()
        fac = 1.01 - abs(look_direction.z)
        # print(fac, look_direction.z, look_direction)

        gluLookAt(self.renderwidget.offset_x, self.renderwidget.offset_z, self.renderwidget.camera_height,
                  self.renderwidget.offset_x + look_direction.x * fac,
                  self.renderwidget.offset_z + look_direction.y * fac,
                  self.renderwidget.camera_height + look_direction.z,
                  0, 0, 1)

        self.renderwidget.camera_direction = Vector3(look_direction.x * fac, look_direction.y * fac, look_direction.z)