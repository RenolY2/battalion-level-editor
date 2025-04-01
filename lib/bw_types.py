from math import sin, cos
import math

if __name__ == "__main__":
    from vectors import Matrix4x4, Vector4, Vector3
else:
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
    def static_rotate_y(mtx, deltay, flip=False):
        mymtx = mtx.reshape((4, 4), order="F")
        rotmtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            cos(deltay), 0.0, -sin(deltay), 0.0,
            0.0, 1.0, 0.0, 0.0,
            sin(deltay), 0.0, cos(deltay), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        if flip:
            newmtx = rotmtx.dot(mymtx)
        else:
            newmtx = mymtx.dot(rotmtx)
        flatten = newmtx.flatten("F")
        mtx[0:15] = flatten[0:15]

    @staticmethod
    def static_rotate_x(mtx, deltax, flip=False):
        mymtx = mtx.reshape((4, 4), order="F")
        rotmtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            1.0, 0.0, 0.0, 0.0,
            0.0, cos(deltax), -sin(deltax), 0.0,
            0.0, sin(deltax), cos(deltax), 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        if flip:
            newmtx = rotmtx.dot(mymtx)
        else:
            newmtx = mymtx.dot(rotmtx)
        flatten = newmtx.flatten("F")
        mtx[0:15] = flatten[0:15]

    @staticmethod
    def static_rotate_z(mtx, deltaz, flip=False):
        mymtx = mtx.reshape((4, 4), order="F")
        rotmtx = ndarray(shape=(4, 4), dtype=float, order="F", buffer=array([
            cos(deltaz), sin(deltaz), 0.0, 0.0,
            -sin(deltaz), cos(deltaz), 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
        if flip:
            newmtx = rotmtx.dot(mymtx)
        else:
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

    def set_position(self, x, y, z):
        self.mtx[12] = x
        self.mtx[13] = y
        self.mtx[14] = z

    def reset_rotation(self):
        self.mtx[0:12] = [1.0, 0.0, 0.0, 0.0,
                          0.0, 1.0, 0.0, 0.0,
                          0.0, 0.0, 1.0, 0.0]


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


def vector2_from(vec_text):
    vals = vec_text.split(",")
    x, z = float(vals[0]), float(vals[1])
    mtx = Vector4(x, 0, z, 0)
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


def vector2_to(vec):
    return "{0},{1}".format(vec.x, vec.z)


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
    "cFxString16": string_from,
    "sMatrix4x4": matrix4x4_from,
    "cMatrix4x4": matrix4x4_from,
    "sVector4": vector4_from,
    "sInt8": int,
    "sInt16": int,
    "sInt32": int,
    "sUInt8": int,
    "sUInt16": int,
    "sUInt32": int,
    "sU8Color": vector4_from,
    "sVectorXZ": vector2_from,
    "cU8Color": vector4_from
}

CONVERTERS_TO = {
    "sFloat": lambda x: "{:f}".format(x),
    "sFloat32": lambda x: "{:f}".format(x),
    "eBoolean": boolean_to,
    "sMatrix4x4": matrix4x4_to,
    "cMatrix4x4": matrix4x4_to,
    "sVector4": vector4_to,
    "sU8Color": vector4_to_u8,
    "sVectorXZ": vector2_to,
    "cU8Color": vector4_to_u8
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

def calc_length(x, y, z):
    return (x**2 + y**2 + z**2) ** 0.5


def decompose(BWMatrix):
    mtx = BWMatrix.mtx.copy().reshape((4, 4), order="F")

    scale_x = calc_length(mtx[0][0], mtx[1][0], mtx[2][0])
    scale_y = calc_length(mtx[0][1], mtx[1][1], mtx[2][1])
    scale_z = calc_length(mtx[0][2], mtx[1][2], mtx[2][2])

    for i in range(3):
        mtx[i][0] = mtx[i][0]/scale_x

    for i in range(3):
        mtx[i][1] = mtx[i][1]/scale_y

    for i in range(3):
        mtx[i][2] = mtx[i][2]/scale_z

    translation_x = mtx[0][3]
    mtx[0][3] = 0
    translation_y = mtx[1][3]
    mtx[1][3] = 0
    translation_z = mtx[2][3]
    mtx[2][3] = 0

    if mtx[0][2] < 1:
        if mtx[0][2] > -1:
            print("A")
            theta_Y = math.asin(mtx[0][2])
            theta_X = math.atan2(-mtx[1][2], mtx[2][2])
            theta_Z = math.atan2(-mtx[0][1], mtx[0][0])
        else:
            print("B")
            theta_Y = -math.pi/2
            theta_X = -math.atan2(mtx[1][0], mtx[1][1])
            theta_Z = 0
    else:
        print("C")
        theta_Y = +math.pi / 2
        theta_X = math.atan2(mtx[1][0], mtx[1][1])
        theta_Z = 0

    return (translation_x, translation_y, translation_z,
            scale_x, scale_y, scale_z,
            math.degrees(theta_X), math.degrees(theta_Y), math.degrees(theta_Z))


def recompose(translation_x, translation_y, translation_z,
              scale_x, scale_y, scale_z,
              theta_X, theta_Y, theta_Z):

    newscalemtx = [scale_x, 0, 0, 0,
                   0, scale_y, 0, 0,
                   0, 0, scale_z, 0,
                   0, 0, 0, 1]

    bwmtx = BWMatrix(*newscalemtx)
    bwmtx.static_rotate_x(bwmtx.mtx, -math.radians(theta_X))
    bwmtx.static_rotate_y(bwmtx.mtx, math.radians(theta_Y))
    bwmtx.static_rotate_z(bwmtx.mtx, math.radians(theta_Z))
    bwmtx.mtx[12] = translation_x
    bwmtx.mtx[13] = translation_y
    bwmtx.mtx[14] = translation_z

    return bwmtx

if __name__ == "__main__":
    mtx = BWMatrix(*[0.806464,0.000000,0.591284,0.000000, 0.000000,1.000000,0.000000,0.000000, -0.591284,0.000000,0.806464,0.000000, 287.851013,0.000000,120.974998,1.000000])
    mtx2 = BWMatrix(*[0.029796,0.352339,0.935398,0.000000, 0.222080,0.910090,-0.349881,0.000000, -0.974573,0.218158,-0.051131,0.000000, 287.851013,0.000000,120.974998,1.000000])
    #mtx2 = BWMatrix(1.387810,-0.417808,1.378194,0.000000, 0.000000,1.913982,0.580236,0.000000, -1.440133,-0.402628,1.328122,0.000000, 287.851013,0.000000,120.974998,1.000000)
    """
    mymtx = mtx2.mtx.reshape((4, 4), order="F")
    original = mtx2.mtx.reshape((4, 4), order="F")
    print(mymtx)
    scale_x = calc_length(mymtx[0][0], mymtx[1][0], mymtx[2][0])
    scale_y = calc_length(mymtx[0][1], mymtx[1][1], mymtx[2][1])
    scale_z = calc_length(mymtx[0][2], mymtx[1][2], mymtx[2][2])

    for i in range(3):
        mymtx[i][0] = mymtx[i][0]/scale_x

    for i in range(3):
        mymtx[i][1] = mymtx[i][1]/scale_y

    for i in range(3):
        mymtx[i][2] = mymtx[i][2]/scale_z

    #print(mymtx)
    translation_x = mymtx[0][3]; mymtx[0][3]=0
    translation_y = mymtx[1][3]; mymtx[1][3]=0
    translation_z = mymtx[2][3]; mymtx[2][3]=0
    #print(mymtx)

    if mymtx[0][2] < 1:
        if mymtx[0][2] > -1:
            print("A")
            theta_Y = math.asin(mymtx[0][2])
            theta_X = math.atan2(-mymtx[1][2], mymtx[2][2])
            theta_Z = math.atan2(-mymtx[0][1], mymtx[0][0])
        else:
            print("B")
            theta_Y = -math.pi/2
            theta_X = -math.atan2(mymtx[1][0], mymtx[1][1])
            theta_Z = 0
    else:
        print("C")
        theta_Y = +math.pi / 2
        theta_X = math.atan2(mymtx[1][0], mymtx[1][1])
        theta_Z = 0

    print(scale_x, scale_y, scale_z)
    print(math.degrees(theta_X), math.degrees(theta_Y), math.degrees(theta_Z))

    newscalemtx = [scale_x, 0, 0, 0,
                    0, scale_y, 0, 0,
                    0, 0, scale_z, 0,
                    0, 0, 0, 1]

    bwmtx = BWMatrix(*newscalemtx)
    bwmtx.static_rotate_x(bwmtx.mtx, -theta_X)
    bwmtx.static_rotate_y(bwmtx.mtx, theta_Y)
    bwmtx.static_rotate_z(bwmtx.mtx, theta_Z)
    print("===")
    #print(original)
    print(bwmtx.mtx.reshape((4, 4), order="F"))"""
    print(mtx2.mtx)
    decomp = decompose(mtx2)
    print(decomp)
    newmtx = recompose(*decomp)
    print(newmtx.mtx)
