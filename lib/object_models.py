import os
import json
from OpenGL.GL import *
from .model_rendering import (GenericObject, Model, TexturedModel,
                              GenericFlyer, GenericCrystallWall, GenericLongLegs, GenericChappy, GenericSnakecrow,
                              GenericSwimmer, Cube)

with open("lib/color_coding.json", "r") as f:
    colors = json.load(f)


class ObjectModels(object):
    def __init__(self):
        self.models = {}
        self.generic = GenericObject()
        self.generic_flyer = GenericFlyer()
        self.generic_longlegs = GenericLongLegs()
        self.generic_chappy = GenericChappy()
        self.generic_snakecrow = GenericSnakecrow()
        self.generic_swimmer = GenericSwimmer()
        self.cube = Cube()
        self.checkpointleft = Cube(colors["CheckpointLeft"])
        self.checkpointright = Cube(colors["CheckpointRight"])
        self.itempoint = Cube(colors["ItemRoutes"])
        self.enemypoint = Cube(colors["EnemyRoutes"])
        self.camera = GenericObject(colors["Camera"])
        self.areas = GenericObject(colors["Areas"])
        self.objects = GenericObject(colors["Objects"])
        self.respawn = GenericObject(colors["Respawn"])
        self.startpoints = GenericObject(colors["StartPoints"])
        #self.purplecube = Cube((0.7, 0.7, 1.0, 1.0))

        self.playercolors = [Cube(color) for color in ((1.0, 0.0, 0.0, 1.0),
                                                       (0.0, 0.0, 1.0, 1.0),
                                                       (1.0, 1.0, 0.0, 1.0),
                                                       (0.0, 1.0, 1.0, 1.0),
                                                       (1.0, 0.0, 1.0, 1.0),
                                                       (1.0, 0.5, 0.0, 1.0),
                                                       (0.0, 0.5, 1.0, 1.0),
                                                       (1.0, 0.0, 0.5, 1.0))]


        genericmodels = {
            "Chappy": self.generic_chappy,
            "Flyer": self.generic_flyer,
            "Longlegs": self.generic_longlegs,
            "Snakecrow": self.generic_snakecrow,
            "Swimmer": self.generic_swimmer
        }

        with open("resources/enemy_model_mapping.json", "r") as f:
            mapping = json.load(f)
            for enemytype, enemies in mapping.items():
                if enemytype in genericmodels:
                    for name in enemies:
                        self.models[name.title()] = genericmodels[enemytype]

        with open("resources/unitsphere.obj", "r") as f:
            self.sphere = Model.from_obj(f, rotate=True)

        with open("resources/unitcylinder.obj", "r") as f:
            self.cylinder = Model.from_obj(f, rotate=True)

        with open("resources/unitcube_wireframe.obj", "r") as f:
            self.wireframe_cube = Model.from_obj(f, rotate=True)

        with open("resources/arrow_head.obj", "r") as f:
            self.arrow_head = Model.from_obj(f, rotate=True, scale=300.0)

    def init_gl(self):
        for dirpath, dirs, files in os.walk("resources/objectmodels"):
            for file in files:
                if file.endswith(".obj"):
                    filename = os.path.basename(file)
                    objectname = filename.rsplit(".", 1)[0]
                    self.models[objectname] = TexturedModel.from_obj_path(os.path.join(dirpath, file), rotate=True)
        for cube in (self.cube, self.checkpointleft, self.checkpointright, self.itempoint, self.enemypoint,
                     self.objects, self.areas, self.respawn, self.startpoints, self.camera):
            cube.generate_displists()

        for cube in self.playercolors:
            cube.generate_displists()

        self.generic.generate_displists()

        # self.generic_wall = TexturedModel.from_obj_path("resources/generic_object_wall2.obj", rotate=True, scale=20.0)

    def draw_arrow_head(self, frompos, topos):
        glPushMatrix()
        dir = topos-frompos
        dir.normalize()

        glMultMatrixf([dir.x, -dir.z, 0, 0,
                       -dir.z, -dir.x, 0, 0,
                       0, 0, 1, 0,
                       topos.x, -topos.z, topos.y, 1])
        self.arrow_head.render()
        glPopMatrix()
        #glBegin(GL_LINES)
        #glVertex3f(frompos.x, -frompos.z, frompos.y)
        #glVertex3f(topos.x, -topos.z, topos.y)
        #glEnd()

    def draw_sphere(self, position, scale):
        glPushMatrix()

        glTranslatef(position.x, -position.z, position.y)
        glScalef(scale, scale, scale)

        self.sphere.render()
        glPopMatrix()

    def draw_sphere_last_position(self, scale):
        glPushMatrix()

        glScalef(scale, scale, scale)

        self.sphere.render()
        glPopMatrix()

    def draw_cylinder(self,position, radius, height):
        glPushMatrix()

        glTranslatef(position.x, -position.z, position.y)
        glScalef(radius, height, radius)

        self.cylinder.render()
        glPopMatrix()

    def draw_wireframe_cube(self, position, rotation, scale):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        mtx = rotation.mtx
        glMultMatrixf(mtx)
        glScalef(-scale.z, scale.x, scale.y)
        self.wireframe_cube.render()
        glPopMatrix()

    def draw_cylinder_last_position(self, radius, height):
        glPushMatrix()

        glScalef(radius, radius, height)

        self.cylinder.render()
        glPopMatrix()

    def render_generic_position(self, position, selected):
        self._render_generic_position(self.cube, position, selected)

    def render_generic_position_colored(self, position, selected, cubename):
        self._render_generic_position(getattr(self, cubename), position, selected)

    def render_player_position_colored(self, position, selected, player):
        self._render_generic_position(self.playercolors[player], position, selected)

    def render_generic_position_rotation(self, position, rotation, selected):
        self._render_generic_position_rotation("generic", position, rotation, selected)

    def render_generic_position_rotation_colored(self, objecttype, position, rotation, selected):
        self._render_generic_position_rotation(objecttype, position, rotation, selected)

    def _render_generic_position_rotation(self, name, position, rotation, selected):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        mtx = rotation.mtx
        #glBegin(GL_LINES)
        #glVertex3f(0.0, 0.0, 0.0)
        #glVertex3f(mtx[0][0] * 2000, mtx[0][1] * 2000, mtx[0][2] * 2000)
        #glEnd()

        glMultMatrixf(mtx)

        glColor3f(0.0, 0.0, 0.0)
        glBegin(GL_LINE_STRIP)
        glVertex3f(0.0, 0.0, 750.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(1000.0, 0.0, 0.0)
        glEnd()


        #glMultMatrixf(rotation.mtx[])
        getattr(self, name).render(selected=selected)

        glPopMatrix()

    def _render_generic_position(self, cube, position, selected):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        cube.render(selected=selected)

        glPopMatrix()

    def render_generic_position_colored_id(self, position, id):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        self.cube.render_coloredid(id)

        glPopMatrix()

    def render_generic_position_rotation_colored_id(self, position, rotation, id):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        mtx = rotation.mtx
        #glMultMatrixf(rotation.mtx[])
        self.generic.render_coloredid(id)

        glPopMatrix()

    def render_line(self, pos1, pos2):
        pass

    def render_object(self, pikminobject, selected):
        glPushMatrix()

        glTranslatef(pikminobject.position.x, -pikminobject.position.z, pikminobject.position.y)
        if "mEmitRadius" in pikminobject.unknown_params and pikminobject.unknown_params["mEmitRadius"] > 0:
            self.draw_cylinder_last_position(pikminobject.unknown_params["mEmitRadius"]/2, 50.0)

        glRotate(pikminobject.rotation.x, 1, 0, 0)
        glRotate(pikminobject.rotation.y, 0, 0, 1)
        glRotate(pikminobject.rotation.z, 0, 1, 0)

        if pikminobject.name in self.models:
            self.models[pikminobject.name].render(selected=selected)
        else:
            glDisable(GL_TEXTURE_2D)
            self.generic.render(selected=selected)

        glPopMatrix()

    def render_object_coloredid(self, pikminobject, id):
        glPushMatrix()

        glTranslatef(pikminobject.position.x, -pikminobject.position.z, pikminobject.position.y)
        glRotate(pikminobject.rotation.x, 1, 0, 0)
        glRotate(pikminobject.rotation.y, 0, 0, 1)
        glRotate(pikminobject.rotation.z, 0, 1, 0)

        if pikminobject.name in self.models:
            self.models[pikminobject.name].render_coloredid(id)
        else:
            self.generic.render_coloredid(id)


        glPopMatrix()
