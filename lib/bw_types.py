from lib.vectors import Matrix4x4, Vector4, Vector3

TYPES = []


class BWMatrix(object):
    def __init__(self, *values):
        self.mtx = Matrix4x4(*values)
        self.mtx.transpose()
        self.position = Vector3(self.mtx.d1, self.mtx.d2, self.mtx.d3)
        self.mtx.d1 = self.mtx.d2 = self.mtx.d3 = 0

    def to_array(self):
        mtx = self.mtx.transposed()
        return [self.mtx.a1, self.mtx.a2, self.mtx.a3, self.mtx.a4,
                self.mtx.b1, self.mtx.b2, self.mtx.b3, self.mtx.b4,
                self.mtx.c1, self.mtx.c2, self.mtx.c3, self.mtx.c4,
                self.position.x, self.position.y, self.position.z, self.mtx.d4]


def boolean_from(bool):
    if bool == "eFalse":
        return False 
    elif bool == "eTrue":
        return True 


def boolean_to(bool):
    if bool:
        return "eTrue"
    else:
        return "eFalse"


def matrix4x4_from(mtx_text):
    vals = mtx_text.split(",")
    mtx = BWMatrix(*(float(x) for x in vals))
    return mtx


def matrix4x4_to(mtx):
    return ",".join(str(v) for v in mtx.to_array())


def vector4_from(vec_text):
    vals = vec_text.split(",")
    mtx = Vector4(*(float(x) for x in vals))
    return mtx


def vector4_to(vec):
    return "{0},{1},{2},{3}".format(vec.x, vec.y, vec.z, vec.w)


# Pass-through
default_from = lambda x: x 
default_to = lambda x: str(x)


CONVERTERS_FROM = {
    "sFloat": float,
    "eBoolean": boolean_from,
    "cFxString8": default_from,
    "sMatrix4x4": matrix4x4_from,
    "cMatrix4x4": matrix4x4_from,
    "sVector4": vector4_from,
    "sInt8": int,
    "sInt16": int,
    "sInt32": int,
    "sUInt8": int,
    "sUInt16": int,
    "sUInt32": int,
    "sU8Color": vector4_from
}

CONVERTERS_TO = {
    "eBoolean": boolean_to,
    "sMatrix4x4": matrix4x4_to,
    "cMatrix4x4": matrix4x4_to,
    "sVector4": vector4_to,
    "sU8Color": vector4_to
}


def convert_from(valuetype, values):
    if valuetype not in TYPES:
        TYPES.append(valuetype)
    if valuetype in CONVERTERS_FROM:
        conv = CONVERTERS_FROM[valuetype]
    else:
        conv = default_from 
    
    return (conv(val) for val in values)


def convert_to(valuetype, value):
    if valuetype in CONVERTERS_TO:
        conv = CONVERTERS_TO[valuetype]
    else:
        conv = default_to

    return conv(value)


def get_types():
    return TYPES
