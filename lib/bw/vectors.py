from math import sqrt
from io import StringIO

class Vector3(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Vector3(self.x, self.y, self.z)

    def norm(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        norm = self.norm()
        self.x /= norm
        self.y /= norm
        self.z /= norm

    def unit(self):
        return self/self.norm()

    def cross(self, other_vec):
        return Vector3(self.y*other_vec.z - self.z*other_vec.y,
                       self.z*other_vec.x - self.x*other_vec.z,
                       self.x*other_vec.y - self.y*other_vec.x)

    def dot(self, other_vec):
        return self.x*other_vec.x + self.y*other_vec.y + self.z*other_vec.z

    def __truediv__(self, other):
        return Vector3(self.x/other, self.y/other, self.z/other)

    def __add__(self, other_vec):
        return Vector3(self.x+other_vec.x, self.y+other_vec.y, self.z+other_vec.z)

    def __mul__(self, other):
        return Vector3(self.x*other, self.y*other, self.z*other)

    def __sub__(self, other_vec):
        return Vector3(self.x-other_vec.x, self.y-other_vec.y, self.z-other_vec.z)

    def cos_angle(self, other_vec):
        return self.dot(other_vec)/(self.norm()*other_vec.norm())

    def __iadd__(self, other_vec):
        self.x += other_vec.x
        self.y += other_vec.y
        self.z += other_vec.z
        return self

    def __isub__(self, other_vec):
        self.x -= other_vec.x
        self.y -= other_vec.y
        self.z -= other_vec.z
        return self

    def __imul__(self, other):
        self.x *= other
        self.y *= other
        self.z *= other
        return self

    def __itruediv__(self, other):
        self.x /= other
        self.y /= other
        self.z /= other
        return self

    def is_zero(self):
        return self.x == self.y == self.z == 0

    def __eq__(self, other_vec):
        return self.x == other_vec.x and self.y == other_vec.y and self.z == other_vec.z

    def __str__(self):
        return str((self.x, self.y, self.z))


class Vector4(Vector3):
    def __init__(self, x, y, z, w):
        Vector3.__init__(self, x, y, z)
        self.w = w

    def copy(self):
        return Vector4(self.x, self.y, self.z, self.w)

    def norm(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2 + self.w**2)

    def normalize(self):
        norm = self.norm()
        self.x /= norm
        self.y /= norm
        self.z /= norm
        self.w /= norm



class Plane(object):
    def __init__(self, origin, vec1, vec2): # a point and two vectors defining the plane
        self.origin = origin
        self.vec1 = vec1
        self.vec2 = vec2
        self.normal = vec1.cross(vec2)

    def point_is_on_plane(self, vec):
        return (vec-self.origin).dot(self.normal) == 0

    def is_parallel(self, vec):
        return self.normal.dot(vec) == 0


class Triangle(object):
    def __init__(self, p1, p2, p3):
        self.origin = p1
        self.p2 = p2
        self.p3 = p3
        self.p1_to_p2 = p2 - p1
        self.p1_to_p3 = p3 - p1

        self.normal = self.p1_to_p2.cross(self.p1_to_p3)


        if not self.normal.is_zero():
            self.normal.normalize()

    def is_parallel(self, vec):
        return self.normal.dot(vec) == 0


class Line(object):
    def __init__(self, origin, direction):
        self.origin = origin
        self.direction = direction
        self.direction.normalize()

    def collide(self, tri: Triangle):
        hit = False

        edge1 = tri.p1_to_p2
        edge2 = tri.p1_to_p3

        normal = tri.normal 
        if normal.is_zero():
            return False

        #d = -normal.dot(self.origin)

        if tri.normal.dot(self.direction) == 0:
            return False

        d = ((tri.origin - self.origin).dot(tri.normal)) / tri.normal.dot(self.direction)

        #if d == 0:
        #    return False

        #t = (normal.dot(self.origin) + d) / normal.dot(self.direction)

        if d < 0:
            return False

        intersection_point = self.origin + self.direction * d

        #return intersection_point
        C0 = intersection_point - tri.origin

        if tri.normal.dot(tri.p1_to_p2.cross(C0)) > 0:
            p2_to_p3 = tri.p3 - tri.p2
            C1 = intersection_point - tri.p2

            if tri.normal.dot(p2_to_p3.cross(C1)) > 0:
                p3_to_p1 = tri.origin - tri.p3
                C2 = intersection_point - tri.p3
                if tri.normal.dot(p3_to_p1.cross(C2)) > 0:
                    return intersection_point, d
                else:
                    return False
            else:
                return False
        else:
            return False


class Matrix4x4(object):
    def __init__(self,
                 val1A, val1B, val1C, val1D,
                 val2A, val2B, val2C, val2D,
                 val3A, val3B, val3C, val3D,
                 val4A, val4B, val4C, val4D):

        self.a1 = val1A
        self.b1 = val1B
        self.c1 = val1C
        self.d1 = val1D

        self.a2 = val2A
        self.b2 = val2B
        self.c2 = val2C
        self.d2 = val2D

        self.a3 = val3A
        self.b3 = val3B
        self.c3 = val3C
        self.d3 = val3D

        self.a4 = val4A
        self.b4 = val4B
        self.c4 = val4C
        self.d4 = val4D

    @classmethod
    def identity(cls):
        return cls(1.0, 0.0, 0.0, 0.0,
                   0.0, 1.0, 0.0, 0.0,
                   0.0, 0.0, 1.0, 0.0,
                   0.0, 0.0, 0.0, 1.0)

    def transpose(self):
        self.__init__(self.a1, self.a2, self.a3, self.a4,
                      self.b1, self.b2, self.b3, self.b4,
                      self.c1, self.c2, self.c3, self.c4,
                      self.d1, self.d2, self.d3, self.d4)

    def multiply_vec4(self, x, y, z, w):
        #print("MATRIX MULTIPLICATION INPUT", x, y, z ,w )
        newx = self.a1 * x + self.b1 * y + self.c1 * z + self.d1 * w
        newy = self.a2 * x + self.b2 * y + self.c2 * z + self.d2 * w
        newz = self.a3 * x + self.b3 * y + self.c3 * z + self.d3 * w
        neww = self.a4 * x + self.b4 * y + self.c4 * z + self.d4 * w
        #print("MATRIX MULTIPLICATION OUTPUT", newx, newy, newz, neww)
        return newx, newy, newz, neww

    def inplace_multiply_mat4(self, othermat):
        col1 = self.multiply_vec4(othermat.a1, othermat.a2, othermat.a3, othermat.a4)
        col2 = self.multiply_vec4(othermat.b1, othermat.b2, othermat.b3, othermat.b4)
        col3 = self.multiply_vec4(othermat.c1, othermat.c2, othermat.c3, othermat.c4)
        col4 = self.multiply_vec4(othermat.d1, othermat.d2, othermat.d3, othermat.d4)

        self.a1, self.a2, self.a3, self.a4 = col1
        self.b1, self.b2, self.b3, self.b4 = col2
        self.c1, self.c2, self.c3, self.c4 = col3
        self.d1, self.d2, self.d3, self.d4 = col4
    
    def multiply_mat4(self, othermat):
        col1 = self.multiply_vec4(othermat.a1, othermat.a2, othermat.a3, othermat.a4)
        col2 = self.multiply_vec4(othermat.b1, othermat.b2, othermat.b3, othermat.b4)
        col3 = self.multiply_vec4(othermat.c1, othermat.c2, othermat.c3, othermat.c4)
        col4 = self.multiply_vec4(othermat.d1, othermat.d2, othermat.d3, othermat.d4)
        
        mtx = Matrix4x4(0, 0, 0, 0,0, 0, 0, 0,0, 0, 0, 0,0, 0, 0, 0) 
        
        mtx.a1, mtx.a2, mtx.a3, mtx.a4 = col1
        mtx.b1, mtx.b2, mtx.b3, mtx.b4 = col2
        mtx.c1, mtx.c2, mtx.c3, mtx.c4 = col3
        mtx.d1, mtx.d2, mtx.d3, mtx.d4 = col4
        
        return mtx
        
    @classmethod
    def from_matrix(cls, matrix):

        return cls(
            matrix.a1, matrix.b1, matrix.c1, matrix.d1,
            matrix.a2, matrix.b2, matrix.c2, matrix.d2,
            matrix.a3, matrix.b3, matrix.c3, matrix.d3,
            matrix.a4, matrix.b4, matrix.c4, matrix.d4
        )

    def __str__(self):
        out = StringIO()
        out.write("{\n")
        out.write(str(self.a1))
        out.write(", ")
        out.write(str(self.b1))
        out.write(", ")
        out.write(str(self.c1))
        out.write(", ")
        out.write(str(self.d1))
        out.write(",\n")

        out.write(str(self.a2))
        out.write(", ")
        out.write(str(self.b2))
        out.write(", ")
        out.write(str(self.c2))
        out.write(", ")
        out.write(str(self.d2))
        out.write(",\n")

        out.write(str(self.a3))
        out.write(", ")
        out.write(str(self.b3))
        out.write(", ")
        out.write(str(self.c3))
        out.write(", ")
        out.write(str(self.d3))
        out.write(",\n")

        out.write(str(self.a4))
        out.write(", ")
        out.write(str(self.b4))
        out.write(", ")
        out.write(str(self.c4))
        out.write(", ")
        out.write(str(self.d4))
        out.write("\n}")

        return out.getvalue()