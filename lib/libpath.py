from .libgen import GeneratorReader
from .vectors import Vector3

def read_link(reader: GeneratorReader):
    token = reader.read_token()

    vals = token.split(" ")
    return int(vals[0]), float(vals[1]), int(vals[2]), int(vals[3])

class Waypoint(object):
    def __init__(self, index, id, position, radius):
        self.index = index
        self.position = position
        self.radius = radius
        self.id = id
        self.waypoint_type = None

        self.incoming_links = []
        self.outgoing_links = []

    def add_incoming(self, link, unkfloat, unkint, unkint2):
        if len(self.incoming_links) >= 8:
            raise RuntimeError("Too many incoming links, cannot add more")

        self.incoming_links.append((link, unkfloat, unkint, unkint2))

    def add_outgoing(self, link, unkfloat, unkint, unkint2):
        if len(self.outgoing_links) >= 8:
            raise RuntimeError("Too many outgoing links, cannot add more")
        self.outgoing_links.append((link, unkfloat, unkint, unkint2))

    def get_incoming_info(self, index):
        for val in self.incoming_links:
            if val[0] == index:
                return val
        return None

    def get_outgoing_info(self, index):
        for val in self.outgoing_links:
            if val[0] == index:
                return val
        return None


class Paths(object):
    def __init__(self):
        self.waypoints = []

        self.unique_paths = []
        self.wide_paths = []

        self.path_info = {}

    def _regenerate_unique_paths(self):
        checked = {}
        paths = []
        for waypoint in self.waypoints:
            for link in waypoint.outgoing_links:
                s = waypoint.index
                t = link[0]

                if (s,t) not in checked and (t,s) not in checked:
                    paths.append((s, t))
                    checked[s, t] = True

            """for link in waypoint.incoming_links:
                t = waypoint.index
                s = link[0]

                if (s,t) not in checked or (t,s) not in checked:
                    paths.append((s, t))
                    checked[s, t] = True"""

        return paths

    def _regenerate_pathwidths(self):
        return

        self.wide_paths = []
        up = Vector3(0, 1, 0)

        for s, t in self.unique_paths:
            p1 = self.waypoints[s]
            p2 = self.waypoints[t]

            dir = p2.position - p1.position

            left = dir.cross(up)
            left.normalize()

            info = p1.get_outgoing_info(p2.index)
            print("hi", info)
            if info is not None:
                info2 = p2.get_incoming_info(p1.index)

                assert info2 is not None

                width1 = info[1]/2
                width2 = info2[1]/2

                c1 = p1.position - left*width1
                c2 = p1.position + left*width1
                c3 = p2.position + left*width2
                c4 = p2.position - left*width2

                self.wide_paths.append((c1, c2, c3, c4))





    @classmethod
    def from_file(cls, f):
        paths = cls()
        reader = GeneratorReader(f)
        version = reader.read_integer()
        if version != 5:
            raise RuntimeError("Unsupported Path Version: {0}".format(version))

        pointcount = reader.read_integer()

        for i in range(pointcount):
            assert i == reader.read_integer()  # index
            position = reader.read_vector3f()
            radius = reader.read_float()
            id = reader.read_string()

            waypoint = Waypoint(i, id, Vector3(*position), radius)

            for i in range(8):
                link = read_link(reader)
                if link[0] != -1:
                    waypoint.add_outgoing(*link)

            for i in range(8):
                link = read_link(reader)
                if link[0] != -1:
                    waypoint.add_incoming(*link)
            waypoint.waypoint_type = reader.read_integer()
            paths.waypoints.append(waypoint)

        paths.unique_paths = paths._regenerate_unique_paths()
        paths._regenerate_pathwidths()

        return paths
