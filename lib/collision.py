import math
from .vectors import Vector3, Triangle


def collides(face_v1, face_v2, face_v3, box_mid_x, box_mid_z, box_size_x, box_size_z):
    min_x = min(face_v1[0], face_v2[0], face_v3[0]) - box_mid_x
    max_x = max(face_v1[0], face_v2[0], face_v3[0]) - box_mid_x

    min_z = min(face_v1[2], face_v2[2], face_v3[2]) - box_mid_z
    max_z = max(face_v1[2], face_v2[2], face_v3[2]) - box_mid_z

    half_x = box_size_x / 2.0
    half_z = box_size_z / 2.0

    if max_x < -half_x or min_x > +half_x:
        return False
    if max_z < -half_z or min_z > +half_z:
        return False

    return True


def subdivide_grid(minx, minz,
                   gridx_start, gridx_end, gridz_start, gridz_end,
                   cell_size, triangles, vertices, result):
    #print("Subdivision with", gridx_start, gridz_start, gridx_end, gridz_end, (gridx_start+gridx_end) // 2, (gridz_start+gridz_end) // 2)
    if gridx_start == gridx_end-1 and gridz_start == gridz_end-1:
        if gridx_start not in result:
            result[gridx_start] = {}
        result[gridx_start][gridz_start] = triangles

        return True

    assert gridx_end > gridx_start or gridz_end > gridz_start

    halfx = (gridx_start+gridx_end) // 2
    halfz = (gridz_start+gridz_end) // 2

    quadrants = (
        [], [], [], []
    )
    # x->
    # 2 3 ^
    # 0 1 z
    coordinates = (
        (0, gridx_start , halfx     , gridz_start   , halfz),   # Quadrant 0
        (1, halfx       , gridx_end , gridz_start   , halfz),     # Quadrant 1
        (2, gridx_start , halfx     , halfz         , gridz_end),     # Quadrant 2
        (3, halfx       , gridx_end , halfz         , gridz_end) # Quadrant 3
    )
    skip = []
    if gridx_start == halfx:
        skip.append(0)
        skip.append(2)
    if halfx == gridx_end:
        skip.append(1)
        skip.append(3)
    if gridz_start == halfz:
        skip.append(0)
        skip.append(1)
    if halfz == gridz_end:
        skip.append(2)
        skip.append(3)


    for i, face in triangles:
        v1_index, v2_index, v3_index = face

        v1 = vertices[v1_index[0]-1]
        v2 = vertices[v2_index[0]-1]
        v3 = vertices[v3_index[0]-1]

        for quadrant, startx, endx, startz, endz in coordinates:
            if quadrant not in skip:
                area_size_x = (endx - startx)*cell_size
                area_size_z = (endz - startz)*cell_size

                if collides(v1, v2, v3,
                            minx+startx*cell_size + area_size_x//2,
                            minz+startz*cell_size + area_size_z//2,
                            area_size_x,
                            area_size_z):
                    #print(i, "collided")
                    quadrants[quadrant].append((i, face))

    for quadrant, startx, endx, startz, endz in coordinates:
        #print("Doing subdivision, skipping:", skip)
        if quadrant not in skip:
            #print("doing subdivision with", coordinates[quadrant])
            subdivide_grid(minx, minz,
                           startx, endx, startz, endz,
                           cell_size, quadrants[quadrant], vertices, result)


def normalize_vector(v1):
    n = (v1[0]**2 + v1[1]**2 + v1[2]**2)**0.5
    return v1[0]/n, v1[1]/n, v1[2]/n


def create_vector(v1, v2):
    return v2[0]-v1[0],v2[1]-v1[1],v2[2]-v1[2]


def cross_product(v1, v2):
    cross_x = v1[1]*v2[2] - v1[2]*v2[1]
    cross_y = v1[2]*v2[0] - v1[0]*v2[2]
    cross_z = v1[0]*v2[1] - v1[1]*v2[0]
    return cross_x, cross_y, cross_z


MAX_X = 200000
MAX_Z = 200000


class Collision(object):
    def __init__(self, verts, faces):
        self.verts = verts
        self.faces = faces
        self.triangles = []
        for v1i, v2i, v3i in self.faces:
            #print(v1i, v2i, v3i, len(self.verts))
            x, y, z = verts[v1i[0]-1]
            v1 = Vector3(x, -z, y)
            x, y, z = verts[v2i[0]-1]
            v2 = Vector3(x, -z, y)
            x, y, z = verts[v3i[0]-1]
            v3 = Vector3(x, -z, y)

            self.triangles.append(Triangle(v1,v2,v3))

        self.cell_size = 2000

        box_size_x = self.cell_size
        box_size_z = self.cell_size

        smallest_x =-MAX_X#max(-6000.0, smallest_x)
        smallest_z = -MAX_Z#max(-6000.0, smallest_z)
        biggest_x = MAX_X#min(6000.0, biggest_x)
        biggest_z = MAX_Z#min(6000.0, biggest_z)
        print("dimensions are changed to", smallest_x, smallest_z, biggest_x, biggest_z)
        start_x = math.floor(smallest_x / box_size_x) * box_size_x
        start_z = math.floor(smallest_z / box_size_z) * box_size_z
        end_x = math.ceil(biggest_x / box_size_x) * box_size_x
        end_z = math.ceil(biggest_z / box_size_z) * box_size_z
        diff_x = abs(end_x - start_x)
        diff_z = abs(end_z - start_z)
        grid_size_x = int(diff_x // box_size_x)
        grid_size_z = int(diff_z // box_size_z)

        self.grid = {}
        triangles = [(i, face) for i, face in enumerate(faces)]
        subdivide_grid(start_x, start_z, 0, grid_size_x, 0, grid_size_z, self.cell_size, triangles, self.verts, self.grid)
        print("finished generating triangles")
        print(grid_size_x, grid_size_z)

    def collide_ray_downwards(self, x, z, y=99999999):
        grid_x = int((x+MAX_X) // self.cell_size)
        grid_z = int((z+MAX_Z) // self.cell_size)

        if grid_x not in self.grid or grid_z not in self.grid[grid_x]:
            return None

        triangles = self.grid[grid_x][grid_z]

        verts = self.verts

        y = y
        dir_x = 0
        dir_y = -1.0
        dir_z = 0

        hit = None

        result = self._collide(verts, triangles, x, y, z, -1.0)

        return result

    def collide_ray_closest(self, x, z, y):
        grid_x = int((x + MAX_X) // self.cell_size)
        grid_z = int((z + MAX_Z) // self.cell_size)

        if grid_x not in self.grid or grid_z not in self.grid[grid_x]:
            return None

        triangles = self.grid[grid_x][grid_z]

        verts = self.verts

        y = y
        dir_x = 0
        dir_y = -1.0
        dir_z = 0

        hit = None

        result1 = self._collide(verts, triangles, x, y, z, -1.0)
        result2 = self._collide(verts, triangles, x, y, z, 1.0)

        if result1 is None and result2 is None:
            return None
        elif result1 is None:
            return result2
        elif result2 is None:
            return result1
        else:
            dist1 = abs(y - result1)
            dist2 = abs(y - result2)
            if dist1 > dist2:
                return result2
            else:
                return result1

    def _collide(self, verts, triangles, x, y, z, dir_y):
        hit = None
        for i, face in triangles:#face in self.faces:#
            v1index, v2index, v3index = face

            v1 = verts[v1index[0]-1]
            v2 = verts[v2index[0]-1]
            v3 = verts[v3index[0]-1]

            edge1 = create_vector(v1, v2)
            edge2 = create_vector(v1, v3)

            normal = cross_product(edge1, edge2)
            if normal[0] == normal[1] == normal[2] == 0.0:
                continue
            normal = normalize_vector(normal)

            D = -v1[0]*normal[0] + -v1[1]*normal[1] + -v1[2]*normal[2]

            if normal[1]*dir_y == 0.0:#abs(normal[1] * dir_y) < 10**(-6):
                continue # triangle parallel to ray

            t = -(normal[0] * x + normal[1] * y + normal[2] * z + D) / (normal[1]*dir_y)

            point = x, (y+dir_y*t), z
            #print(point)
            edg1 = create_vector(v1, v2)
            edg2 = create_vector(v2, v3)
            edg3 = create_vector(v3, v1)

            vectest1 = cross_product(edg1, create_vector(v1, point))
            vectest2 = cross_product(edg2, create_vector(v2, point))
            vectest3 = cross_product(edg3, create_vector(v3, point))

            if ((normal[0]*vectest1[0] + normal[1]*vectest1[1] + normal[2]*vectest1[2]) >= 0 and
                 (normal[0]*vectest2[0] + normal[1]*vectest2[1] + normal[2]*vectest2[2]) >= 0 and
                  (normal[0]*vectest3[0] + normal[1]*vectest3[1] + normal[2]*vectest3[2]) >= 0):

                height = point[1]

                if hit is None or abs(y - height) < abs(y - hit):
                    hit = height

        return hit

    def collide_ray(self, ray):
        best_distance = None
        place_at = None

        for tri in self.triangles:
            collision = ray.collide(tri)

            if collision is not False:
                point, distance = collision

                if best_distance is None or distance < best_distance:
                    place_at = point
                    best_distance = distance

        return place_at