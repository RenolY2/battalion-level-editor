from struct import unpack

def read_vertex(v_data):
    split = v_data.split("/")
    if len(split) == 3:
        vnormal = int(split[2])
    else:
        vnormal = None
    v = int(split[0])
    return v, vnormal

def read_obj(objfile):

    vertices = []
    faces = []
    face_normals = []
    normals = []

    for line in objfile:
        line = line.strip()
        args = line.split(" ")

        if len(args) == 0 or line.startswith("#"):
            continue
        cmd = args[0]

        if cmd == "v":
            if "" in args:
                args.remove("")
            x,y,z = map(float, args[1:4])
            vertices.append((x,y,z))
        elif cmd == "f":
            # if it uses more than 3 vertices to describe a face then we panic!
            # no triangulation yet.
            if len(args) == 5:
                v1, v2, v3, v4 = map(read_vertex, args[1:5])
                faces.append((v1, v3, v2))
                faces.append((v3, v1, v4))
            elif len(args) == 4:
                v1, v2, v3 = map(read_vertex, args[1:4])
                faces.append((v1, v2, v3))
            elif len(args) > 5:
                raise RuntimeError("Mesh has faces with more than 4 polygons! Only Tris and Quads supported.")
        elif cmd == "vn":
            nx,ny,nz = map(float, args[1:4])
            normals.append((nx,ny,nz))


    #objects.append((current_object, vertices, faces))

    return vertices, faces, normals

def read_uint32(f):
    val = f.read(0x4)
    return unpack(">I", val)[0]

def read_float_tripple(f):
    val = f.read(0xC)
    return unpack(">fff", val)

def read_uint16(f):
    return unpack(">H", f.read(2))[0]


class BJMP(object):
    def __init__(self, f):
        magic = read_uint32(f)
        if magic != 0x013304E6:
            raise RuntimeError("Expected magic {:x}, got unsupported magic {:x}.".format(0x013304E6, magic))

        unknown = f.read(4*12)  # AABB or something?
        vertex_count = read_uint16(f)

        self.vertices = []
        for i in range(vertex_count):
            self.vertices.append(read_float_tripple(f))

        self.triangles = []
        tri_count = read_uint32(f)
        for i in range(tri_count):
            v1, v2, v3 = read_uint16(f), read_uint16(f), read_uint16(f)
            self.triangles.append((v1, v2, v3))

            f.read(0x78-6)

class PikminCollision(object):
    def __init__(self, f):

        # Read vertices
        vertex_count = read_int(f)
        vertices = []
        for i in range(vertex_count):
            x,y,z = read_float_tripple(f)
            vertices.append((x,y,z))
        assert vertex_count == len(vertices)

        # Read faces
        face_count = read_int(f)
        faces = []
        for i in range(face_count):
            v1 = read_int(f)
            v2 = read_int(f)
            v3 = read_int(f)
            norm_x, norm_y, norm_z = read_float_tripple(f)
            rest = list(unpack(">" + "f"*(0x34//4), f.read(0x34)))

            faces.append([((v1+1, 0),(v2+1, 0),(v3+1, 0)), (norm_x, norm_y, norm_z), rest])

        self.vertices = vertices
        self.faces = faces

        # Read all
        self.tail_offset = f.tell()
        f.seek(0)
        self.data = f.read(self.tail_offset)

        # Store the tail header because we don't know how to change/read it yet
        self.tail_header = f.read(0x28)

        # Read the face groups.
        # Each group is: 4 bytes face count, then 4 bytes face index per face.
        face_groups = []

        while True:
            val = f.read(0x04)

            assert len(val) == 4 or len(val) == 0
            if len(val) == 0:
                break

            data_count = unpack(">I", val)[0]

            group = []

            for i in range(data_count):
                group.append(read_int(f))
            face_groups.append(group)

        self.face_groups = face_groups