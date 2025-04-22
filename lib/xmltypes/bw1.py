from lib.BattalionXMLLib import BattalionObject
from lib.bw_types import BWMatrix


class SceneryCluster(BattalionObject):
    mBase: "SceneryClusterBase"
    Seed: int
    Mat: BWMatrix
    SystemFlags: int


class SceneryClusterBase(BattalionObject):
    CollideType: int
    ObjFlags: int
    MaxHealth: int
    MaxUsedTypes: int
    ScnComponentAngle: float
    mSurfaceType: str
    mfGroundLightFactor: float
    mfAlphaFadeDistBias: float
    mbHonourSpacingOverNumber: int
    Element: list[BattalionObject]
    DeadElement: list[BattalionObject]
    MaxSize: float
    MaxLength: float
    MinSep: float
    MaxSep: float
    MinScnComponentSize: float
    MaxScnComponentSize: float
    NumOfElement: list[int]

