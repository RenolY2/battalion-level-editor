import json
from struct import unpack, pack
from numpy import ndarray, array
from binascii import hexlify
from math import cos, sin
from .vectors import Vector3
from collections import OrderedDict
from io import BytesIO
from copy import deepcopy

def read_uint8(f):
    return unpack(">B", f.read(1))[0]


def read_int16(f):
    return unpack(">h", f.read(2))[0]


def read_uint16(f):
    return unpack(">H", f.read(2))[0]


def read_uint24(f):
    return unpack(">I", b"\x00"+f.read(3))[0]


def read_uint32(f):
    return unpack(">I", f.read(4))[0]


def read_float(f):
    return unpack(">f", f.read(4))[0]


def read_string(f):
    start = f.tell()

    next = f.read(1)
    n = 0

    if next != b"\x00":
        next = f.read(1)
        n += 1
    if n > 0:
        curr = f.tell()
        f.seek(start)
        string = f.read(n)
        f.seek(curr)
    else:
        string = ""

    return string


def write_uint16(f, val):
    f.write(pack(">H", val))


PADDING = b"This is padding data to align"


def write_padding(f, multiple):
    next_aligned = (f.tell() + (multiple - 1)) & ~(multiple - 1)

    diff = next_aligned - f.tell()

    for i in range(diff):
        pos = i % len(PADDING)
        f.write(PADDING[pos:pos + 1])


class Rotation(object):
    def __init__(self, forward, up, left):
        self.mtx = ndarray(shape=(4,4), dtype=float, order="F")

        self.mtx[0][0] = forward.x
        self.mtx[0][1] = -forward.z
        self.mtx[0][2] = forward.y
        self.mtx[0][3] = 0.0

        self.mtx[1][0] = left.x
        self.mtx[1][1] = -left.z
        self.mtx[1][2] = left.y
        self.mtx[1][3] = 0.0

        self.mtx[2][0] = up.x
        self.mtx[2][1] = -up.z
        self.mtx[2][2] = up.y
        self.mtx[2][3] = 0.0

        self.mtx[3][0] = self.mtx[3][1] = self.mtx[3][2] = 0.0
        self.mtx[3][3] = 1.0
        #print(forward.x, -forward.z, forward.y)
        #print(self.mtx)
        #print([x for x in self.mtx])

    def rotate_around_x(self, degrees):
        mtx = ndarray(shape=(4,4), dtype=float, order="F", buffer=array([
            cos(degrees), 0.0, -sin(degrees), 0.0,
            0.0, 1.0, 0.0, 0.0,
            sin(degrees), 0.0, cos(degrees), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))

        self.mtx = self.mtx.dot(mtx)

    def rotate_around_y(self, degrees):
        mtx = ndarray(shape=(4,4), dtype=float, order="F", buffer=array([
            1.0, 0.0, 0.0, 0.0,
            0.0, cos(degrees), -sin(degrees), 0.0,
            0.0, sin(degrees), cos(degrees), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))

        self.mtx = self.mtx.dot(mtx)

    def rotate_around_z(self, degrees):
        mtx = ndarray(shape=(4,4), dtype=float, order="F", buffer=array([
            cos(degrees),-sin(degrees), 0.0, 0.0,
            sin(degrees), cos(degrees), 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))

        self.mtx = self.mtx.dot(mtx)

    @classmethod
    def default(cls):
        return cls(Vector3(1, 0, 0),
                   Vector3(0, 1, 0),
                   Vector3(0, 0, -1))

    @classmethod
    def from_mkdd_rotation(cls,
                           s16forwardx, s16forwardy, s16forwardz,
                           s16upx, s16upy, s16upz):
        forward = Vector3(s16forwardx * 0.0001, s16forwardy * 0.0001, s16forwardz * 0.0001)
        up = Vector3(s16upx * 0.0001, s16upy * 0.0001, s16upz * 0.0001)
        left = up.cross(forward)

        return cls(forward, up, left)

    @classmethod
    def from_file(cls, f):
        return cls.from_mkdd_rotation(
            read_int16(f), read_int16(f), read_int16(f),
            read_int16(f), read_int16(f), read_int16(f)
        )

    def get_vectors(self):
        forward = Vector3(self.mtx[0][0], self.mtx[0][2], -self.mtx[0][1])
        up = Vector3(self.mtx[2][0], self.mtx[2][2], -self.mtx[2][1])
        left = Vector3(self.mtx[1][0], self.mtx[1][2], -self.mtx[1][1])
        return forward, up, left

    def set_vectors(self, forward, up, left):
        self.mtx[0][0] = forward.x
        self.mtx[0][1] = -forward.z
        self.mtx[0][2] = forward.y
        self.mtx[0][3] = 0.0

        self.mtx[1][0] = left.x
        self.mtx[1][1] = -left.z
        self.mtx[1][2] = left.y
        self.mtx[1][3] = 0.0

        self.mtx[2][0] = up.x
        self.mtx[2][1] = -up.z
        self.mtx[2][2] = up.y
        self.mtx[2][3] = 0.0

        self.mtx[3][0] = self.mtx[3][1] = self.mtx[3][2] = 0.0
        self.mtx[3][3] = 1.0

    def write(self, f):
        forward = Vector3(self.mtx[0][0], self.mtx[0][2], -self.mtx[0][1])
        up = Vector3(self.mtx[2][0], self.mtx[2][2], -self.mtx[2][1])

        f.write(pack(">hhh",
                     int(round(forward.x * 10000)),
                     int(round(forward.y * 10000)),
                     int(round(forward.z * 10000))
                     ))
        f.write(pack(">hhh",
                     int(round(up.x * 10000)),
                     int(round(up.y * 10000)),
                     int(round(up.z * 10000))
                     ))


class ObjectContainer(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_file(cls, f, count, objcls):
        container = cls()

        for i in range(count):
            obj = objcls.from_file(f)
            container.append(obj)

        return container


ENEMYITEMPOINT = 1
CHECKPOINT = 2
ROUTEGROUP = 3
ROUTEPOINT = 4
OBJECTS = 5
KARTPOINT = 6
AREA = 7
CAMERA = 8
RESPAWNPOINT = 9
LIGHTPARAM = 10
MINIGAME = 11


class ColorRGB(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    @classmethod
    def from_file(cls, f):
        return cls(read_uint8(f), read_uint8(f), read_uint8(f))

    def write(self, f):
        f.write(pack(">BBB", self.r, self.g, self.b))


class ColorRGBA(ColorRGB):
    def __init__(self, r, g, b, a):
        super().__init__(r, g, b)
        self.a = a

    @classmethod
    def from_file(cls, f):
        return cls(*unpack(">BBBB", f.read(4)))

    def write(self, f):
        super().write(f)
        f.write(pack(">B", self.a))


# Section 1
# Enemy/Item Route Code Start
class EnemyPoint(object):
    def __init__(self, position, pointsetting, link, scale, groupsetting, group, pointsetting2, unk1=0, unk2=0):
        self.position = position
        self.pointsetting = pointsetting
        self.link = link
        self.scale = scale
        self.groupsetting = groupsetting
        self.group = group
        self.pointsetting2 = pointsetting2
        self.unk1 = unk1
        self.unk2 = unk2

    @classmethod
    def new(cls):
        return cls(
            Vector3(0.0, 0.0, 0.0),
            0, -1, 1000.0, 0, 0, 0
        )

    @classmethod
    def from_file(cls, f, old_bol=False):
        start = f.tell()
        args = [Vector3(*unpack(">fff", f.read(12)))]
        if not old_bol:
            args.extend(unpack(">HhfHBBBH", f.read(15)))
            padding = f.read(5)  # padding
            assert padding == b"\x00" * 5
        else:
            args.extend(unpack(">HhfHBB", f.read(12)))
            args.extend((0, 0))

        obj = cls(*args)
        obj._size = f.tell() - start
        if old_bol:
            obj._size += 8
        return obj

    def write(self, f):
        start = f.tell()
        f.write(pack(">fff", self.position.x, self.position.y, self.position.z))
        f.write(pack(">Hhf", self.pointsetting, self.link, self.scale))
        f.write(pack(">HBBBH", self.groupsetting, self.group, self.pointsetting2, self.unk1, self.unk2))
        f.write(b"\x00"*5)
        #assert f.tell() - start == self._size


class EnemyPointGroup(object):
    def __init__(self):
        self.points = []
        self.id = 0

    @classmethod
    def new(cls):
        return cls()

    def insert_point(self, enemypoint, index=-1):
        self.points.insert(index, enemypoint)

    def move_point(self, index, targetindex):
        point = self.points.pop(index)
        self.points.insert(targetindex, point)

    def copy_group(self, new_id):
        group = EnemyPointGroup()
        group.id = new_id
        for point in self.points:
            new_point = deepcopy(point)
            new_point.group = new_id
            group.points.append(new_point)

        return group

    def copy_group_after(self, new_id, point):
        group = EnemyPointGroup()
        group.id = new_id
        pos = self.points.index(point)

        # Check if the element is the last element
        if not len(self.points)-1 == pos:
            for point in self.points[pos+1:]:
                new_point = deepcopy(point)
                new_point.group = new_id
                group.points.append(new_point)

        return group

    def remove_after(self, point):
        pos = self.points.index(point)
        self.points = self.points[:pos+1]


class EnemyPointGroups(object):
    def __init__(self):
        self.groups = []
        self._group_ids = {}

    @classmethod
    def from_file(cls, f, count, old_bol=False):
        enemypointgroups = cls()
        curr_group = None

        for i in range(count):
            enemypoint = EnemyPoint.from_file(f, old_bol)
            print("Point", i, "in group", enemypoint.group, "links to", enemypoint.link)
            if enemypoint.group not in enemypointgroups._group_ids:
                # start of group
                curr_group = EnemyPointGroup()
                curr_group.id = enemypoint.group
                enemypointgroups._group_ids[enemypoint.group] = curr_group
                curr_group.points.append(enemypoint)
                enemypointgroups.groups.append(curr_group)
            else:
                enemypointgroups._group_ids[enemypoint.group].points.append(enemypoint)

        return enemypointgroups

    def points(self):
        for group in self.groups:
            for point in group.points:
                yield point

    def new_group_id(self):
        return len(self.groups)

    def used_links(self):
        links = []
        for group in self.groups:
            for point in group.points:
                point: EnemyPoint
                if point.link != -1:
                    if point.link not in links:
                        links.append(point.link)

        return links

    def new_link_id(self):
        existing_links = self.used_links()
        existing_links.sort()
        if len(existing_links) == 0:
            return 0

        max_link = existing_links[-1]

        for i in range(max_link):
            if i not in existing_links:
                return i

        return max_link+1


# Enemy/Item Route Code End


##########
# Section 2
# Checkpoint Group Code Start
class CheckpointGroup(object):
    def __init__(self, grouplink):
        self.points = []
        self._pointcount = 0
        self.grouplink = grouplink
        self.prevgroup = [0, -1, -1, -1]
        self.nextgroup = [0, -1, -1, -1]

    @classmethod
    def new(cls):
        return cls(0)

    def copy_group(self, new_id):
        group = CheckpointGroup(new_id)
        group.grouplink = new_id
        group.prevgroup = deepcopy(self.prevgroup)
        group.nextgroup = deepcopy(self.nextgroup)

        for point in self.points:
            new_point = deepcopy(point)
            group.points.append(new_point)

        return group

    def copy_group_after(self, new_id, point):
        group = CheckpointGroup(new_id)
        pos = self.points.index(point)

        # Check if the element is the last element
        if not len(self.points)-1 == pos:
            for point in self.points[pos+1:]:
                new_point = deepcopy(point)
                group.points.append(new_point)

        return group

    def remove_after(self, point):
        pos = self.points.index(point)
        self.points = self.points[:pos+1]

    @classmethod
    def from_file(cls, f):
        pointcount = read_uint16(f)
        checkpointgroup = cls(read_uint16(f))
        checkpointgroup._pointcount = pointcount

        for i in range(4):
            checkpointgroup.prevgroup[i] = read_int16(f)

        for i in range(4):
            checkpointgroup.nextgroup[i] = read_int16(f)

        return checkpointgroup

    def write(self, f):
        self._pointcount = len(self.points)

        f.write(pack(">HH", self._pointcount, self.grouplink))
        f.write(pack(">hhhh", *self.prevgroup))
        f.write(pack(">hhhh", *self.nextgroup))


class Checkpoint(object):
    def __init__(self, start, end, unk1=0, unk2=0, unk3=0, unk4=0):
        self.start = start
        self.end = end
        self.mid = (start+end)/2.0
        self.unk1 = unk1
        self.unk2 = unk2
        self.unk3 = unk3
        self.unk4 = unk4

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0),
                   Vector3(0.0, 0.0, 0.0))


    @classmethod
    def from_file(cls, f):
        startoff = f.tell()
        start = Vector3(*unpack(">fff", f.read(12)))
        end = Vector3(*unpack(">fff", f.read(12)))
        unk1, unk2, unk3, unk4 = unpack(">BBBB", f.read(4))
        #print(start, end)
        assert unk4 == 0
        assert unk2 == 0 or unk2 == 1
        assert unk3 == 0 or unk3 == 1
        return cls(start, end, unk1, unk2, unk3, unk4)

    def write(self, f):
        f.write(pack(">fff", self.start.x, self.start.y, self.start.z))
        f.write(pack(">fff", self.end.x, self.end.y, self.end.z))
        f.write(pack(">BBBB", self.unk1, self.unk2, self.unk3, self.unk4))


class CheckpointGroups(object):
    def __init__(self):
        self.groups = []

    @classmethod
    def from_file(cls, f, count):
        checkpointgroups = cls()

        for i in range(count):
            group = CheckpointGroup.from_file(f)
            checkpointgroups.groups.append(group)

        for group in checkpointgroups.groups:
            for i in range(group._pointcount):
                checkpoint = Checkpoint.from_file(f)
                group.points.append(checkpoint)

        return checkpointgroups

    def new_group_id(self):
        return len(self.groups)

    def points(self):
        for group in self.groups:
            for point in group.points:
                yield point


# Section 3
# Routes/Paths for cameras, objects and other things
class Route(object):
    def __init__(self):
        self.points = []
        self._pointcount = 0
        self._pointstart = 0
        self.unk1 = 0
        self.unk2 = 0

    @classmethod
    def new(cls):
        return cls()


    @classmethod
    def from_file(cls, f):
        route = cls()
        route._pointcount = read_uint16(f)
        route._pointstart = read_uint16(f)
        #pad = f.read(4)
        #assert pad == b"\x00\x00\x00\x00"
        route.unk1 = read_uint32(f)
        route.unk2 = read_uint8(f)
        pad = f.read(7)
        assert pad == b"\x00"*7

        return route

    def add_routepoints(self, points):
        for i in range(self._pointcount):
            self.points.append(points[self._pointstart+i])

    def write(self, f, pointstart):
        f.write(pack(">HH", len(self.points), pointstart))
        f.write(pack(">IB", self.unk1, self.unk2))
        f.write(b"\x00"*7)


# Section 4
# Route point for use with routes from section 3
class RoutePoint(object):
    def __init__(self, position):
        self.position = position
        self.unk = 0

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0))


    @classmethod
    def from_file(cls, f):
        position = Vector3(*unpack(">fff", f.read(12)))
        point = cls(position)

        point.unk = read_uint32(f)

        padding = f.read(16)
        assert padding == b"\x00"*16
        return point

    def write(self, f):
        f.write(pack(">fffI", self.position.x, self.position.y, self.position.z,
                     self.unk))
        f.write(b"\x00"*16)


# Section 5
# Objects
class MapObject(object):
    def __init__(self, position, objectid):
        self.position = position
        self.scale = Vector3(1.0, 1.0, 1.0)
        self.rotation = Rotation.default()
        self.objectid = objectid
        self.pathid = -1
        self.unk_28 = 0
        self.unk_2a = 0
        self.presence_filter = 255
        self.presence = 0x3
        self.unk_flag = 0
        self.unk_2f = 0
        self.userdata = [0 for i in range(8)]

        self.widget = None

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0), 1)

    @classmethod
    def from_file(cls, f):
        start = f.tell()
        position = Vector3(*unpack(">fff", f.read(12)))
        scale = Vector3(*unpack(">fff", f.read(12)))
        fx, fy, fz = read_int16(f), read_int16(f), read_int16(f)
        ux, uy, uz = read_int16(f), read_int16(f), read_int16(f)

        objectid = read_uint16(f)

        obj = MapObject(position, objectid)
        obj.scale = scale
        obj.rotation = Rotation.from_mkdd_rotation(fx, fy, fz, ux, uy, uz)
        obj.pathid = read_int16(f)
        obj.unk_28 = read_uint16(f)
        obj.unk_2a = read_int16(f)
        obj.presence_filter = read_uint8(f)
        obj.presence = read_uint8(f)
        obj.unk_flag = read_uint8(f)
        obj.unk_2f = read_uint8(f)

        for i in range(8):
            obj.userdata[i] = read_int16(f)
        obj._size = f.tell() - start
        return obj

    def write(self, f):
        start = f.tell()
        f.write(pack(">fff", self.position.x, self.position.y, self.position.z))
        f.write(pack(">fff", self.scale.x, self.scale.y, self.scale.z))
        self.rotation.write(f)

        f.write(pack(">hhHh", self.objectid, self.pathid, self.unk_28, self.unk_2a))
        f.write(pack(">BBBB", self.presence_filter, self.presence, self.unk_flag, self.unk_2f))

        for i in range(8):
            f.write(pack(">h", self.userdata[i]))
        #assert f.tell() - start == self._size


class MapObjects(object):
    def __init__(self):
        self.objects = []

    def reset(self):
        del self.objects
        self.objects = []

    @classmethod
    def from_file(cls, f, objectcount):
        mapobjs = cls()

        for i in range(objectcount):
            obj = MapObject.from_file(f)
            mapobjs.objects.append(obj)

        return mapobjs


# Section 6
# Kart/Starting positions
POLE_LEFT = 0
POLE_RIGHT = 1


class KartStartPoint(object):
    def __init__(self, position):
        self.position = position
        self.scale = Vector3(1.0, 1.0, 1.0)
        self.rotation = Rotation.default()
        self.poleposition = POLE_LEFT

        # 0xFF = All, otherwise refers to player who starts here
        # Example: 0 = Player 1
        self.playerid = 0xFF

        self.unknown = 0

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0))

    @classmethod
    def from_file(cls, f):
        position = Vector3(*unpack(">fff", f.read(12)))

        kstart = cls(position)
        kstart.scale = Vector3(*unpack(">fff", f.read(12)))
        kstart.rotation = Rotation.from_file(f)
        kstart.poleposition = read_uint8(f)
        kstart.playerid = read_uint8(f)
        kstart.unknown = read_uint16(f)
        #assert kstart.unknown == 0
        return kstart

    def write(self, f):
        f.write(pack(">fff", self.position.x, self.position.y, self.position.z))
        f.write(pack(">fff", self.scale.x, self.scale.y, self.scale.z))
        self.rotation.write(f)
        f.write(pack(">BBH", self.poleposition, self.playerid, self.unknown))


class KartStartPoints(object):
    def __init__(self):
        self.positions = []

    @classmethod
    def from_file(cls, f, count):
        kspoints = cls()

        for i in range(count):
            kstart = KartStartPoint.from_file(f)
            kspoints.positions.append(kstart)

        return kspoints


# Section 7
# Areas
class Area(object):
    def __init__(self, position):
        self.position = position
        self.scale = Vector3(1.0, 1.0, 1.0)
        self.rotation = Rotation.default()
        self.check_flag = 0
        self.area_type = 0
        self.camera_index = -1
        self.unk1 = 0
        self.unk2 = 0
        self.unkfixedpoint = 0
        self.unkshort = 0
        self.shadow_id = 0
        self.lightparam_index = 0

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0))

    @classmethod
    def from_file(cls, f):
        position = Vector3(*unpack(">fff", f.read(12)))

        area = cls(position)
        area.scale = Vector3(*unpack(">fff", f.read(12)))
        area.rotation = Rotation.from_file(f)
        area.check_flag = read_uint8(f)
        area.area_type = read_uint8(f)
        area.camera_index = read_int16(f)
        area.unk1 = read_uint32(f)
        area.unk2 = read_uint32(f)
        area.unkfixedpoint = read_int16(f)
        area.unkshort = read_int16(f)
        area.shadow_id = read_int16(f)
        area.lightparam_index = read_int16(f)

        return area

    def write(self, f):
        f.write(pack(">fff", self.position.x, self.position.y, self.position.z))
        f.write(pack(">fff", self.scale.x, self.scale.y, self.scale.z))
        self.rotation.write(f)
        f.write(pack(">BBh", self.check_flag, self.area_type, self.camera_index))
        f.write(pack(">II", self.unk1, self.unk2))
        f.write(pack(">hhhh", self.unkfixedpoint, self.unkshort, self.shadow_id, self.lightparam_index))


class Areas(object):
    def __init__(self):
        self.areas = []

    @classmethod
    def from_file(cls, f, count):
        areas = cls()
        for i in range(count):
            areas.areas.append(Area.from_file(f))

        return areas


# Section 8
# Cameras
class Camera(object):
    def __init__(self, position):
        self.position = position
        self.position2 = Vector3(0.0, 0.0, 0.0)
        self.position3 = Vector3(0.0, 0.0, 0.0)
        self.rotation = Rotation.default()

        self.unkbyte = 0
        self.camtype = 0
        self.startzoom = 0
        self.camduration = 0
        self.startcamera = 0
        self.unk2 = 0
        self.unk3 = 0
        self.route = -1
        self.routespeed = 0
        self.endzoom = 0
        self.nextcam = -1
        self.name = "null"

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0))

    @classmethod
    def from_file(cls, f):
        start = f.tell()
        hexd = f.read(4*3*4)
        f.seek(start)
        print(hexlify(hexd))

        position = Vector3(*unpack(">fff", f.read(12)))

        cam = cls(position)
        cam.rotation = Rotation.from_file(f)
        cam.position2 = Vector3(*unpack(">fff", f.read(12)))
        cam.position3 = Vector3(*unpack(">fff", f.read(12)))
        cam.unkbyte = read_uint8(f)
        cam.camtype = read_uint8(f)
        cam.startzoom = read_uint16(f)
        cam.camduration = read_uint16(f)
        cam.startcamera = read_uint16(f)
        cam.unk2 = read_uint16(f)
        cam.unk3 = read_uint16(f)
        cam.route = read_int16(f)
        cam.routespeed = read_uint16(f)
        cam.endzoom = read_uint16(f)
        cam.nextcam = read_int16(f)
        cam.name = str(f.read(4), encoding="ascii")

        return cam

    def write(self, f):
        f.write(pack(">fff", self.position.x, self.position.y, self.position.z))
        self.rotation.write(f)
        f.write(pack(">fff", self.position2.x, self.position2.y, self.position2.z))
        f.write(pack(">fff", self.position3.x, self.position3.y, self.position3.z))
        f.write(pack(">BBHHH", self.unkbyte, self.camtype, self.startzoom, self.camduration, self.startcamera))
        f.write(pack(">HHhHHh",
                     self.unk2, self.unk3, self.route,
                     self.routespeed, self.endzoom, self.nextcam))
        assert len(self.name) == 4
        f.write(bytes(self.name, encoding="ascii"))


# Section 9
# Jugem Points
class JugemPoint(object):
    def __init__(self, position):
        self.position = position
        self.rotation = Rotation.default()
        self.respawn_id = 0
        self.unk1 = 0
        self.unk2 = 0
        self.unk3 = 0

    @classmethod
    def new(cls):
        return cls(Vector3(0.0, 0.0, 0.0))

    @classmethod
    def from_file(cls, f):
        position = Vector3(*unpack(">fff", f.read(12)))
        jugem = cls(position)
        jugem.rotation = Rotation.from_file(f)
        jugem.respawn_id = read_uint16(f)
        jugem.unk1 = read_uint16(f)
        jugem.unk2 = read_int16(f)
        jugem.unk3 = read_int16(f)

        return jugem

    def write(self, f):
        f.write(pack(">fff", self.position.x, self.position.y, self.position.z))
        self.rotation.write(f)
        f.write(pack(">HHhh", self.respawn_id, self.unk1, self.unk2, self.unk3))


# Section 10
# LightParam
class LightParam(object):
    def __init__(self):
        self.color1 = ColorRGBA(0x64, 0x64, 0x64, 0xFF)
        self.color2 = ColorRGBA(0x64, 0x64, 0x64, 0x00)
        self.unkvec = Vector3(0.0, 0.0, 0.0)



    @classmethod
    def new(cls):
        return cls()

    @classmethod
    def from_file(cls, f):
        lp = cls()
        lp.color1 = ColorRGBA.from_file(f)
        lp.unkvec = Vector3(*unpack(">fff", f.read(12)))
        lp.color2 = ColorRGBA.from_file(f)

        return lp

    def write(self, f):
        self.color1.write(f)
        f.write(pack(">fff", self.unkvec.x, self.unkvec.y, self.unkvec.z))
        self.color2.write(f)


# Section 11
# MG (MiniGame?)
class MGEntry(object):
    def __init__(self):
        self.unk1 = 0
        self.unk2 = 0
        self.unk3 = 0
        self.unk4 = 0

    @classmethod
    def new(cls):
        return cls(0)

    @classmethod
    def from_file(cls, f):
        mgentry = MGEntry()
        mgentry.unk1 = read_int16(f)
        mgentry.unk2 = read_int16(f)
        mgentry.unk3 = read_int16(f)
        mgentry.unk4 = read_int16(f)

        return mgentry

    def write(self, f):
        f.write(pack(">hhhh", self.unk1, self.unk2, self.unk3, self.unk4))


class BOL(object):
    def __init__(self):
        self.roll = 0
        self.rgb_ambient = ColorRGB(0x64, 0x64, 0x64)
        self.rgba_light = ColorRGBA(0xFF, 0xFF, 0xFF, 0xFF)
        self.lightsource = Vector3(0.0, 0.0, 0.0)
        self.fog_type = 0
        self.fog_color = ColorRGB(0x64, 0x64, 0x64)
        self.fog_startz = 8000.0
        self.fog_endz = 230000.0
        self.unk1 = 0
        self.unk2 = 0
        self.unk3 = 0
        self.unk4 = 0
        self.unk5 = 0
        self.unk6 = 0

        self.shadow_color = ColorRGB(0x00, 0x00, 0x00)


        self.sections = {}

        self.lap_count = 3
        self.music_id = 0x21

        self.enemypointgroups = EnemyPointGroups()
        self.checkpoints = CheckpointGroups()
        self.routes = ObjectContainer()
        self.objects = MapObjects()
        self.kartpoints = KartStartPoints()
        self.areas = Areas()
        self.cameras = ObjectContainer()
        self.respawnpoints = ObjectContainer()
        self.lightparams = ObjectContainer()
        self.mgentries = ObjectContainer()

    def objects_with_position(self):
        for group in self.enemypointgroups.groups.values():
            for point in group.points:
                yield point

        for route in self.routes:
            for point in route.points:
                yield point

    def objects_with_2positions(self):
        for group in self.checkpoints.groups:
            for point in group.points:
                yield point

    def objects_with_rotations(self):
        for object in self.objects.objects:
            assert object is not None
            yield object

        for kartpoint in self.kartpoints.positions:
            assert kartpoint is not None
            yield kartpoint

        for area in self.areas.areas:
            assert area is not None
            yield area

        for camera in self.cameras:
            assert camera is not None
            yield camera

        for respawn in self.respawnpoints:
            assert respawn is not None
            yield respawn


    @classmethod
    def from_file(cls, f):
        bol = cls()
        magic = f.read(4)
        print(magic, type(magic))
        assert magic == b"0015" or magic == b"0012"
        old_bol = magic == b"0012"

        bol.roll = read_uint8(f)
        bol.rgb_ambient = ColorRGB.from_file(f)

        if not old_bol:
            bol.rgba_light = ColorRGBA.from_file(f)
            bol.lightsource = Vector3(read_float(f), read_float(f), read_float(f))

        bol.lap_count = read_uint8(f)
        bol.music_id = read_uint8(f)

        sectioncounts = {}
        for i in (ENEMYITEMPOINT, CHECKPOINT, OBJECTS, AREA, CAMERA, ROUTEGROUP, RESPAWNPOINT):
            sectioncounts[i] = read_uint16(f)

        bol.fog_type = read_uint8(f)
        bol.fog_color = ColorRGB.from_file(f)

        bol.fog_startz = read_float(f)
        bol.fog_endz = read_float(f)
        bol.unk1 = read_uint16(f)
        bol.unk2 = read_uint8(f)
        bol.unk3 = read_uint8(f)
        bol.shadow_color = ColorRGB.from_file(f)
        bol.unk4 = read_uint8(f)
        bol.unk5 = read_uint8(f)

        sectioncounts[LIGHTPARAM] = read_uint8(f)
        sectioncounts[MINIGAME] = read_uint8(f)
        bol.unk6 = read_uint8(f)

        filestart = read_uint32(f)
        print(hex(f.tell()), filestart)
        assert filestart == 0

        sectionoffsets = {}
        for i in range(11):
            sectionoffsets[i+1] = read_uint32(f)

        padding = f.read(12) # padding
        assert padding == b"\x00"*12
        endofheader = f.tell()


        #calculated_count = (sectionoffsets[CHECKPOINT] - sectionoffsets[ENEMYITEMPOINT])//0x20
        #assert sectioncounts[ENEMYITEMPOINT] == calculated_count
        f.seek(sectionoffsets[ENEMYITEMPOINT])
        bol.enemypointgroups = EnemyPointGroups.from_file(f, sectioncounts[ENEMYITEMPOINT], old_bol)

        f.seek(sectionoffsets[CHECKPOINT])
        bol.checkpoints = CheckpointGroups.from_file(f, sectioncounts[CHECKPOINT])

        f.seek(sectionoffsets[ROUTEGROUP])
        bol.routes = ObjectContainer.from_file(f, sectioncounts[ROUTEGROUP], Route)

        f.seek(sectionoffsets[ROUTEPOINT])
        routepoints = []
        count = (sectionoffsets[OBJECTS] - sectionoffsets[ROUTEPOINT])//0x20
        for i in range(count):
            routepoints.append(RoutePoint.from_file(f))

        for route in bol.routes:
            route.add_routepoints(routepoints)

        f.seek(sectionoffsets[OBJECTS])
        bol.objects = MapObjects.from_file(f, sectioncounts[OBJECTS])

        f.seek(sectionoffsets[KARTPOINT])
        bol.kartpoints = KartStartPoints.from_file(f, (sectionoffsets[AREA] - sectionoffsets[KARTPOINT])//0x28)

        f.seek(sectionoffsets[AREA])
        bol.areas = Areas.from_file(f, sectioncounts[AREA])

        f.seek(sectionoffsets[CAMERA])
        bol.cameras = ObjectContainer.from_file(f, sectioncounts[CAMERA], Camera)

        f.seek(sectionoffsets[RESPAWNPOINT])
        bol.respawnpoints = ObjectContainer.from_file(f, sectioncounts[RESPAWNPOINT], JugemPoint)

        f.seek(sectionoffsets[LIGHTPARAM])

        bol.lightparams = ObjectContainer.from_file(f, sectioncounts[LIGHTPARAM], LightParam)

        f.seek(sectionoffsets[MINIGAME])
        bol.mgentries = ObjectContainer.from_file(f, sectioncounts[MINIGAME], MGEntry)

        return bol

    def write(self, f):
        f.write(b"0015")
        f.write(pack(">B", self.roll))
        self.rgb_ambient.write(f)
        self.rgba_light.write(f)
        f.write(pack(">fff", self.lightsource.x, self.lightsource.y, self.lightsource.z))
        f.write(pack(">BB", self.lap_count, self.music_id))

        enemypoints = 0
        for group in self.enemypointgroups.groups:
            enemypoints += len(group.points)
        write_uint16(f, enemypoints)
        write_uint16(f, len(self.checkpoints.groups))
        write_uint16(f, len(self.objects.objects))
        write_uint16(f, len(self.areas.areas))
        write_uint16(f, len(self.cameras))
        write_uint16(f, len(self.routes))
        write_uint16(f, len(self.respawnpoints))

        f.write(pack(">B", self.fog_type))
        self.fog_color.write(f)
        f.write(pack(">ffHBB",
                self.fog_startz, self.fog_endz,
                self.unk1, self.unk2, self.unk3))
        self.shadow_color.write(f)
        f.write(pack(">BB", self.unk4, self.unk5))
        f.write(pack(">BB", len(self.lightparams), len(self.mgentries)))
        f.write(pack(">B", self.unk6))

        f.write(b"\x00"*4) # Filestart 0

        offset_start = f.tell()
        offsets = []
        for i in range(11):
            f.write(b"FOOB") # placeholder for offsets
        f.write(b"\x00"*12) # padding

        offsets.append(f.tell())
        for group in self.enemypointgroups.groups:
            #group = self.enemypointgroups.groups[groupindex]
            for point in group.points:
                point.group = group.id
                point.write(f)

        offsets.append(f.tell())
        for group in self.checkpoints.groups:
            group.write(f)
        for group in self.checkpoints.groups:
            for point in group.points:
                point.write(f)

        offsets.append(f.tell())

        index = 0
        for route in self.routes:
            route.write(f, index)
            index += len(route.points)

        offsets.append(f.tell())
        for route in self.routes:
            for point in route.points:
                point.write(f)

        offsets.append(f.tell())
        for object in self.objects.objects:
            object.write(f)

        offsets.append(f.tell())
        for startpoint in self.kartpoints.positions:
            startpoint.write(f)

        offsets.append(f.tell())
        for area in self.areas.areas:
            area.write(f)

        offsets.append(f.tell())
        for camera in self.cameras:
            camera.write(f)

        offsets.append(f.tell())
        for respawnpoint in self.respawnpoints:
            respawnpoint.write(f)

        offsets.append(f.tell())
        for lightparam in self.lightparams:
            lightparam.write(f)

        offsets.append(f.tell())
        for mgentry in self.mgentries:
            mgentry.write(f)
        print(len(offsets))
        assert len(offsets) == 11
        f.seek(offset_start)
        for offset in offsets:
            f.write(pack(">I", offset))


with open("lib/mkddobjects.json", "r") as f:
    tmp = json.load(f)
    OBJECTNAMES = {}
    for key, val in tmp.items():
        OBJECTNAMES[int(key)] = val
    del tmp

REVERSEOBJECTNAMES = OrderedDict()
valpairs = [(x, y) for x, y in OBJECTNAMES.items()]
valpairs.sort(key=lambda x: x[1])

for key, val in valpairs:
    REVERSEOBJECTNAMES[OBJECTNAMES[key]] = key

with open("lib/music_ids.json", "r") as f:
    tmp = json.load(f)
    MUSIC_IDS = {}
    for key, val in tmp.items():
        MUSIC_IDS[int(key)] = val
    del tmp

REVERSE_MUSIC_IDS = OrderedDict()
for key in sorted(MUSIC_IDS.keys()):
    REVERSE_MUSIC_IDS[MUSIC_IDS[key]] = key


def get_full_name(id):
    if id not in OBJECTNAMES:
        OBJECTNAMES[id] = "Unknown {0}".format(id)
        REVERSEOBJECTNAMES[OBJECTNAMES[id]] = id
        #return
    #else:
    return OBJECTNAMES[id]


def temp_add_invalid_id(id):
    if id not in OBJECTNAMES:
        name = get_full_name(id)
        OBJECTNAMES[id] = name
        REVERSEOBJECTNAMES[name] = id


if __name__ == "__main__":
    with open("mario_course.bol", "rb") as f:
        bol = BOL.from_file(f)

    with open("mario_course_new.bol", "wb") as f:
        bol.write(f)

    with open("mario_course_new.bol", "rb") as f:
        newbol = BOL.from_file(f)

    with open("mario_course_new2.bol", "wb") as f:
        newbol.write(f)