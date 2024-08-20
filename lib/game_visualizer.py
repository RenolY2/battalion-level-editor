from OpenGL.GL import *
from math import pi, atan2, degrees, sin, cos

#from lib.memorylib import Dolphin
#from bw_widgets import BolMapViewer, MODE_TOPDOWN, MODE_3D
#from lib.vectors import Vector3

from lib.memorylib import Dolphin
from lib.vectors import Vector3
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_widgets

EVERYTHING_OK = 0
DOLPHIN_FOUND_NO_GAME = 1
DOLPHIN_NOT_FOUND = 2
WRONG_VERSION = 3


def angle_diff(angle1, angle2):
    angle1 = (angle1+2*pi)%(2*pi)
    angle2 = (angle2+2*pi)%(2*pi)
    #print(angle1, angle2)
    if angle1 > angle2:
        angle2 = (angle2 + 2*pi)#%(2*pi)
    return angle2-angle1


class Game(object):
    def __init__(self):
        self.dolphin = Dolphin()
        self.object_addresses = {}
        self.running = False
        self.timer = 0.0

    def initialize(self):
        self.dolphin.reset()
        self.object_addresses = {}
        self.running = False

        if self.dolphin.find_dolphin():
            if self.dolphin.init_shared_memory():
                gameid = bytes(self.dolphin.read_ram(0, 4))
                print(gameid)
                if gameid != b"G8WE":
                    return "Not supported: Found Game ID '{0}'.".format(str(gameid, encoding="ascii"))
                else:


                    print("Success!")
                    self.running = True
                    return ""
            else:
                self.dolphin.reset()
                return "Dolphin found but game isn't running."
        else:
            self.dolphin.reset()
            return "Dolphin not found."

    def render_visual(self, renderer, selected):
        p = 0
        for valid, kartpos in self.karts:
            if valid:
                glPushMatrix()
                forward = self.kart_headings[p]
                up = Vector3(0.0, 1.0, 0.0)
                right = forward.cross(up)
                #up = right.cross(forward)

                """glMultMatrixf([
                    forward.x, forward.y, forward.z, 0,

                    right.x, right.y, right.z, 0,
                    up.x, up.y, up.z, 0,
                    kartpos.x, -kartpos.z, kartpos.y, 1]
                )"""

                """glMultMatrixf([
                    forward.x, right.x, up.x, 0,
                    -forward.z, -right.z, -up.z, 0,
                    forward.y, right.y, up.y, 0,

                    kartpos.x, -kartpos.z, kartpos.y, 1]
                )"""
                horiz = atan2(self.kart_headings[p].x,
                              self.kart_headings[p].z) - pi / 2.0

                glTranslatef(kartpos.x, -kartpos.z, kartpos.y)
                glRotatef(degrees(horiz), 0.0, 0.0, 1.0)

                renderer.models.playercolors[p].render(valid in selected)
                #renderer.models.render_player_position_colored(kartpos, valid in selected, p)
                glPopMatrix()

                glBegin(GL_LINE_STRIP)
                glColor3f(0.1, 0.1, 0.1)
                glVertex3f(kartpos.x, -kartpos.z, kartpos.y)
                glVertex3f(self.kart_targets[p].x, -self.kart_targets[p].z, self.kart_targets[p].y)
                glEnd()

                renderer.models.render_player_position_colored(self.kart_targets[p], False, p)
            p += 1

    def render_collision(self, renderer, objlist):
        if self.dolphin.memory is not None:
            idbase = 0x100000
            offset = len(objlist)
            for ptr, pos in self.karts:
                objlist.append((ptr, pos, None, None))
                renderer.models.render_generic_position_colored_id(pos, idbase + (offset) * 4)
                offset += 1

    def logic(self, renderer, delta, diff):
        if not self.running:
            return
        renderer: bw_widgets.BolMapViewer
        if len(self.object_addresses) == 0:
            self.setup_address_map(renderer.level_file.objects)

        self.timer += delta
        for obj in renderer.selected:
            if obj.id in self.object_addresses:
                mtx = obj.getmatrix().mtx
                addr = self.object_addresses[obj.id]
                mtxstart = 0x30
                if obj.type == "cMapZone":
                    mtxstart += 8

                # Validate matrix to make sure we're overwriting the right spot
                for i in range(12):
                    assert -1.0 <= self.dolphin.read_float(addr + mtxstart + i*4) <= 1.0
                assert self.dolphin.read_float(addr + mtxstart + 0x3C) == 1.0

                self.dolphin.write_float(addr + mtxstart, mtx[0])
                self.dolphin.write_float(addr + mtxstart + 0x4, mtx[1])
                self.dolphin.write_float(addr + mtxstart + 0x8, mtx[2])
                self.dolphin.write_float(addr + mtxstart + 0xC, mtx[3])

                self.dolphin.write_float(addr + mtxstart + 0x10, mtx[4])
                self.dolphin.write_float(addr + mtxstart + 0x14, mtx[5])
                self.dolphin.write_float(addr + mtxstart + 0x18, mtx[6])
                self.dolphin.write_float(addr + mtxstart + 0x1C, mtx[7])

                self.dolphin.write_float(addr + mtxstart + 0x20, mtx[8])
                self.dolphin.write_float(addr + mtxstart + 0x24, mtx[9])
                self.dolphin.write_float(addr + mtxstart + 0x28, mtx[10])
                self.dolphin.write_float(addr + mtxstart + 0x2C, mtx[11])

                self.dolphin.write_float(addr + mtxstart + 0x30, mtx[12])
                #self.dolphin.write_float(addr + mtxstart + 0x34, mtx[13])
                self.dolphin.write_float(addr + mtxstart + 0x38, mtx[14])

        #renderer.do_redraw()

        if self.timer >= 60.0:
            self.timer = 0.0

    def deref(self, val):
        return self.dolphin.read_uint32(val)

    def resolve_id(self, id):
        dataptr = 0x803b0b28

        bucketindex = (id%0x400)*8  # My guess, seems like ids are stored in 0x400 different buckets for quicker lookup
        valptr = dataptr + 0x60C + bucketindex

        next = self._get_val(valptr, self.deref(valptr), 0)  # Get next value as long as end of list hasn't been reached?
        if next != 0:
            while next != 0:
                if self.deref(next+0xC) == id:
                    return next
                nextptr = next
                next = self._get_val(dataptr+0x60C+bucketindex, self.deref(nextptr), 0)

        next = dataptr + 0x260C
        nextval = 0
        while True:
            nextval = self._get_val(dataptr+0x260C, next, 0)
            if nextval == 0:
                return 0
            if self.deref(nextval+0xC) == id:
                return nextval
            next = self.deref(nextval)

        return None

    # Compare 80252310
    def _get_val(self, val1, val2, val3):
        if val2+val3 != val1:
            return val2
        else:
            return 0

    def setup_address_map(self, objects):
        for objectid, object in objects.items():
            mtx = object.getmatrix()
            if mtx is not None:
                address = self.resolve_id(int(objectid))
                self.object_addresses[objectid] = address


if __name__ == "__main__":
    bwgame = Game()
    print(bwgame.initialize())

    ptr = bwgame.resolve_id(450001876)
    print(hex(ptr))
    """r9 = bwgame.deref(ptr+0x10)
    r0 = bwgame.deref(r9+0xA4)
    r3 = bwgame.deref(r9+0xA0) #LHA
    r3 = ptr + r3

    print("Calling function {0} with value {1}".format(hex(r0), hex(r3)))"""
    import time

    while True:
        time.sleep(1)
        val = bwgame.dolphin.read_float(ptr+0x60)
        bwgame.dolphin.write_float(ptr+0x60, val+1)