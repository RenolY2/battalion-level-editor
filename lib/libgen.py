from collections import OrderedDict
from copy import deepcopy

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))
from lib.vectors import Vector3


class GenSyntaxError(Exception):
    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __str__(self):
        if self.data["value"] is not None:
            return "{0} on line {1}: {2}".format(self.message, self.data["line"],  self.data["value"])
        else:
            return "{0} on line {1}".format(self.message, self.data["line"])


def syntax_assert(check, msg, line, token=None):
    if not check:
        raise GenSyntaxError(msg, data={"line": line, "value": token})


class GeneratorWriter(object):
    def __init__(self, file):
        self.f = file
        self.current_line = 0

        self.indent = 0



    def write_token(self, token, comment = None):
        self.f.write(self.indent*"\t")
        self.f.write(token)

        if comment is not None:
            if not comment.startswith("//") and not comment.startswith("#"):
                raise RuntimeError("Comment started with invalid character: {0}".format(comment))
            self.f.write(" ")
            self.f.write(comment)

        self.f.write("\n")
        self.current_line += 1

    def write_comment(self, comment):
        if not comment.startswith("//") and not comment.startswith("#"):
            raise RuntimeError("Comment started with invalid character: {0}".format(comment))
        self.f.write(self.indent*"\t")
        self.f.write(" ")
        self.f.write(comment)

        self.f.write("\n")

    def open_bracket(self):
        self.write_token("{")
        self.indent += 1

    def close_bracket(self):
        self.indent -= 1
        self.write_token("}")

    def write_vector3f(self, x, y, z):
        res = "{0:.8f} {1:.8f} {2:.8f}".format(x, y, z)
        if "e" in res or "inf" in res:
            raise RuntimeError("invalid float: {0}".format(res))
        self.write_token(res)

    def write_string(self, string):
        self.write_token("\""+string+"\"")

    def write_float(self, val):
        res = "{0:.8f}".format(val)
        if "e" in res or "inf" in res:
            raise RuntimeError("invalid float: {0}".format(res))
        self.write_token(res)

    def write_integer(self, val):
        assert isinstance(val, int)
        self.write_token(str(val))

    def write_string_tripple(self, string1, string2, string3):
        res = "{0} {1} {2}".format(string1, string2, string3)
        self.write_token(res)

    def write_float_int(self, f, i):
        res = "{0} {1}".format(f, i)
        self.write_token(res)

    def write_int_string(self, i, s):
        assert isinstance(i, int)
        self.write_token("{0} \"{1}\"".format(i, s))


class GeneratorReader(object):
    def __init__ (self, file):
        self.f = file
        self.current_line = 0

        self._didremovecomments = False

    def read_token(self):
        self.f.tell()  # <--- EXTREMELY IMPORTANT, do not remove or bugs will appear on parsing
        line = self.f.readline()
        #print("pos", hex(curr), "Line", line)
        #print(hex(self.f.tell()))
        self.current_line += 1
        if not line:
            return ""
        line = line.strip()
        comment = line.find("#")

        if comment != -1:
            line = line[:comment]
            self._didremovecomments = True

        comment2 = line.find("//")
        if comment2 != -1:
            line = line[:comment2]
            self._didremovecomments = True

        if line.strip() == "":
            line = self.read_token()  # Try reading the next token

        return line.strip()

    def peek_token(self):
        #print("next is a peek")
        curr = self.f.tell()
        currline = self.current_line
        next_token = self.read_token()
        self.current_line = currline

        self.f.seek(curr)
        #print(curr, self.f.tell())
        assert curr == self.f.tell()
        #print("peek done, result:", next_token)
        return next_token

    def read_section_rest_raw(self):
        curr = f.tell()
        self.skip_current_section()
        end = f.tell()
        f.seek(curr)

        rest = f.read(end-curr)

        f.seek(curr)
        return rest

    def skip_next_section(self):
        token = self.read_token()
        if token == "{":
            level = 1

            while level != 0:
                token = self.read_token()

                if token == "{":
                    level += 1
                elif token == "}":
                    level -= 1
                elif token == "":
                    raise RuntimeError("Reached end of file while skipping {{ }} block. File is likely malformed")
        else:
            raise RuntimeError("Expected '{{' for start of section, instead got {0}".format(token))

    def skip_current_section(self):
        level = 0
        while level != -1:
            token = self.read_token()
            if token == "{":
                level += 1
            elif token == "}":
                level -= 1
            elif token == "":
                raise RuntimeError("Reached end of file while skipping to end of current { } block. File is likely malformed.")

    def read_vector3f(self):
        val = self.read_token()
        floats = val.split(" ")
        if len(floats) != 3:
            raise RuntimeError("Tried to read Vector3f but got {0}".format(floats))

        return float(floats[0]), float(floats[1]), float(floats[2])

    def read_integer(self):
        val = self.read_token()
        if val == "":
            raise RuntimeError("Reached end of file while reading integer!")
        return int(val)

    def read_float(self):
        val = self.read_token()
        if val == "":
            raise RuntimeError("Reached end of file while reading float!")
        return float(val)

    def read_string(self):
        val = self.read_token()
        #print(val)

        #assert val[0] == "\"" and val[-1] == "\""
        syntax_assert(val[0] == "\"" and val[-1] == "\"",
                      "Malformed String", self.current_line, val)
        return val[1:-1]

    def read_string_tripple(self):
        val = self.read_token()
        tripple = []

        start = None

        #for i in range(3):
        for i, char in enumerate(val):
            if char == "\"" and start is None:
                start = i
            elif char == "\"" and start is not None:
                tripple.append(val[start:i+1])
                start = None

        if start is not None:
            raise RuntimeError("Malformed string tripple {0}".format(val))

        return tripple

    def read_float_int(self):
        val = self.read_token()
        f, i = val.split(" ")

        return float(f), int(i)

    def read_int_string(self):
        val = self.read_token()
        i, s = val.split(" ")
        s = s.strip()

        syntax_assert(s[0] == "\"" and s[-1] == "\"",
                      "Malformed String", self.current_line, val)

        return int(i), s[1:-1]


class GeneratorParameters(object):
    pass


class GeneratorObject(object):
    def __init__(self, name, version, generatorid=["", "", ""]):
        self.name = name
        self.version = version
        self.generatorid = generatorid

        self.spline = []
        self.spline_float = None
        self.spline_params = []

        self.position = Vector3(0, 0, 0)
        self.rotation = Vector3(0, 0, 0)
        self.scale = 1.0

        self.unknown_params = OrderedDict()

    def from_other(self, obj):
        self.name = obj.name
        self.version = obj.version
        self.generatorid = obj.generatorid

        self.spline = obj.spline
        self.spline_params = obj.spline_params

        self.position = obj.position
        self.rotation = obj.rotation
        self.scale = obj.scale

        self.unknown_params = obj.unknown_params

    def copy(self):
        return deepcopy(self)

    @classmethod
    def from_generator_file(cls, reader: GeneratorReader):

        name = reader.read_string()
        #print("NOW WE ARE DOING ", name)
        version = reader.read_string()
        generatorid = reader.read_string_tripple()
        gen = cls(name, version, generatorid)
        gen.read_parameters(reader)
        gen._read_spline(reader)

        return gen

    def write(self, writer: GeneratorWriter):
        writer.write_string(self.name)
        writer.write_string(self.version)
        writer.write_string_tripple(*self.generatorid)
        self.write_parameters(writer)
        if len(self.spline) == 0:
            writer.write_string("no-spline")
        else:
            writer.write_string("spline")
            writer.write_integer(len(self.spline))
            for x, y, z in self.spline:
                writer.write_vector3f(x, y, z)

            writer.write_float_int(self.spline_float, len(self.spline_params))

            for id, name, params in self.spline_params:
                writer.write_int_string(id, name)
                writer.open_bracket()
                for paramname, paramval in params.items():
                    writer.open_bracket()
                    writer.write_string(paramname)
                    writer.write_token(paramval)
                    writer.close_bracket()
                writer.close_bracket()


    def write_parameters(self, writer:GeneratorWriter):
        writer.open_bracket()

        writer.open_bracket()
        writer.write_string("mPos")
        writer.write_vector3f(self.position.x, self.position.y, self.position.z)
        writer.close_bracket()


        writer.open_bracket()
        writer.write_string("mBaseScale")
        writer.write_float(self.scale)
        writer.close_bracket()


        writer.open_bracket()
        writer.write_string("mPosture")
        writer.write_vector3f(self.rotation.x, self.rotation.y, self.rotation.z)
        writer.close_bracket()

        for param, values in self.unknown_params.items():
            writer.open_bracket()
            writer.write_string(param)

            if param == "mEmitRadius":
                writer.write_float(values)
            else:
                level = 0
                for val in values:
                    if val == "{":
                        writer.open_bracket()
                        level += 1
                    elif val == "}":
                        writer.close_bracket()
                        level -= 1
                    else:
                        writer.write_token(val)
                syntax_assert(level==0, "Bracket mismatch", writer.current_line)
            writer.close_bracket()

        writer.close_bracket()

    def read_parameters(self, reader: GeneratorReader):
        if reader.read_token() != "{":
            raise RuntimeError("")

        next = reader.read_token()
        if next == "":
            raise RuntimeError("Tried to read parameters but encountered EOF")

        assert next in ("{", "}")

        while next != "}":
            param_name = reader.read_string()
            if param_name == "mPos":
                self.position = Vector3(*reader.read_vector3f())
                reader.read_token()
            elif param_name == "mPosture":
                self.rotation = Vector3(*reader.read_vector3f())
                reader.read_token()
            elif param_name == "mBaseScale":
                self.scale = reader.read_float()
                reader.read_token()
            elif param_name == "mEmitRadius":
                self.unknown_params[param_name] = reader.read_float()
                reader.read_token()
            else:
                unkdata = []
                level = 0
                while level != -1:
                    subnext = reader.read_token()
                    if subnext == "":
                        raise RuntimeError("Encountered EOF while reading parameter")
                    elif subnext == "{":
                        level += 1
                    elif subnext == "}":
                        level -= 1

                    if level != -1:
                        unkdata.append(subnext)

                self.unknown_params[param_name] = unkdata

            next = reader.read_token()
            syntax_assert(next != "",
                          "Reached end of file while parsing parameters",
                          reader.current_line)
            syntax_assert(next in ("{", "}"),
                          "Malformed file, expected {{ or }} but got {0}".format(next),
                          reader.current_line)
            #assert next in ("{", "}", "")

    def _read_spline(self, reader: GeneratorReader):
        splinetext = reader.read_string()

        if splinetext == "no_spline":
            pass
        elif splinetext == "spline":
            spline_count = reader.read_integer()
            for i in range(spline_count):
                self.spline.append(reader.read_vector3f())

            self.spline_float, paramcount = reader.read_float_int()
            self.spline_params = []

            for i in range(paramcount):
                id, splinename = reader.read_int_string()

                assert reader.read_token() == "{"
                next = reader.read_token()
                assert next != ""
                params = OrderedDict()

                while next != "}":
                    assert next == "{"
                    paramname = reader.read_string()
                    paramval = reader.read_token()
                    assert reader.read_token() == "}"

                    next = reader.read_token()

                    params[paramname] = paramval

                self.spline_params.append((id, splinename, params))


class GeneratorFile(object):
    def __init__(self):
        self.generators = []

    @classmethod
    def from_file(cls, f):
        """data = f.read()
        if "#" not in data:
            #print(data)
            #assert "#" in f.read()
            dontsave = True
        else:
            dontsave = False
        f.seek(0)"""
        genfile = cls()
        reader = GeneratorReader(f)
        written = {}

        try:
            start = reader.read_token()
            if start != "{":
                raise RuntimeError("Expected file to start with '{'")

            next = reader.peek_token()
            if next == "":
                raise RuntimeError("Malformed file, expected generator object or '}'")

            while next != "}":
                start = reader.f.tell()

                generator = GeneratorObject.from_generator_file(reader)
                end = reader.f.tell()
                #print(generator.name)
                genfile.generators.append(generator)
                next = reader.peek_token()
                #assert reader.peek_token() == next
                #assert reader.peek_token() == next
                #print(reader.peek_token())
                #print(reader.peek_token())

                #if generator.name not in written and not dontsave:
                #    written[generator.name] = (start, end)

                if next == "":
                    raise RuntimeError("Malformed file, expected generator object or '}'")

            """curr = f.tell()
            for obj, pos in written.items():
                start, end = pos
                reader.f.seek(start)
                assert reader.f.tell() == start
                adata = reader.f.read(end - start)
                reader.f.seek(end)
                assert reader.f.tell() == end

                with open("examples/"+obj+".txt", "w", encoding="utf-8") as g:
                    g.write(adata)

                # reader.f.seek(end)
            f.seek(curr)"""
            return genfile

        except Exception as e:
            print("Last line:", reader.current_line)
            raise

    def write(self, writer: GeneratorWriter):
        writer.open_bracket()
        for genobj in self.generators:
            genobj.write(writer)
        writer.close_bracket()


if __name__ == "__main__":
    with open("p29.txt", "r", encoding="shift-jis", errors="replace") as f:
        genfile = GeneratorFile.from_file(f)
