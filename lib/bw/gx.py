from enum import Enum, IntEnum

VTXFMT = Enum("VTXFMT", ["NOT_PRESENT", "DIRECT", "INDEX8", "INDEX16"], start=0)

components = ["PosMatIdx"]

for i in range(8):
    components.append("Tex{0}MatIdx".format(i))

components.extend(["Position", "Normal", "Color0", "Color1"])

for i in range(8):
    components.append("Tex{0}Coord".format(i))
VTX = IntEnum("VTX", components)


def get_vtxformat(val):
    if val == 0:
        return VTXFMT.NOT_PRESENT
    elif val == 1:
        return VTXFMT.DIRECT
    elif val == 2:
        return VTXFMT.INDEX8
    elif val == 3:
        return VTXFMT.INDEX16
    else:
        raise RuntimeError("unknown format: {0}".format(val))


class VertexDescriptor(object):
    def __init__(self):
        self.posmat = False
        self.texmat = [False, False, False, False, False, False, False, False]
        self.position = VTXFMT.NOT_PRESENT
        self.normal = VTXFMT.NOT_PRESENT
        self.color0 = VTXFMT.NOT_PRESENT
        self.color1 = VTXFMT.NOT_PRESENT
        self.texcoord = [False, False, False, False, False, False, False, False]

        self.active = []

    def active_attributes(self):
        return self.active

    def _active_attributes(self):
        for attr in VTX:
            if self.exists(attr):
                if attr in (VTX.Position, VTX.Normal, VTX.Color0, VTX.Color1):
                    yield (attr, self.get_format(attr))
                else:
                    yield (attr, None)

    def exists(self, enumval):
        if VTX.Tex0MatIdx <= enumval <= VTX.Tex7MatIdx:
            texmatid = enumval-VTX.Tex0MatIdx
            return self.texmat[texmatid]
        elif VTX.Tex0Coord <= enumval <= VTX.Tex7Coord:
            texcoordid = enumval - VTX.Tex0Coord
            return self.texcoord[texcoordid]
        elif enumval == VTX.PosMatIdx:
            return self.posmat
        elif enumval == VTX.Position:
            return self.position != VTXFMT.NOT_PRESENT
        elif enumval == VTX.Normal:
            return self.normal != VTXFMT.NOT_PRESENT
        elif enumval == VTX.Color0:
            return self.color0 != VTXFMT.NOT_PRESENT
        elif enumval == VTX.Color1:
            return self.color1 != VTXFMT.NOT_PRESENT
        else:
            raise RuntimeError("Unknown enum for exists: {0}", str(enumval))

    def get_format(self, enumval):
        if enumval == VTX.Position:
            return self.position
        elif enumval == VTX.Normal:
            return self.normal
        elif enumval == VTX.Color0:
            return self.color0
        elif enumval == VTX.Color1:
            return self.color1
        else:
            raise RuntimeError("Unknown enum for exists: {0}", str(enumval))

    def from_value(self, val):
        self.posmat = False
        self.texmat = [False, False, False, False, False, False, False, False]
        self.position = VTXFMT.NOT_PRESENT
        self.normal = VTXFMT.NOT_PRESENT
        self.color0 = VTXFMT.NOT_PRESENT
        self.color1 = VTXFMT.NOT_PRESENT
        self.texcoord = [False, False, False, False, False, False, False, False]

        self.active = []



        #print("test", bin(val))
        self.posmat = (val & 0b1) == 1
        val = val >> 1

        for i in range(8):
            self.texmat[i] = (val & 0b1) == 1
            val = val >> 1

        self.position = get_vtxformat(val & 0b11)
        val = val >> 2
        self.normal = get_vtxformat(val & 0b11)
        val = val >> 2
        self.color0 = get_vtxformat(val & 0b11)
        val = val >> 2
        self.color1 = get_vtxformat(val & 0b11)
        val = val >> 2

        for i in range(8):
            self.texcoord[i] = (val & 0b1) == 1
            val = val >> 1

        self.active = list(x for x in self._active_attributes())