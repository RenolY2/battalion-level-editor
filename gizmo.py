from OpenGL.GL import *

from lib.model_rendering import Model
from lib.vectors import Vector3, Plane, Line
from widgets.editor_widgets import catch_exception
from itertools import chain

id_to_meshname = {
    0x1: "gizmo_x",
    0x2: "gizmo_y",
    0x3: "gizmo_z",
    0x4: "rotation_x",
    0x5: "rotation_y",
    0x6: "rotation_z",
    0x7: "middle"
}

AXIS_X = 0
AXIS_Y = 1
AXIS_Z = 2

X_COLOR = (1.0, 0.1, 0.1, 1.0)
Y_COLOR = (0.0, 1.0, 0.0, 1.0)
Z_COLOR = (0.0, 0.0, 1.0, 1.0)
MIDDLE = (0.3, 0.4, 0.3, 1.0)


class Gizmo(Model):
    def __init__(self):
        super().__init__()

        self.position = Vector3(0.0, 0.0, 0.0)
        self.hidden = True

        self.callbacks = {}

        self.was_hit = {}
        self.was_hit_at_all = False
        for meshname in id_to_meshname.values():
            self.was_hit[meshname] = False

        self.render_axis = None

        with open("resources/gizmo_collision.obj", "r") as f:
            self.collision = Model.from_obj(f, rotate=True, generate_collision=True, collision_flip=True)

    def set_render_axis(self, axis):
        self.render_axis = axis

    def reset_axis(self):
        self.render_axis = None

    def collide(self, ray, scale, is3d=True, translation_visible=True, rotation_visible=True):
        if self.hidden:
            return None, 999999
        else:
            meshes = []
            if translation_visible:
                meshes.append((self.collision.named_meshes["gizmo_x"], 1))
                if is3d: meshes.append((self.collision.named_meshes["gizmo_y"], 2))
                meshes.append((self.collision.named_meshes["gizmo_z"], 3))
                if not is3d: meshes.append((self.collision.named_meshes["middle"], 7))

            if rotation_visible:
                if is3d: meshes.append((self.collision.named_meshes["rotation_x"], 4))
                meshes.append((self.collision.named_meshes["rotation_y"], 5))
                if is3d: meshes.append((self.collision.named_meshes["rotation_z"], 6))

            dist = 999999
            hit = None
            print("Ray point:", ray.origin, "Gizmo:", self.position)
            local_ray = Line(ray.origin.copy(), ray.direction)
            local_ray.origin = (local_ray.origin - self.position)*(1/scale)
            print("COLLISION CHECK: ", local_ray.origin, local_ray.direction)
            for mesh, meshid in meshes:
                for tri in mesh.collision_tris:
                    result = local_ray.collide(tri)
                    if result:
                        pos, d = result
                        if d < dist:
                            dist = d
                            hit = meshid

            return hit, dist


    def move_to_average(self, objects, misc_objects, bwterrain, waterheight, visualize):
        for obj in chain(objects, misc_objects):
            if obj is None:
                continue
            if obj.getmatrix() is not None or obj.getposition() is not None:
                self.hidden = False
                break
        else:
            self.hidden = True
            return


        avgx = None
        avgy = None
        avgz = None
        count = 0
        for obj in chain(objects, misc_objects):
            if obj.getmatrix() is not None:
                if visualize and obj.mtxoverride is not None:
                    mtx = obj.mtxoverride
                else:
                    mtx = obj.getmatrix()
                    if mtx is not None:
                        mtx = mtx.mtx
                x, objheight, z = mtx[12:15]
            elif obj.getposition() is not None:
                x, objheight, z = obj.getposition()
            else:
                x, objheight, z = None, None, None

            if x is not None:
                count += 1

                if not visualize:
                    h = obj.calculate_height(bwterrain, waterheight)
                    if h is not None:
                        objheight = h

                if avgx is None:
                    avgx = x
                    avgy = objheight
                    avgz = z
                else:
                    avgx += x
                    avgy += objheight
                    avgz += z

        self.position.x = avgx / count
        self.position.y = avgy / count
        self.position.z = avgz / count
        #print("New position is", self.position, len(objects))

    def render_collision_check(self, scale, is3d=True, translation_visible=True, rotation_visible=True):
        if not self.hidden:
            glPushMatrix()
            glTranslatef(self.position.x, self.position.z, self.position.y)
            glScalef(scale, scale, scale)

            named_meshes = self.collision.named_meshes

            if translation_visible:
                named_meshes["gizmo_x"].render_colorid(0x1)
                if is3d: named_meshes["gizmo_y"].render_colorid(0x2)
                named_meshes["gizmo_z"].render_colorid(0x3)
                if not is3d: named_meshes["middle"].render_colorid(0x7)

            if rotation_visible:
                if is3d: named_meshes["rotation_x"].render_colorid(0x4)
                named_meshes["rotation_y"].render_colorid(0x5)
                if is3d: named_meshes["rotation_z"].render_colorid(0x6)

            glPopMatrix()

    def register_callback(self, gizmopart, func):
        assert gizmopart in self.named_meshes

        self.callbacks[gizmopart] = func

    @catch_exception
    def run_callback(self, hit_id):
        if hit_id not in id_to_meshname: return
        meshname = id_to_meshname[hit_id]
        #print("was hit", meshname)
        #assert meshname in self.was_hit
        #assert all(x is False for x in self.was_hit.values())
        self.was_hit[meshname] = True
        self.was_hit_at_all = True
        #if meshname in self.callbacks:
        #    self.callbacks[meshname]()

    def reset_hit_status(self):
        for key in self.was_hit:
            self.was_hit[key] = False
        self.was_hit_at_all = False

    def _draw_line(self, v1, v2):
        glBegin(GL_LINES)  # Bottom, z1
        glVertex3f(v1.x, v1.y, v1.z)
        glVertex3f(v2.x, v2.y, v2.z)
        glEnd()

    @catch_exception
    def render(self, is3d=True, translation_visible=True, rotation_visible=True):
        if not self.hidden:
            glColor4f(*X_COLOR)
            if translation_visible: self.named_meshes["gizmo_x"].render()
            if is3d and rotation_visible: self.named_meshes["rotation_x"].render()

            glColor4f(*Y_COLOR)
            if is3d and translation_visible: self.named_meshes["gizmo_y"].render()
            if rotation_visible: self.named_meshes["rotation_y"].render()
            glColor4f(*Z_COLOR)
            if translation_visible: self.named_meshes["gizmo_z"].render()
            if is3d and rotation_visible: self.named_meshes["rotation_z"].render()
            glColor4f(*MIDDLE)
            if not is3d and translation_visible: self.named_meshes["middle"].render()

    def render_scaled(self, scale, is3d=True, translation_visible=True, rotation_visible=True):
        glPushMatrix()
        glTranslatef(self.position.x, self.position.z, self.position.y)

        if self.render_axis == AXIS_X:
            glColor4f(*X_COLOR)
            self._draw_line(Vector3(-99999, 0, 0), Vector3(99999, 0, 0))
        elif self.render_axis == AXIS_Y:
            glColor4f(*Y_COLOR)
            self._draw_line(Vector3(0, 0, -99999), Vector3(0, 0, 99999))
        elif self.render_axis == AXIS_Z:
            glColor4f(*Z_COLOR)
            self._draw_line(Vector3(0, -99999, 0), Vector3(0, 99999, 0))
        glClear(GL_DEPTH_BUFFER_BIT)
        glScalef(scale, scale, scale)
        if not self.hidden:
            self.render(is3d,
                        translation_visible=translation_visible,
                        rotation_visible=rotation_visible)


        glPopMatrix()

