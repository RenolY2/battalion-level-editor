from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import pyqtSignal, QTimer


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
    def __init__(self, shutdowncallback=None):
        self.dolphin = Dolphin()
        self.object_addresses = {}
        self.running = False
        self.timer = 0.0
        self.do_once = False
        self.visualize = False
        self.objectlist_address = None
        self.shutdowncallback = shutdowncallback
        self.current_address = None

    def initialize(self, level_file=None, shutdown=False, matchoverride=False, shutdowncallback=None):
        self.dolphin.reset()
        self.object_addresses = {}
        self.running = False
        self.shutdowncallback = shutdowncallback

        self.do_once = True
        self.objectlist_address = None
        self.current_address = None

        if shutdown:
            return ""
        # BW1 PAL: 803b6f08
        # BW2 805c3ca8
        if self.dolphin.find_dolphin():
            if self.dolphin.init_shared_memory():
                gameid = bytes(self.dolphin.read_ram(0, 4))
                print(gameid)
                if gameid == b"G8WE":  # US BW1
                    self.objectlist_address = 0x803b0b28
                elif gameid == b"G8WP":  # PAL BW1
                    self.objectlist_address = 0x803b6f08
                elif gameid == b"G8WJ":  # JP BW1
                    self.objectlist_address = 0x803b5f88
                elif gameid == b"RBWE":  # US BW2
                    self.objectlist_address = 0x805c3ca8
                elif gameid == b"RBWP": # PAL BW2
                    self.objectlist_address = 0x805c5828
                elif gameid == b"RBWJ":  # JP BW2
                    self.objectlist_address = 0x805c5d68

                if self.objectlist_address is None:
                    return "Not supported: Found Game ID '{0}'.".format(str(gameid, encoding="ascii"))
                else:
                    found, notfound = self.setup_address_map(level_file.objects)
                    print("{0} vs {1} objects found/not found".format(found, notfound))
                    if found > notfound or matchoverride:
                        print("Success!")
                        self.current_address = self.dolphin.read_uint32(self.objectlist_address)
                        self.running = True
                        return ""
                    else:
                        return "Level mismatch, cannot hook. {0} objects found, {1} objects not found".format(found, notfound)
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

    def do_visualize(self):
        return self.running and self.visualize

    def logic(self, renderer, delta, diff):
        if not self.running:
            return

        renderer: bw_widgets.BolMapViewer


        self.timer += delta
        if self.timer > 0.1:
            self.timer = 0
        else:
            return
        if not self.dolphin.is_shared_memory_open():
            self.shutdowncallback()
            return

        fails = 0
        successes = 0
        for id, addr in self.object_addresses.items():
            try:
                newaddr = self.resolve_id(int(id))
                if newaddr != addr:
                    fails += 1
                else:
                    successes += 1
            except Exception as err:
                print(err)
                fails = 10

            if successes > 50:
                break

            if fails >= min(5, len(self.object_addresses)):
                self.running = False
                print("Object address mismatch, likely level or game change: Shutting down Dolphin hook.")
                if self.shutdowncallback is not None:
                    self.shutdowncallback()
                return


        updateobjects = []
        updateobjectsonce = []
        visible = renderer.visibility_menu.object_visible
        if self.visualize:
            for objid, obj in renderer.level_file.objects_with_positions.items():
                if not self.do_once and not visible(obj.type, obj):
                    continue
                if obj in renderer.selected:
                    continue
                if obj.id not in self.object_addresses:
                    continue

                addr = self.object_addresses[obj.id]
                mtxstart = 0x30
                if obj.type in ("cMapZone", "cCoastZone", "cDamageZone", "cNogoHintZone"):
                    mtxstart += 8
                if obj.type in ("cTroop", "cGroundVehicle", "cAirVehicle", "cWaterVehicle",
                                "cCamera", "cBuilding", "cObjectiveMarker"):

                    mtxarray = [self.dolphin.read_float(addr + mtxstart + i * 4) for i in range(16)]
                    mtxoverride = obj.mtxoverride

                    # Test if the object has moved compared to last time and only move then.
                    if mtxoverride is None or any(mtxoverride[i] != mtxarray[i] for i in (0, 1, 2, 12, 13, 14)):
                        updateobjects.append(obj)
                        obj.set_mtx_override(mtxarray)

                elif self.do_once:
                    updateobjects.append(obj)

                    mtxarray = [self.dolphin.read_float(addr+mtxstart+i*4) for i in range(16)]
                    obj.set_mtx_override(mtxarray)
        else:
            for objid, obj in renderer.level_file.objects_with_positions.items():
                obj.set_mtx_override(None)

        #if doonce:
        #    renderer.do_redraw(forcespecific=updateobjectsonce)
        #    doonce = False

        for obj in renderer.selected:
            if not hasattr(obj, "id"):
                continue
            if obj.id in self.object_addresses:
                if obj.mtxoverride is not None:
                    mtx = obj.mtxoverride
                    objheight = mtx[13]
                else:
                    mtx = obj.getmatrix().mtx
                    objheight = obj.height
                addr = self.object_addresses[obj.id]
                mtxstart = 0x30
                if obj.type in ("cMapZone", "cCoastZone", "cDamageZone", "cNogoHintZone"):
                    mtxstart += 8

                # Validate matrix to make sure we're overwriting the right spot
                tests = []
                for i in range(12):
                    # Sometimes a value is ever so slightly above 1.0 so need to round
                    tests.append(-1.0 <= round(self.dolphin.read_float(addr + mtxstart + i*4), 2) <= 1.0)

                tests.append(self.dolphin.read_float(addr + mtxstart + 0x3C) == 1.0)
                if all(tests):
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
                    self.dolphin.write_float(addr + mtxstart + 0x34, objheight)
                    self.dolphin.write_float(addr + mtxstart + 0x38, mtx[14])
                else:
                    print("warning, mtx test failed for", hex(addr), obj.name)

        #renderer.do_redraw()
        renderer.do_redraw(forcespecific=updateobjects)
        self.do_once = False
        #if self.timer >= 60.0:
        #    self.timer = 0.0

    def deref(self, val):
        return self.dolphin.read_uint32(val)

    def resolve_id(self, id):
        dataptr = self.objectlist_address

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
        self.object_addresses = {}
        objectsnotfound = 0
        objectsfound = 0
        for objectid, object in objects.items():
            mtx = object.getmatrix()
            if mtx is not None:
                address = self.resolve_id(int(objectid))
                if address is not None and address != 0:
                    self.object_addresses[objectid] = address
                    objectsfound += 1
                else:
                    objectsnotfound += 1

        return objectsfound, objectsnotfound


class LevelFileDummy(object):
    def __init__(self):
        self.objects = {}


class MiniHook(Game):
    def __init__(self):
        super().__init__()

    def initialize(self, level_file=None, shutdown=False, matchoverride=False, shutdowncallback=None):
        self.dolphin.reset()
        self.object_addresses = {}
        self.running = False
        self.shutdowncallback = shutdowncallback

        self.do_once = True
        self.region = None
        self.current_address = None

        if shutdown:
            return ""
        # BW1 PAL: 803b6f08
        # BW2 805c3ca8


        if self.dolphin.find_dolphin():
            if self.dolphin.init_shared_memory():
                gameid = bytes(self.dolphin.read_ram(0, 4))
                print(gameid)
                if gameid == b"G8WE":  # US BW1
                    self.region = gameid
                elif gameid == b"G8WP":  # PAL BW1
                    self.region = gameid
                elif gameid == b"G8WJ":  # JP BW1
                    self.region = gameid
                elif gameid == b"RBWE":  # US BW2
                    self.region = gameid
                elif gameid == b"RBWP": # PAL BW2
                    self.region = gameid
                elif gameid == b"RBWJ":  # JP BW2
                    self.region = gameid

                if self.region is None:
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
       

class DebugInfoWIndow(QtWidgets.QMdiSubWindow):
    closing = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(800, 400)
        self.game = MiniHook()
        self.game.initialize()
        self.helptext = QtWidgets.QTextEdit(self)
        self.setWindowTitle("Debug Info")
        self.helptext.setReadOnly(True)

        self.setWidget(self.helptext)
        self.updatetimer = QTimer()
        self.updatetimer.setInterval(100)
        self.updatetimer.timeout.connect(self.update_info)
        self.updatetimer.start()

        font = QtGui.QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(20)

        metrics = QtGui.QFontMetrics(font)
        self.helptext.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        self.helptext.setFont(font)

        self.freelists = []

        self.mem1addresses = None
        self.mem2addresses = None

        if self.game.region == b"RBWE":
            self.mem1addresses = (0x805acf6c, 0x805acf68, 0x805acf74, 0x805acf30, 0x80600330)
            self.mem2addresses = (0x805acfc0, 0x805acfbc, 0x805acfc8, 0x805acf84, 0x80600330)
            self.freelists.append(("Quad Tree Nodes", 0x80600610))  # QuadTree Nodes
            self.freelists.append(("Quad Tree Lists", 0x80600614))  # Quadtree lists
            self.freelists.append(("Joints", 0x805afe68))  # Joints
            self.freelists.append(("Joint Anims", 0x805afe6c))  # Joint Anims
            self.freelists.append(("Ban Joints", 0x805afe70))  # Num ban joints
            self.freelists.append(("Object Instances", 0x806004c8))  # Num object instances
            self.freelists.append(("Object Anim Instances", 0x806004d8))  # Num object anim instances
            self.freelists.append(("Polynodes", 0x80600600))  # Num polynodes
            self.freelists.append(("Node Hierarchies", 0x806005f0))  # Num node hierarchies

    def get_mem1_remaining(self):
        if self.mem1addresses is not None:
            top = self.game.deref(self.mem1addresses[0])
            if self.game.deref(self.mem1addresses[1]) & 0x1:
                top = self.game.deref(self.mem1addresses[2])
            bottom = self.game.deref(self.mem1addresses[3]+self.game.deref(self.mem1addresses[4])*0xC)
            return top-bottom

    def get_mem2_remaining(self):
        if self.mem2addresses is not None:
            top = self.game.deref(self.mem2addresses[0])
            if self.game.deref(self.mem2addresses[1]) & 0x1:
                top = self.game.deref(self.mem2addresses[2])
            bottom = self.game.deref(self.mem2addresses[3] + self.game.deref(self.mem2addresses[4]) * 0xC)
            return top - bottom

    def update_info(self):
        info = []
        if self.game.running:
            if self.game.region != b"RBWE":
                info.append("Only the US version of Battalion Wars 2 is currently supported. If it is running, please close this debug window and reopen it again.")
            deref = self.game.deref

            info.append("Mem1 free: {0} bytes".format(self.get_mem1_remaining()))
            info.append("Mem2 free: {0} bytes".format(self.get_mem2_remaining()))
            info.append("\nFree list Info:")

            for name, addr in self.freelists:
                freelistinfo_ptr = deref(addr)
                freelist_addr = deref(freelistinfo_ptr+0)
                totalsize = deref(freelistinfo_ptr+0x18)
                count = deref(freelistinfo_ptr+0x14)
                freeinactive = deref(freelistinfo_ptr+0x28)
                maxused = deref(freelistinfo_ptr+0x2C)
                info.append("{}: \nAddress: {}\nTotal size: {}\n Free or inactive:{}\n Max used/Max count: {}/{}\n".format(
                    name, hex(freelist_addr), hex(totalsize), freeinactive, maxused, count,
                ))
            curr = self.helptext.verticalScrollBar().value()
            self.helptext.setText("\n".join(info))
            self.helptext.verticalScrollBar().setValue(curr)
        else:
            self.helptext.setText("Cannot show debug info because editor is not connected to game. Close window and open again when Live Edit/View is running.")

    def closeEvent(self, closeEvent: QtGui.QCloseEvent) -> None:
        self.closing.emit()


if __name__ == "__main__":

    bwgame = Game()
    print(bwgame.initialize(LevelFileDummy(), matchoverride=True))

    #ptr = bwgame.resolve_id(450001876)
    #print(hex(ptr))
    """r9 = bwgame.deref(ptr+0x10)
    r0 = bwgame.deref(r9+0xA4)
    r3 = bwgame.deref(r9+0xA0) #LHA
    r3 = ptr + r3

    print("Calling function {0} with value {1}".format(hex(r0), hex(r3)))"""
    import time
    from binascii import unhexlify, hexlify
    offset = 0
    while True:
        value = bwgame.dolphin.read_ram(offset, 16)

        if value[:4] == unhexlify("029F0010"):
            print(hex(offset))
            print(hexlify(value))
        offset += 16
        #time.sleep(1)
        #val = bwgame.dolphin.read_float(ptr+0x60)
        #bwgame.dolphin.write_float(ptr+0x60, val+1)