from dataclasses import dataclass, field


@dataclass
class TelescopeInfo:
    NAME: str = "Unknown"
    DIAMETER: float = 0.0
    CABINET: str = "Unknown"
    MANUFACTURER: str = "Unknown"


@dataclass
class TelescopeConfig:
    CAPABILITIES: int = 0
    MOUNTOPTIONS: str = "Unknown"
    MOUNT: str = "Unknown"


@dataclass
class TelescopeStatus:
    GLOBAL: int = 0


@dataclass
class Telescope:
    READY_STATE: float = 0.0
    MOTION_STATE: float = 0.0
    INFO: TelescopeInfo = field(default_factory=TelescopeInfo)
    CONFIG: TelescopeConfig = field(default_factory=TelescopeConfig)
    STATUS: TelescopeStatus = field(default_factory=TelescopeStatus)


@dataclass
class ObjectInstrumental:
    RA: float = 0.0
    DEC: float = 0.0
    HA: float = 0.0


@dataclass
class ObjectHorizontal:
    ALT: float = 0.0
    AZ: float = 0.0


@dataclass
class ObjectEquatorial:
    EPOCH: str = "Unknown"
    EQUINOX: str = "Unknown"
    RA_PM: float = 0.0
    DEC_PM: float = 0.0
    RA_RATE: float = 0.0
    DEC_RATE: float = 0.0
    RA: float = 0.0
    DEC: float = 0.0
    HA: float = 0.0


@dataclass
class Object:
    INSTRUMENTAL: ObjectInstrumental = field(default_factory=ObjectInstrumental)
    HORIZONTAL: ObjectHorizontal = field(default_factory=ObjectHorizontal)
    EQUATORIAL: ObjectEquatorial = field(default_factory=ObjectEquatorial)


@dataclass
class PointingOffsets:
    HA: float = 0.0
    DEC: float = 0.0
    ALT: float = 0.0
    AZ: float = 0.0


@dataclass
class Pointing:
    OFFSETS: PointingOffsets = field(default_factory=PointingOffsets)
    SLEWTIME: float = 0.0


@dataclass
class PositionLocal:
    SIDEREAL_TIME: float = 0.0
    JD: float = 0.0
    LATITUDE: float = 0.0
    LONGITUDE: float = 0.0
    HEIGHT: float = 0.0


@dataclass
class PositionAxis:
    POWER_STATE: float = 0.0
    ERROR_STATE: str = ""
    MOTION_STATE: int = 0
    REFERENCED: float = 0.0
    REALPOS: float = 0.0
    CURRPOS: float = 0.0
    TARGETPOS: float = 0.0
    CURRSPEED: float = 0.0
    TARGETDISTANCE: float = 0.0
    OFFSET: float = 0.0


@dataclass
class PositionInstrumental:
    HA: PositionAxis = field(default_factory=PositionAxis)
    DEC: PositionAxis = field(default_factory=PositionAxis)
    ALT: PositionAxis = field(default_factory=PositionAxis)
    AZ: PositionAxis = field(default_factory=PositionAxis)
    FOCUS: PositionAxis = field(default_factory=PositionAxis)


@dataclass
class PositionHorizontal:
    ALT: float = 0.0
    AZ: float = 0.0
    DOME: float = 0.0


@dataclass
class PositionEquatorial:
    RA_J2000: float = 0.0
    DEC_J2000: float = 0.0
    HA_J2000: float = 0.0


@dataclass
class Position:
    LOCAL: PositionLocal = field(default_factory=PositionLocal)
    INSTRUMENTAL: PositionInstrumental = field(default_factory=PositionInstrumental)
    HORIZONTAL: PositionHorizontal = field(default_factory=PositionHorizontal)
    EQUATORIAL: PositionEquatorial = field(default_factory=PositionEquatorial)


@dataclass
class Dome:
    REALPOS: float = 0.0
    TARGETPOS: float = 0.0
    ERROR_STATE: int = 0
    READY_STATE: float = 0.0
    MOTION_STATE: float = 0.0
    AZ: float = 0.0


@dataclass
class Cover:
    REALPOS: float = 0.0


@dataclass
class Auxiliary:
    DOME: Dome = field(default_factory=Dome)
    COVER: Cover = field(default_factory=Cover)


@dataclass
class Telemetry:
    TELESCOPE: Telescope = field(default_factory=Telescope)
    OBJECT: Object = field(default_factory=Object)
    POINTING: Pointing = field(default_factory=Pointing)
    POSITION: Position = field(default_factory=Position)
    AUXILIARY: Auxiliary = field(default_factory=Auxiliary)
