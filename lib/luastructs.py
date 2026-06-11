import struct


class StructResult(object):
    def __init__(self, values, fieldnames):
        self._fieldnames = fieldnames
        for attr, v in zip(fieldnames, values):
            setattr(self, attr, v)

    def print(self):
        for n in self._fieldnames:
            print(n, getattr(self, n))


def prepend(luastruct, n):
    for i in range(len(luastruct.fieldnames)):
        luastruct.fieldnames[i] = n+"_"+luastruct.fieldnames[i]

    return luastruct


class LuaStructClass(object):
    def __init__(self, structstring, fieldnames):
        self.struct = structstring
        self.fieldnames = [name for name in fieldnames]

        self.size = struct.calcsize(self.struct)

    def __add__(self, other):
        return LuaStructClass(self.struct+other.struct, self.fieldnames+other.fieldnames)

    def append(self, other):
        self.struct += other.struct
        self.fieldnames = self.fieldnames+other.fieldnames

        self.size = struct.calcsize(self.struct)

    def unpack(self, data):
        values = struct.unpack(">"+self.struct, data)

        return StructResult(values, self.fieldnames)

    def print_struct(self):
        print(self.struct)
        for v in self.fieldnames:
            print(v)



class CommonHeaderClass(LuaStructClass):
    def __init__(self):
        super().__init__("IBB", ["next_gc", "type", "marked"])


class TObjectClass(LuaStructClass):
    def __init__(self):
        super().__init__("II8s", ["type", "padding", "value"])

    def type_unpack(self, data):
        data = self.unpack(data)
        if data.type == 3:
            data.value = struct.unpack(">d", data.value)[0]
        else:
            data.value, _ = struct.unpack(">II", data.value)

        return data

    @staticmethod
    def static_unpack(vtype, value):
        if type == 3:
            value = struct.unpack(">d", value)[0]
        else:
            value, _ = struct.unpack(">II", value)

        return value


class TStringClass(LuaStructClass):
    def __init__(self):
        super().__init__("", [])
        self.append(CommonHeaderClass())
        self.append(LuaStructClass("BBII", ["reserved", "padding", "hash", "length"]))
        assert self.size == 16


class TableClass(LuaStructClass):
    def __init__(self):
        super().__init__("", [])
        self.append(CommonHeaderClass())
        self.append(LuaStructClass("BB", ["flags", "lsizenode"]))
        self.append(LuaStructClass("IIIIII",
                                   ["metatable",
                                              "array",
                                              "node",
                                              "firstfree",
                                              "gclist",
                                              "sizearray"]))


class NodeClass(LuaStructClass):
    def __init__(self):
        super().__init__("", [])
        self.append(prepend(TObjectClass(), "key"))
        self.append(prepend(TObjectClass(), "value"))
        self.append(LuaStructClass("II", ["next", "padding"]))


CommonHeader = CommonHeaderClass()
TObject = TObjectClass()
TString = TStringClass()
Table = TableClass()
Node = NodeClass()

Table.print_struct()
TString.print_struct()

Node.print_struct()