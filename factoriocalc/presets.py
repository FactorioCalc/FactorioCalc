from contextvars import ContextVar,copy_context
from copy import copy
from . import itm, machines as mch
from . import config

__all__ = ('MP_EARLY_GAME', 'MP_LATE_GAME',
           'MP_MAX_PROD', 'MachinePrefs', 'SPEED_BEACON', 'withSettings')

class MachinePrefs(tuple):
    def __new__(cls, *args):
        return tuple.__new__(cls, args)
    def __add__(self, other):
        return tuple.__new__(MachinePrefs, tuple.__add__(self, other))
    def __radd__(self, other):
        if isinstance(other, tuple):
            return tuple.__new__(MachinePrefs, tuple.__add__(other, self))
        else:
            return NotImplemented
    def __mul__(self, num):
        raise NotImplementedError
    __rmul__ = __mul__
    def withSpeedBeacons(self, mapping):
        lst = list(self)
        for i, m in enumerate(lst):
            cls = type(m)
            try:
                numBeacons = mapping[cls]
            except KeyError:
                pass
            else:
                m = copy(m)
                m.beacons = numBeacons * SPEED_BEACON
                lst[i] = m
        return MachinePrefs(*lst)

MP_EARLY_GAME = MachinePrefs(mch.AssemblingMachine1(), mch.StoneFurnance())
 
MP_LATE_GAME = MachinePrefs(mch.AssemblingMachine3(), mch.ElectricFurnace())

MP_MAX_PROD = MachinePrefs(
    mch.AssemblingMachine3(modules=4*[itm.productivity_module_3]),
    mch.ElectricFurnace(modules=2*[itm.productivity_module_3]),
    mch.ChemicalPlant(modules=3*[itm.productivity_module_3]),
    mch.OilRefinery(modules=3*[itm.productivity_module_3]),
    mch.RocketSilo(modules=4*[itm.productivity_module_3]),
    mch.Centrifuge(modules=2*[itm.productivity_module_3]),
)

SPEED_BEACON = mch.Beacon(modules=[itm.speed_module_3, itm.speed_module_3])


def withSettings(settings, fun, *args, **kwargs):
    "helper function to locally set a ContextVar"
    ctx = copy_context()
    return ctx.run(__withSettings, settings, fun, *args, **kwargs)
        

def __withSettings(settings, fun, *args, **kwargs):
    for var, val in settings.items():
        var.set(val)
    return fun(*args, **kwargs)
    
