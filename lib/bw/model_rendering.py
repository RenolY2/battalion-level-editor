import os

from OpenGL.GL import *
from binascii import hexlify
from struct import unpack
from .vectors import Vector3, Matrix4x4
from .read_binary import *
from .gx import VertexDescriptor, VTX, VTXFMT
from math import floor, ceil
from lib.model_rendering import TexturedBWModel, TexturedBWMesh
from timeit import default_timer as timer


class Material(object):
    def __init__(self):
        self.tex1 = None
        self.tex2 = None
        self.tex3 = None
        self.tex4 = None
        self.data = None

    def from_file(self, f):
        self.tex1 = f.read(0x20).lower()  #.strip(b"\x00")
        self.tex2 = f.read(0x20).lower()  #.strip(b"\x00")
        self.tex3 = f.read(0x20).lower()  #.strip(b"\x00")
        self.tex4 = f.read(0x20).lower()  #.strip(b"\x00")
        self.data = f.read(0x24)  # rest

        if self.tex1.count(b"\x00") == 32:
            self.tex1 = None
        if self.tex2.count(b"\x00") == 32:
            self.tex2 = None
        if self.tex3.count(b"\x00") == 32:
            self.tex3 = None
        if self.tex4.count(b"\x00") == 32:
            self.tex4 = None

    def textures(self):
        if self.tex1 is not None:
            yield self.tex1
        if self.tex2 is not None:
            yield self.tex2
        if self.tex3 is not None:
            yield self.tex3
        if self.tex4 is not None:
            yield self.tex4

        return

    def first_texture(self):
        for tex in self.textures():
            return tex
        return None

    def __str__(self):
        return str([x.strip(b"\x00") for x in self.textures()])


class MaterialBW1(Material):
    def from_file(self, f):
        self.tex1 = f.read(0x10).lower()  #.strip(b"\x00")
        self.tex2 = f.read(0x10).lower()  #.strip(b"\x00")
        #self.tex3 = f.read(0x20).lower()  #.strip(b"\x00")
        #self.tex4 = f.read(0x20).lower()  #.strip(b"\x00")
        self.data = f.read(0x28)  # rest

        if self.tex1.count(b"\x00") == 16:
            self.tex1 = None
        if self.tex2.count(b"\x00") == 16:
            self.tex2 = None


class Model(object):
    def __init__(self):
        pass

    def render(self, *args, **kwargs):
        pass


class BW2Model(Model):
    def __init__(self):
        self.version = None
        self.nodecount = None
        self.additionalcount = None
        self.additionaldata = []
        self.unkint = None
        self.floattuple = None

        self.bgfname = b"Model.bgf"

        self.nodes = []

    def destroy(self):
        for node in self.nodes:
            node.destroy_displaylists()

    def from_file(self, f):
        self.version = (read_uint32(f), read_uint32(f))
        self.nodecount = read_uint16(f)
        self.additionaldatacount = read_uint16(f)
        self.unkint = read_uint32(f)
        self.floattuple = (read_float(f), read_float(f), read_float(f), read_float(f))


        bgfnamelength = read_uint32(f)
        self.bgfname = f.read(bgfnamelength)

        self.additionaldata = []
        for i in range(self.additionaldatacount):
            self.additionaldata.append(read_uint32(f))

        self._skip_section(f, b"MEMX")  # Unused

        self.nodes = []
        for i in range(self.nodecount):
            node = NodeBW2(self.additionaldatacount)
            node.from_file(f)
            self.nodes.append(node)

        cntname = f.read(4)
        #print(cntname)
        assert cntname == b"TCNC"
        cnctsize = read_uint32_le(f)
        start = f.tell()
        assert cnctsize == self.unkint*4

        for i in range(self.unkint):
            parent = read_uint16_le(f)
            child = read_uint16_le(f)
            #print("Concat:", child, parent)
            self.nodes[child].parent = self.nodes[parent]

        assert f.tell() == start+cnctsize
        self.render_order = []
        for node in self.nodes:
            #start = timer()
            node.create_displaylists()
            #print("node", node.name, "took", timer() - start, "s")
            self.render_order.append(node )

    def _skip_section(self, f, secname):
        name = f.read(4)
        #print(name)
        assert name == secname
        size = read_uint32_le(f)
        f.read(size)

    def sort_render_order(self, camerax, cameray, cameraz):
        origin = Vector3(camerax, cameray, cameraz)

        def distance(node):
            dist_vec = origin - node.world_center
            distance = dist_vec.norm()
            return distance

        self.render_order.sort(key = lambda x: distance(x), reverse=True)

    def render(self, texturearchive, shader, j=0):
        #for node in self.nodes:
        i = 0
        for node in self.render_order:
            #box.render()
            if node.do_skip():
                continue
            i += 1

            if (j > 0 and j != i):
                continue

            """if j > 0:
                print("current node:", node.name)
                print("transform:", node.transform.floats)
            """
            node.render(texturearchive, shader)
            #print("Rendering first:", node.name, node.world_center.x, node.world_center.y, node.world_center.z)
            #break
            #node.transform.reset_transform()

    def make_textured_model(self, texturearchive):
        model = TexturedBWModel()
        alltextures = {}
        for node in self.nodes:
            for material in node.materials:
                for texturename in material.textures():
                    if texturename not in alltextures:
                        alltextures[texturename] = TexturedBWMesh(texturename.strip(b"\x00").decode("ascii"))

        for node in self.nodes:
            if node.do_skip():
                continue
            mvmat = Matrix4x4.identity()
            mvmat.a1 = 1.0
            # normals_mvmat = Matrix4x4.identity()

            currnode = node
            mvmat.inplace_multiply_mat4(node.transform.matrix4)
            while currnode.parent is not None:
                currnode = currnode.parent
                mvmat.inplace_multiply_mat4(currnode.transform.matrix4)
                # normals_mvmat.inplace_multiply_mat4(currnode.transform.matrix4)

            # print(mvmat)
            vertices = []
            for x, y, z in node.vertices:
                newx, newy, newz, _ = mvmat.multiply_vec4(x * node.vscl, y * node.vscl, z * node.vscl, 1)
                vertices.append((newx, newy, newz))
                #obj.write("v {0} {1} {2}\n".format(-newx, newy, newz))

            # for x, y, z in node.normals:
            #    newx, newy, newz, _ = mvmat.multiply_vec4(x, y, z, 0)
            #    obj.write("vn {0} {1} {2}\n".format(newx, newy, newz))
            uvs = []
            for u, v in node.uvmaps[0]:
                uvs.append((u,v))


            for matindex, mesh in node.meshes:

                texname = node.materials[matindex].tex1

                assert texname is not None
                currmesh = alltextures[texname]

                for prim in mesh:
                    if prim.type == 0x98:
                        pass
                    # elif prim.type == 0x90:
                    #    glBegin(GL_TRIANGLES)
                    else:
                        raise RuntimeError("woops unsupported prim type {0:x}".format(prim.type))
                    i = 0
                    vert1, vert2, vert3 = None, None, None

                    for vertex in prim.vertices:
                        if vert1 is None:
                            vert1 = vertex
                            continue
                        elif vert2 is None:
                            vert2 = vertex
                            continue
                        elif vert3 is None:
                            vert3 = vertex
                        else:
                            vert1 = vert2
                            vert2 = vert3
                            vert3 = vertex
                            i = (i + 1) % 2

                        if i == 0:
                            v1 = vert1
                            v2 = vert2
                            v3 = vert3
                        else:
                            v1 = vert2
                            v2 = vert1
                            v3 = vert3

                        for v in (v3, v2, v1):
                            posindex, normindex = v[0], v[1]
                            tex0 = v[2]
                            tex1 = v[3]
                            hasNormals = False
                            hasTexcoords = False

                            if not tex1 is None:
                                hasTexcoords = True
                                # print(tex1, self.uvmaps[0])
                                if not tex0 is None:
                                    texcoordindex = tex0 << 8 | tex1
                                else:
                                    texcoordindex = tex1

                                currmesh.trilist.append((vertices[posindex], uvs[texcoordindex]))

        model.mesh_list.extend(alltextures.values())
        return model

    def export_obj(self, outputpath, texturearchive):
        modelname = str(self.bgfname.strip(b"\00"), encoding="ascii")
        objpath = os.path.join(outputpath, modelname+".obj")
        matpath = os.path.join(outputpath, modelname+".mtl")

        exported_textures = []
        for node in self.nodes:
            for material in node.materials:
                for texturename in material.textures():
                    if texturename not in exported_textures:
                        exported_textures.append(texturename)

        for texturename in exported_textures:
            texname = str(texturename.strip(b"\x00"), encoding="ascii") + ".png"
            result = texturearchive.get_texture(texturename.lower())
            if result is not None:
                tex, texid = result
                tex.dump_to_file(os.path.join(outputpath, texname))

        normal_offset = 1
        texcoord_offset = 1
        vertex_offset = 1

        obj = open(objpath, "w", encoding="utf-8")
        mtl = open(matpath, "w", encoding="utf-8")
        obj.write("mtllib {0}\n".format(modelname+".mtl"))
        try:
            for node in self.nodes:
                if node.do_skip():
                    continue
                #mvmat = Matrix4x4(*node._mvmat[0], *node._mvmat[1], *node._mvmat[2], *node._mvmat[3])
                #mvmat.transpose()
                mvmat = Matrix4x4.identity()
                mvmat.a1 = 1.0
                #normals_mvmat = Matrix4x4.identity()

                currnode = node
                mvmat.inplace_multiply_mat4(node.transform.matrix4)
                while currnode.parent is not None:
                    currnode = currnode.parent
                    mvmat.inplace_multiply_mat4(currnode.transform.matrix4)
                    #normals_mvmat.inplace_multiply_mat4(currnode.transform.matrix4)

                #print(mvmat)

                for x, y, z in node.vertices:
                    newx, newy, newz, _ = mvmat.multiply_vec4(x*node.vscl, y*node.vscl, z*node.vscl, 1)
                    obj.write("v {0} {1} {2}\n".format(-newx, newy, newz))

                #for x, y, z in node.normals:
                #    newx, newy, newz, _ = mvmat.multiply_vec4(x, y, z, 0)
                #    obj.write("vn {0} {1} {2}\n".format(newx, newy, newz))

                for u, v in node.uvmaps[0]:
                    obj.write("vt {0} {1}\n".format(u, 1-v))

                for i, mat in enumerate(node.materials):
                    print(node.name)
                    matname = str(node.name.strip(b"\00"), encoding="latin-1")+"_mat{0}".format(i)

                    mtl.write("newmtl {0}\n".format(matname))
                    texturename = mat.tex1
                    if texturename is None:
                        texturename = matname+"_notex1"
                        mtl.write("map_kd {0}\n".format(texturename + ".png"))
                    else:
                        mtl.write("map_kd {0}\n".format(str(texturename.strip(b"\x00"), encoding="ascii") + ".png"))

            for node in self.nodes:
                if node.do_skip():
                    continue
                materials = []
                obj.write("o {0}\n".format(str(node.name.strip(b"\00"), encoding="latin-1")))
                for i, mat in enumerate(node.materials):
                    matname = str(node.name.strip(b"\00"), encoding="latin-1")+"_mat{0}".format(i)
                    materials.append((matname, mat))

                for matindex, mesh in node.meshes:
                    matname, mat = materials[matindex]
                    obj.write("usemtl {0}\n".format(matname))

                    for prim in mesh:
                        if prim.type == 0x98:
                            pass
                        #elif prim.type == 0x90:
                        #    glBegin(GL_TRIANGLES)
                        else:
                            raise RuntimeError("woops unsupported prim type {0:x}".format(prim.type))
                        i = 0
                        vert1, vert2, vert3 = None, None, None

                        for vertex in prim.vertices:
                            if vert1 is None:
                                vert1 = vertex
                                continue
                            elif vert2 is None:
                                vert2 = vertex
                                continue
                            elif vert3 is None:
                                vert3 = vertex
                            else:
                                vert1 = vert2
                                vert2 = vert3
                                vert3 = vertex
                                i = (i + 1) % 2

                            if i == 0:
                                v1 = vert1
                                v2 = vert2
                                v3 = vert3
                            else:
                                v1 = vert2
                                v2 = vert1
                                v3 = vert3


                            obj.write("f ")

                            for v in (v3, v2, v1):
                                posindex, normindex = v[0], v[1]
                                tex0 = v[2]
                                tex1 = v[3]
                                posindex += vertex_offset
                                hasNormals = False
                                hasTexcoords = False
                                obj.write("{0}".format(posindex))

                                if not tex1 is None:
                                    hasTexcoords = True
                                    # print(tex1, self.uvmaps[0])
                                    if not tex0 is None:
                                        texcoordindex = tex0 << 8 | tex1
                                    else:
                                        texcoordindex = tex1
                                    texcoordindex += texcoord_offset
                                    #u, v = uvmap_0[texcoordindex]

                                    #glVertexAttrib2f(2, u, v)
                                    #glVertexAttrib2f(4, u, v)
                                    obj.write("/{0}".format(texcoordindex))

                                #if normindex is not None:
                                #    if not hasTexcoords:
                                #        obj.write("/")
                                #    normindex += normal_offset
                                #    obj.write("/{0}".format(normindex))

                                obj.write(" ")
                            obj.write("\n")

                vertex_offset += len(node.vertices)
                normal_offset += len(node.normals)
                texcoord_offset += len(node.uvmaps[0])

        except Exception as e:
            obj.close()
            mtl.close()
            raise e

        obj.close()
        mtl.close()


class BW1Model(BW2Model):
    def from_file(self, f):
        #self.version = (read_uint32(f), read_uint32(f))
        self.nodecount = read_uint16_le(f)
        self.additionaldatacount = read_uint8(f)
        f.read(1) #padding
        self.unkint = read_uint32(f)
        self.floattuple = (read_float(f), read_float(f), read_float(f), read_float(f))


        #bgfnamelength = read_uint32(f)
        #self.bgfname = f.read(bgfnamelength)

        self.additionaldata = []
        for i in range(self.additionaldatacount):
            self.additionaldata.append(read_uint32(f))

        self._skip_section(f, b"MEMX")  # Unused

        self.nodes = []
        #print("nodecount is ", self.nodecount)
        for i in range(self.nodecount):
            node = NodeBW1(self.additionaldatacount)
            node.from_file(f, i)
            self.nodes.append(node)

        cntname = f.read(4)
        #print(cntname)
        assert cntname == b"TCNC"
        cnctsize = read_uint32_le(f)
        start = f.tell()
        #print(cnctsize, self.unkint)
        #assert cnctsize == self.unkint*4

        for i in range(cnctsize//4):
            parent = read_uint16_le(f)
            child = read_uint16_le(f)
            #print("Concat:", child, parent)
            self.nodes[child].parent = self.nodes[parent]

        assert f.tell() == start+cnctsize
        self.render_order = []
        for node in self.nodes:
            start = timer()
            node.create_displaylists()
            #print("node", node.name, "took", timer() - start, "s")
            self.render_order.append(node )
            #print(node._displaylists, node.meshes)


class LODLevel(object):
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.sections = []


class Primitive(object):
    def __init__(self, primtype):
        self.type = primtype
        self.vertices = []


class NodeBW2(object):
    def __init__(self, additionaldatacount):
        self.children = []
        self.parent = None
        self.transform = None

        self.additionaldatacount = additionaldatacount

        self.bbox = None # Boundary box
        self.rnod = None # Only used by soldier models?
        self.materials = []

        self.sections = []

        self.name = b"NodeName"

        self.unkshort1 = None
        self.unkshort2 = None
        self.unkshort3 = None
        self.padd = None
        self.xbs2count = None
        self.vscl = None

        self.vertices = []
        self.normals = []
        self.binormals = []
        self.tangents = []
        self.triprimitives = []
        self.meshes = []
        self.uvmaps = [[],[],[],[]]

        self.additionaldata = []
        self.lods = []

        self._displaylists = []

        self.world_center = Vector3(0, 0, 0)

        self._mvmat = None

    def do_skip(self):
        return b"NODRAW" in self.name or b"COLLIDE" in self.name or b"COLLISION" in self.name or self.xbs2count == 0

    def setparent(self, parent):
        self.parent = parent

    def from_file(self, f):
        nodename = f.read(4)
        assert nodename == b"EDON"
        nodesize = read_uint32_le(f)
        nodestart = f.tell()
        nodeend = f.tell() + nodesize

        nodenamelength = read_uint32(f)
        self.name = f.read(nodenamelength)
        headerstart = f.tell()
        # Do stuff
        self.unkshort1, self.unkshort2, self.unkshort3, self.padd, self.xbs2count = unpack("HHHHI", f.read(12))
        assert self.padd == 0
        # unkshort1, unkshort2, unkshort3, padd = unpack(">HHHH", f.read(8))
        floats = unpack("f" * 11, f.read(4 * 11))
        self.transform = Transform(floats)

        assert f.tell() - headerstart == 0x38

        self.additionaldata = []
        for i in range(self.additionaldatacount):
            self.additionaldata.append(read_uint32(f))
        start = f.tell()
        
        assert read_id(f) == b"BBOX"
        assert read_uint32_le(f) == 4*6
        ppos = f.tell()
        x1, y1, z1, x2, y2, z2 = unpack("ffffff", f.read(4*6))

        self.bbox = Box((x1, y1, z1), (x2, y2, z2))

        self.world_center.x = (x1 + x2) / 2.0
        self.world_center.y = (y1 + y2) / 2.0
        self.world_center.z = (z1 + z2) / 2.0

        secname = read_id(f)
        
        size = read_uint32_le(f)
        
        while secname != b"MATL":
            if secname == b"RNOD":
                self.rnod = f.read(size)

            elif secname == b"VSCL":
                assert size == 4
                self.vscl = read_float_le(f)

            else:
                raise RuntimeError("Unknown secname {0}", secname)

            secname = read_id(f)
            size = read_uint32_le(f)

        assert secname == b"MATL"
        assert size % 0xA4 == 0
        assert self.xbs2count*0xA4 == size

        self.materials = []
        for i in range(self.xbs2count):
            material = Material()
            material.from_file(f)
            self.materials.append(material)

        vertexdesc = 0

        self.uvmaps = [[], [], [], []]

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            end = f.tell()+size

            if secname == b"SCNT":
                val = read_uint32(f)
                assert size == 4
                self.lods.append(val)

            elif secname in (b"VUV1", b"VUV2", b"VUV3", b"VUV4"):
                uvindex = secname[3] - b"1"[0]

                for i in range(size // 4):
                    scale = 2.0**11
                    u_int = read_int16(f)
                    v_int = read_int16(f)
                    u, v = (u_int)/(scale), (v_int)/(scale)
                    self.uvmaps[uvindex].append((u, v))

            elif secname == b"XBS2":
                #eprint(hex(f.tell()))
                materialindex = read_uint32(f)
                unknown = (read_uint32(f), read_uint32(f))
                gx_data_size = read_uint32(f)
                gx_data_end = f.tell() + gx_data_size
                #print(hex(gx_data_end), hex(gx_data_size))

                mesh = []
                self.meshes.append((materialindex, mesh))

                while f.tell() < gx_data_end:
                    opcode = read_uint8(f)

                    if opcode == 0x8:  # Load CP Reg
                        command = read_uint8(f)
                        val = read_uint32(f)
                        if command == 0x50:
                            vertexdesc &= ~0x1FFFF
                            vertexdesc |= val
                        elif command == 0x60:
                            vertexdesc &= 0x1FFFF
                            vertexdesc |= (val << 17)
                        else:
                            raise RuntimeError("unknown CP command {0:x}".format(command))

                    elif opcode == 0x10:  # Load XF Reg
                        x = read_uint32(f)
                        y = read_uint32(f)

                    elif opcode & 0xFA == 0x98:  # Triangle strip
                        attribs = VertexDescriptor()
                        attribs.from_value(vertexdesc)

                        vertex_count = read_uint16(f)
                        prim = Primitive(0x98)
                        #print(bin(vertexdesc))
                        #print([x for x in attribs.active_attributes()])

                        for i in range(vertex_count):
                            primattrib = [None, None,
                                          None,None,None,None,None,None,None,None]

                            for attrib, fmt in attribs.active_attributes():
                                # matindex = read_uint8(f)

                                if attrib == VTX.Position:
                                    if fmt == VTXFMT.INDEX8:
                                        posIndex = read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        posIndex = read_uint16(f)
                                    else:
                                        raise RuntimeError("unknown position format")
                                    primattrib[0] = posIndex
                                elif attrib == VTX.Normal:
                                    if fmt == VTXFMT.INDEX8:
                                        normIndex = read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        normIndex = read_uint16(f)
                                    else:
                                        raise RuntimeError("unknown normal format")
                                    primattrib[1] = normIndex
                                elif attrib is not None and VTX.Tex0Coord <= attrib <= VTX.Tex7Coord:
                                    coordindex = attrib - VTX.Tex0Coord
                                    val = read_uint8(f)
                                    primattrib[2+coordindex] = val
                                elif fmt is not None:
                                    if fmt == VTXFMT.INDEX8:
                                        read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        read_uint16(f)
                                    else:
                                        RuntimeError("unknown fmt format")

                                else:
                                    read_uint8(f)

                            prim.vertices.append(primattrib)

                        #self.triprimitives.append(prim)
                        mesh.append(prim)
                    elif opcode == 0x00:
                        pass
                    else:
                        #print(self.name, hex(f.tell()-nodestart))
                        raise RuntimeError("Unknown opcode: {0:x}".format(opcode))

                f.seek(gx_data_end)

            elif secname == b"VPOS":
                if len(self.vertices) > 0:
                    f.read(size)
                    self.sections.append(secname)
                    break
                #print(self.name, size)
                assert size%6 == 0
                #assert size%4 == 0

                for i in range(size//6):
                    #self.vertices.append((read_float_le(f), read_float_le(f), read_float_le(f)))
                    self.vertices.append(read_int16_tripple(f))

            elif secname == b"VNRM":
                assert size%3 == 0
                for i in range(size//3):
                    self.normals.append(read_int8_tripple(f))

            elif secname == b"VNBT":
                assert size%3 == 0
                assert size%9 == 0
                assert size % 36 == 0
                for i in range(size//36):
                    #self.normals.append((read_int8(f), read_int8(f), read_int8(f)))
                    #f.read(6)
                    self.normals.append(read_float_tripple(f))
                    self.binormals.append(read_float_tripple(f))

                    self.tangents.append(read_float_tripple(f))

            else:
                f.read(size)
            self.sections.append(secname)

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            f.read(size)
            self.sections.append(secname)

        assert f.tell() == nodeend

    def initialize_textures(self, texarchive):
        for material in self.materials:
            if material.tex1 is not None:
                texarchive.initialize_texture(material.tex1)

    def render(self, texarchive, shader):#, program):
        #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,GL_REPEAT)
        #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        #print(len(self.materials), len(self._displaylists))
        #print(self.xbs2count, self.sections)
        #assert len(self.materials) == len(self._displaylists)
        #for material, displist in zip(self.materials, self._displaylists):
        """if self._mvmat is None:
            self.transform.backup_transform()

            currnode = self
            j = 0
            while currnode is not None:
                j += 1

                currnode.transform.apply_transform()
                currnode = currnode.parent
                if j > 200:
                    raise RuntimeError("Possibly endless loop detected!")


            self._mvmat = glGetFloatv(GL_MODELVIEW_MATRIX)
            self.transform.reset_transform()"""

        #matloc = glGetUniformLocation(shader, "modelview")
        #glUniformMatrix4fv(matloc, 1, False, self._mvmat)

        for i, displist in self._displaylists:
            material = self.materials[i]


            if material.tex1 is not None:
                glEnable(GL_TEXTURE_2D)
                texture = texarchive.get_texture(material.tex1)
                if texture is not None:
                    tex, texid = texture
                    #texname = str(tex.name.strip(b"\x00"), encoding="ascii")
                    #tex.dump_to_file(texname+".png")
                    #print("texture bound!", texid)
                    #print(glGetError())
                    glActiveTexture(GL_TEXTURE0)
                    glBindTexture(GL_TEXTURE_2D, texid)
                    #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,GL_REPEAT)
                    #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                else:
                    #print("oops case 2 disable")
                    glDisable(GL_TEXTURE_2D)
            else:
                #print("oops case 1 disable")
                glDisable(GL_TEXTURE_2D)

            glCallList(displist)

    def destroy_displaylists(self):
        for matindex, i in self._displaylists:
            glDeleteLists(i, 1)

    #def setup_world_center(self):
    def create_displaylists(self):
        if len(self._displaylists) > 0:
            for matindex, i in self._displaylists:
                glDeleteLists(i, 1)
            self._displaylists = []

        if len(self.vertices) == 0:
            return
        #for material, mesh in zip(self.materials, self.meshes):
        for i, mesh in self.meshes:

            material = self.materials[i]

            displist = glGenLists(1)
            glNewList(displist, GL_COMPILE)
            self.transform.backup_transform()
            box = self.bbox
            currnode = self
            glScalef(-1, 1, 1)
            j = 0

            while currnode is not None:
                j += 1

                currnode.transform.apply_transform()

                currnode = currnode.parent
                if j > 200:
                    raise RuntimeError("Possibly endless loop detected!")

            #glEnable(GL_TEXTURE_2D)
            #print("node", self.name, "textures:", str(material))
            #for tex in material.textures():

            glColor3f(1.0, 1.0, 1.0)
            """
            glBegin(GL_TRIANGLE_FAN)
            #glColor3f(1.0, 0.0, 1.0)
            glVertexAttrib2f(2, 0, 0)
            glVertex3f(0, 0, 0+i*10)
            glVertexAttrib2f(2, 0, 1)
            glVertex3f(0, 10, 0+i*10)
            #glColor3f(1.0, 0.0, 0.0)
            glVertexAttrib2f(2, 1, 1)
            glVertex3f(10, 10, 0+i*10)
            glVertexAttrib2f(2, 1, 0)
            glVertex3f(10, 0, 0+i*10)
            glEnd()"""

            vertices = self.vertices
            uvmap_0 = self.uvmaps[0]
            normals, binormals, tangents = self.normals, self.binormals, self.tangents
            scale = self.vscl
            for prim in mesh:
                if prim.type == 0x98:
                    glBegin(GL_TRIANGLE_STRIP)
                elif prim.type == 0x90:
                    glBegin(GL_TRIANGLES)
                else:
                    print("woop woop")
                    raise RuntimeError("Unknown Prim Type: {0:x}".format(prim.type))

                for vertex in prim.vertices:
                    if len(vertex) == 0:
                        continue
                    posindex, normindex = vertex[0], vertex[1]
                    tex0 = vertex[2]
                    tex1 = vertex[3]
                    if posindex >= len(vertices):
                        print(len(vertices), posindex)
                    x,y,z = vertices[posindex]

                    if not tex1 is None:
                        #print(tex1, self.uvmaps[0])
                        if not tex0 is None:
                            texcoordindex = tex0 << 8 | tex1
                        else:
                            texcoordindex = tex1
                        u,v = uvmap_0[texcoordindex]
                        glTexCoord2f(u, v)
                        #glVertexAttrib2f(2, u, v)
                        #glVertexAttrib2f(4, u, v)

                    if normindex is not None:
                        glVertexAttrib3f(3, *normals[normindex])
                        if len(binormals) > 0:
                            glVertexAttrib3f(5, *binormals[normindex])
                            glVertexAttrib3f(6, *tangents[normindex])
                    glVertex3f(x * scale, y * scale, z * scale)

                glEnd()
            self.transform.reset_transform()
            glEndList()
            self._displaylists.append((i, displist))


class NodeBW1(NodeBW2):
    def do_skip(self):
        return self.xbs2count == 0 or self.unkshort1 == 151 or self.unkshort1 == 150

    def from_file(self, f, i=0):
        nodename = f.read(4)
        #print(nodename)
        assert nodename == b"EDON"
        nodesize = read_uint32_le(f)
        nodestart = f.tell()
        nodeend = f.tell() + nodesize

        #nodenamelength = read_uint32(f)
        #self.name = f.read(nodenamelength)

        headerstart = f.tell()
        # Do stuff
        self.unkshort1, self.unkshort2, self.unkint1, _, _, _, self.unkint2 = unpack("HHBBBBI", f.read(12))
        self.name = bytes("Node {0}".format(i), encoding="ascii")
        #assert self.padd == 0
        # unkshort1, unkshort2, unkshort3, padd = unpack(">HHHH", f.read(8))
        floats = unpack("f" * 11, f.read(4 * 11))
        self.transform = Transform(floats)

        assert f.tell() - headerstart == 0x38

        self.additionaldata = []
        for i in range(self.additionaldatacount):
            self.additionaldata.append(read_uint32(f))
        start = f.tell()

        assert read_id(f) == b"BBOX"
        assert read_uint32_le(f) == 4 * 6
        ppos = f.tell()
        x1, y1, z1, x2, y2, z2 = unpack("ffffff", f.read(4 * 6))

        self.bbox = Box((x1, y1, z1), (x2, y2, z2))

        self.world_center.x = (x1 + x2) / 2.0
        self.world_center.y = (y1 + y2) / 2.0
        self.world_center.z = (z1 + z2) / 2.0

        secname = read_id(f)

        size = read_uint32_le(f)

        while secname != b"MATL":
            if secname == b"RNOD":
                self.rnod = f.read(size)

            elif secname == b"VSCL":
                assert size == 4
                self.vscl = read_float_le(f)

            else:
                raise RuntimeError("Unknown secname {0}", secname)

            secname = read_id(f)
            size = read_uint32_le(f)

        assert secname == b"MATL"
        #print(hex(size), self.unkint1)
        assert size % 0x48 == 0
        #assert self.unkint1 * 0x48 == size

        self.materials = []
        for i in range(size//0x48):
            material = MaterialBW1()
            material.from_file(f)
            self.materials.append(material)

        vertexdesc = 0

        self.uvmaps = [[], [], [], []]

        while f.tell() < nodeend:
            secname = read_id(f)
            size = read_uint32_le(f)
            end = f.tell() + size

            if secname == b"SCNT":
                val = read_uint32(f)
                assert size == 4
                self.lods.append(val)

            elif secname in (b"VUV1", b"VUV2", b"VUV3", b"VUV4"):
                uvindex = secname[3] - b"1"[0]

                for i in range(size // 4):
                    scale = 2.0 ** 11
                    u_int = read_int16(f)
                    v_int = read_int16(f)
                    u, v = (u_int) / (scale), (v_int) / (scale)
                    self.uvmaps[uvindex].append((u, v))

            elif secname == b"XBST":
                # eprint(hex(f.tell()))
                materialindex = read_uint32(f)
                unknown = (read_uint32(f),)
                gx_data_size = read_uint32(f)
                gx_data_end = f.tell() + gx_data_size
                # print(hex(gx_data_end), hex(gx_data_size))

                mesh = []
                self.meshes.append((materialindex, mesh))

                while f.tell() < gx_data_end:
                    opcode = read_uint8(f)

                    if opcode == 0x8:  # Load CP Reg
                        command = read_uint8(f)
                        val = read_uint32(f)
                        if command == 0x50:
                            vertexdesc &= ~0x1FFFF
                            vertexdesc |= val
                        elif command == 0x60:
                            vertexdesc &= 0x1FFFF
                            vertexdesc |= (val << 17)
                        else:
                            raise RuntimeError("unknown CP command {0:x}".format(command))
                    elif opcode == 0x10:  # Load XF Reg
                        x = read_uint32(f)
                        y = read_uint32(f)

                    elif opcode & 0xFA == 0x98:  # Triangle strip
                        attribs = VertexDescriptor()
                        attribs.from_value(vertexdesc)

                        vertex_count = read_uint16(f)
                        prim = Primitive(0x98)
                        # print(bin(vertexdesc))
                        # print([x for x in attribs.active_attributes()])

                        for i in range(vertex_count):
                            primattrib = [None, None,
                                          None, None, None, None, None, None, None, None]

                            for attrib, fmt in attribs.active_attributes():
                                # matindex = read_uint8(f)

                                if attrib == VTX.Position:
                                    if fmt == VTXFMT.INDEX8:
                                        posIndex = read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        posIndex = read_uint16(f)
                                    else:
                                        raise RuntimeError("unknown position format")
                                    primattrib[0] = posIndex
                                elif attrib == VTX.Normal:
                                    if fmt == VTXFMT.INDEX8:
                                        normIndex = read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        normIndex = read_uint16(f)
                                    else:
                                        raise RuntimeError("unknown normal format")
                                    primattrib[1] = normIndex
                                elif attrib is not None and VTX.Tex0Coord <= attrib <= VTX.Tex7Coord:
                                    coordindex = attrib - VTX.Tex0Coord
                                    val = read_uint8(f)
                                    primattrib[2 + coordindex] = val
                                elif fmt is not None:
                                    if fmt == VTXFMT.INDEX8:
                                        read_uint8(f)
                                    elif fmt == VTXFMT.INDEX16:
                                        read_uint16(f)
                                    else:
                                        RuntimeError("unknown fmt format")

                                else:
                                    read_uint8(f)

                            prim.vertices.append(primattrib)

                        # self.triprimitives.append(prim)
                        mesh.append(prim)
                    elif opcode == 0x00:
                        pass
                    else:
                        #print(self.name, hex(f.tell() - nodestart))
                        raise RuntimeError("Unknown opcode: {0:x}".format(opcode))

                f.seek(gx_data_end)

            elif secname == b"VPOS":
                if len(self.vertices) > 0:
                    f.read(size)
                    self.sections.append(secname)
                    break
                # print(self.name, size)
                assert size % 6 == 0
                # assert size%4 == 0

                for i in range(size // 6):
                    # self.vertices.append((read_float_le(f), read_float_le(f), read_float_le(f)))
                    self.vertices.append(read_int16_tripple(f))

            elif secname == b"VNRM":
                assert size % 3 == 0
                for i in range(size // 3):
                    self.normals.append(read_int8_tripple(f))

            elif secname == b"VNBT":
                assert size % 3 == 0
                assert size % 9 == 0
                assert size % 36 == 0
                for i in range(size // 36):
                    # self.normals.append((read_int8(f), read_int8(f), read_int8(f)))
                    # f.read(6)
                    self.normals.append(read_float_tripple(f))
                    self.binormals.append(read_float_tripple(f))

                    self.tangents.append(read_float_tripple(f))

            else:
                f.read(size)
            self.sections.append(secname)
        #print("skipping sections...")
        while f.tell() < nodeend:
            secname = read_id(f)
            #print(secname)
            size = read_uint32_le(f)
            f.read(size)
            self.sections.append(secname)
        #print("end of node")
        assert f.tell() == nodeend


class Transform(object):
    def __init__(self, floats):
        self.floats = floats
        x,y,z,w = floats[3:7]

        #self.matrix = [w**2+x**2-y**2-z**2,     2*x*y+2*w*z,            2*x*z-2*w*y,            0.0,
        #               2*x*y-2*w*z,             y**2+w**2-x**2-z**2,    2*y*z+2*w*x,            0.0,
        #               2*x*z+2*w*y,             2*y*z-2*w*x,            z**2+w**2-x**2-y**2,    0.0,
        #               floats[0],               floats[1],              floats[2],              1.0]
        #c, b, d, a = floats[3:7]
        #d, c, b, a = floats[3:7]
        a, b, c, d = floats[3:7]
        a, d, c, b = floats[3:7]
        a, c, b, d = floats[3:7]
        a, d, b, c = floats[3:7]
        a, b, d, c = floats[3:7]
        a, c, d, b = floats[3:7]

        b, a, c, d = floats[3:7]
        b, a, d, c = floats[3:7]
        b, d, a, c = floats[3:7]
        b, d, c, a = floats[3:7]
        b, c, a, d = floats[3:7]
        b, c, d, a = floats[3:7]

        c, b, a, d = floats[3:7]
        c, b, d, a = floats[3:7]
        c, d, a, b = floats[3:7]
        c, d, b, a = floats[3:7]
        c, a, d, b = floats[3:7]
        c, a, b, d = floats[3:7]

        d, a, b, c = floats[3:7]
        d, a, c, b = floats[3:7]
        d, b, a, c = floats[3:7]
        d, b, c, a = floats[3:7]
        d, c, a, b = floats[3:7]
        d, c, b, a = floats[3:7]

        #self.matrix = [a**2+b**2-c**2-d**2,     2*b*c+2*a*d,            2*x*z-2*w*y,            0.0,
        #               2*b*c-2*a*d,             a**2-b**2+c**2-d**2,    2*c*d-2*a*b,            0.0,
        #               2*b*d-2*a*c,             2*c*d+2*a*b,            a**2-b**2-c**2+d**2,    0.0,
        #               floats[0],               floats[1],              floats[2],              1.0]
        """self.matrix = [a**2+b**2-c**2-d**2,     2*b*c+2*a*d,            2*b*d-2*a*c,            0.0,
                       2*b*c-2*a*d,             a**2-b**2+c**2-d**2,    2*c*d+2*a*b,            0.0,
                       2*b*d+2*a*c,             2*c*d-2*a*b,            a**2-b**2-c**2+d**2,    0.0,
                       floats[0], floats[1], floats[2], 1.0]"""

        """self.matrix = [a**2+b**2-c**2-d**2,     2*b*c-2*a*d,            2*b*d+2*a*c,            0.0,
                       2*b*c+2*a*d,             a**2-b**2+c**2-d**2,    2*c*d-2*a*b,            0.0,
                       2*b*d-2*a*c,             2*c*d+2*a*b,            a**2-b**2-c**2+d**2,    0.0,
                       floats[0], floats[1], floats[2], 1.0]"""

        """self.matrix = [a**2+b**2-c**2-d**2,     2*b*c+2*a*d,            2*b*d-2*a*c,            0.0,
                       2*b*c-2*a*d,             a**2-b**2+c**2-d**2,    2*c*d+2*a*b,            0.0,
                       2*b*d+2*a*c,             2*c*d-2*a*b,            a**2-b**2-c**2+d**2,    0.0,
                       floats[0], floats[1], floats[2], 1.0]"""
        x, y, z, w = d, c, b, a
        self.matrix = [1- 2*y**2 - 2*z**2,  2*x*y+2*w*z,        2*x*z-2*w*y,        0.0,
                       2*x*y-2*w*z,         1-2*x**2-2*z**2,    2*y*z+2*w*x,        0.0,
                       2*x*z+2*w*y,         2*y*z-2*w*x,        1-2*x**2-2*y**2,    0.0,
                       floats[0], floats[1], floats[2], 1.0]

        self.rotmatrix = [1 - 2 * y ** 2 - 2 * z ** 2, 2 * x * y + 2 * w * z, 2 * x * z - 2 * w * y, 0.0,
                       2 * x * y - 2 * w * z, 1 - 2 * x ** 2 - 2 * z ** 2, 2 * y * z + 2 * w * x, 0.0,
                       2 * x * z + 2 * w * y, 2 * y * z - 2 * w * x, 1 - 2 * x ** 2 - 2 * y ** 2, 0.0,
                       0.0, 0.0, 0.0, 1.0]

        self.transmatrix = [1.0, 0.0, 0.0, 0.0,
                       0.0, 1.0, 0.0, 0.0,
                       0.0, 0.0, 1.0, 0.0,
                       floats[0], floats[1], floats[2], 1.0]

        self.matrix4 = Matrix4x4(*self.matrix)
        self.matrix4.transpose()
        #self.matrix2 = [a**2+b**2-c**2-d**2,     2*b*c+2*a*d,            2*b*d-2*a*c,            0.0,
        #               2*b*c-2*a*d,             a**2-b**2+c**2-d**2,    2*c*d+2*a*b,            0.0,
        #               2*b*d+2*a*c,             2*c*d-2*a*b,            a**2-b**2-c**2+d**2,    0.0,
        #               0.0, 0.0, 0.0, 1.0]


    def backup_transform(self):
        glPushMatrix()

    def apply_transform(self):
        glMultMatrixf(self.matrix)

    def apply_translation(self):
        #glPushMatrix()
        #glTranslatef(self.floats[0], self.floats[2], -self.floats[1])
        #glTranslatef(self.floats[8], self.floats[10], -self.floats[9])
        #cos_alpha = self.floats[3]
        #sin_alpha = self.floats[6]
        #glTranslatef(self.floats[0], self.floats[2], self.floats[9])
        #glTranslatef(self.floats[0], self.floats[2], self.floats[10])
        # Column major, i.e. each column comes first
        """glMultMatrixf([1.0, 0.0, 0.0, self.floats[0],
                      0.0, 1.0, 0.0, self.floats[1],
                      0.0, 0.0, 1.0, self.floats[2],
                      0.0, 0.0, 0.0, 1.0])"""
        #glMultMatrixf(self.matrix2)
        #glMultMatrixf(self.matrix)
        glMultMatrixf(self.transmatrix)

    def apply_rotation(self):
        glMultMatrixf(self.rotmatrix)
        #print(self.floats)
        """for i in (self.floats[3], self.floats[4], self.floats[5], self.floats[6], self.floats[7]):
            print(abs(i))
            assert abs(i) <= 1.0"""

    def reset_transform(self):
        glPopMatrix()


class Box(Model):
    def __init__(self, corner_bottomleft, corner_topright):
        self.corner_bottomleft = corner_bottomleft
        self.corner_topright = corner_topright

    def render(self):
        x1, y1, z1 = self.corner_bottomleft
        x2, y2, z2 = self.corner_topright
        glColor3f(1.0, 0.0, 1.0)
        glBegin(GL_LINE_STRIP)  # Bottom, z1
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)
        glVertex3f(x2, y1, z1)

        glEnd()
        glBegin(GL_LINE_STRIP)  # Front, x1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Side, y1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1)
        glVertex3f(x1, y1, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Back, x2
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glVertex3f(x2, y1, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Side, y2
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glEnd()

        glBegin(GL_LINE_STRIP)  # Top, z2
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x1, y1, z2)
        glEnd()

    def render_(self):
        x1,y1,z1 = self.corner_bottomleft
        x2,y2,z2 = self.corner_topright
        glColor3f(1.0, 0.0, 1.0)
        glBegin(GL_LINE_STRIP) # Bottom, z1
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)



        glEnd()
        glColor3f(0.1, 0.1875, 0.8125)
        glBegin(GL_LINE_STRIP) # Front, x1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x1, y2, z1)
        glEnd()

        glBegin(GL_LINE_STRIP) # Side, y1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1)
        glEnd()
        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_LINE_STRIP) # Back, x2
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glColor3f(0.1, 0.1875, 0.8125)
        glBegin(GL_LINE_STRIP) # Side, y2
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glColor3f(0.1, 0.1875, 0.8125)
        glBegin(GL_LINE_STRIP) # Top, z2
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y1, z2)
        glEnd()
