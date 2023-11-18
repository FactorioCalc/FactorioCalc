from dataclasses import dataclass
from contextvars import copy_context

from .core import CraftingMachine, Recipe, RecipeComponent
from . import itm
from .machine import Beacon

__all__ = ('withSettings','FakeLab','FakeBeacon')

def withSettings(settings, fun, *args, **kwargs):
    "helper function to locally set a ContextVar"
    ctx = copy_context()
    return ctx.run(_withSettings, settings, fun, *args, **kwargs)

def _withSettings(settings, fun, *args, **kwargs):
    for var, val in settings.items():
        var.set(val)
    return fun(*args, **kwargs)

@dataclass(init=False)
class FakeLab(CraftingMachine):
    pass

class FakeBeacon(Beacon):
    moduleInventorySize = 1
    distributionEffectivity = 1

    def __init__(self, speed=0, productivity=0, energy=0, pollution=0):
        from .core import _FakeModule,Effect
        from .fracs import frac
        effect = Effect(speed = frac(speed,100),
                        productivity = frac(productivity,100),
                        consumption = frac(energy,100),
                        pollution = frac(pollution,100))
        super().__init__(modules = [_FakeModule(effect)])

    def _name(self):
        return 'FakeBeacon'

    def _fmtModulesRepr(self, prefix, lst):
        effect = self.modules[0].effect
        if effect.speed != 0:
            lst.append(f'speed={effect.speed*100!r}')
        if effect.productivity != 0:
            lst.append(f'productivity={effect.productivity*100!r}')
        if effect.consumption != 0:
            lst.append(f'speed={effect.consumption*100!r}')
        if effect.pollution != 0:
            lst.append(f'productivity={effect.pollution*100!r}')

    def _fmtModulesStr(self, lst):
        lst.append(str(self.modules[0].effect))

