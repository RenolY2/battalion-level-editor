import json
from time import time
from OpenGL.GL import *
from .vectors import Vector3
from struct import unpack
import os
from OpenGL.GL import *

from PyQt6 import QtGui

with open("lib/color_coding.json") as f:
    colors = json.load(f)

#selectioncolor = colors["SelectionColor"]


def read_vertex(v_data):
    split = v_data.split("/")
    if len(split) >= 2:
        if split[1] == "":
            texcoord = None
        else:
            texcoord = int(split[1]) - 1
    else:
        texcoord = None
    v = int(split[0])
    return v, texcoord


class Mesh(object):
    def __init__(self, name):
        self.name = name
        self.primtype = "Triangles"
        self.vertices = []
        self.texcoords = []
        self.triangles = []
        self.lines = []

        self._vbo = None

        self.texture = None
        self._displist = None

    def generate_displist(self):
        if self._displist is not None:
            glDeleteLists(self._displist, 1)

        displist = glGenLists(1)
        glNewList(displist, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for v1, v2, v3 in self.triangles:
            v1i, v1coord = v1
            v2i, v2coord = v2
            v3i, v3coord = v3
            glVertex3f(*self.vertices[v1i])
            glVertex3f(*self.vertices[v2i])
            glVertex3f(*self.vertices[v3i])
        glEnd()
        glEndList()
        self._displist = displist

    def render(self):
        if self._displist is None:
            self.generate_displist()
        glCallList(self._displist)

    def render_colorid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        self.render()


class TexturedMesh(object):
    def __init__(self, material):
        self.triangles = []
        self.vertex_positions = []
        self.vertex_texcoords = []

        self.material = material
        self._displist = None

    def generate_displist(self):
        if self._displist is not None:
            glDeleteLists(self._displist, 1)

        displist = glGenLists(1)
        glNewList(displist, GL_COMPILE)
        glBegin(GL_TRIANGLES)

        for triangle in self.triangles:
            assert len(triangle) == 3
            for vi, ti in triangle:
                if self.material.tex is not None and ti is not None:
                    if ti >= len(self.vertex_texcoords):
                        print(len(self.vertex_texcoords), ti)
                    else:
                        glTexCoord2f(*self.vertex_texcoords[ti])
                glVertex3f(*self.vertex_positions[vi])

        glEnd()
        glEndList()
        self._displist = displist

    def render(self, selected=False):
        if self._displist is None:
            self.generate_displist()

        if self.material.tex is not None:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.material.tex)
        else:
            glDisable(GL_TEXTURE_2D)

        if not selected:
            if self.material.diffuse is not None:
                if len(self.material.diffuse) == 4:
                    glColor4f(*self.material.diffuse)
                else:
                    glColor3f(*self.material.diffuse)
            else:
                glColor3f(1.0, 1.0, 1.0)
        else:
            glColor4f(*selectioncolor)

        glCallList(self._displist)

    def render_coloredid(self, id):

        if self._displist is None:
            self.generate_displist()
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glCallList(self._displist)


class TexturedBWMesh(object):
    def __init__(self, texname):
        self.trilist = []


        self.texname = texname
        self._displist = None

    def generate_displist(self):
        if self._displist is not None:
            glDeleteLists(self._displist, 1)

        displist = glGenLists(1)
        glNewList(displist, GL_COMPILE)
        glBegin(GL_TRIANGLES)

        assert len(self.trilist) % 3 == 0
        for vtxpos, uv in self.trilist:
            if self.texname is not None and uv is not None:
                glTexCoord2f(*uv)
            glVertex3f(*vtxpos)

        glEnd()
        glEndList()
        self._displist = displist

    def render(self, texturearchive, selected=False):
        if self._displist is None:
            self.generate_displist()

        if self.texname is not None:
            result = texturearchive.get_texture(self.texname.lower())
            if result is not None:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, result[1])
            else:
                glDisable(GL_TEXTURE_2D)
        else:
            glDisable(GL_TEXTURE_2D)

        if not selected:
            #if self.material.diffuse is not None:
            #    glColor3f(*self.material.diffuse)
            #else:
            glColor3f(1.0, 1.0, 1.0)
        else:
            glColor4f(*selectioncolor)

        glCallList(self._displist)


class Material(object):
    def __init__(self, diffuse=None, texturepath=None):
        if texturepath is not None:
            ID = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, ID)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

            if texturepath.endswith(".png"):
                fmt = "png"
            elif texturepath.endswith(".jpg"):
                fmt = "jpg"
            else:
                raise RuntimeError("unknown tex format: {0}".format(texturepath))

            qimage = QtGui.QImage(texturepath, fmt)
            qimage = qimage.convertToFormat(QtGui.QImage.Format.Format_ARGB32)

            imgdata = bytes(qimage.bits().asarray(qimage.width() * qimage.height() * 4))

            glTexImage2D(GL_TEXTURE_2D, 0, 4, qimage.width(), qimage.height(), 0, GL_BGRA, GL_UNSIGNED_BYTE, imgdata)

            del qimage

            self.tex = ID
        else:
            self.tex = None

        self.diffuse = diffuse


class Model(object):
    def __init__(self):
        self.mesh_list = []
        self.named_meshes = {}

    def render(self):
        for mesh in self.mesh_list:
            mesh.render()

    def render_coloredid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        self.render()

    def add_mesh(self, mesh: Mesh):
        if mesh.name not in self.named_meshes:
            self.named_meshes[mesh.name] = mesh
            self.mesh_list.append(mesh)
        elif mesh.name != "":
            raise RuntimeError("Duplicate mesh name: {0}".format(mesh.name))
        else:
            self.mesh_list.append(mesh)

    @classmethod
    def from_obj(cls, f, scale=1.0, rotate=False):
        model = cls()
        vertices = []
        texcoords = []

        curr_mesh = None

        for line in f:
            line = line.strip()
            args = line.split(" ")

            if len(args) == 0 or line.startswith("#"):
                continue
            cmd = args[0]

            if cmd == "o":
                objectname = args[1]
                if curr_mesh is not None:
                    model.add_mesh(curr_mesh)
                curr_mesh = Mesh(objectname)
                curr_mesh.vertices = vertices

            elif cmd == "v":
                if "" in args:
                    args.remove("")
                x, y, z = map(float, args[1:4])
                if not rotate:
                    vertices.append((x*scale, y*scale, z*scale))
                else:
                    vertices.append((x * scale, z * scale, y * scale, ))

            elif cmd == "l":
                curr_mesh.lines.append((int(args[1])-1, int(args[2])-1))
            elif cmd == "f":
                if curr_mesh is None:
                    curr_mesh = Mesh("")
                    curr_mesh.vertices = vertices

                # if it uses more than 3 vertices to describe a face then we panic!
                # no triangulation yet.
                if len(args) == 5:
                    #raise RuntimeError("Model needs to be triangulated! Only faces with 3 vertices are supported.")
                    v1, v2, v3, v4 = map(read_vertex, args[1:5])
                    curr_mesh.triangles.append(((v1[0] - 1, None), (v3[0] - 1, None), (v2[0] - 1, None)))
                    curr_mesh.triangles.append(((v3[0] - 1, None), (v1[0] - 1, None), (v4[0] - 1, None)))

                elif len(args) == 4:
                    v1, v2, v3 = map(read_vertex, args[1:4])
                    curr_mesh.triangles.append(((v1[0]-1, None), (v3[0]-1, None), (v2[0]-1, None)))
        model.add_mesh(curr_mesh)
        return model
        #elif cmd == "vn":
        #    nx, ny, nz = map(float, args[1:4])
        #    normals.append((nx, ny, nz))


class TexturedModel(object):
    def __init__(self):
        self.mesh_list = []

    def render(self, selected=False, selectedPart=None):
        for mesh in self.mesh_list:
            mesh.render(selected)

    def render_coloredid(self, id):
        for mesh in self.mesh_list:
            mesh.render_coloredid(id)

    #def render_coloredid(self, id):
    #    glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
    #    self.render()

    """def add_mesh(self, mesh: Mesh):
        if mesh.name not in self.named_meshes:
            self.named_meshes[mesh.name] = mesh
            self.mesh_list.append(mesh)
        elif mesh.name != "":
            raise RuntimeError("Duplicate mesh name: {0}".format(mesh.name))
        else:
            self.mesh_list.append(mesh)"""

    @classmethod
    def from_obj_path(cls, objfilepath, scale=1.0, rotate=False):


        model = cls()
        vertices = []
        texcoords = []

        default_mesh = TexturedMesh(Material(diffuse=(1.0, 1.0, 1.0)))
        default_mesh.vertex_positions = vertices
        default_mesh.vertex_texcoords = texcoords
        material_meshes = {}
        materials = {}

        currmat = None

        objpath = os.path.dirname(objfilepath)
        with open(objfilepath, "r") as f:
            for line in f:
                line = line.strip()
                args = line.split(" ")

                if len(args) == 0 or line.startswith("#"):
                    continue
                cmd = args[0]

                if cmd == "mtllib":
                    mtlpath = " ".join(args[1:])
                    if not os.path.isabs(mtlpath):
                        mtlpath = os.path.join(objpath, mtlpath)

                    with open(mtlpath, "r") as g:
                        lastmat = None
                        lastdiffuse = None
                        lasttex = None
                        for mtl_line in g:
                            mtl_line = mtl_line.strip()
                            mtlargs = mtl_line.split(" ")

                            if len(mtlargs) == 0 or mtl_line.startswith("#"):
                                continue
                            if mtlargs[0] == "newmtl":
                                if lastmat is not None:
                                    if lasttex is not None and not os.path.isabs(lasttex):
                                        lasttex = os.path.join(objpath, lasttex)
                                    materials[lastmat] = Material(diffuse=lastdiffuse, texturepath=lasttex)
                                    lastdiffuse = None
                                    lasttex = None

                                lastmat = " ".join(mtlargs[1:])
                            elif mtlargs[0].lower() == "Kd":
                                r, g, b = map(float, mtlargs[1:4])
                                lastdiffuse = (r,g,b)
                            elif mtlargs[0].lower() == "map_kd":
                                lasttex = " ".join(mtlargs[1:])
                                if lasttex.strip() == "":
                                    lasttex = None

                        if lastmat is not None:
                            if lasttex is not None and not os.path.isabs(lasttex):
                                lasttex = os.path.join(objpath, lasttex)
                            materials[lastmat] = Material(diffuse=lastdiffuse, texturepath=lasttex)
                            lastdiffuse = None
                            lasttex = None

                elif cmd == "usemtl":
                    mtlname = " ".join(args[1:])
                    currmat = mtlname
                    if currmat not in material_meshes:
                        material_meshes[currmat] = TexturedMesh(materials[currmat])
                        material_meshes[currmat].vertex_positions = vertices
                        material_meshes[currmat].vertex_texcoords = texcoords

                elif cmd == "v":
                    if "" in args:
                        args.remove("")
                    x, y, z = map(float, args[1:4])
                    if not rotate:
                        vertices.append((x*scale, y*scale, z*scale))
                    else:
                        vertices.append((x * scale, z * scale, y * scale, ))

                elif cmd == "vt":
                    if "" in args:
                        args.remove("")
                    #x, y, z = map(float, args[1:4])
                    #if not rotate:
                    texcoords.append((float(args[1]), 1-float(args[2])  ))
                    #else:
                    #    vertices.append((x, y, ))

                #elif cmd == "l":
                #    curr_mesh.lines.append((int(args[1])-1, int(args[2])-1))
                elif cmd == "f":
                    if currmat is None:
                        faces = default_mesh.triangles
                    else:
                        faces = material_meshes[currmat].triangles

                    # if it uses more than 3 vertices to describe a face then we panic!
                    # no triangulation yet.
                    if len(args) == 5:
                        #raise RuntimeError("Model needs to be triangulated! Only faces with 3 vertices are supported.")
                        v1, v2, v3, v4 = map(read_vertex, args[1:5])
                        faces.append(((v1[0] - 1, v1[1]), (v3[0] - 1, v3[1]), (v2[0] - 1, v2[1])))
                        faces.append(((v3[0] - 1, v3[1]), (v1[0] - 1, v1[1]), (v4[0] - 1, v4[1])))

                    elif len(args) == 4:
                        v1, v2, v3 = map(read_vertex, args[1:4])
                        faces.append(((v1[0]-1, v1[1]), (v3[0]-1, v3[1]), (v2[0]-1, v2[1])))

            if len(default_mesh.triangles) > 0:
                model.mesh_list.append(default_mesh)

            for mesh in material_meshes.values():
                model.mesh_list.append(mesh)
            #model.add_mesh(curr_mesh)
            return model
            #elif cmd == "vn":
            #    nx, ny, nz = map(float, args[1:4])
            #    normals.append((nx, ny, nz))


class TexturedBWModel(TexturedModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_textures = []

        self.boundsphere = (0, 0, 0)
        self.boundsphereradius = 0

    def render(self, texarchive, selected=False):
        for mesh in self.mesh_list:
            mesh.render(texarchive, selected)

    def set_boundsphere(self, x, y, z, r):
        self.boundsphere = (x,y,z)
        self.boundsphereradius = r

ALPHA = 0.8


class Waterbox(Model):
    def __init__(self, corner_bottomleft, corner_topright):
        self.corner_bottomleft = corner_bottomleft
        self.corner_topright = corner_topright

    def render(self):
        x1,y1,z1 = self.corner_bottomleft
        x2,y2,z2 = self.corner_topright
        glColor4f(0.1, 0.1875, 0.8125, ALPHA)
        glBegin(GL_TRIANGLE_FAN) # Bottom, z1
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Front, x1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x1, y2, z1)
        glEnd()

        glBegin(GL_TRIANGLE_FAN) # Side, y1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Back, x2
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Side, y2
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Top, z2
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y1, z2)
        glEnd()


class SelectableModel(Model):
    def __init__(self):
        self.mesh_list = []
        self.named_meshes = {}
        self.displistSelected = None
        self.displistUnselected = None

    def generate_displists(self):
        for mesh in self.mesh_list:
            mesh.generate_displist()
        self.displistSelected = glGenLists(1)
        self.displistUnselected = glGenLists(1)
        glNewList(self.displistSelected, GL_COMPILE)
        self._render(True)
        glEndList()
        glNewList(self.displistUnselected, GL_COMPILE)
        self._render(False)
        glEndList()

    def render(self, selected=False):
        if selected:
            glCallList(self.displistSelected)
        else:
            glCallList(self.displistUnselected)

    def _render(self, selected=False):
        pass


class Cube(SelectableModel):
    def __init__(self, color=(0.9, 0.9,0.9, 1.0)):
        super().__init__()
        with open("resources/cube.obj", "r") as f:
            model = Model.from_obj(f, scale=4, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.mesh_list

        self.color = color

    def _render(self, selected=False):

        glEnable(GL_CULL_FACE)
        if selected:
            glColor4f(*selectioncolor)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)
        glCullFace(GL_FRONT)
        glPushMatrix()

        if selected:
            glScalef(1.7, 1.7, 1.7)
        else:
            glScalef(1.4, 1.4, 1.4)

        self.mesh_list[0].render()
        glPopMatrix()
        glCullFace(GL_BACK)

        glColor4f(*self.color)
        self.mesh_list[0].render()
        glDisable(GL_CULL_FACE)

    def render_coloredid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glPushMatrix()
        glScalef(1.2, 1.2, 1.2)
        self.mesh_list[0].render()
        glPopMatrix()


class GenericObject(SelectableModel):
    def __init__(self, bodycolor=(1.0, 1.0, 1.0, 1.0)):
        super().__init__()

        with open("resources/generic_object.obj", "r") as f:
            model = Model.from_obj(f, scale=150, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.named_meshes
        self.bodycolor = bodycolor

    def _render(self, selected=False):
        glEnable(GL_CULL_FACE)
        if selected:
            glColor4f(*selectioncolor)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)
        glCullFace(GL_FRONT)
        glPushMatrix()

        if selected:
            glScalef(1.5, 1.5, 1.5)
        else:
            glScalef(1.2, 1.2, 1.2)

        self.named_meshes["Cube"].render()
        glPopMatrix()
        glCullFace(GL_BACK)

        glColor4f(*self.bodycolor)
        self.named_meshes["Cube"].render()
        glColor4ub(0x09, 0x93, 0x00, 0xFF)
        self.named_meshes["tip"].render()
        #glColor4ub(0x00, 0x00, 0x00, 0xFF)
        #self.mesh_list[2].render()
        glDisable(GL_CULL_FACE)

    def render_coloredid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glPushMatrix()
        glScalef(1.2, 1.2, 1.2)
        self.named_meshes["Cube"].render()
        glPopMatrix()


class GenericComplexObject(GenericObject):
    def __init__(self, modelpath, height, tip, eyes, body, rest):
        self.scale = 10
        with open(modelpath, "r") as f:
            model = Model.from_obj(f, scale=self.scale, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.mesh_list

        self._tip = tip
        self._eyes = eyes
        self._body = body
        self._height = height
        self._rest = rest

    def render(self, selected=False):
        glEnable(GL_CULL_FACE)
        if selected:
            glColor4f(*selectioncolor)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)
        glCullFace(GL_FRONT)
        glPushMatrix()
        glTranslatef(0.0, 0.0, self._height * self.scale)
        if selected:
            glScalef(1.5, 1.5, 1.5)
        else:
            glScalef(1.2, 1.2, 1.2)

        self.mesh_list[self._body].render()
        glPopMatrix()
        glCullFace(GL_BACK)
        glPushMatrix()
        glTranslatef(0.0, 0.0, self._height*self.scale)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        self.mesh_list[self._body].render()
        glColor4ub(0x09, 0x93, 0x00, 0xFF)
        self.mesh_list[self._tip].render() # tip
        glColor4ub(0x00, 0x00, 0x00, 0xFF)
        self.mesh_list[self._eyes].render() # eyes

        glPopMatrix()

        if selected:
            glColor4f(*selectioncolor)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)

        self.mesh_list[self._rest].render()
        glDisable(GL_CULL_FACE)

    def render_coloredid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glPushMatrix()
        glTranslatef(0.0, 0.0, self._height * self.scale)

        self.mesh_list[self._body].render()
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0.0, 0.0, self._height*self.scale)
        self.mesh_list[self._body].render()
        self.mesh_list[self._tip].render() # tip
        self.mesh_list[self._eyes].render() # eyes

        glPopMatrix()
        self.mesh_list[self._rest].render()


class GenericFlyer(GenericObject):
    def __init__(self):
        with open("resources/generic_object_flyer.obj", "r") as f:
            model = Model.from_obj(f, scale=10, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.mesh_list


class GenericCrystallWall(GenericObject):
    def __init__(self):
        with open("resources/generic_object_crystalwall.obj", "r") as f:
            model = Model.from_obj(f, scale=10, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.mesh_list


class GenericLongLegs(GenericComplexObject):
    def __init__(self):
        super().__init__("resources/generic_object_longlegs2.obj",
                         height=5.0, tip=3, body=2, eyes=1, rest=0)

class GenericChappy(GenericComplexObject):
    def __init__(self):
        super().__init__("resources/generic_chappy.obj",
                         height=2.56745, tip=0, body=2, eyes=1, rest=3)



class __GenericChappy(GenericObject):
    def __init__(self):
        self.scale = 10
        with open("resources/generic_chappy.obj", "r") as f:
            model = Model.from_obj(f, scale=self.scale, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.mesh_list

    def render(self, selected=False):
        glEnable(GL_CULL_FACE)
        if selected:
            glColor4f(*selectioncolor)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)

        mainbodyheight = 2.56745
        glCullFace(GL_FRONT)
        glPushMatrix()
        glTranslatef(0.0, 0.0, mainbodyheight * self.scale)
        if selected:
            glScalef(1.5, 1.5, 1.5)
        else:
            glScalef(1.2, 1.2, 1.2)

        self.mesh_list[1].render()
        glPopMatrix()
        glCullFace(GL_BACK)
        glPushMatrix()
        glTranslatef(0.0, 0.0, 2.56745*self.scale)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        self.mesh_list[1].render()


        glColor4ub(0x09, 0x93, 0x00, 0xFF)
        self.mesh_list[2].render() # tip
        glPopMatrix()
        glColor4ub(0x00, 0x00, 0x00, 0xFF)
        self.mesh_list[3].render() # eyes


        if selected:
            glColor4f(*selectioncolor)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)
        self.mesh_list[0].render()  # leg
        glDisable(GL_CULL_FACE)

    def render_coloredid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glPushMatrix()
        glScalef(1.2, 1.2, 1.2)
        glTranslatef(0.0, 0.0, 2.56745 * self.scale)
        self.mesh_list[1].render()
        glPopMatrix()


class GenericSnakecrow(GenericComplexObject):
    def __init__(self):
        super().__init__("resources/generic_snakecrow.obj",
                         height=6.63505, tip=1, body=0, eyes=2, rest=3)


class __GenericSnakecrow(GenericObject):
    def __init__(self):
        self.scale = 10
        with open("resources/generic_snakecrow.obj", "r") as f:
            model = Model.from_obj(f, scale=self.scale, rotate=True)
        self.mesh_list = model.mesh_list
        self.named_meshes = model.mesh_list

    def render(self, selected=False):
        glEnable(GL_CULL_FACE)
        if selected:
            glColor4f(255/255, 223/255, 39/255, 1.0)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)

        mainbodyheight = 6.63505
        glCullFace(GL_FRONT)
        glPushMatrix()
        glTranslatef(0.0, 0.0, mainbodyheight * self.scale)
        if selected:
            glScalef(1.5, 1.5, 1.5)
        else:
            glScalef(1.2, 1.2, 1.2)


        self.mesh_list[1].render()
        glPopMatrix()
        glCullFace(GL_BACK)
        glPushMatrix()
        glTranslatef(0.0, 0.0, mainbodyheight*self.scale)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        self.mesh_list[1].render()
        glPopMatrix()

        glColor4ub(0x09, 0x93, 0x00, 0xFF)
        self.mesh_list[2].render() # tip

        glColor4ub(0x00, 0x00, 0x00, 0xFF)
        self.mesh_list[3].render() # eyes


        if selected:
            glColor4f(255/255, 223/255, 39/255, 1.0)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)
        self.mesh_list[0].render()  # leg
        glDisable(GL_CULL_FACE)

    def render_coloredid(self, id):
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glPushMatrix()
        glScalef(1.2, 1.2, 1.2)
        glTranslatef(0.0, 0.0, 2.56745 * self.scale)
        self.mesh_list[1].render()
        glPopMatrix()


class GenericSwimmer(GenericComplexObject):
    def __init__(self):
        super().__init__("resources/generic_swimmer.obj",
                         height=0.0, tip=0, body=3, eyes=1, rest=2)


class TexturedPlane(object):
    def __init__(self, planewidth, planeheight, qimage):
        ID = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, ID)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

        imgdata = bytes(qimage.bits().asarray(qimage.width()*qimage.height()*4))
        glTexImage2D(GL_TEXTURE_2D, 0, 4, qimage.width(), qimage.height(), 0, GL_BGRA, GL_UNSIGNED_BYTE, imgdata)

        self.ID = ID
        self.planewidth = planewidth
        self.planeheight = planeheight

        self.offset_x = 0
        self.offset_z = 0
        self.color = (0.0, 0.0, 0.0)

    def set_offset(self, x, z):
        self.offset_x = x
        self.offset_z = z

    def set_color(self, color):
        self.color = color

    def apply_color(self):
        glColor4f(self.color[0], self.color[1], self.color[2], 1.0)

    def render(self):
        w, h = self.planewidth, self.planeheight
        offsetx, offsetz = self.offset_x, self.offset_z
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.ID)
        glBegin(GL_TRIANGLE_FAN)
        glTexCoord2f(0.0, 0.0)
        glVertex3f(-0.5*w+offsetx, -0.5*h+offsetz, 0)
        glTexCoord2f(0.0, 1.0)
        glVertex3f(-0.5*w+offsetx, 0.5*h+offsetz, 0)
        glTexCoord2f(1.0, 1.0)
        glVertex3f(0.5*w+offsetx, 0.5*h+offsetz, 0)
        glTexCoord2f(1.0, 0.0)
        glVertex3f(0.5*w+offsetx, -0.5*h+offsetz, 0)
        glEnd()

    def render_coloredid(self, id):
        w, h = self.planewidth, self.planeheight
        offsetx, offsetz = self.offset_x, self.offset_z
        glDisable(GL_TEXTURE_2D)
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glBegin(GL_TRIANGLE_FAN)
        #glTexCoord2f(0.0, 0.0)
        glVertex3f(-0.5*w+offsetx, -0.5*h+offsetz, 0)
        #glTexCoord2f(0.0, 1.0)
        glVertex3f(-0.5*w+offsetx, 0.5*h+offsetz, 0)
        #glTexCoord2f(1.0, 1.0)
        glVertex3f(0.5*w+offsetx, 0.5*h+offsetz, 0)
        #glTexCoord2f(1.0, 0.0)
        glVertex3f(0.5*w+offsetx, -0.5*h+offsetz, 0)
        glEnd()


ORIENTATIONS = {
    0: [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)],
    1: [(1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0)],
    2: [(1.0, 1.0), (1.0, 0.0), (0.0, 0.0), (0.0, 1.0)],
    3: [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
}


class Minimap(object):
    def __init__(self, corner1, corner2, orientation, texpath=None):
        self.ID = None
        if texpath is not None:
            self.set_texture(texpath)

        self.corner1 = corner1
        self.corner2 = corner2
        self.orientation = orientation
        print("fully initialized")

    def is_available(self):
        return self.ID is not None

    def set_texture(self, path):
        if self.ID is not None:
            glDeleteTextures(1, int(self.ID))

        qimage = QtGui.QImage(path, "png")
        qimage = qimage.convertToFormat(QtGui.QImage.Format.Format_ARGB32)
        ID = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, ID)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

        imgdata = bytes(qimage.bits().asarray(qimage.width() * qimage.height() * 4))
        glTexImage2D(GL_TEXTURE_2D, 0, 4, qimage.width(), qimage.height(), 0, GL_BGRA, GL_UNSIGNED_BYTE, imgdata)
        self.ID = ID

    def render(self):
        if self.ID is None:
            return

        corner1, corner2 = self.corner1, self.corner2

        glDisable(GL_ALPHA_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)
        #glEnable(GL_DEPTH_TEST)
        glColor4f(1.0, 1.0, 1.0, 0.70)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.ID)
        glBegin(GL_TRIANGLE_FAN)

        glTexCoord2f(*ORIENTATIONS[self.orientation][0])
        glVertex3f(corner1.x, -corner1.z, corner1.y)
        glTexCoord2f(*ORIENTATIONS[self.orientation][1])
        glVertex3f(corner1.x, -corner2.z, corner1.y)
        glTexCoord2f(*ORIENTATIONS[self.orientation][2])
        glVertex3f(corner2.x, -corner2.z, corner1.y)
        glTexCoord2f(*ORIENTATIONS[self.orientation][3])
        glVertex3f(corner2.x, -corner1.z, corner1.y)
        glEnd()

        glColor4f(1.0, 1.0, 1.0, 1.0)
        #glDisable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)
        glBlendFunc(GL_ZERO, GL_ONE)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_ALPHA_TEST)


class Grid(Mesh):
    def __init__(self, width, length, step):
        super().__init__("Grid")
        self.width = width
        self.length = length
        self.step = step

    def generate_displist(self):
        if self._displist is not None:
            glDeleteLists(self._displist, 1)

        offset = +0.5
        width = self.width
        length = self.length

        self._displist = glGenLists(1)
        glNewList(self._displist, GL_COMPILE)
        glColor3f(0.0, 0.0, 0.0)
        glLineWidth(4.0)
        glBegin(GL_LINES)
        glVertex3f(-width, 0, offset)
        glVertex3f(width, 0, offset)

        glVertex3f(0, -length, offset)
        glVertex3f(0, length, offset)
        glEnd()
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for ix in range(-width, width+self.step, self.step):
            glVertex3f(ix, -length, offset)
            glVertex3f(ix, length, offset)

        for iy in range(-length, length+self.step, self.step):
            glVertex3f(-width, iy, offset)
            glVertex3f(width, iy, offset)

        glEnd()
        glEndList()


def _compile_shader_with_error_report(shaderobj):
    glCompileShader(shaderobj)
    if not glGetShaderiv(shaderobj, GL_COMPILE_STATUS):
        raise RuntimeError(str(glGetShaderInfoLog(shaderobj), encoding="ascii"))


colortypes = {
    0x00: (250, 213, 160),
    0x01: (128, 128, 128),
    0x02: (192, 192, 192),
    0x03: (76, 255, 0),
    0x04: (0, 255, 255),
    0x08: (255, 106, 0),
    0x0C: (250, 213, 160),
    0x0F: (0, 38, 255),
    0x10: (250, 213, 160),
    0x12: (64, 64, 64),
    0x13: (250, 213, 160)
}

otherwise = (40, 40, 40)


class CollisionModel(object):
    def __init__(self, mkdd_collision):
        meshes = {}
        self.program = None
        vertices = mkdd_collision.vertices
        self._displists = []

        for v1, v2, v3, coltype, rest in mkdd_collision.triangles:
            vertex1 = Vector3(*vertices[v1])
            vertex1.z = -vertex1.z
            vertex2 = Vector3(*vertices[v2])
            vertex2.z = -vertex2.z
            vertex3 = Vector3(*vertices[v3])
            vertex3.z = -vertex3.z

            v1tov2 = vertex2 - vertex1
            v1tov3 = vertex3 - vertex1

            normal = v1tov2.cross(v1tov3)
            if normal.norm() != 0.0:
                normal.normalize()

            if coltype not in meshes:
                meshes[coltype] = []

            shift = coltype >> 8

            if shift in colortypes:
                color = colortypes[shift]

            else:
                color = otherwise
            color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
            meshes[coltype].append((vertex1, vertex2, vertex3, normal, color))

        self.meshes = meshes

    def generate_displists(self):
        if self.program is None:
            self.create_shaders()

        for meshtype, mesh in self.meshes.items():
            displist = glGenLists(1)
            glNewList(displist, GL_COMPILE)
            glBegin(GL_TRIANGLES)

            for v1, v2, v3, normal, color in mesh:
                glVertexAttrib3f(3, normal.x, normal.y, normal.z)
                glVertexAttrib3f(4, *color)
                glVertex3f(v1.x, -v1.z, v1.y)
                glVertexAttrib3f(3, normal.x, normal.y, normal.z)
                glVertexAttrib3f(4, *color)
                glVertex3f(v2.x, -v2.z, v2.y)
                glVertexAttrib3f(3, normal.x, normal.y, normal.z)
                glVertexAttrib3f(4, *color)
                glVertex3f(v3.x, -v3.z, v3.y)



            glEnd()
            glEndList()

            self._displists.append((meshtype, displist))

    def create_shaders(self):
        vertshader = """
        #version 330 compatibility
        layout(location = 0) in vec4 vert;
        layout(location = 3) in vec3 normal;
        layout(location = 4) in vec3 color;
        uniform float interpolate;
        out vec3 vecNormal;
        out vec3 vecColor;
        vec3 selectedcol = vec3(1.0, 0.0, 0.0);
        vec3 lightvec = normalize(vec3(0.3, 0.0, -1.0));
        
        void main(void)
        {
            vecNormal = normal;
            vec3 col = (1-interpolate) * color + interpolate*selectedcol;
            vecColor = col*clamp(1.0-dot(lightvec, normal), 0.3, 1.0);
            gl_Position = gl_ModelViewProjectionMatrix * vert;
            
        }
        
        """

        fragshader = """
        #version 330
        in vec3 vecNormal;
        in vec3 vecColor;
        out vec4 finalColor;
        
        void main (void)
        {   
            finalColor = vec4(vecColor, 1.0);
        }"""

        vertexShaderObject = glCreateShader(GL_VERTEX_SHADER)
        fragmentShaderObject = glCreateShader(GL_FRAGMENT_SHADER)
        # glShaderSource(vertexShaderObject, 1, vertshader, len(vertshader))
        # glShaderSource(fragmentShaderObject, 1, fragshader, len(fragshader))
        glShaderSource(vertexShaderObject, vertshader)
        glShaderSource(fragmentShaderObject, fragshader)

        _compile_shader_with_error_report(vertexShaderObject)
        _compile_shader_with_error_report(fragmentShaderObject)

        program = glCreateProgram()

        glAttachShader(program, vertexShaderObject)
        glAttachShader(program, fragmentShaderObject)

        glLinkProgram(program)
        self.program = program

    def render(self, selected=False, selectedPart=None):
        if self.program is None:
            self.generate_displists()
        factorval = glGetUniformLocation(self.program, "interpolate")

        glUseProgram(self.program)

        for colltype, displist in self._displists:
            if colltype == selectedPart:
                glUniform1f(factorval, 1.0)
            else:
                glUniform1f(factorval, 0.0)
            glCallList(displist)

        glUseProgram(0)
