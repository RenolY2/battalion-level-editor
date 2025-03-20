from math import sqrt, inf
from io import StringIO
from numpy import array


class Vector3(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Vector3(self.x, self.y, self.z)

    def norm_nosqrt(self):
        return self.x**2 + self.y**2+self.z**2

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

    def swap_yz(self):
        tmp = self.y
        self.y = self.z
        self.z = tmp

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

    def __str__(self):
        return str((self.x, self.y, self.z, self.w))

    def __eq__(self, other_vec):
        return self.x == other_vec.x and self.y == other_vec.y and self.z == other_vec.z and self.w == other_vec.w

    def is_zero(self):
        return self.x == self.y == self.z == self.w == 0


class Vector2(Vector3):
    def __init__(self, x, y):
        super().__init__(x, y, 0)

    def copy(self):
        return Vector2(self.x, self.y)

    def __truediv__(self, other):
        return Vector2(self.x/other, self.y/other)

    def __add__(self, other_vec):
        return Vector2(self.x+other_vec.x, self.y+other_vec.y)

    def __mul__(self, other):
        return Vector2(self.x*other, self.y*other)

    def __sub__(self, other_vec):
        return Vector2(self.x-other_vec.x, self.y-other_vec.y)


class Plane(object):
    def __init__(self, origin, vec1, vec2): # a point and two vectors defining the plane
        self.origin = origin
        self._vec1 = vec1
        self._vec2 = vec2
        self.normal = vec1.cross(vec2)

    @classmethod
    def from_implicit(cls, origin, normal):
        dummyvec = Vector3(0.0, 0.0, 0.0)
        plane = cls(origin, dummyvec, dummyvec)
        plane.normal = normal
        return plane

    def point_is_on_plane(self, vec):
        return (vec-self.origin).dot(self.normal) == 0

    def is_parallel(self, vec):
        return self.normal.dot(vec) == 0

    @classmethod
    def xy_aligned(cls, origin):
        return cls(origin, Vector3(1, 0, 0), Vector3(0, 1, 0))

    @classmethod
    def xz_aligned(cls, origin):
        return cls(origin, Vector3(1, 0, 0), Vector3(0, 0, 1))

    @classmethod
    def yz_aligned(cls, origin):
        return cls(origin, Vector3(0, 1, 0), Vector3(0, 0, 1))


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


# p1 p2
# p3 p4
class Quad(object):
    def __init__(self, p1, p2, p3, p4):
        self.tri1 = Triangle(p1, p2, p3)
        self.tri2 = Triangle(p2, p4, p3)

        # P2 P4
        # P1 P3

        self.p2_to_p4 = p4 - p2
        self.p4_to_p3 = p3 - p4
        self.p3_to_p1 = p1 - p3

        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.p4 = p4


class Line(object):
    def __init__(self, origin, direction):
        self.origin = origin
        self.direction = direction
        self.direction.normalize()

    def swap_yz(self):
        self.origin.swap_yz()
        self.direction.swap_yz()

    def swapped_yz(self):
        line = Line(self.origin.copy(), self.direction.copy())
        line.swap_yz()
        return line

    def collide_quad_nonplanar(self, quad: Quad, d_filter=inf):
        result = self.collide(quad.tri1)
        if not result:
            result = self.collide(quad.tri2)

        return result

    def collide_quad(self, quad: Quad, d_filter=inf):
        tri = quad.tri1

        normal = tri.normal

        if normal.dot(self.direction) == 0:
            return False

        d = ((tri.origin - self.origin).dot(normal)) / normal.dot(self.direction)

        if d < 0:
            return False

        if d > d_filter:  # d is too far away so we leave early
            return False

        intersection_point = self.origin + self.direction * d

        # return intersection_point
        C0 = intersection_point - tri.origin

        if tri.normal.dot(tri.p1_to_p2.cross(C0)) > 0:
            C1 = intersection_point - tri.p2

            if tri.normal.dot(quad.p2_to_p4.cross(C1)) > 0:
                C2 = intersection_point - quad.p4

                if tri.normal.dot(quad.p4_to_p3.cross(C2)) > 0:
                    C3 = intersection_point - quad.p3

                    if tri.normal.dot(quad.p3_to_p1.cross(C3)) > 0:
                        return intersection_point, d
                    else:
                        return False
                else:
                    return False
            else:
                return False
        else:
            return False

    def collide(self, tri: Triangle):
        normal = tri.normal
        if normal.is_zero():
            return False

        if tri.normal.dot(self.direction) == 0:
            return False

        d = ((tri.origin - self.origin).dot(normal)) / normal.dot(self.direction)

        if d < 0:
            return False

        intersection_point = self.origin + self.direction * d

        # return intersection_point
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

    def collide_py(self, tri: Triangle):
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

    def collide_plane(self, plane: Plane):
        pos = self.origin
        dir = self.direction

        if not plane.is_parallel(dir):
            d = ((plane.origin - pos).dot(plane.normal)) / plane.normal.dot(dir)
            if d >= 0:
                point = pos + (dir * d)
                return point, d
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
    def from_opengl_matrix(cls, row1, row2, row3, row4):
        return cls(row1[0], row1[1], row1[2], row1[3],
                   row2[0], row2[1], row2[2], row2[3],
                   row3[0], row3[1], row3[2], row3[3],
                   row4[0], row4[1], row4[2], row4[3])
    
    def transpose(self):
        self.__init__(self.a1, self.a2, self.a3, self.a4,
                      self.b1, self.b2, self.b3, self.b4,
                      self.c1, self.c2, self.c3, self.c4,
                      self.d1, self.d2, self.d3, self.d4)

    def transposed(self):
        return Matrix4x4(
                        self.a1, self.a2, self.a3, self.a4,
                        self.b1, self.b2, self.b3, self.b4,
                        self.c1, self.c2, self.c3, self.c4,
                        self.d1, self.d2, self.d3, self.d4
        )

    def multiply_vec4(self, x, y, z, w):
        #print("MATRIX MULTIPLICATION INPUT", x, y, z ,w )
        newx = self.a1 * x + self.b1 * y + self.c1 * z + self.d1 * w
        newy = self.a2 * x + self.b2 * y + self.c2 * z + self.d2 * w
        newz = self.a3 * x + self.b3 * y + self.c3 * z + self.d3 * w
        neww = self.a4 * x + self.b4 * y + self.c4 * z + self.d4 * w
        #print("MATRIX MULTIPLICATION OUTPUT", newx, newy, newz, neww)
        return newx, newy, newz, neww

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
