from dataclasses import dataclass
from struct import pack, unpack, unpack_from, Struct
from lib.vectors import Triangle, Vector3, Quad, Line
from OpenGL import *
from numpy import array
from math import inf


def read_uint32(f):
    return unpack("I", f.read(4))[0]


def is_end(f):
    curr = f.tell()
    result = False

    if f.read(1) == b"":
        result = True

    f.seek(curr)
    return result


class BWSectionedFile(object):
    def __init__(self, f):
        self.sections = {}

        while not is_end(f):
            section_name = f.read(4)
            size = read_uint32(f)
            data = f.read(size)

            self.sections[section_name] = data


def initiate_from_section(cls, section):
    assert len(section)%cls.size == 0.0
    return list(cls.from_array(section, i) for i in range(len(section)//cls.size))


@dataclass
class Color:
    r: float
    g: float
    b: float
    a: float
    size = 4

    @classmethod
    def from_array(cls, section, i):
        return cls(*(x/255.0 for x in unpack_from("BBBB", section, i*cls.size)))


@dataclass
class UVPoint:
    x: float  # ushort
    y: float  # ushort
    size = 4

    @classmethod
    def from_array(cls, section, i):
        x, y = unpack_from(">HH", section, i*cls.size)
        return cls(x/4096.0, y/4096.0)


@dataclass
class Vertex:
    pos: array
    color: Color
    uv1: UVPoint
    uv2: UVPoint


# 11 12
# 13 14

# 21 22
# 23 24


class AABB(object):
    def __init__(self, min: Vector3, max: Vector3):
        self.min = min
        self.max = max
        self.middle = (self.min + self.max)*0.5
        self.quads = []

        corner11 = Vector3(min.x, max.y, min.z)
        corner12 = Vector3(max.x, max.y, min.z)
        corner13 = Vector3(min.x, max.y, max.z)
        corner14 = Vector3(max.x, max.y, max.z)

        corner21 = Vector3(min.x, min.y, min.z)
        corner22 = Vector3(max.x, min.y, min.z)
        corner23 = Vector3(min.x, min.y, max.z)
        corner24 = Vector3(max.x, min.y, max.z)

        # Top
        self.quads.append(Quad(corner11, corner12, corner13, corner14))

        # Sides
        self.quads.append(Quad(corner13, corner14, corner23, corner24))
        self.quads.append(Quad(corner11, corner13, corner21, corner23))
        self.quads.append(Quad(corner12, corner11, corner22, corner21))
        self.quads.append(Quad(corner14, corner12, corner24, corner22))

        # Bottom
        self.quads.append(Quad(corner21, corner22, corner23, corner24))

    def ray_hits_box(self, line: Line, d_filter=inf):
        for quad in self.quads:
            result = line.collide_quad(quad, d_filter)
            if result is not False:
                return True
        return False

    @classmethod
    def from_aabb_list(cls, aabbs: list["AABB"]):
        min_vec = Vector3(inf, inf, inf)
        max_vec = Vector3(-inf, -inf, -inf)

        for aabb in aabbs:
            if aabb.min.x < min_vec.x:
                min_vec.x = aabb.min.x

            if aabb.min.y < min_vec.y:
                min_vec.y = aabb.min.y

            if aabb.min.z < min_vec.z:
                min_vec.z = aabb.min.z

            if aabb.max.x > max_vec.x:
                max_vec.x = aabb.max.x

            if aabb.max.y > max_vec.y:
                max_vec.y = aabb.max.y

            if aabb.max.z > max_vec.z:
                max_vec.z = aabb.max.z

        return cls(min_vec, max_vec)


class TileModel(object):
    def __init__(self, tile, materials, offsetx, offsety):
        self.vertices = []
        self.quads = []
        self.material = materials[tile.material_index]
        self.quads_collision = []

        tl = tile.surface_coordinates[0]
        tr = tile.surface_coordinates[1]
        bl = tile.surface_coordinates[2]
        br = tile.surface_coordinates[3]

        aabb_max = Vector3(-inf, -inf, -inf)
        aabb_min = Vector3(inf, inf, inf)


        for y in range(4):
            for x in range(4):
                fx = x/3.0
                fy = y/3.0
                u = fy*(fx*tl.x + (1-fx)*tr.x) + (1-fy)*(fx*bl.x + (1-fx)*br.x)
                v = fy*(fx*tl.y + (1-fx)*tr.y) + (1-fy)*(fx*bl.y + (1-fx)*br.y)

                index = 4*y + x
                height = tile.heights[index]/16.0
                position = array([(x+offsetx)*4*(4/3)-2048, height, (y+offsety)*4*(4/3)-2048])
                uv1 = UVPoint(u, v)
                uv2 = tile.detail_coordinates[index]
                color = tile.vertex_colors[index]

                self.vertices.append(Vertex(position, color, uv1, uv2))

                if x < 3 and y < 3:
                    indexr = 4*y + x+1
                    indexb = 4*(y+1) + x
                    indexbr = 4*(y+1) + x+1

                    self.quads.append((index, indexr, indexbr, indexb))

        v1 = Vector3(*self.vertices[0].pos)
        v2 = Vector3(*self.vertices[3].pos)
        v3 = Vector3(*self.vertices[3*4+0].pos)
        v4 = Vector3(*self.vertices[3*4+3].pos)
        self.lod_quad = Quad(v1, v2, v3, v4)

        for v1i, v2i, v4i, v3i in self.quads:
            v1 = Vector3(*self.vertices[v1i].pos)
            v2 = Vector3(*self.vertices[v2i].pos)
            v3 = Vector3(*self.vertices[v3i].pos)
            v4 = Vector3(*self.vertices[v4i].pos)
            quad = Quad(v1, v2, v3, v4)
            self.quads_collision.append(quad)

            aabb_min.x = min(aabb_min.x, v1.x, v2.x, v3.x, v4.x)
            aabb_min.y = min(aabb_min.y, v1.y, v2.y, v3.y, v4.y)
            aabb_min.z = min(aabb_min.z, v1.z, v2.z, v3.z, v4.z)
            aabb_max.x = max(aabb_max.x, v1.x, v2.x, v3.x, v4.x)
            aabb_max.y = max(aabb_max.y, v1.y, v2.y, v3.y, v4.y)
            aabb_max.z = max(aabb_max.z, v1.z, v2.z, v3.z, v4.z)

        self.aabb = AABB(aabb_min, aabb_max)

    def ray_collide(self, line: Line, d_filter=inf):
        hit = self.aabb.ray_hits_box(line, d_filter)

        if hit:
            aabb_dist = (line.origin - self.aabb.middle).norm_nosqrt()

            if aabb_dist > 350**2:
                quads = [self.lod_quad]
            else:
                quads = self.quads_collision

            dist = d_filter
            point = None
            for quad in quads:#self.quads_collision:
                result = line.collide_quad(quad, dist)
                if result is not False:
                    p, d = result
                    if d < dist:
                        dist = d
                        point = p
            if point is not None:
                return point, dist
            else:
                return False
        else:
            return False


@dataclass
class Tile:
    heights: list[int]                  # 16 ushorts
    vertex_colors: list[int]            # 16 vertex colors
    surface_coordinates: list[UVPoint]  # 4 UVs
    detail_coordinates: list[UVPoint]   # 16 UVs
    material_index: int
    size = 180

    @classmethod
    def from_array(cls, array, i):
        tiledata = array[i*cls.size:(i+1)*cls.size]
        offset = 0
        heights = list(unpack_from(">16H", tiledata, offset))
        offset += 16*2

        vertex_colors = initiate_from_section(Color, tiledata[offset:offset+16*4])
        offset += 16*4

        surface_coordinates = initiate_from_section(UVPoint, tiledata[offset:offset+16])
        offset += 4*4

        detail_coordinates = initiate_from_section(UVPoint, tiledata[offset:offset+16*4])
        offset += 16*4

        material_index = unpack_from(">I", tiledata, offset)[0]
        offset += 4

        assert offset == cls.size

        return cls(heights, vertex_colors, surface_coordinates, detail_coordinates, material_index)


@dataclass
class Chunk(object):
    tiles: list[Tile]
    size = Tile.size*16

    @classmethod
    def from_array(cls, array, i):
        chunkdata = array[i*cls.size:(i+1)*cls.size]
        tiles = initiate_from_section(Tile, chunkdata)
        return cls(tiles)


@dataclass
class TerrainData:
    chunks_x: int
    chunks_y: int
    unknown_count: int
    material_count: int

    @classmethod
    def from_section(cls, section):
        return cls(*unpack("IIII", section))


@dataclass
class MapMaterial:
    mat1: str
    mat2: str
    unk1: int
    unk2: int
    unk3: int
    unk4: int
    size = 48

    @classmethod
    def from_array(cls, array, i):
        mat1, mat2, unk1, unk2, unk3, unk4 = unpack_from("16s16sIIII", array, i*cls.size)
        mat1 = mat1.strip(b"\x00").decode("ascii")
        mat2 = mat2.strip(b"\x00").decode("ascii")

        return cls(mat1, mat2, unk1, unk2, unk3, unk4)


@dataclass
class MapChunkReference:
    a: int
    b: int
    chunkindex: int
    size = 4

    @classmethod
    def from_array(cls, array, i):
        return cls(*unpack_from(">BBH", array, i*4))


class AABBGroup(object):
    def __init__(self, items: list[TileModel] | list["AABBGroup"]):
        self.items = items
        self.aabb = AABB.from_aabb_list([item.aabb for item in items])

    def subdivide(self, levels=1):
        if levels > 0 and len(self.items) > 0:
            middle = self.aabb.middle

            # group2 group3
            # group1 group4
            group1 = []
            group2 = []
            group3 = []
            group4 = []

            for item in self.items:
                item_middle = item.aabb.middle
                if item_middle.x <= middle.x:
                    if item_middle.z <= middle.z:
                        group1.append(item)  # -x -z
                    else:
                        group4.append(item)  # +x -z
                else:
                    if item_middle.z <= middle.z:
                        group2.append(item)  # -x -z
                    else:
                        group3.append(item)  # -x +z

            aabbgroup1 = AABBGroup(group1)
            aabbgroup2 = AABBGroup(group2)
            aabbgroup3 = AABBGroup(group3)
            aabbgroup4 = AABBGroup(group4)

            aabbgroup1.subdivide(levels - 1)
            aabbgroup2.subdivide(levels - 1)
            aabbgroup3.subdivide(levels - 1)
            aabbgroup4.subdivide(levels - 1)

            self.items = [aabbgroup1, aabbgroup2, aabbgroup3, aabbgroup4]

    def ray_collide(self, line: Line, d_filter=inf, sort_level=0):
        if self.aabb.ray_hits_box(line, d_filter):
            point, dist = None, d_filter

            sorted_items = []

            if sort_level < 3:
                for item in self.items:
                    item_dist = (item.aabb.middle - line.origin).norm_nosqrt()
                    sorted_items.append((item, item_dist))
                sorted_items.sort(key=lambda x: x[1])
            else:
                sorted_items.extend(self.items)

            for item, itemdist in sorted_items:
                result = item.ray_collide(line, dist)

                if result is not False:
                    p, d = result
                    if d < dist:
                        dist = d
                        point = p

            if point is not None:
                return point, dist
            else:
                return False
        else:
            return False


class BWTerrainV2(BWSectionedFile):
    def __init__(self, f):
        super().__init__(f)
        #width, height, unk1, unk2 = unpack("IIII", self.sections[b"RRET"])
        self.terrain_data = TerrainData.from_section(self.sections[b"RRET"])
        self.chunks = initiate_from_section(Chunk, self.sections[b"KNHC"])
        self.map = initiate_from_section(MapChunkReference, self.sections[b"PAMC"])
        self.materials = initiate_from_section(MapMaterial, self.sections[b"LTAM"])

        assert self.terrain_data.chunks_x == self.terrain_data.chunks_y == 64

        self.pointdata = [[None for y in range(self.terrain_data.chunks_y * 16 + 1)] for x in range(self.terrain_data.chunks_y * 16 + 1)]

        self.grids = []
        chunk_group = []

        self.meshes: dict[TileModel] = {}
        for chunkx in range(64):
            for chunky in range(64):
                mapchunk = self.map[chunky*64 + chunkx]
                if mapchunk.b == 1:
                    chunk = self.chunks[mapchunk.chunkindex]

                    chunk_tiles = []

                    for tilex in range(4):
                        for tiley in range(4):
                            tile = chunk.tiles[tiley*4+tilex]

                            if tile.material_index not in self.meshes:
                                self.meshes[tile.material_index] = []

                            for x in range(4):
                                for y in range(4):
                                    index = y*4 + x
                                    self.pointdata[chunkx*16 + tilex*4 + x][chunky*16+tiley*4+y] = tile.heights[index]/16.0

                            tilemodel = TileModel(tile, self.materials, chunkx*16 + tilex*4 - tilex -chunkx*4, chunky*16 + tiley*4 - tiley - chunky*4)
                            self.meshes[tile.material_index].append(tilemodel)
                            chunk_tiles.append(tilemodel)
                            chunk_group.append(tilemodel)

            self.chunk_group = AABBGroup(chunk_group)
            self.chunk_group.subdivide(5)

    def check_height(self, x, y):
        mapx = int((x + 2048)*0.25)
        mapy = int((y + 2048)*0.25)
        if 0 <= mapx < 1024 and 0 <= mapy < 1024:
            if self.pointdata[mapx][mapy] is None:
                return None
            return self.pointdata[mapx][mapy]
        else:
            return None

    def ray_collide(self, line: Line):
        point, dist = None, inf
        result = self.chunk_group.ray_collide(line)
        if result is not False:
            p, d = result
            dist = d
            point = p

        if point is not None:
            return point, dist
        else:
            return False


class BWTerrain(BWSectionedFile):
    def __init__(self, f):
        super().__init__(f)

        width, height, unk1, unk2 = unpack("IIII", self.sections[b"RRET"])
        assert width == height == 64
        self.tiles = self.sections[b"KNHC"]
        self.map = self.sections[b"PAMC"]

        self.triangles = []
        self.colors = []
        pointdata = {}
        self.pointdata = [[None for y in range(height*16+1)] for x in range(width*16+1)]
        pointdata = self.pointdata

        for x in range(width):
            for y in range(height):
                a, b, index = self.get_map_entry(x, y)
                tilegroupdata = self.tiles[180*16*index:180*16*(index+1)]
                if b == 1:

                    for ix in range(4):
                        for iy in range(4):
                            groupdindex = iy * 4 + ix
                            tiledata = tilegroupdata[180*groupdindex:180*(groupdindex+1)]

                            for iix in range(4):
                                for iiy in range(4):
                                    pointindex = iiy*4 + iix
                                    pheight,  = unpack(">H", tiledata[2*pointindex:2*(pointindex+1)])
                                    r, g, b, unused = unpack("BBBB", tiledata[32 + 4*pointindex:32 + 4*(pointindex+1)])
                                    pointdata[x*16 + ix*4 + iix][y*16 + iy*4 + iiy] = (pheight, r, g, b)

        for x in range(width):
            for y in range(height):
                a, b, index = self.get_map_entry(x, y)
                tilegroupdata = self.tiles[180 * 16 * index:180 * 16 * (index + 1)]

                if b == 1:
                    for ix in range(4):
                        for iy in range(4):
                            for iix in range(4):
                                for iiy in range(4):
                                    totalx = x*16 + ix*4 + iix
                                    totaly = y*16 + iy*4 + iiy

                                    if (pointdata[totalx+1][totaly] is None
                                        or pointdata[totalx+1][totaly+1] is None
                                        or pointdata[totalx][totaly+1] is None):

                                        continue

                                    fac = 0.25
                                    hfac = 32.0
                                    v1 = Vector3((totalx)/fac - 2048,    -((totaly)/fac - 2048), pointdata[totalx][totaly][0]/hfac)
                                    v2 = Vector3((totalx+1)/fac - 2048,  -((totaly)/fac - 2048), pointdata[totalx+1][totaly][0]/hfac)
                                    v3 = Vector3((totalx+1)/fac - 2048,  -((totaly+1)/fac - 2048), pointdata[totalx+1][totaly+1][0]/hfac)
                                    v4 = Vector3((totalx)/fac - 2048,    -((totaly+1)/fac - 2048), pointdata[totalx][totaly+1][0]/hfac)

                                    c1 = pointdata[totalx][totaly][1:]
                                    c2 = pointdata[totalx+1][totaly][1:]
                                    c3 = pointdata[totalx+1][totaly+1][1:]
                                    c4 = pointdata[totalx][totaly+1][1:]

                                    tri1 = Triangle(v1, v3, v2)
                                    tri2 = Triangle(v1, v3, v4)

                                    self.triangles.append(tri1)
                                    self.triangles.append(tri2)
                                    self.colors.append((c1, c3, c2))
                                    self.colors.append((c1, c3, c4))

    def get_map_entry(self, map_x, map_y):
        index = map_y * 64 + map_x
        a, b, tileindex = unpack_from(">BBH", self.map, index*4)
        return a, b, tileindex


if __name__ == "__main__":
    with open("MP4.out", "rb") as f:
        bwterrain = BWTerrainV2(f)

    #print(bwterrain.chunks)
    #print(bwterrain.map)
    print(bwterrain.materials)

    for chunk in bwterrain.chunks:
        for tile in chunk.tiles:
            print(tile.surface_coordinates)