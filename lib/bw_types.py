from math import sin, cos
from lib.vectors import Matrix4x4, Vector4, Vector3
from numpy import array, float32, shape, reshape, ndarray
TYPES = []

X = 12
Y = 13
Z = 14





class BWMatrix(object):
    def __init__(self, *values):
        self.mtx = array(values, dtype=float32) #Matrix4x4(*values)
        #self.mtx.transpose()
        #self.position = Vector3(self.mtx.d1, self.mtx.d2, self.mtx.d3)
        #self.mtx.d1 = self.mtx.d2 = self.mtx.d3 = 0

    def to_array(self):
        return self.mtx

    def add_position(self, dx=0, dy=0, dz=0):
        self.mtx[12] += dx
        self.mtx[13] += dy
        self.mtx[14] += dz

    def rotate_y(self, deltay):
        mymtx = self.mtx.reshape((4,4), order="F")
        mtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            cos(deltay), 0.0, -sin(deltay), 0.0,
            0.0, 1.0, 0.0, 0.0,
            sin(deltay), 0.0, cos(deltay), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        mtx = mymtx.dot(mtx)
        flatten = mtx.flatten("F")
        self.mtx[0:15] = flatten[0:15]

    @staticmethod
    def static_rotate_y(mtx, deltay):
        mymtx = mtx.reshape((4, 4), order="F")
        rotmtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            cos(deltay), 0.0, -sin(deltay), 0.0,
            0.0, 1.0, 0.0, 0.0,
            sin(deltay), 0.0, cos(deltay), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        newmtx = mymtx.dot(rotmtx)
        flatten = newmtx.flatten("F")
        mtx[0:15] = flatten[0:15]

    @staticmethod
    def static_rotate_x(mtx, deltax):
        mymtx = mtx.reshape((4, 4), order="F")
        rotmtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            1.0, 0.0, 0.0, 0.0,
            0.0, cos(deltax), -sin(deltax), 0.0,
            0.0, sin(deltax), cos(deltax), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        newmtx = mymtx.dot(rotmtx)
        flatten = newmtx.flatten("F")
        mtx[0:15] = flatten[0:15]

    @staticmethod
    def static_rotate_z(mtx, deltaz):
        mymtx = mtx.reshape((4, 4), order="F")
        rotmtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            cos(deltaz), sin(deltaz), 0.0, 0.0,
            -sin(deltaz), cos(deltaz), 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        newmtx = mymtx.dot(rotmtx)
        flatten = newmtx.flatten("F")
        mtx[0:15] = flatten[0:15]

    @staticmethod
    def vertical_reset(mtx):
        mymtx = mtx.reshape((4, 4), order="F")
        print(mymtx)
        cosval = mymtx[0][0]
        sinval = mymtx[0][2]
        mymtx[0][1] = 0

        length = (cosval**2 + sinval**2)**0.5
        if length > 0:
            cosval = cosval/length
            sinval = sinval/length

        mymtx[0][0] = cosval
        mymtx[0][2] = sinval

        mymtx[1][0] = 0
        mymtx[1][1] = 1
        mymtx[1][2] = 0

        mymtx[2][0] = -sinval
        mymtx[2][1] = 0
        mymtx[2][2] = cosval

        flatten = mymtx.flatten("F")
        mtx[0:15] = flatten[0:15]

    @property
    def x(self):
        return self.mtx[12]

    @property
    def y(self):
        return self.mtx[13]

    @property
    def z(self):
        return self.mtx[14]



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
    rows = []
    vals = mtx.to_array()
    for i in range(4):
        rows.append(",".join("{:f}".format(v) for v in vals[i*4:(i+1)*4]))
    return ", ".join(rows)


def vector4_from(vec_text):
    vals = vec_text.split(",")
    mtx = Vector4(*(float(x) for x in vals))
    return mtx


def decrshift(val, shift):
    return val//(10**shift)

# For correctly rounding the mInertiaBox value to the original value
#  ... please don't use such massive floats without a good reason...
def floatformat(val):
    strval = "{:f}".format(val)

    if val > 10**36:
        dot = strval.find(".")
        value = int(strval[:dot-1])
        for i in range(19):
            digit = decrshift(value, i)%10
            if digit >= 5:
                value += (10-digit)*(10**i)
            else:
                value -= digit*(10**i)

        return str(value)+".000000"
    else:
        return strval


def vector4_to(vec):
    return "{0},{1},{2},{3}".format(floatformat(vec.x),
                                    floatformat(vec.y),
                                    floatformat(vec.z),
                                    floatformat(vec.w))


def vector4_to_u8(vec):
    return "{0},{1},{2},{3}".format(int(vec.x), int(vec.y), int(vec.z), int(vec.w))


# Pass-through
default_from = lambda x: x
default_to = lambda x: str(x)


def string_from(val):
    if val is None:
        return ""
    else:
        return str(val)



CONVERTERS_FROM = {
    "sFloat": float,
    "sFloat32": float,
    "eBoolean": boolean_from,
    "cFxString8": string_from,
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
    "sFloat": lambda x: "{:f}".format(x),
    "sFloat32": lambda x: "{:f}".format(x),
    "eBoolean": boolean_to,
    "sMatrix4x4": matrix4x4_to,
    "cMatrix4x4": matrix4x4_to,
    "sVector4": vector4_to,
    "sU8Color": vector4_to_u8
}


def convert_from(valuetype, value):
    if valuetype not in TYPES:
        TYPES.append(valuetype)
    if valuetype in CONVERTERS_FROM:
        conv = CONVERTERS_FROM[valuetype]
    else:
        conv = default_from

    return conv(value)#(conv(val) for val in values)


def convert_to(valuetype, value):
    if valuetype in CONVERTERS_TO:
        conv = CONVERTERS_TO[valuetype]
    else:
        conv = default_to

    return conv(value)


def get_types():
    return TYPES


if __name__ == "__main__":
    mtx = BWMatrix([1,0,0,0, 0,1,0,0, 0,0,1,0, 1,0,0,0])
    print(mtx.mtx)
    print(shape(mtx.mtx))