from math import sqrt
# PyQt4 imports
from PyQt5 import QtGui, QtCore, QtOpenGL, QtWidgets
#from PyQt5.QtOpenGL import QOpenGLWidget
# PyOpenGL imports
from OpenGL.GL import *
import OpenGL.arrays.vbo as glvbo
from lib.vectors import Vector3, Triangle

from widgets.editor_widgets import catch_exception

def make_gradient(start, end, step=1, max=None):
    r1, g1, b1 = start
    r2, g2, b2 = end

    diff_r, diff_g, diff_b = r2-r1, g2-g1, b2-b1
    norm = sqrt(diff_r**2 + diff_g**2 + diff_b**2)
    norm_r, norm_g, norm_b = diff_r/norm, diff_g/norm, diff_b/norm

    gradient = []
    gradient.append((int(r1), int(g1), int(b1)))

    if max is not None:
        step = int((r2-r1)/norm_r)//max

    #curr_r, curr_g, curr_b = r1, g1, b1
    for i in range(0, int((r2-r1)/norm_r), step):
        curr_r = r1+i*norm_r
        curr_g = g1+i*norm_g
        curr_b = b1+i*norm_b
        gradient.append((int(curr_r), int(curr_g), int(curr_b)))
    gradient.append((int(r2), int(g2), int(b2)))
    return gradient

COLORS = []
for coltrans in [
    #((106, 199, 242), (190, 226, 241), 1), # Ocean level
    #((190, 226, 241), (120, 147, 78), 1), # Transition Ocean->Ground
    ((20, 20, 20), (230,230,230), 1),
    ((120, 147, 78), (147,182,95), 3), # Ground level
    ((147,182,95), (249, 239, 160), 3), # Higher areas, going into mountains, green to yellow
    ((249, 239, 160), (214, 127, 70), 3), # Even higher, yellow to brown
    ((214, 127, 70), (150, 93, 60), 4), # brown to dark brown #(119, 68, 39)
    ((150, 93, 60), (130,130, 130), 4), # dark brown to grey, very high
    (((130,130, 130), (250, 250, 250), 4))]: # grey to white, very very high

    start, end, repeat = coltrans
    for i, color in enumerate(make_gradient(start, end, step=8)):
        #if i % 2 == 0: continue
        for j in range(repeat):
            COLORS.append(color)

DO_GRAYSCALE = False

def draw_collision(verts, faces):
    biggest, smallest = None, None
    for x, y, z in verts:
        if biggest is None:
            biggest = smallest = y
        if y > biggest:
            biggest = y
        if y < smallest:
            smallest = y
    scaleheight = biggest - smallest
    if scaleheight == 0:
        scaleheight = 1

    print(len(COLORS))
    lightvec = Vector3(0, 1, -1)

    glBegin(GL_TRIANGLES)

    i = -1
    for v1, v2, v3 in faces:
        i += 1
        v1x, v1y, v1z = verts[v1[0]-1]
        v2x, v2y, v2z = verts[v2[0]-1]
        v3x, v3y, v3z = verts[v3[0]-1]

        # grayscale = ((v1y+v2y+v3y)/3.0)/scaleheight
        """average_y = max(v1y, v2y,v3y) - smallest#(v1y+v2y+v3y)/3.0 - smallest
        index = int((average_y/scaleheight)*len(COLORS))
        if index < 0:
            index = 0
        if index >= len(COLORS):
            index = len(COLORS)-1
        r, g, b = COLORS[index]
        glColor3f(r/256.0,g/256.0,b/256.0)"""

        if DO_GRAYSCALE:
            average_y = (v1y + v2y + v3y) / 3.0 - smallest
            grayscale = average_y / scaleheight

            glColor3f(grayscale, grayscale, grayscale)
            glVertex3f(v1x, -v1z, v1y)
            glVertex3f(v2x, -v2z, v2y)
            glVertex3f(v3x, -v3z, v3y)

        else:
            face = Triangle(Vector3(v1x, -v1z, v1y), Vector3(v2x, -v2z, v2y), Vector3(v3x, -v3z, v3y))
            if face.normal.norm() != 0:
                angle = lightvec.cos_angle(face.normal)
            else:
                angle = 0.0
            light = max(abs(angle), 0.3)

            average_y = v1y - smallest
            index = int((average_y / scaleheight) * len(COLORS))
            if index < 0:
                index = 0
            if index >= len(COLORS):
                index = len(COLORS) - 1
            r, g, b = (i * light for i in COLORS[index])
            glColor3f(r / 256.0, g / 256.0, b / 256.0)
            glVertex3f(v1x, -v1z, v1y)

            average_y = v2y - smallest
            index = int((average_y / scaleheight) * len(COLORS))
            if index < 0:
                index = 0
            if index >= len(COLORS):
                index = len(COLORS) - 1
            r, g, b = (i * light for i in COLORS[index])
            glColor3f(r / 256.0, g / 256.0, b / 256.0)
            glVertex3f(v2x, -v2z, v2y)

            average_y = v3y - smallest
            index = int((average_y / scaleheight) * len(COLORS))
            if index < 0:
                index = 0
            if index >= len(COLORS):
                index = len(COLORS) - 1
            r, g, b = (i * light for i in COLORS[index])
            glColor3f(r / 256.0, g / 256.0, b / 256.0)
            glVertex3f(v3x, -v3z, v3y)
    glEnd()

class GLPlotWidget(QtWidgets.QOpenGLWidget):
    # default window size
    width, height = 2000, 2000

    def set_size(self, width, height):
        self.width = width
        self.height = height

    def set_data(self, verts, faces):
        #Load 2D data as a Nx2 Numpy array.
        self.verts = verts
        self.faces = faces
        self.colors = None

    def set_color_data(self, facecolors):
        self.colors = facecolors

    def initializeGL(self):
        #Initialize OpenGL, VBOs, upload data on the GPU, etc.
        # background color
        #glClearColor(1.0, 1.0, 1.0, 0.0)
        pass
        # create a Vertex Buffer Object with the specified data
        #self.vbo = glvbo.VBO(self.data)

    @catch_exception
    def paintGL(self):
        #Paint the scene.
        # clear the buffer
        #gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # clear the screen
        glDisable(GL_CULL_FACE)
        # set yellow color for subsequent drawing rendering calls
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-6000.0, 6000.0, -6000.0, 6000.0, -3000.0, 2000.0)


        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        draw_collision(self.verts, self.faces)
        glFinish()
        print("drawn")

    def resizeGL(self, width, height):
        # Called upon window resizing: reinitialize the viewport.
        # update the window size
        self.width, self.height = width, height
        # paint within the whole window
        glEnable( GL_DEPTH_TEST )
        glViewport(0, 0, self.width, self.width)


# define a Qt window with an OpenGL widget inside it
class TempRenderWindow(QtWidgets.QMainWindow):
    def __init__(self, verts, faces, render_res):
        super(TempRenderWindow, self).__init__()
        # generate random data points
        # self.data = np.array(.2*rdn.randn(100000,2),dtype=np.float32)
        # initialize the GL widget
        self.widget = GLPlotWidget()
        self.widget.set_size(*render_res)
        self.widget.set_data(verts, faces)
        # put the window at the screen position (100, 100)
        self.setGeometry(100, 100, self.widget.width, self.widget.height)
        self.setCentralWidget(self.widget)
        #self.update()


if __name__ == '__main__':
    # import numpy for generating random data points
    import sys
    import numpy as np
    import numpy.random as rdn
    from py_obj import read_obj

    with open("tutorial.obj", "r") as f:
        verts, faces, normals = read_obj(f)



    # create the Qt App and window
    app = QtWidgets.QApplication(sys.argv)
    window = TempRenderWindow(verts, faces)
    window.show()
    app.exec_()
