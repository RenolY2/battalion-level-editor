from vectors import Matrix4x4, Vector4, Vector3

TYPES = []

class BWMatrix(object):
    def __init__(self, *values):
        self.rotation = Matrix4x4(*values)
        self.rotation.transpose()
        self.position = Vector3(self.rotation.d1, self.rotation.d2, self.rotation.d3)
        self.rotation.d1 = self.rotation.d2 = self.rotation.d3 = 0


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
        

def vector4_from(vec_text):
    vals = vec_text.split(",")
    mtx = Vector4(*(float(x) for x in vals))
    return mtx
        


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


def convert_from(type,values):
    if type not in TYPES:
        TYPES.append(type)
    if type in CONVERTERS_FROM:
        conv = CONVERTERS_FROM[type]
    else:
        conv = default_from 
    
    return (conv(val) for val in values)
        
def get_types():
    return TYPES