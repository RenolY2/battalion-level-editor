from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import pyqtSignal, QTimer


from OpenGL.GL import *
from math import pi, atan2, degrees, sin, cos

#from lib.memorylib import Dolphin
#from bw_widgets import BolMapViewer, MODE_TOPDOWN, MODE_3D
#from lib.vectors import Vector3
from timeit import default_timer
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
        self.bw2 = False

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
                    self.bw2 = True
                elif gameid == b"RBWP": # PAL BW2
                    self.objectlist_address = 0x805c5828
                    self.bw2 = True
                elif gameid == b"RBWJ":  # JP BW2
                    self.objectlist_address = 0x805c5d68
                    self.bw2 = True

                if self.bw2:
                    self.dolphin.update_mem1_offset()

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
        starttime = default_timer()
        if not self.running:
            renderer.fpscounter.frametime_liveedit = 0
            return

        renderer: bw_widgets.BolMapViewer


        self.timer += delta
        if self.timer > 0.1:
            self.timer = 0
        else:
            return
        if not self.dolphin.is_shared_memory_open(wii=self.bw2):
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
        renderer.fpscounter.frametime_liveedit = default_timer()-starttime
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
       

class Item(QtWidgets.QTableWidgetItem):
    def __init__(self, value):
        super().__init__()
        self.setText(value)


class Gradient(object):
    def __init__(self):
        self.grad = []

    def add(self, val, color_r, color_g, color_b, text_r, text_g, text_b):
        self.grad.append((val, color_r, color_g, color_b, text_r, text_g, text_b))
        self.grad.sort(key=lambda x: x[0])

    def get_value(self, val):
        prev = None

        for v, r, g, b, textr, textg, textb in self.grad:
            if prev is None:
                if val <= v:
                    return r, g, b, textr, textg, textb
            elif v == val:
                return r, g, b, textr, textg, textb
            elif v < val:
                pass
            else:
                prev_v = prev[0]
                diff = v-prev_v
                val_rel = val-prev_v
                fac = val_rel/diff

                texfac = round(fac)

                return (fac*r + (1-fac)*prev[1], fac*g + (1-fac)*prev[2], fac*b + (1-fac)*prev[3],
                        texfac*textr + (1-texfac)*prev[4], texfac*textg + (1-texfac)*prev[5], texfac*textb + (1-texfac)*prev[6])
            prev = (v, r, g, b, textr, textg, textb)

        return r,g,b, textr, textg, textb


class DebugInfoWIndow(QtWidgets.QMdiSubWindow):
    closing = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(800, 400)
        self.game = MiniHook()
        self.game.initialize()
        self.ctrwidget = QtWidgets.QWidget(self)
        self.widgetlayout = QtWidgets.QVBoxLayout(self)

        self.info = QtWidgets.QTableWidget(self)
        self.widgetlayout.addWidget(self.info)
        #self.helptext = QtWidgets.QTextEdit(self)
        self.setWindowTitle("Debug Info")
        #self.helptext.setReadOnly(True)
        self.info.setColumnCount(5)

        self.ctrwidget.setLayout(self.widgetlayout)
        self.setWidget(self.ctrwidget)

        self.checkboxlayout = QtWidgets.QHBoxLayout(self)
        self.advanced = QtWidgets.QRadioButton(self)
        self.text = QtWidgets.QLabel("Advanced", self)
        self.checkboxlayout.addWidget(self.advanced)
        self.checkboxlayout.addWidget(self.text)
        self.checkboxlayout.addStretch(1)
        self.widgetlayout.addLayout(self.checkboxlayout)


        self.updatetimer = QTimer()
        self.updatetimer.setInterval(100)
        self.updatetimer.timeout.connect(self.update_info)
        self.updatetimer.start()

        font = QtGui.QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(20)

        palette = self.palette()
        color = palette.color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base)
        textcolor = palette.color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Text)

        self.gradient = Gradient()
        self.gradient.add(0.0,
                          color.red(), color.blue(), color.green(),
                          textcolor.red(), textcolor.green(), textcolor.blue())
        self.gradient.add(0.9,
                          color.red(), color.blue(), color.green(),
                          textcolor.red(), textcolor.green(), textcolor.blue())
        self.gradient.add(0.95,
                          255, 255, 0,
                          0, 0, 0)
        self.gradient.add(1.0, 255, 0, 0,
                          255, 255, 255)

        r, g, b, _, _, _ = self.gradient.get_value(0.91)
        r2, g2, b2, _, _, _ = self.gradient.get_value(0.97)
        self.gradient.add(0.91,
                          r, g, b, 0, 0, 0)
        self.gradient.add(0.97, r2, g2, b2, 0, 0, 0)

        self.copyshortcut = QtGui.QShortcut("Ctrl+C", self)
        self.copyshortcut.activated.connect(self.copytable)

        metrics = QtGui.QFontMetrics(font)
        #self.helptext.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        #self.helptext.setFont(font)

        self.heaps = []
        self.freelists = []

        self.mem1addresses = None
        self.mem2addresses = None
        if self.game.region == b"G8WE":
            self.heaps.append(("Lua Memory", 0x802fcf70, False))
            self.heaps.append(("Action Heap", 0x802fe02c, False))
            self.heaps.append(("Unit Group Item Heap", 0x802fdfc4, True))
            self.heaps.append(("Texture Cache ARAM Heap", 0x8031340c, True))

            self.freelists.append(("Quad Tree Nodes", 0x803bbf00))  # QuadTree Nodes
            self.freelists.append(("Quad Tree Lists", 0x803bbf04))  # Quadtree lists

            self.freelists.append(("Joints", 0x802c86fc))
            self.freelists.append(("Joint Anims", 0x802c8700))  # Joint Anims

            self.freelists.append(("Ban Joints", 0x802c8704))
            self.freelists.append(("Object Instances", 0x803bbdd8))
            self.freelists.append(("Object Anim Instances", 0x803bbde0))

            self.freelists.append(("Polynodes", 0x803bf09c))

            self.freelists.append(("Node Hierarchies", 0x803bbee0))

            self.freelists.append(("Blend Animation", 0x803bbd78))
            self.freelists.append(("Animation Stretch Blends", 0x803bbdc4))
            self.freelists.append(("Blend Nodes Stretch Continuous", 0x803bbd84))
            self.freelists.append(("Blend Nodes Continuous", 0x803bbd90))
            self.freelists.append(("Blend Transitions", 0x803bbd9c))
            self.freelists.append(("Blend Transition Stretch", 0x803bbda8))

        elif self.game.region == b"RBWE":
            self.mem1addresses = (0x805acf6c, 0x805acf68, 0x805acf74, 0x805acf30, 0x80600330)
            self.mem2addresses = (0x805acfc0, 0x805acfbc, 0x805acfc8, 0x805acf84, 0x80600330)

            self.heaps.append(("System Malloc Heap", 0x804fbf70, True))
            self.heaps.append(("Network Heap", 0x805c28c4, True))
            self.heaps.append(("Lua Memory", 0x80513814, False))
            self.heaps.append(("Action Heap", 0x8051a6dc, False))
            self.heaps.append(("Unit Group Item Heap", 0x8051d2ac, True))
            self.heaps.append(("Texture Render Target Heap", 0x805bc334, False))

            self.freelists.append(("Quad Tree Nodes", 0x80600610))  # QuadTree Nodes
            self.freelists.append(("Quad Tree Lists", 0x80600614))  # Quadtree lists

            # Joints: Affected by lots of objects (probably that can break into multiple pieces).  Grunts are also a few joints?
            self.freelists.append(("Joints", 0x805afe68))
            # Joint anims: affected by e.g. vehicles, multiple anims per vehicle (multiple joints in a vehicle can be animated?)
            self.freelists.append(("Joint Anims", 0x805afe6c))  # Joint Anims

            # Num ban joints: Amount of cTroops multiplied by 46
            self.freelists.append(("Ban Joints", 0x805afe70))
            # Num object instances: can be level objects or stuff like bullets, explosions. One grunt can be multiple objects (grunt, hat, weapon?)
            self.freelists.append(("Object Instances", 0x806004c8))
            # Num object anim instances: All units seem to go into here (+ maybe a few extra special objects?)
            self.freelists.append(("Object Anim Instances", 0x806004d8))

            # Num polynodes: Guess: Amount of nodes containing 3d data
            self.freelists.append(("Polynodes", 0x80600600))

            # Num node hierarchies: Max amount of node hierarchy resources
            self.freelists.append(("Node Hierarchies", 0x806005f0))


            self.freelists.append(("Blend Animation", 0x8060044c))
            self.freelists.append(("Animation Stretch Blends", 0x8060049c))
            self.freelists.append(("Blend Nodes Stretch Continuous", 0x80600458))
            self.freelists.append(("Blend Nodes Continuous", 0x80600464))
            self.freelists.append(("Blend Transitions", 0x80600470))
            self.freelists.append(("Blend Transition Stretch", 0x8060047c))

        self.info.setRowCount(len(self.freelists) + len(self.heaps) + 10)

        #self.testfac = 0.8

    def copytable(self):
        selectedrangelist: QtWidgets.QTableWidgetSelectionRange = self.info.selectedRanges()
        if len(selectedrangelist) > 0:
            selectedrange = selectedrangelist[0]
        else:
            selectedrange = QtWidgets.QTableWidgetSelectionRange()
        if selectedrange.columnCount() > 0 and selectedrange.rowCount() > 0:
            lx = selectedrange.leftColumn()
            ty = selectedrange.topRow()
            rx = selectedrange.rightColumn()
            by = selectedrange.bottomRow()

            rows = []
            for j in range(ty, by+1):
                row = []
                for i in range(lx, rx+1):
                    item = self.info.item(j, i)
                    if item is None:
                        row.append("")
                    else:
                        row.append(item.text())
                rows.append(",".join(row))

            clipboard = QtGui.QGuiApplication.clipboard()
            clipboard.setText("\n".join(rows))

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

    def set_row_values(self, row, *values):
        for i, v in enumerate(values):
            curritem = self.info.item(row, i)
            if curritem is not None:
                curritem.setText(str(values[i]))
            else:
                item = Item(str(values[i]))
                self.info.setItem(row, i, item)

    def clear_row(self, row):
        self.set_row_values(row, *["" for x in range(self.info.columnCount())])

    def set_color(self, row, column, color):
        item = self.info.item(row, column)
        if item is not None:
            brush = QtGui.QBrush(QtGui.QColor(int(color[0]), int(color[1]), int(color[2])))
            fr = QtGui.QBrush(QtGui.QColor(int(color[3]), int(color[4]), int(color[5])))
            item.setForeground(fr)
            item.setBackground(brush)

    def update_info(self):
        info = []
        if self.game.running:
            bw1 = False

            if self.game.region in (b"RBWE", b"RBWP", b"RBWJ"):
                if self.game.region != b"RBWE":
                    self.set_row_values(0,
                                        "Only the US version of Battalion Wars 2 is currently supported. If it is running, please close this debug window and reopen it again.")
                    self.info.resizeRowsToContents()
                    return
            elif self.game.region in (b"G8WP", b"G8WE", b"G8WJ"):
                bw1 = True
                if self.game.region != b"G8WE":
                    self.set_row_values(0,
                                        "Only the US version of Battalion Wars 1 is currently supported. If it is running, please close this debug window and reopen it again.")
                    self.info.resizeRowsToContents()
                    return
            else:
                self.set_row_values(0,
                                    "Unsupported game.")
                self.info.resizeRowsToContents()
                return

            deref = self.game.deref

            info.append("\nHeap Info:")
            if self.mem1addresses is not None:
                self.set_row_values(0, "Mem1 free", self.get_mem1_remaining())
                self.set_row_values(1, "Mem2 free", self.get_mem2_remaining())

            self.set_row_values(3, "Heap", "Address", "Total (Bytes)", "Used (Bytes)", "Free (Bytes)")
            i = 0
            for name, addr, advanced in self.heaps:
                if not advanced or (advanced and self.advanced.isChecked()):
                    size = deref(addr + 0x60)
                    if bw1:
                        used = "-"
                        free = "-"
                    else:
                        used = deref(addr + 0x48)
                        free = deref(addr + 0x4C)
                    """info.append(
                        "{0}: \n Address: {1}\n Total: {3} bytes\n Used: {2} bytes\n Free: {4} bytes\n".format(
                            name, hex(addr), used, size, free
                        ))"""
                    self.set_row_values(4+i, name, hex(addr), size, used, free)
                    if not bw1 and size != 0:
                        fac = used/size
                        self.set_color(4+i, 4, self.gradient.get_value(fac))
                    i += 1


            # "Size (Bytes)",
            self.clear_row(4+i)
            offset = 4 + i + 1
            self.set_row_values(offset, "Free list", "Address", "Total", "Max Used", "Free")
            i = offset + 1
            for name, addr in self.freelists:
                freelistinfo_ptr = deref(addr)
                if freelistinfo_ptr == 0:
                    continue
                freelist_addr = deref(freelistinfo_ptr+0)
                totalsize = deref(freelistinfo_ptr+0x18)
                count = deref(freelistinfo_ptr+0x14)
                if bw1:
                    freeinactive = deref(freelistinfo_ptr + 0x24)
                    maxused = deref(freelistinfo_ptr + 0x28)
                else:
                    freeinactive = deref(freelistinfo_ptr+0x28)
                    maxused = deref(freelistinfo_ptr+0x2C)
                #info.append("{}: \n Address: {}\n Total size: {}\n Free or inactive:{}\n Max used/Max count: {}/{}\n".format(
                #    name, hex(freelist_addr), totalsize, freeinactive, maxused, count,
                #))#
                # totalsize,
                self.set_row_values(i, name, hex(freelist_addr), count, maxused, freeinactive)
                if size != 0:
                    fac = maxused/count
                    fac2 = (count-freeinactive) / count
                    #self.testfac += 0.0001
                    #if self.testfac > 1.0:
                    #    self.testfac = 0.8

                    #fac2 = self.testfac

                    self.set_color(i, 3, self.gradient.get_value(fac))
                    self.set_color(i, 4, self.gradient.get_value(fac2))
                i += 1
            for j in range(i, self.info.rowCount()+1):
                self.clear_row(j)
            self.info.resizeColumnToContents(0)
            """cursor = self.helptext.textCursor()
            hasselection = cursor.hasSelection()
            if hasselection:
                position = cursor.position()
                anchor = cursor.anchor()
            curr = self.helptext.verticalScrollBar().value()
            self.helptext.setText("\n".join(info))

            if hasselection:
                cursor = self.helptext.textCursor()
                cursor.setPosition(anchor, mode=QtGui.QTextCursor.MoveMode.MoveAnchor)
                cursor.setPosition(position, mode=QtGui.QTextCursor.MoveMode.KeepAnchor)
                self.helptext.setTextCursor(cursor)
            self.helptext.verticalScrollBar().setValue(curr)"""

        else:
            self.set_row_values(0, "Cannot show debug info because editor is not connected to game. Close window and open again when game is running.")
            self.info.resizeRowsToContents()

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