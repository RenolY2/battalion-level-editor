from OpenGL.GL import *
from math import pi, atan2, degrees, sin, cos

from lib.memorylib import Dolphin
from bw_widgets import BolMapViewer, MODE_TOPDOWN, MODE_3D
from lib.vectors import Vector3

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
        self.karts = []
        self.kart_targets = []
        self.kart_headings = []

        for i in range(8):
            self.karts.append([None, Vector3(0.0, 0.0, 0.0)])
            self.kart_targets.append(Vector3(0.0, 0.0, 0.0))
            self.kart_headings.append(Vector3(0.0, 0.0, 0.0))
        self.stay_focused_on_player = -1

        self.timer = 0.0
        self.last_angle = 0.0
        self.last_x = 0.0
        self.last_z = 0.0
        
        self.last_kart_x = None
        self.last_kart_z = None

        self.last_angles = []

    def initialize(self):
        self.stay_focused_on_player = -1
        self.dolphin.reset()
        if self.dolphin.find_dolphin():
            if self.dolphin.init_shared_memory():
                gameid = bytes(self.dolphin.read_ram(0, 4))
                print(gameid)
                if gameid in (b"GM4P", b"GM4J"):
                    return "PAL/NTSC-J version of MKDD currently isn't supported for Dolphin hooking."
                elif gameid != b"GM4E":
                    return "Game doesn't seem to be MKDD: Found Game ID '{0}'.".format(str(gameid, encoding="ascii"))
                else:
                    print("Success!")
                    
                    return ""
            else:
                self.dolphin.reset()
                return "Dolphin found but game isn't running."
        else:
            self.dolphin.reset()
            return "Dolphin not found."

    def render_visual(self, renderer: BolMapViewer, selected):
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

    def render_collision(self, renderer: BolMapViewer, objlist):
        if self.dolphin.memory is not None:
            idbase = 0x100000
            offset = len(objlist)
            for ptr, pos in self.karts:
                objlist.append((ptr, pos, None, None))
                renderer.models.render_generic_position_colored_id(pos, idbase + (offset) * 4)
                offset += 1

    def logic(self, renderer: BolMapViewer, delta, diff):
        self.timer += delta
        if self.dolphin.memory is not None:
            kartctrlPtr = self.dolphin.read_uint32(0x803CC588)
            if kartctrlPtr is None or not self.dolphin.address_valid(kartctrlPtr):
                self.dolphin.reset()
                for i in range(8):
                    self.karts[i][0] = None
            else:
                for i in range(8):
                    kartPtr = self.dolphin.read_uint32(kartctrlPtr + 0xA0 + i * 4)
                    if self.dolphin.address_valid(kartPtr):
                        
                        x = self.dolphin.read_float(kartPtr + 0x23C)
                        y = self.dolphin.read_float(kartPtr + 0x240)
                        z = self.dolphin.read_float(kartPtr + 0x244)
                        self.karts[i][0] = kartPtr

                        self.kart_headings[i].x = self.dolphin.read_float(kartPtr + 0x308)
                        self.kart_headings[i].y = self.dolphin.read_float(kartPtr + 0x30C)
                        self.kart_headings[i].z = self.dolphin.read_float(kartPtr + 0x310)

                        karttarget = self.dolphin.read_uint32(kartctrlPtr + 0x1C0 + i*4)

                        if self.dolphin.address_valid(karttarget):
                            clpoint = self.dolphin.read_uint32(karttarget)
                            if self.dolphin.address_valid(clpoint):
                                vec3ptr = self.dolphin.read_uint32(clpoint+4)
                                if self.dolphin.address_valid(vec3ptr):
                                    self.kart_targets[i].x = self.dolphin.read_float(vec3ptr)
                                    self.kart_targets[i].y = self.dolphin.read_float(vec3ptr+4)
                                    self.kart_targets[i].z = self.dolphin.read_float(vec3ptr+8)
                                    
                                    if self.last_kart_x is None:
                                        self.last_kart_x = self.kart_targets[i].x
                                    
                                    if self.last_kart_z is None:
                                        self.last_kart_z = self.kart_targets[i].z
                    else:
                        x = y = z = 0.0
                        y = -50000
                        self.karts[i][0] = None

                    if not self.karts[i][0] in renderer.selected:
                        self.karts[i][1].x = x
                        self.karts[i][1].y = y
                        self.karts[i][1].z = z
                    else:
                        """diff_x = self.last_kart_x - x 
                        diff_z = self.last_kart_z - z 
                        
                        self.last_kart_x = x
                        self.last_kart_z = z
                        
                        self.dolphin.write_float(kartPtr + 0x23C, x + diff_x)
                        self.dolphin.write_float(kartPtr + 0x240, self.karts[i][1].y)
                        self.dolphin.write_float(kartPtr + 0x244, z+diff_z)"""
                        self.dolphin.write_float(kartPtr + 0x23C, self.karts[i][1].x)
                        self.dolphin.write_float(kartPtr + 0x240, self.karts[i][1].y)
                        self.dolphin.write_float(kartPtr + 0x244, self.karts[i][1].z)

            if self.stay_focused_on_player >= 0:
                if renderer.mode == MODE_TOPDOWN:
                    renderer.offset_x = -self.karts[self.stay_focused_on_player][1].x
                    renderer.offset_z = -self.karts[self.stay_focused_on_player][1].z
                else:
                    x = self.kart_headings[self.stay_focused_on_player].x
                    z = self.kart_headings[self.stay_focused_on_player].z


                    angletmp = atan2(x,z) - pi/2.0
                    diff1 = angle_diff(angletmp, self.last_angle)
                    diff2 = angle_diff(self.last_angle, angletmp)
                    if diff1 < diff2:
                        diff = -diff1
                    else:
                        diff = diff2

                    if abs(diff) < 0.001:
                        angle = angletmp
                    else:
                        angle = self.last_angle + diff * delta*3

                    self.last_angle = angle

                    newx = sin(angle + pi/2.0)
                    newz = cos(angle + pi/2.0)

                    #renderer.offset_x = (self.karts[self.stay_focused_on_player][1].x
                    #                     - self.kart_headings[self.stay_focused_on_player].x*1000)
                    #renderer.offset_z = -(self.karts[self.stay_focused_on_player][1].z
                    #                      - self.kart_headings[self.stay_focused_on_player].z*1000)
                    renderer.offset_x = (self.karts[self.stay_focused_on_player][1].x
                                         - newx * 1000)
                    renderer.offset_z = -(self.karts[self.stay_focused_on_player][1].z
                                          - newz * 1000)
                    height = self.karts[self.stay_focused_on_player][1].y
                    #if height < renderer.camera_height:
                    renderer.camera_height = height+500

                    #angle = atan2(self.kart_headings[self.stay_focused_on_player].x,
                    #              self.kart_headings[self.stay_focused_on_player].z) - pi/2.0
                    renderer.camera_horiz = angle

                    if diff >= 1/60.0 and False:
                        diffx = x - self.last_x
                        diffz = z - self.last_z

                        x += diffx*0.01
                        z += diffz*0.01
                        renderer.camera_horiz = atan2(x, z) - pi/2.0

                        self.last_x = x
                        self.last_z = z
                        #self.last_angles.append()
                        """interpolate = (self.timer % 10.0)/10.0
                        if interpolate <= 0.01:
                            #renderer.camera_horiz = angle
                            #self.last_angle = angle
                            self.last_x = (1-interpolate)*self.last_x + interpolate*x
                            self.last_z = (1 - interpolate) * self.last_z + interpolate * z
                            #renderer.camera_horiz = atan2(x, z) - pi/2.0
                        else:
                            tmpx = (1-interpolate)*self.last_x + interpolate*x
                            tmpz = (1 - interpolate) * self.last_z + interpolate * z
                            renderer.camera_horiz = atan2(tmpx, tmpz) - pi / 2.0
                        print(renderer.camera_horiz)"""
                    #renderer.canvas_height =
            renderer.do_redraw()

        if self.timer >= 60.0:
            self.timer = 0.0
