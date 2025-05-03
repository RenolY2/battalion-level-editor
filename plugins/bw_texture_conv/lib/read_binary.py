from struct import unpack, Struct, pack

uint32_struct = Struct(">I")
uint32_unpack = uint32_struct.unpack
uint32_pack = uint32_struct.pack

int16_tripple = Struct(">hhh")
int16_tripple_unpack = int16_tripple.unpack

int8_tripple = Struct("bbb")
int8_tripple_unpack = int8_tripple.unpack

float_struct = Struct(">f")
float_unpack = float_struct.unpack

float_tripple = Struct(">fff")
float_tripple_unpack = float_tripple.unpack



def read_id(f):
    c1 = f.read(1)
    c2 = f.read(1)
    c3 = f.read(1)
    c4 = f.read(1)
    return c4+c3+c2+c1


def write_id(f, val):
    f.write(val[::-1])


def read_uint32(f):
    #return unpack(">I", f.read(4))[0]
    return uint32_unpack(f.read(4))[0]


def read_int32(f):
    return unpack(">i", f.read(4))[0]


def read_uint32_le(f):
    return unpack("I", f.read(4))[0]


def read_int32_le(f):
    return unpack("i", f.read(4))[0]


def read_uint16(f):
    return unpack(">H", f.read(2))[0]


def read_int16(f):
    return unpack(">h", f.read(2))[0]


def read_int16_tripple(f):
    return int16_tripple_unpack(f.read(6))


def read_uint16_le(f):
    return unpack("H", f.read(2))[0]


def read_int16_le(f):
    return unpack("h", f.read(2))[0]


def read_float(f):
    #return unpack(">f", f.read(4))[0]
    return float_unpack(f.read(4))[0]


def read_float_tripple(f):
    return float_tripple_unpack(f.read(12))


def read_uint8(f):
    return unpack("B", f.read(1))[0]


def read_int8(f):
    return unpack("b", f.read(1))[0]


def read_int8_tripple(f):
    return int8_tripple_unpack(f.read(3))


def read_float_le(f):
    return unpack("f", f.read(4))[0]
    
    
def write_uint32(f, val):
    f.write(uint32_pack(val))


def write_uint32(f, val):
    f.write(pack("i", val))


def write_uint32_le(f, val):
    f.write(pack("I", val))


def write_int32_le(f, val):
    f.write(pack("i", val))