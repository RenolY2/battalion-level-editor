import lupa.lua51 as lua
import threading
import time

if __name__ == "__main__":
    import bw1_functions as bw1_functions
    import bw2_functions as bw2_functions
else:
    import lib.lua.bw1_functions as bw1_functions
    import lib.lua.bw2_functions as bw2_functions


DO_NOT_REPLACE = [
    "EndFrame", "UpdateMusic", "WaitFor", "DebugOut", "RegisterReflectionId", "Kill",
    "GetTime", "GetFramesPerSecond"
]


class Node(object):
    def __init__(self, value=None):
        self.value = value
        self.children = {}

    def add_child(self, key):
        if key in self.children:
            return self.children[key]
        else:
            child = Node()

            self.children[key] = child
            return child


class Tree(Node):
    def __init__(self):
        super().__init__()

    def add_child_chain(self, keys, value=None):
        curr = self

        for key in keys:
            curr = curr.add_child(key)

        curr.value = value

    def add_function_chain(self, funcname, keys, value=None):
        chain = [funcname] + list(keys)
        self.add_child_chain(chain, value)

    def get_return_value(self, funcname, keys):
        if funcname in self.children:
            curr = self.children[funcname]

            for key in keys:
                if key in curr.children:
                    curr = curr.children[key]
                else:
                    curr = None
                    break

            if curr is not None:
                return curr.value
            else:
                return None
        else:
            return None


class LuaSimulator(object):
    def __init__(self, output_hook, is_bw1):
        self.funcs = {}

        self.runtime = lua.LuaRuntime()
        self.context = ""

        self.output_hook = output_hook
        self.runtime.globals().LuaHook = self.lua_hook
        self.runtime.globals().DebugOut = self.debug_out
        self.runtime.globals().EndFrame_ = self.end_frame
        self.runtime.globals().RegisterReflectionId = self.register_reflection
        self.runtime.globals().SetDefaultReturn = self.set_default_return
        self.runtime.globals().SetReturn = self.add_argument_return
        self.runtime.globals().Kill = self.kill_script
        self.runtime.globals().GetFramesPerSecond = self.get_frames_per_second


        self.debug = False
        self.debug_call = False

        self.runtime.execute(f"""
                        function EndFrame()
                            EndFrame_()
                            coroutine.yield()
                        end""")

        self.runtime.globals().UpdateMusic = self.runtime.globals().EndFrame

        self.runtime.execute(f"""
                            function WaitFor(waittime)
                                local start = os.time()
                                
                                while os.time() - start < waittime do
                                    --print(os.time()-start, waittime)
                                    coroutine.yield()
                                end
                            end""")
        self.runtime.execute(f"""
                            function GetTime()
                                return os.time()
                            end""")

        if is_bw1:
            self.runtime.globals().constant = self.set_constants()
            funcs = bw1_functions.FUNCTIONS
        else:
            self.runtime.globals().constant = self.set_constants_bw2()
            funcs = bw2_functions.FUNCTIONS

        for funcname in funcs:
            if funcname not in DO_NOT_REPLACE:
                self.runtime.execute(f"""
                    {funcname} = function (...)  
                        return LuaHook(\"{funcname}\", ...)     
                    end""")

        self.stop = False

        self.context_dirty = False

        self.pressed = False
        self._coroutines = []
        self._coroutine_dead = {}

        self.current_routine = None
        self.prepend_routine_name_to_print = False

        self.default_return = {}
        self.argument_return_override = Tree()

    def get_frames_per_second(self):
        return 30.0

    def kill_script(self, id):
        try:
            id = int(id)
            for coroutinename, owner, func in self._coroutines:
                if owner == id:
                    self._coroutine_dead[coroutinename] = True
                    ##if self.debug:
                    self.debug_out(self.current_routine, "has killed", coroutinename, f"({func})")
        except Exception as err:
            print(err)

    def add_argument_return(self, func, value, *arguments):
        self.argument_return_override.add_function_chain(func, arguments, value)

    def set_default_return(self, func, value):
        self.default_return[func] = value

    def lua_hook(self, funcname, *args):
        return_val = self.argument_return_override.get_return_value(funcname, args)
        if return_val is None:
            return_val = self.default_return.get(funcname)

        if self.debug_call:
            if len(args) == 0:
                self.debug_out("CALL:", funcname, "has been called.")
            else:
                self.debug_out("CALL:", funcname, "has been called with args", ", ".join(str(x) for x in args))

            self.debug_out("RETURN:", funcname, "returned", str(return_val))

        if self.stop:
            raise RuntimeError("Stopping Lua...")

        return return_val

    def set_function(self, funcname, func, force=False):
        if funcname not in self.runtime.globals() and not force:
            raise RuntimeError(f"Unknown function {funcname}")
        self.runtime.globals()[funcname] = func

    def get_globals(self):
        result = {}
        for key in self.runtime.globals():
            result[key] = self.runtime.globals()[key]

        return result

    def set_constants(self):
        self.runtime.globals().CARD = {
            "NONE": 0,
            "CardFull": 1,
            "NoSpace": 2,
            "NoData": 3,
            "AskFormat": 4,
            "LoadFailed": 5,
            "SaveFailed": 6,
            "LoadOK": 7,
            "SaveOK": 8,
            "AskOverwrite": 9,
            "FormatFailed": 10,
            "Damaged": 11,
            "CRCError": 12,
            "NotSupported": 13,
            "NoMemoryCard": 14,
            "NoFiles": 15,
            "FormatOK": 16,
            "DeleteOK": 17,
            "AskDelete": 0x12,
            "Corrupt": 19,
            "Unformatted": 20,
            "WrongDevice": 21,
            "DifferentFile": 22,
            "FileOK": 23,
            "CardOK": 24,
            "DifferentCard": 25,
            "NoPrevious": 26,
            "CRCRecoverable": 27
        }

        self.runtime.globals().GAMESTATUS = {
            "NONE": 0,
            "PLAY": 1,
            "QUIT": 2,
            "LOSE": 3,
            "WIN": 4,
            "MISSIONS": 5,
            "UNITS": 6,
            "GALLERY": 7
        }

        self.runtime.globals().LEVELSTATUS = {
            "NEW": 0,
            "NEXT": 1,
            "DONE": 2,
            "LOCKED": 3
        }

        self.runtime.globals().VIDEO = {
            "OFF": 0,
            "ONCE": 1,
            "LOOPED": 2
        }

        self.runtime.globals().GUI = {
            "GUI": 0,
            "PAGE": 1,
            "GADGET": 2,
            "FLAT": 3,
            "RECT": 4,
            "SPRITE": 5,
            "BUTTON": 6,
            "TEXTBOX": 7
        }

        self.runtime.globals().JUSTIFY = {
            "LEFT": 0,
            "CENTRE": 1,
            "RIGHT": 2,
            "FULL1": 3,
            "FULL2": 4
        }

        self.runtime.globals().GRADE = {
            "NONE": 0,
            "C": 1,
            "B": 2,
            "A": 3,
            "S": 4
        }

        constants = {}
        constants["ID_NONE"] = 0
        constants["PAUSESCR_LTRIGGER"] = 1
        constants["PAUSESCR_RTRIGGER"] = 2
        constants["PAUSESCR_ZBUTTON"] = 3
        constants["PAUSESCR_LSTICK"] = 4
        constants["PAUSESCR_DPAD"] = 5
        constants["PAUSESCR_CSTICK"] = 6
        constants["PAUSESCR_XBUTTON"] = 7
        constants["PAUSESCR_YBUTTON"] = 8
        constants["PAUSESCR_ABUTTON"] = 9
        constants["PAUSESCR_BBUTTON"] = 10
        constants["TRANSFER_BYZFROMTARGET"] = 1
        constants["TRANSFER_BYZFROMCMDBAR"] = 2
        constants["TRANSFER_BYDEATH"] = 3
        constants["TRANSFER_BYMAP"] = 4
        constants["TRANSFER_BYVEHICLE"] = 5
        constants["TRANSFER_NO"] = 6
        constants["MSGSTYLE_FRIENDLY"] = 1
        constants["MSGSTYLE_UNFRIENDLY"] = 0
        constants["MISSIONOVER_LOSE"] = 0
        constants["MISSIONOVER_PLAYER1_WINS"] = 1
        constants["MISSIONOVER_PLAYER2_WINS"] = 2
        constants["MISSIONOVER_BOTH_WIN"] = 3
        constants["AI_ATTACK_STYLE"] = 0
        constants["ATTACKSTYLE_DEFENSIVE"] = 0
        constants["ATTACKSTYLE_AGGRESSIVE"] = 1
        constants["AI_MOVE_STYLE"] = 1
        constants["MOVESTYLE_RESPOND_TO_ATTACK"] = 0
        constants["MOVESTYLE_ATTACK_ON_SIGHT"] = 1
        constants["AI_DODGE"] = 2
        constants["DODGE_ALLOWED"] = 1
        constants["DODGE_NOT_ALLOWED"] = 0
        constants["ORDER_NORMAL"] = 0
        constants["ORDER_FORCED"] = 1
        constants["FORMATION_DISALLOWED"] = 0
        constants["FORMATION_ALLOWED"] = 1
        constants["ACTIVE"] = 1
        constants["INACTIVE"] = 0
        constants["DONT_ADJUST_WEAPON"] = 0
        constants["ADJUST_WEAPON"] = 1
        constants["ACTION_STATE_ATTACK"] = 1
        constants["ACTION_STATE_DYING"] = 2
        constants["ACTION_STATE_EMPTY_VEHICLE"] = 3
        constants["ACTION_STATE_ENTERING_VEHICLE"] = 4
        constants["ACTION_STATE_FOLLOWING"] = 5
        constants["ACTION_STATE_FOLLOWING_PLAYER"] = 6
        constants["ACTION_STATE_GOTO_COVERPOINT"] = 8
        constants["ACTION_STATE_IN_COVERPOINT"] = 7
        constants["ACTION_STATE_GUARD_AREA"] = 9
        constants["ACTION_STATE_IN_CAPTUREPOINT"] = 10
        constants["ACTION_STATE_GOING_TO_CAPTUREPOINT"] = 11
        constants["ACTION_STATE_IN_UNIT_CARRIER"] = 12
        constants["ACTION_STATE_JUMPING"] = 13
        constants["ACTION_STATE_MOVING_TO_AREA"] = 14
        constants["ACTION_STATE_SLIDE"] = 15
        constants["ACTION_STATE_STUNNED"] = 16
        constants["ACTION_STATE_PLAYER_IN_UNIT_CARRIER"] = 17
        constants["ACTION_STATE_PLAYER_IS_TROOP"] = 18
        constants["ACTION_STATE_RESOLVE_AVOID"] = 21
        constants["ACTION_STATE_CELEBRATING"] = 22
        constants["MOVEMENT_STATE_AIRBORNE"] = 1
        constants["MOVEMENT_STATE_FLAILING"] = 2
        constants["MOVEMENT_STATE_SWIMMING"] = 3
        constants["MOVEMENT_STATE_ON_GROUND"] = 4
        constants["OBJECTIVE_MARKER_DATA_VISIBLE"] = 0
        constants["OBJECTIVE_MARKER_DATA_ATTACHED_TO"] = 1
        constants["OBJECTIVE_MARKER_DATA_POSITION"] = 2
        constants["OBJECTIVE_DATA_TEXT"] = 0
        constants["OBJECTIVE_DATA_VISIBLE"] = 1
        constants["OBJECTIVE_DATA_STATE"] = 2
        constants["OBJECTIVE_DATA_COLOUR"] = 3
        constants["TYPE"] = 0
        constants["GTYPE"] = 1
        constants["CONTROL_PRESSED_THIS_LEVEL"] = 0
        constants["CONTROL_JUST_PRESSED"] = 1
        constants["CONTROL_HELD"] = 2
        constants["CONTROL_JUST_RELEASED"] = 3
        constants["CONTROL_ACCELERATE"] = 0
        constants["CONTROL_BRAKE"] = 1
        constants["CONTROL_STEER_LEFT"] = 2
        constants["CONTROL_STEER_RIGHT"] = 3
        constants["CONTROL_TURRET_UP"] = 4
        constants["CONTROL_TURRET_DOWN"] = 5
        constants["CONTROL_TURRET_LEFT"] = 6
        constants["CONTROL_TURRET_RIGHT"] = 7
        constants["CONTROL_FLY_UP"] = 9
        constants["CONTROL_FLY_DOWN"] = 10
        constants["CONTROL_FLYUP_MODIFIER"] = 11
        constants["CONTROL_WALK_FORWARD"] = 12
        constants["CONTROL_WALK_BACK"] = 13
        constants["CONTROL_TURN_LEFT"] = 14
        constants["CONTROL_TURN_RIGHT"] = 15
        constants["CONTROL_STRAFE_LEFT"] = 16
        constants["CONTROL_STRAFE_RIGHT"] = 17
        constants["CONTROL_LOOK_UP"] = 18
        constants["CONTROL_LOOK_DOWN"] = 19
        constants["CONTROL_NEXT_UNIT_TYPE"] = 20
        constants["CONTROL_PREV_UNIT_TYPE"] = 21
        constants["CONTROL_NEXT_UNIT"] = 22
        constants["CONTROL_PREV_UNIT"] = 23
        constants["CONTROL_TRANSFER"] = 24
        constants["CONTROL_HUD_TRANSFER"] = 25
        constants["CONTROL_CALL"] = 26
        constants["CONTROL_SEND"] = 27
        constants["CONTROL_DISMISS"] = 28
        constants["CONTROL_LOCAL_CALL"] = 29
        constants["CONTROL_FIRE"] = 30
        constants["CONTROL_JUMP"] = 31
        constants["CONTROL_ROLL"] = 32
        constants["CONTROL_LOOK_MODIFIER"] = 33
        constants["CONTROL_STRAFE_MODIFIIER"] = 34
        constants["CONTROL_STRAFELOCK_MODIFIER"] = 35
        constants["CONTROL_LOAD_VEHICLE"] = 36
        constants["CONTROL_UNLOAD_VEHICLE"] = 37
        constants["CONTROL_GLOBAL_TOGGLE"] = 38
        constants["CONTROL_GLOBAL_LOOK_MODIFIER"] = 39
        constants["CONTROL_GLOBAL_LOCK_MODIFIER"] = 40
        constants["CONTROL_GLOBAL_LOOK_UP"] = 41
        constants["CONTROL_GLOBAL_LOOK_DOWN"] = 42
        constants["CONTROL_GLOBAL_LOOK_LEFT"] = 43
        constants["CONTROL_GLOBAL_LOOK_RIGHT"] = 44
        constants["CONTROL_TOGGLE_MAP"] = 66
        constants["CONTROL_PAUSE"] = 83
        constants["CONTROL_SKIP_CUTSCENE"] = 99
        constants["CONTROL_SKIP_CUTSCENE_ALT"] = 100
        constants["TOTAL_DEAD_HEALTH"] = 0
        constants["TOTAL_ALIVE_HEALTH"] = 1
        constants["WAIT"] = 1
        constants["NO_WAIT"] = 0
        constants["FADE_IN"] = 0
        constants["FADE_OUT"] = 1
        constants["CAMERA_WAYPOINT"] = 0
        constants["TARGET_WAYPOINT"] = 1
        constants["IMMEDIATE"] = 0
        constants["SMOOTH"] = 1
        constants["ARMY_WF"] = 0
        constants["ARMY_XYLVANIAN"] = 1
        constants["ARMY_TUNDRAN"] = 2
        constants["ARMY_SOLAR"] = 3
        constants["ARMY_UNDERWORLD"] = 4
        constants["ARMY_NEUTRAL"] = 5
        constants["CAPTUREPOINTFLAG_RAISING"] = 0
        constants["CAPTUREPOINTFLAG_LOWERING"] = 1
        constants["HUD_RADAR"] = 0
        constants["HUD_COMMANDBAR"] = 1
        constants["HUD_COMMANDSTACK"] = 2
        constants["HUD_RETICULE"] = 3
        constants["HUD_STATUSBAR"] = 4
        constants["HUD_STATUSICONS"] = 5
        constants["HUD_PLAYERICON"] = 6
        constants["HUD_CONTROLIMAGE_ALL"] = 7
        constants["HUD_CONTROLIMAGE_SHOULDERL"] = 8
        constants["HUD_CONTROLIMAGE_SHOULDERR"] = 9
        constants["HUD_CONTROLIMAGE_STICK"] = 10
        constants["HUD_CONTROLIMAGE_CSTICK"] = 11
        constants["HUD_CONTROLIMAGE_DPAD"] = 12
        constants["HUD_CONTROLIMAGE_A"] = 13
        constants["HUD_CONTROLIMAGE_B"] = 14
        constants["HUD_CONTROLIMAGE_X"] = 15
        constants["HUD_CONTROLIMAGE_Y"] = 16
        constants["HUD_CONTROLIMAGE_Z"] = 17
        constants["HUD_CONTROLIMAGE_STARTPAUSE"] = 18
        constants["HUD_ITEM_ON"] = 0
        constants["HUD_ITEM_OFF"] = 1
        constants["HUD_ITEM_FLASH"] = 2
        constants["INTRO"] = 0
        constants["MAIN_MUSIC"] = 1
        constants["OUTRO"] = 2
        constants["FILENAME"] = 3
        constants["ONCE"] = 1
        constants["LOOPED"] = 0
        constants["flag"] = 0
        constants["TYPE_WFRONTIER"] = 1
        constants["TYPE_XYLVANIAN"] = 2
        constants["TYPE_TUNDRAN"] = 32
        constants["TYPE_SOLAR"] = 1024
        constants["TYPE_UNDERWORLD"] = 2048
        constants["TYPE_NEUTRAL"] = 4096
        constants["TYPE_GVEHICLE"] = 64
        constants["TYPE_AIRCRAFT"] = 128
        constants["TYPE_INFANTRY"] = 256
        constants["TYPE_PICKUP"] = 1048576
        constants["TYPE_ALL"] = 65535
        constants["GTYPE_STRATOFORTRESS"] = 1
        constants["GTYPE_BOMBER"] = 2
        constants["GTYPE_TRANSPORT"] = 4
        constants["GTYPE_GUNSHIP"] = 8
        constants["GTYPE_FIGHTER"] = 16
        constants["GTYPE_BATTLESTATION"] = 32
        constants["GTYPE_ANTI_AIR"] = 64
        constants["GTYPE_ARTILLARY"] = 128
        constants["GTYPE_HEAVY_TANK"] = 256
        constants["GTYPE_LIGHT_TANK"] = 512
        constants["GTYPE_HEAVY_TRANSPORT"] = 1024
        constants["GTYPE_LIGHT_TRANSPORT"] = 2048
        constants["GTYPE_RECON"] = 4096
        constants["GTYPE_SHOTGUN"] = 8192
        constants["GTYPE_VET_ANTI_AIR"] = 16384
        constants["GTYPE_GRENADE"] = 32768
        constants["GTYPE_FLAMER"] = 65536
        constants["GTYPE_VET_ANTI_ARMOUR"] = 131072
        constants["GTYPE_VET_HMG"] = 262144
        constants["GTYPE_GRUNT"] = 524288
        constants["GTYPE_ALL"] = 16777215
        constants["LAND"] = 1
        constants["SOUND"] = 1
        constants["VISUAL"] = 2
        constants["GRADE"] = 0
        constants["NONE"] = 0
        constants["C"] = 1
        constants["B"] = 2
        constants["A"] = 3
        constants["S"] = 4

        return constants

    def set_constants_bw2(self):
        constants = {}
        constants["ID_NONE"] = 0
        constants["PAUSESCR_LTRIGGER"] = 1
        constants["PAUSESCR_RTRIGGER"] = 2
        constants["PAUSESCR_ZBUTTON"] = 3
        constants["PAUSESCR_LSTICK"] = 4
        constants["PAUSESCR_DPAD"] = 5
        constants["PAUSESCR_CSTICK"] = 6
        constants["PAUSESCR_XBUTTON"] = 7
        constants["PAUSESCR_YBUTTON"] = 8
        constants["PAUSESCR_ABUTTON"] = 9
        constants["PAUSESCR_BBUTTON"] = 10
        constants["TRANSFER_BYZFROMTARGET"] = 1
        constants["TRANSFER_BYZFROMCMDBAR"] = 2
        constants["TRANSFER_BYDEATH"] = 3
        constants["TRANSFER_BYMAP"] = 4
        constants["TRANSFER_BYVEHICLE"] = 5
        constants["TRANSFER_NO"] = 6
        constants["MSGSTYLE_FRIENDLY"] = 1
        constants["MSGSTYLE_UNFRIENDLY"] = 0
        constants["MISSIONOVER_LOSE"] = 0
        constants["MISSIONOVER_PLAYER1_WINS"] = 1
        constants["MISSIONOVER_PLAYER2_WINS"] = 2
        constants["MISSIONOVER_BOTH_WIN"] = 3
        constants["AI_ATTACK_STYLE"] = 0
        constants["ATTACKSTYLE_DEFENSIVE"] = 0
        constants["ATTACKSTYLE_AGGRESSIVE"] = 1
        constants["AI_MOVE_STYLE"] = 1
        constants["MOVESTYLE_RESPOND_TO_ATTACK"] = 0
        constants["MOVESTYLE_ATTACK_ON_SIGHT"] = 1
        constants["AI_DODGE"] = 2
        constants["DODGE_ALLOWED"] = 1
        constants["DODGE_NOT_ALLOWED"] = 0
        constants["ORDER_NORMAL"] = 0
        constants["ORDER_FORCED"] = 1
        constants["FORMATION_DISALLOWED"] = 0
        constants["FORMATION_ALLOWED"] = 1
        constants["ACTIVE"] = 1
        constants["INACTIVE"] = 0
        constants["DONT_ADJUST_WEAPON"] = 0
        constants["ADJUST_WEAPON"] = 1
        constants["ACTION_STATE_ATTACK"] = 4
        constants["ACTION_STATE_ATTACK_MELEE"] = 5
        constants["ACTION_STATE_DYING"] = 6
        constants["ACTION_STATE_EMPTY_VEHICLE"] = 7
        constants["ACTION_STATE_ENTERING_VEHICLE"] = 8
        constants["ACTION_STATE_FOLLOWING"] = 9
        constants["ACTION_STATE_FOLLOWING_PLAYER"] = 10
        constants["ERROR! - ACTION_STATE_IN_FORMATION"] = 11
        constants["ACTION_STATE_GOTO_COVERPOINT"] = 13
        constants["ACTION_STATE_IN_COVERPOINT"] = 12
        constants["ACTION_STATE_GUARD"] = 2
        constants["ACTION_STATE_WAIT"] = 1
        constants["ACTION_STATE_IN_CAPTUREPOINT"] = 16
        constants["ACTION_STATE_GOING_TO_CAPTUREPOINT"] = 17
        constants["ACTION_STATE_IN_UNIT_CARRIER"] = 18
        constants["ACTION_STATE_JUMPING"] = 19
        constants["ACTION_STATE_MOVING_TO_AREA"] = 20
        constants["ACTION_STATE_SLIDE"] = 21
        constants["ACTION_STATE_STUNNED"] = 22
        constants["ACTION_STATE_PLAYER_IN_UNIT_CARRIER"] = 23
        constants["ACTION_STATE_PLAYER_IS_TROOP"] = 24
        constants["ACTION_STATE_RESOLVE_AVOID"] = 27
        constants["ACTION_STATE_CELEBRATING"] = 28
        constants["ACTION_STATE_LAMENTING"] = 29
        constants["ACTION_STATE_ZOMBIE"] = 30
        constants["ACTION_STATE_MELEE_HIT"] = 33
        constants["ACTION_STATE_MELEE_RECOIL"] = 34
        constants["ACTION_STATE_MELEE_ROLL"] = 35
        constants["ACTION_STATE_MELEE_STRIKE"] = 36
        constants["ACTION_STATE_PLAYER_MELEE"] = 37
        constants["ACTION_STATE_PLAYER_MELEE_BLOCK"] = 38
        constants["ACTION_STATE_PLAYER_MELEE_STRIKE"] = 39
        constants["ACTION_STATE_BRACED"] = 40
        constants["ACTION_STATE_COWERING"] = 41
        constants["MOVEMENT_STATE_AIRBORNE"] = 1
        constants["MOVEMENT_STATE_FLAILING"] = 2
        constants["MOVEMENT_STATE_SWIMMING"] = 3
        constants["MOVEMENT_STATE_ON_GROUND"] = 4
        constants["MOVEMENT_STATE_SAILING"] = 5
        constants["MOVEMENT_STATE_BEACHED"] = 6
        constants["OBJECTIVE_MARKER_DATA_VISIBLE"] = 0
        constants["OBJECTIVE_MARKER_DATA_ATTACHED_TO"] = 1
        constants["OBJECTIVE_MARKER_DATA_POSITION"] = 2
        constants["OBJECTIVE_DATA_TEXT"] = 0
        constants["OBJECTIVE_DATA_VISIBLE"] = 1
        constants["OBJECTIVE_DATA_STATE"] = 2
        constants["OBJECTIVE_DATA_COLOUR"] = 3
        constants["TYPE"] = 0
        constants["GTYPE"] = 1
        constants["CONTROL_PRESSED_THIS_LEVEL"] = 0
        constants["CONTROL_JUST_PRESSED"] = 1
        constants["CONTROL_HELD"] = 2
        constants["CONTROL_JUST_RELEASED"] = 3
        constants["CONTROL_ACCELERATE"] = 0
        constants["CONTROL_BRAKE"] = 1
        constants["CONTROL_STEER_LEFT"] = 2
        constants["CONTROL_STEER_RIGHT"] = 3
        constants["CONTROL_TURRET_UP"] = 4
        constants["CONTROL_TURRET_DOWN"] = 5
        constants["CONTROL_TURRET_LEFT"] = 6
        constants["CONTROL_TURRET_RIGHT"] = 7
        constants["CONTROL_FLY_UP"] = 9
        constants["CONTROL_FLY_DOWN"] = 10
        constants["CONTROL_FLYUP_MODIFIER"] = 11
        constants["CONTROL_WALK_FORWARD"] = 18
        constants["CONTROL_WALK_BACK"] = 19
        constants["CONTROL_TURN_LEFT"] = 20
        constants["CONTROL_TURN_RIGHT"] = 21
        constants["CONTROL_STRAFE_LEFT"] = 22
        constants["CONTROL_STRAFE_RIGHT"] = 23
        constants["CONTROL_LOOK_UP"] = 24
        constants["CONTROL_LOOK_DOWN"] = 25
        constants["CONTROL_NEXT_UNIT_TYPE"] = 31
        constants["CONTROL_NEXT_UNIT_TYPE_ALT"] = 32
        constants["CONTROL_PREV_UNIT_TYPE"] = 33
        constants["CONTROL_NEXT_UNIT"] = 38
        constants["CONTROL_PREV_UNIT"] = 39
        constants["CONTROL_TRANSFER"] = 43
        constants["CONTROL_HUD_TRANSFER"] = 44
        constants["CONTROL_MAP_TRANSFER"] = 108
        constants["CONTROL_CALL"] = 45
        constants["CONTROL_SEND"] = 46
        constants["CONTROL_DISMISS"] = 47
        constants["CONTROL_LOCAL_CALL"] = 49
        constants["CONTROL_FIRE"] = 50
        constants["CONTROL_STRIKE"] = 51
        constants["CONTROL_BLOCK"] = 52
        constants["CONTROL_JUMP"] = 53
        constants["CONTROL_ROLL"] = 55
        constants["CONTROL_180"] = 26
        constants["CONTROL_LOOK_MODIFIER"] = 59
        constants["CONTROL_STRAFE_MODIFIIER"] = 60
        constants["CONTROL_STRAFELOCK_MODIFIER"] = 61
        constants["CONTROL_LOAD_VEHICLE"] = 62
        constants["CONTROL_UNLOAD_VEHICLE"] = 63
        constants["CONTROL_GLOBAL_TOGGLE"] = 64
        constants["CONTROL_GLOBAL_LOOK_MODIFIER"] = 65
        constants["CONTROL_GLOBAL_LOCK_MODIFIER"] = 66
        constants["CONTROL_GLOBAL_LOOK_UP"] = 67
        constants["CONTROL_GLOBAL_LOOK_DOWN"] = 68
        constants["CONTROL_GLOBAL_LOOK_LEFT"] = 69
        constants["CONTROL_GLOBAL_LOOK_RIGHT"] = 70
        constants["CONTROL_TOGGLE_MAP"] = 96
        constants["CONTROL_PAUSE"] = 118
        constants["CONTROL_SKIP_CUTSCENE"] = 139
        constants["CONTROL_SKIP_CUTSCENE_ALT"] = 140
        constants["GCONTROL_GLOBAL_SLIDEUP"] = 133
        constants["GCONTROL_GLOBAL_SLIDEDOWN"] = 134
        constants["GCONTROL_PAUSE_SELECT"] = 99
        constants["NORMAL_CONTROL_MODE"] = 0
        constants["ADVANCED_CONTROL_MODE"] = 1
        constants["TOTAL_DEAD_HEALTH"] = 0
        constants["TOTAL_ALIVE_HEALTH"] = 1
        constants["WAIT"] = 1
        constants["NO_WAIT"] = 0
        constants["FADE_IN"] = 0
        constants["FADE_OUT"] = 1
        constants["CAMERA_WAYPOINT"] = 0
        constants["TARGET_WAYPOINT"] = 1
        constants["IMMEDIATE"] = 0
        constants["SMOOTH"] = 1
        constants["ARMY_WF"] = 0
        constants["ARMY_XYLVANIAN"] = 1
        constants["ARMY_TUNDRAN"] = 2
        constants["ARMY_SOLAR"] = 3
        constants["ARMY_UNDERWORLD"] = 4
        constants["ARMY_NEUTRAL"] = 5
        constants["ARMY_ANGLO"] = 6
        constants["CAPTUREPOINTFLAG_RAISING"] = 0
        constants["CAPTUREPOINTFLAG_LOWERING"] = 1
        constants["HUD_PAUSESYSTEM"] = 0
        constants["HUD_COBOX"] = 1
        constants["HUD_TIMER"] = 2
        constants["HUD_COMPASS"] = 3
        constants["HUD_RADAR"] = 4
        constants["HUD_COMMANDBAR"] = 5
        constants["HUD_MESSAGE"] = 6
        constants["HUD_INSTALLATIONS"] = 7
        constants["HUD_INFORMATIONMENU"] = 8
        constants["HUD_PAUSEDIALOG"] = 9
        constants["HUD_NOTIFICATIONS"] = 10
        constants["HUD_FUNCTIONINDICATOR"] = 11
        constants["HUD_RETICULE"] = 12
        constants["HUD_COMMANDSTACK"] = 13
        constants["HUD_STATUSBAR"] = 14
        constants["HUD_STATUSICONS"] = 15
        constants["HUD_PLAYERICON"] = 16
        constants["HUD_CONTROLIMAGE_ALL"] = 17
        constants["HUD_CONTROLIMAGE_DPAD"] = 18
        constants["HUD_CONTROLIMAGE_A"] = 19
        constants["HUD_CONTROLIMAGE_TRIGGER"] = 20
        constants["HUD_CONTROLIMAGE_RETURN"] = 21
        constants["HUD_CONTROLIMAGE_HOME"] = 22
        constants["HUD_CONTROLIMAGE_PAUSE"] = 23
        constants["HUD_CONTROLIMAGE_1"] = 24
        constants["HUD_CONTROLIMAGE_2"] = 25
        constants["HUD_CONTROLIMAGE_ANALOGUE"] = 26
        constants["HUD_CONTROLIMAGE_C"] = 27
        constants["HUD_CONTROLIMAGE_Z"] = 28
        constants["HUD_CONTROLIMAGE_TWIST"] = 29
        constants["HUD_CONTROLIMAGE_FLICK"] = 30
        constants["HUD_CONTROLIMAGE_NUNCHUK_ABOVE"] = 31
        constants["HUD_CONTROLIMAGE_NUNCHUK_FLICK_ABOVE"] = 32
        constants["HUD_CONTROLIMAGE_CONTROL_STICK_ABOVE"] = 33
        constants["HUD_ITEM_ON"] = 0
        constants["HUD_ITEM_OFF"] = 1
        constants["HUD_ITEM_FLASH"] = 2
        constants["HUD_FUNC_INDICATOR_ON"] = 0
        constants["HUD_FUNC_INDICATOR_OFF"] = 1
        constants["HUD_FUNC_INDICATOR_AUTO"] = 2
        constants["HUD_FUNC_INDICATOR_ATTACK"] = 0
        constants["HUD_FUNC_INDICATOR_FOLLOW"] = 1
        constants["HUD_FUNC_INDICATOR_WAIT"] = 2
        constants["HUD_FUNC_INDICATOR_GUARD"] = 3
        constants["HUD_FUNC_INDICATOR_LOAD"] = 4
        constants["HUD_FUNC_INDICATOR_UNLOAD"] = 5
        constants["HUD_FUNC_INDICATOR_CAPTURE"] = 6
        constants["HUD_FUNC_INDICATOR_TRANSFER"] = 7
        constants["HUD_FUNC_INDICATOR_TRANSFER_LOCK_ON"] = 8
        constants["HUD_FUNC_INDICATOR_PAUSE_CONTINUE"] = 9
        constants["HUD_FUNC_INDICATOR_STACK"] = 10
        constants["HUD_FUNC_INDICATOR_NONE"] = -1
        constants["NEW_PRIMARY_OBJECTIVE"] = 1
        constants["NEW_SECONDARY_OBJECTIVE"] = 2
        constants["PRIMARY_OBJECTIVE_COMPLETE"] = 3
        constants["SECONDARY_OBJECTIVE_COMPLETE"] = 4
        constants["INTRO"] = 0
        constants["MAIN_MUSIC"] = 1
        constants["OUTRO"] = 2
        constants["FILENAME"] = 3
        constants["ONCE"] = 1
        constants["LOOPED"] = 0
        constants["PLAYER_ONE"] = 0
        constants["PLAYER_TWO"] = 1
        constants["PLAYER_THREE"] = 2
        constants["PLAYER_FOUR"] = 3
        constants["flag"] = 0
        constants["TYPE_WFRONTIER"] = 1
        constants["TYPE_XYLVANIAN"] = 2
        constants["TYPE_TUNDRAN"] = 32
        constants["TYPE_SOLAR"] = 1024
        constants["TYPE_UNDERWORLD"] = 2048
        constants["TYPE_ANGLO"] = 131072
        constants["TYPE_NEUTRAL"] = 4096
        constants["TYPE_GVEHICLE"] = 64
        constants["TYPE_AIRCRAFT"] = 128
        constants["TYPE_INFANTRY"] = 256
        constants["TYPE_HORSE"] = 8192
        constants["TYPE_PICKUP"] = 1048576
        constants["TYPE_ALL"] = 65535
        constants["GTYPE_STRATOFORTRESS"] = 1
        constants["GTYPE_BOMBER"] = 2
        constants["GTYPE_TRANSPORT"] = 4
        constants["GTYPE_GUNSHIP"] = 8
        constants["GTYPE_FIGHTER"] = 16
        constants["GTYPE_BATTLESTATION"] = 1024
        constants["GTYPE_ANTI_AIR"] = 2048
        constants["GTYPE_ARTILLARY"] = 4096
        constants["GTYPE_HEAVY_TANK"] = 8192
        constants["GTYPE_LIGHT_TANK"] = 16384
        constants["GTYPE_HEAVY_TRANSPORT"] = 32768
        constants["GTYPE_LIGHT_TRANSPORT"] = 65536
        constants["GTYPE_RECON"] = 131072
        constants["GTYPE_SHOTGUN"] = 262144
        constants["GTYPE_VET_ANTI_AIR"] = 524288
        constants["GTYPE_GRENADE"] = 1048576
        constants["GTYPE_FLAMER"] = 2097152
        constants["GTYPE_VET_ANTI_ARMOUR"] = 4194304
        constants["GTYPE_VET_HMG"] = 8388608
        constants["GTYPE_GRUNT"] = 16777216
        constants["GTYPE_BATTLESHIP"] = 64
        constants["GTYPE_FRIGATE"] = 128
        constants["GTYPE_SUBMARINE"] = 256
        constants["GTYPE_GUNBOAT"] = 512
        constants["GTYPE_DREADNAUGHT"] = 32
        constants["GTYPE_ALL"] = -1
        constants["LAND"] = 1
        constants["SOUND"] = 1
        constants["VISUAL"] = 2
        constants["GRADE"] = 0
        constants["NONE"] = 0
        constants["C"] = 1
        constants["B"] = 2
        constants["A"] = 3
        constants["S"] = 4
        constants["eWiiMatchingStatus"] = 0
        constants["Busy"] = 0
        constants["Success"] = 1
        constants["Failure"] = 2
        constants["Connecting"] = 3
        constants["BusyThread"] = 4
        constants["ConnectionProblem"] = 5
        constants["eAddFriendResults"] = 0
        constants["OK"] = 0
        constants["InvalidKey"] = -1
        constants["AlreadyInList"] = -2
        constants["NoRoom"] = -3
        constants["Self"] = -4
        constants["eNameCheckResults"] = 0
        constants["Pending"] = 0
        constants["Allowed"] = 1
        constants["Denied"] = 2
        constants["eRematchStatus"] = 0
        constants["Yes"] = 0
        constants["Pending"] = 1
        constants["No"] = 2
        constants["eModeAction"] = 0
        constants["Wait"] = 1
        constants["Follow"] = 0
        constants["eFieldToggle"] = 0
        constants["Off"] = 0
        constants["On"] = 1
        return constants

    def add_script(self, funcname, funcpath, owners=None):
        with open(funcpath, "r") as f:
            luacode = f.read()
        if funcname not in luacode:
            print(funcpath, "has no code!")
        else:
            if owners is None:
                owners = []
            self.funcs[funcname] = (luacode, owners)

    def add_script_owner(self, funcname, owner):
        self.funcs[funcname][1].append(owner)

    def update_context(self):
        if self.context_dirty:
            self.runtime.execute(self.context)
            self.context_dirty = False

    def debug_out(self, *args):
        values = [str(x) for x in args]
        if self.prepend_routine_name_to_print:
            if self.current_routine is None:
                routine = "MAIN"
            else:
                routine = self.current_routine
            out = routine+": "+" ".join(values)
        else:
            out = " ".join(values)
        print(out)
        self.output_hook(out)

        if self.stop:
            raise RuntimeError("Stopping Lua...")
        time.sleep(0.001)

    def register_reflection(self, value):
        return int(value)

    def end_frame(self):
        self.update_context()
        if self.stop:
            raise RuntimeError("Stopping Lua...")

    # Variable/constant definitions
    def set_context(self, context):
        self.context_dirty = True
        self.context = context

    def setup_coroutine(self):
        self.update_context()

        for func, codeentry in self.funcs.items():
            code, owners = codeentry
            print("Setting up", func)
            self.runtime.execute(code)
            #print("code___")
            #print(code)
            #print("func___")
            #print(func)
            for i, owner in enumerate(owners):
                coroutinename = "CO_{}_{}".format(i, owner)

                self.runtime.execute(f"{coroutinename} = coroutine.create({func})")
                self._coroutines.append((coroutinename, owner, func))

    def coroutine_iteration(self):
        everyone_dead = True
        for coroutinename, owner, func in self._coroutines:
            if coroutinename not in self._coroutine_dead:
                everyone_dead = False
                self.current_routine = "{} ({})".format(func, owner)
                self.runtime.execute(f"result__, error = coroutine.resume({coroutinename}, {owner})")
                if not self.runtime.globals().result__:
                    self._coroutine_dead[coroutinename] = True
                    print(coroutinename,":",func, "stopped")
                    self.runtime.execute(f"print(result__, a)")
        return everyone_dead

    def run(self, owner_id):
        self.update_context()
        self.runtime.execute(self.luacode)
        func = self.runtime.globals()[self.funcname]

        func(owner_id)

    def create_thread(self, owner_id):
        thread = threading.Thread(target=self.run, args=(owner_id, ))
        thread.daemon = True
        return thread

    def coroutine_loop(self):
        timestart = time.time()
        while not self.stop:
            if time.time()-timestart > 10:
                print("still alive...")
                timestart = time.time()
            stop = self.coroutine_iteration()

            if stop:
                self.stop = True

    def create_coroutine_thread(self):
        thread = threading.Thread(target=self.coroutine_loop)
        thread.daemon = True
        return thread


if __name__ == "__main__":
    import time

    def debug_out_hook(msg):
        print(msg)



    sim = LuaSimulator(debug_out_hook, True)
    sim.add_script("C1M1_Kill_Cutscene_End",
                   r"game_lua_scripts\C1_OnPatrol_Level.res_lua\C1M1_Kill_Cutscene_End.lua",
                   [12345])
    sim.add_script("C1M1_Jump", r"game_lua_scripts\C1_OnPatrol_Level.res_lua\C1M1_Jump.lua",
                   [12346])

    sim.set_context("""
    C1M1_Global_Variable = 0
    cutsceneEnd = 1""")
    sim.setup_coroutine()
    thread = sim.create_coroutine_thread()
    thread.start()

    time.sleep(2)
    sim.set_context("C1M1_Global_Variable = 1")
    time.sleep(3)
    sim.set_context("C1M1_Global_Variable = 14")
    time.sleep(10)

    """
    luathread = sim.create_thread(1234)
    luathread.start()
    
    luathread2 = sim.create_thread(12345)
    luathread2.start()
    
    import time
    print("Hello")
    time.sleep(5)
    print("Sleeping")
    sim.set_context("C1M1_Global_Variable = 5")
    print("Var set")
    time.sleep(5)
    sim.set_context("C1M1_Global_Variable = 14")
    time.sleep(1)
    sim.pressed = True"""


