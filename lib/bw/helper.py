from struct import unpack, pack


def read_uint32(fileobj):
    return unpack("I", fileobj.read(4))[0]

# read int as a big endian number
def read_uint32_BE(fileobj):
    return unpack(">I", fileobj.read(4))[0]

def read_uint16_BE(fileobj):
    return unpack(">H", fileobj.read(2))[0]

def unpack_uint32(data, offset):
    return unpack("I", data[offset:offset+4])[0]

def write_uint32(fileobj, val):
    fileobj.write(pack("I", val))