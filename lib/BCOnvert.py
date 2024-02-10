# BCOnvert.py v0.1 by Yoshi2

import time
import argparse
import os
import subprocess
from re import match
from struct import pack, unpack
from math import floor, ceil
import math


def read_vertex(v_data):
    split = v_data.split("/")
    #if len(split) == 3:
    #    vnormal = int(split[2])
    #else:
    #    vnormal = None
    v = int(split[0])
    return v#, vnormal


def read_obj(objfile):
    vertices = []
    faces = []
    face_normals = []
    normals = []

    floor_type = None

    smallest_x = smallest_z = biggest_x = biggest_z = None


    for line in objfile:
        line = line.strip()
        args = line.split(" ")

        if len(args) == 0 or line.startswith("#"):
            continue
        cmd = args[0]

        if cmd == "v":
            #print(args)
            for i in range(args.count("")):
                args.remove("")

            x,y,z = map(float, args[1:4])
            vertices.append((x,y,z))

            if smallest_x is None:
                # Initialize values
                smallest_x = biggest_x = x
                smallest_z = biggest_z = z
            else:
                if x < smallest_x:
                    smallest_x = x
                elif x > biggest_x:
                    biggest_x = x
                if z < smallest_z:
                    smallest_z = z
                elif z > biggest_z:
                    biggest_z = z

        elif cmd == "f":
            # if it uses more than 3 vertices to describe a face then we panic!
            # no triangulation yet.
            if len(args) != 4:
                raise RuntimeError("Model needs to be triangulated! Only faces with 3 vertices are supported.")
            v1, v2, v3 = map(read_vertex, args[1:4])
            
            faces.append((v1, v2, v3, floor_type))

        elif cmd == "vn":
            nx,ny,nz = map(float, args[1:4])
            normals.append((nx,ny,nz))

        elif cmd == "usemtl":
            assert len(args) >= 2

            matname = " ".join(args[1:])

            floor_type_match = match("^(.*?)(0x[0-9a-fA-F]{4})(.*?)$", matname)

            if floor_type_match is not None:
                floor_type = int(floor_type_match.group(2), 16)
            else:
                floor_type = None

            #print("Found material:", matname, "Using floor type:", hex(floor_type))

    #objects.append((current_object, vertices, faces))
    return vertices, faces, normals, (smallest_x, smallest_z, biggest_x, biggest_z)


def create_line(start, end):
    deltax = end[0]-start[0]
    deltay = end[1]-start[1]
    return (start, (deltax, deltay), (deltax**2 + deltay**2)**0.5)


def point_is_on_line(point, line):
    start, delta, length = line
    if delta[0] == delta[1] == 0:
        return start[0] == point[0] and start[1] == point[1]

    if delta[0] == 0:
        a1 = None
    else:
        a1 = (point[0]-start[0])/delta[0]

    if delta[1] == 0:
        a2 = None
    else:
        a2 = (point[1] - start[1]) / delta[1]

    if a1 is None:
        return start[0] == point[0] and 0 <= a2 <= length
    elif a2 is None:
        return start[1] == point[1] and 0 <= a1 <= length
    else:
        return a1 == a2 and 0 <= a1 <= length


def collides(face_v1, face_v2, face_v3, box_mid_x, box_mid_z, box_size_x, box_size_z):
    min_x = min(face_v1[0], face_v2[0], face_v3[0]) - box_mid_x
    max_x = max(face_v1[0], face_v2[0], face_v3[0]) - box_mid_x

    min_z = min(face_v1[2], face_v2[2], face_v3[2]) - box_mid_z
    max_z = max(face_v1[2], face_v2[2], face_v3[2]) - box_mid_z

    """point1 = (face_v1[0] - box_mid_x, face_v1[2] - box_mid_z)
    point2 = (face_v2[0] - box_mid_x, face_v2[2] - box_mid_z)
    point3 = (face_v3[0] - box_mid_x, face_v3[2] - box_mid_z)"""


    half_x = box_size_x / 2.0
    half_z = box_size_z / 2.0

    if max_x < -half_x or min_x > +half_x:
        return False
    if max_z < -half_z or min_z > +half_z:
        return False

    """tri_line1 = create_line(point1, point2)
    tri_line2 = create_line(point1, point3)
    tri_line3 = create_line(point2, point3)

    quad_line1 = create_line((-half_x, -half_z), (-half_x, half_z))
    quad_line2 = create_line((-half_x, -half_z), (half_x, -half_z))
    quad_line3 = create_line((half_x, half_z), (-half_x, half_z))
    quad_line4 = create_line((half_x, half_z), (half_x, -half_z))"""

    return True


def calc_middle(vertices, v1, v2, v3):
    x1, y1, z1 = vertices[v1]
    x2, y2, z2 = vertices[v2]
    x3, y3, z3 = vertices[v3]

    return (x1+x2+x3)/3.0, (y1+y2+y3)/3.0, (z1+z2+z3)/3.0


def calc_middle_of_2(vertices, v1, v2):
    x1, y1, z1 = vertices[v1]
    x2, y2, z2 = vertices[v2]

    return (x1+x2)/2.0, (y1+y2)/2.0, (z1+z2)/2.0


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


def calc_lookuptable(v1, v2, v3):
    min_x = min_z = max_x = max_z = None

    if v1[0] <= v2[0] and v1[0] <= v3[0]:
        min_x = 0
    elif v2[0] <= v1[0] and v2[0] <= v3[0]:
        min_x = 1
    elif v3[0] <= v1[0] and v3[0] <= v2[0]:
        min_x = 2

    if v1[0] >= v2[0] and v1[0] >= v3[0]:
        max_x = 0
    elif v2[0] >= v1[0] and v2[0] >= v3[0]:
        max_x = 1
    elif v3[0] >= v1[0] and v3[0] >= v2[0]:
        max_x = 2

    if v1[2] <= v2[2] and v1[2] <= v3[2]:
        min_z = 0
    elif v2[2] <= v1[2] and v2[2] <= v3[2]:
        min_z = 1
    elif v3[2] <= v1[2] and v3[2] <= v2[2]:
        min_z = 2

    if v1[2] >= v2[2] and v1[2] >= v3[2]:
        max_z = 0
    elif v2[2] >= v1[2] and v2[2] >= v3[2]:
        max_z = 1
    elif v3[2] >= v1[2] and v3[2] >= v2[2]:
        max_z = 2

    return min_x, min_z, max_x, max_z


def read_int(f):
    val = f.read(0x4)
    return unpack(">I", val)[0]


def read_float_tripple(f):
    val = f.read(0xC)
    return unpack(">fff", val)


def write_uint32(f, val):
    f.write(pack(">I", val))


def write_int32(f, val):
    f.write(pack(">i", val))


def write_ushort(f, val):
    f.write(pack(">H", val))


def write_short(f, val):
    f.write(pack(">h", val))


def write_byte(f, val):
    f.write(pack("B", val))


def write_float(f, val):
    f.write(pack(">f", val))


def subdivide_coordinates(startx, startz, endx, endz):
    halfx = (startx+endx)/2.0
    halfz = (startz+endz)/2.0
    quadrant00 = (startx, startz, halfx, halfz)
    quadrant10 = (halfx, startz, endx, halfz)
    quadrant01 = (startx, halfz, halfx, endz)
    quadrant11 = (halfx, halfz, endx, endz)

    # x ->
    # 01 11 ^
    # 00 10 z
    # Bottom left is (startx,startz), top right is (endx, endz)

    return quadrant00, quadrant10, quadrant01, quadrant11


def subdivide_cell(cell_start_x, cell_start_z, cell_end_x, cell_end_z, triangles, vertices):
    quadrants = ([], [], [], [])
    quadrant_coords = subdivide_coordinates(cell_start_x, cell_start_z,
                                            cell_end_x, cell_end_z)

    for i, quadrant in enumerate(quadrant_coords):
        startx, startz, endx, endz = quadrant
        midx, midz = (startx+endx)/2.0, (startz+endz)/2.0
        sizex, sizez = endx-startx, endz-startz

        for j, face in triangles:
            v1_index, v2_index, v3_index = face

            v1 = vertices[v1_index - 1]
            v2 = vertices[v2_index - 1]
            v3 = vertices[v3_index - 1]

            if collides(v1, v2, v3,
                        midx,
                        midz,
                        sizex,
                        sizez):
                # print(i, "collided")
                quadrants[i].append((j, face))

    return quadrants, quadrant_coords


def subdivide_grid(minx, minz,
                   gridx_start, gridx_end, gridz_start, gridz_end,
                   cell_size, triangles, vertices, result):
    # print("Subdivision with", gridx_start, gridz_start, gridx_end, gridz_end, (gridx_start+gridx_end) // 2, (gridz_start+gridz_end) // 2)
    if gridx_start == gridx_end - 1 and gridz_start == gridz_end - 1:
        if gridx_start not in result:
            result[gridx_start] = {}
        result[gridx_start][gridz_start] = triangles

        return True

    assert gridx_end > gridx_start or gridz_end > gridz_start

    halfx = (gridx_start + gridx_end) // 2
    halfz = (gridz_start + gridz_end) // 2

    quadrants = (
        [], [], [], []
    )
    # x->
    # 2 3 ^
    # 0 1 z
    coordinates = (
        (0, gridx_start, halfx, gridz_start, halfz),  # Quadrant 0
        (1, halfx, gridx_end, gridz_start, halfz),  # Quadrant 1
        (2, gridx_start, halfx, halfz, gridz_end),  # Quadrant 2
        (3, halfx, gridx_end, halfz, gridz_end)  # Quadrant 3
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

        v1 = vertices[v1_index - 1]
        v2 = vertices[v2_index - 1]
        v3 = vertices[v3_index - 1]

        for quadrant, startx, endx, startz, endz in coordinates:
            if quadrant not in skip:
                area_size_x = (endx - startx) * cell_size
                area_size_z = (endz - startz) * cell_size

                if collides(v1, v2, v3,
                            minx + startx * cell_size + area_size_x // 2,
                            minz + startz * cell_size + area_size_z // 2,
                            area_size_x,
                            area_size_z):
                    # print(i, "collided")
                    quadrants[quadrant].append((i, face))

    for quadrant, startx, endx, startz, endz in coordinates:
        # print("Doing subdivision, skipping:", skip)
        if quadrant not in skip:
            # print("doing subdivision with", coordinates[quadrant])
            subdivide_grid(minx, minz,
                           startx, endx, startz, endz,
                           cell_size, quadrants[quadrant], vertices, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("input",
                        help="Filepath of the wavefront .obj file that will be converted into collision")
    parser.add_argument("output", default=None, nargs = '?',
                        help="Output path of the created collision file")
    parser.add_argument("--cell_size", default=1000, type=int,
                        help=("Size of a single cell in the grid. Bigger size results in smaller grid size but higher "
                              "amount of triangles in a single cell."))

    parser.add_argument("--quadtree_depth", default=2, type=int,
                        help=("Depth of the quadtree structure that's used for optimizing collision detection. "
                              "Quadtrees are used to subdivide cells in the grid further when a cell has too many "
                              "triangles."))

    parser.add_argument("--max_tri_count", default=20, type=int,
                        help=("The maximum amount of triangles a cell or a leaf of a quadtree "
                              "is allowed to have before it is subdivided further."))
    
    parser.add_argument("--soundfile", default=None, type=str,
                        help=("Path to sound file that assigns sounds to collision types"))
                        
    parser.add_argument("--steep_faces_as_walls", action="store_true",
                        help="If set, steep faces that have no collision type asigned to them will become walls")
                        
    parser.add_argument("--steep_face_angle", default=89.5, type=float,
                        help=("Minimum angle from the horizontal in degrees a face needs to have to count as a steep face. "
                              "Value needs to be between 0 and 90"))

    args = parser.parse_args()
    input_model = args.input
    entry_max_tri_count = args.max_tri_count
    quadtree_depth = args.quadtree_depth
    steep_faces_as_walls = args.steep_faces_as_walls
    
    base_dir = os.path.dirname(input_model)

    if args.output is None:
        output = input_model + ".bco"
    else:
        output = args.output
    
    sounds = None 
    default = None 
    
    if not (0 <= args.steep_face_angle <= 90):
        raise RuntimeError("Steep face angle needs to be between 0 and 90!")
    
    cos_steep_face_angle = math.cos(math.radians(args.steep_face_angle))

    
    if args.soundfile is not None:
        try:
            sounds = {}
            with open(args.soundfile, "r") as f:
                for line in f:
                    line = line.strip()
                    line = line.split("#")[0]
                    floortype, soundentry = line.split("=")
                    soundval, unk1, unk2 = soundentry.split(",")
                    if floortype.lower().strip() == "default" and default is None:
                        default = (int(soundval,16), int(unk1,16), int(unk2,16))
                    else:
                        sounds[int(floortype, 16)] = (int(soundval,16), int(unk1,16), int(unk2,16))
                        
        except FileNotFoundError as e:
            print(e)
        

    with open(input_model, "r") as f:
        vertices, triangles, normals, minmax_coords = read_obj(f)
    print(input_model, "loaded")
    if len(triangles) > 2**16:
        raise RuntimeError("Too many triangles: {0}\nOnly <=65536 triangles supported!".format(len(triangles)))

    smallest_x, smallest_z, biggest_x, biggest_z = minmax_coords

    assert args.cell_size > 0

    cell_size_x = args.cell_size #1000.0
    cell_size_z = args.cell_size #1000.0


    grid_start_x = floor(smallest_x / cell_size_x) * cell_size_x
    grid_start_z = floor(smallest_z / cell_size_z) * cell_size_z

    grid_end_x = ceil(biggest_x / cell_size_x) * cell_size_x
    grid_end_z = ceil(biggest_z / cell_size_z) * cell_size_z

    grid_size_x = (grid_end_x - grid_start_x) / cell_size_x
    grid_size_z = (grid_end_z - grid_start_z) / cell_size_z

    print(grid_start_x, grid_start_z, grid_end_x, grid_end_z)
    print(grid_size_x, grid_size_z)

    assert grid_size_x % 1 == 0
    assert grid_size_z % 1 == 0

    grid_size_x = int(grid_size_x)
    grid_size_z = int(grid_size_z)

    grid = {}
    children = []
    print("calculating grid")

    def calc_average_height(face):
        return (vertices[face[0] - 1][1]+
                vertices[face[1] - 1][1]+
                vertices[face[2] - 1][1])/3.0

    triangles.sort(key=calc_average_height, reverse=True)

    triangles_indexed = ((i, face[:3]) for i, face in enumerate(triangles))
    subdivide_grid(grid_start_x, grid_start_z,
                   0, grid_size_x, 0, grid_size_z, cell_size_x,
                   triangles_indexed, vertices,
                   grid)
    print("grid calculated")
    print("writing bco file")

    with open(output, "wb") as f:
        f.write(b"0003")
        write_ushort(f, grid_size_x)
        write_ushort(f, grid_size_z)
        write_int32(f, int(grid_start_x))
        write_int32(f, int(grid_start_z))
        write_uint32(f, int(cell_size_x))
        write_uint32(f, int(cell_size_z))
        write_ushort(f, 0x0000) # Entry count of last section
        write_ushort(f, 0x0000) # Padding?

        # Placeholder values for later
        write_uint32(f, 0x1234ABCD) # Triangle indices offset
        write_uint32(f, 0x2345ABCD) # triangles offset
        write_uint32(f, 0x3456ABCD) # vertices offset
        write_uint32(f, 0x00000000) # unknown section offset

        print(hex(f.tell()))
        assert f.tell() == 0x2C

        grid_offset = 0x2C

        groups = []

        triangle_group_index = 0

        class GridEntry(object):
            def __init__(self):
                self.triangles = []
                self.child_index = 0
                self.triangle_index = 0
                self.coords = None

        base_offset = grid_size_x*grid_size_z
        remaining_entries = []


        #for entry in grid:
        for iz in range(grid_size_z):
            print("progress:",iz+1, "/",grid_size_z)
            for ix in range(grid_size_x):
                entry = grid[ix][iz]
                tricount = len(entry)
                """if tricount >= 120:
                    raise RuntimeError("Too many triangles in one spot:", tricount)"""

                if tricount > entry_max_tri_count:
                    write_byte(f, 0x00)
                    write_byte(f, 0x00)
                    write_ushort(f, base_offset+len(remaining_entries))
                    write_uint32(f, triangle_group_index) # We can simply reuse the group index

                    startx = grid_start_x + ix*cell_size_x
                    startz = grid_start_z + iz*cell_size_z
                    endx = startx + cell_size_x
                    endz = startz + cell_size_z

                    quadrants, quadrant_coords = subdivide_cell(startx, startz, endx, endz, entry, vertices)
                    has_tris = False

                    for quadrant, coords in zip(quadrants, quadrant_coords):
                        gridentry = GridEntry()
                        if len(quadrant) > 0:
                            has_tris = True
                        #if len(quadrant) > 30:
                        #    pass
                        #    #more_quadrants, more_quadrant_coords = subdivide_cell()
                        #else:
                        gridentry.coords = coords
                        gridentry.triangles = quadrant
                        gridentry.triangle_index = triangle_group_index
                        triangle_group_index += len(quadrant)
                        remaining_entries.append(gridentry)
                        groups.append(quadrant)
                    assert has_tris is True

                else:
                    write_byte(f, tricount)
                    write_byte(f, 0x00)
                    write_ushort(f, 0x0000)
                    write_uint32(f, triangle_group_index)

                    triangle_group_index += tricount
                    groups.append(entry)


        offset = 0

        for i in range(quadtree_depth):
            base_offset += len(remaining_entries)
            new_remaining_entries = []
            original_length = len(remaining_entries)
            print("quadtree depth", i, original_length)
            for gridentry in remaining_entries:
                if i == quadtree_depth - 1 and len(gridentry.triangles) > 250:
                    print(len(gridentry.triangles))
                    print(gridentry.coords)
                    raise RuntimeError("Too many triangles in a portion of the model")

                if i < quadtree_depth - 1 and len(gridentry.triangles) > entry_max_tri_count:
                    write_byte(f, 0x00) # A grid entry with children has no triangles
                    write_byte(f, 0x00) # Padding
                    write_ushort(f, base_offset+len(new_remaining_entries))
                    write_uint32(f, triangle_group_index)

                    startx, startz, endx, endz = gridentry.coords

                    quadrants, quadrant_coords = subdivide_cell(startx, startz, endx, endz,
                                                                gridentry.triangles, vertices)
                    has_tris = False

                    for quadrant, coords in zip(quadrants, quadrant_coords):
                        gridentry = GridEntry()
                        if len(quadrant) > 0:
                            has_tris = True
                            
                        gridentry.coords = coords
                        gridentry.triangles = quadrant
                        gridentry.triangle_index = triangle_group_index
                        triangle_group_index += len(quadrant)
                        new_remaining_entries.append(gridentry)
                        groups.append(quadrant)
                    assert has_tris is True

                else:
                    write_byte(f, len(gridentry.triangles))
                    write_byte(f, 0x00)
                    write_ushort(f, gridentry.child_index)
                    write_uint32(f, gridentry.triangle_index)

            remaining_entries = new_remaining_entries

            offset = original_length
            
        print("written grid")
        tri_indices_offset = f.tell()
        for trianglegroup in groups:
            for triangle_index, triangle in trianglegroup:
                write_ushort(f, triangle_index)
        print("written triangle indices")
        assert (f.tell() % 4) in (2, 0) 
        if f.tell() % 4 == 2:
            write_ushort(f, 0x00) # Padding 
        tri_offset = f.tell()
        assert tri_offset % 4 == 0


        neighbours = {}
        """for i, triangle in enumerate(triangles):
            v1_index = triangle[0]
            v2_index = triangle[1]
            v3_index = triangle[2]

            indices = [v1_index, v2_index, v3_index] # sort the indices to always have them in the same order
            indices.sort()

            if i == 0xFFFF:
                print("Warning: Your collision has a triangle with index 0xFFFF. "
                      "This might cause unintended side effects related to that specific triangle.")"""

        """ for edge in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
                if edge not in neighbours:
                    neighbours[edge] = [i]
                elif len(neighbours[edge]) == 1:
                    neighbours[edge].append(i)
                else:
                    print("Warning: Edge {0} already has neighbours {1}, but there is an additional "
                          "neighbour {2} that will be ignored.".format(edge, neighbours[edge], i))"""
        
        floor_sound_types = {}
        
        for i, triangle in enumerate(triangles):
            v1_index = triangle[0]
            v2_index = triangle[1]
            v3_index = triangle[2]

            floor_type = triangle[3]

            v1 = vertices[v1_index-1]
            v2 = vertices[v2_index-1]
            v3 = vertices[v3_index-1]

            v1tov2 = create_vector(v1,v2)
            v2tov3 = create_vector(v2,v3)
            v3tov1 = create_vector(v3,v1)
            v1tov3 = create_vector(v1,v3)

            cross_norm = cross_product(v1tov2, v1tov3)
            #cross_norm = cross_product(v1tov2, v1tov3)

            if cross_norm[0] == cross_norm[1] == cross_norm[2] == 0.0:
                norm = cross_norm
                norm_fail = True 
                print("norm calculation failed")
            else:
                norm = normalize_vector(cross_norm)
                norm_fail = False

            norm_x = int(round(norm[0], 4) * 10000)
            norm_y = int(round(norm[1], 4) * 10000)
            norm_z = int(round(norm[2], 4) * 10000)

            midx = (v1[0]+v2[0]+v3[0])/3.0
            midy = (v1[1]+v2[1]+v3[1])/3.0
            midz = (v1[2]+v2[2]+v3[2])/3.0
            
            if floor_type is None:
                if norm_fail:
                    floor_type = 0x200 # 0x200 is fall-through
                else:
                    if steep_faces_as_walls and abs(round(norm[1], 4)) < cos_steep_face_angle:
                        floor_type = 0x1200
                    else:
                        floor_type = 0x0100
                
            

            floatval = (-1)*(round(norm[0], 4) * midx + round(norm[1], 4) * midy + round(norm[2], 4) * midz)

            min_x, min_z, max_x, max_z = calc_lookuptable(v1, v2, v3)

            vlist = (v1, v2, v3)
            assert vlist[min_x][0] == min(v1[0], v2[0], v3[0])
            assert vlist[min_z][2] == min(v1[2], v2[2], v3[2])

            assert vlist[max_x][0] == max(v1[0], v2[0], v3[0])
            assert vlist[max_z][2] == max(v1[2], v2[2], v3[2])

            indices = [v1_index, v2_index, v3_index]  # sort the indices to always have them in the same order
            indices.sort()

            """local_neighbours = []
            for edge in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
                if edge in neighbours:
                    neighbour = neighbours[edge]
                    if len(neighbour) == 1:
                        local_neighbours.append(0xFFFF)
                    elif i == neighbour[0] and (floor_type & 0xFF00) == (triangles[neighbour[1]][3] & 0xFF00):
                        local_neighbours.append(neighbour[1])
                    elif i == neighbour[1] and (floor_type & 0xFF00) == (triangles[neighbour[0]][3] & 0xFF00):
                        local_neighbours.append(neighbour[0])
                    else:
                        local_neighbours.append(0xFFFF)
                else:
                    local_neighbours.append(0xFFFF)"""

            start = f.tell()

            write_uint32(f, v1_index-1)
            write_uint32(f, v2_index-1)
            write_uint32(f, v3_index-1)

            write_float(f, floatval)

            write_short(f, norm_x)
            write_short(f, norm_y)
            write_short(f, norm_z)

            write_ushort(f,floor_type)
            floor_sound_types[floor_type] = True

            write_byte(f, (max_z << 6) | (max_x << 4) | (min_z << 2) | min_x)  # Lookup table for min/max values
            write_byte(f, 0x01)  # Unknown

            write_ushort(f, 0xFFFF)  #local_neighbours[0]) # Triangle index, 0xFFFF means no triangle reference
            write_ushort(f, 0xFFFF)  #local_neighbours[1]) # Triangle index
            write_ushort(f, 0xFFFF)  #local_neighbours[2]) # Triangle index
            write_uint32(f, 0x00000000)  # Unknown, padding or value that can be set to 0
            end = f.tell()
            assert (end-start) == 0x24

        vertex_offset = f.tell()
        print("written triangle data")
        assert f.tell() % 4 == 0
        for x, y, z in vertices:
            write_float(f, x)
            write_float(f, y)
            write_float(f, z)
        print("written vertices")
        unknown_offset = f.tell()

        f.seek(0x1C)

        write_uint32(f, tri_indices_offset)  # Triangle indices offset
        write_uint32(f, tri_offset)  # triangles offset
        write_uint32(f, vertex_offset)  # vertices offset
        write_uint32(f, unknown_offset)  # unknown section offset
        f.seek(unknown_offset)
        for soundtype in sorted(floor_sound_types.keys()):
            write_ushort(f, soundtype)  # floortype
            
            if sounds is not None and soundtype in sounds:
                sound, unk1, unk2 = sounds[soundtype]
            elif default is not None:
                sound, unk1, unk2 = default 
            else:
                sound, unk1, unk2 = 0x2, 0, 0
            write_short(f, sound)  # Sound to be played?
            write_uint32(f, unk1)
            write_uint32(f, unk2)

        f.seek(0x18)
        write_ushort(f, len(floor_sound_types))

    print("done, file written to", output)
