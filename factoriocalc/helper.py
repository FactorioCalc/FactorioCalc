from dataclasses import dataclass
from copy import copy

from .contextvars_ import copy_context
from .core import CraftingMachine, Recipe, RecipeComponent, Mul
from . import itm, fracs
from .machine import Beacon

__all__ = ('withSettings','FakeLab','FakeBeacon','useSpeedBeacons', 'useEffectivityBeacons', 'useBeacons')

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
            lst.append(f'energy={effect.consumption*100!r}')
        if effect.pollution != 0:
            lst.append(f'pollution={effect.pollution*100!r}')

    def _fmtModulesStr(self, lst):
        lst.append(str(self.modules[0].effect))

def useSpeedBeacons(machine, beacon, *, num=1, max=fracs.Inf, roundUp=False, stripExisting=True):
    """Add enough speed beacons to reduce the number of machines needed to *num*.

    If *max* is specified use up to that number of beacons.  If more beacons
    are needed, increase the number of machines so that no more than *max*
    beacons are used per machine.

    """
    from .fracs import div,ceil
    if beacon.effect().speed <= 0:
        raise ValueError('provided beacon does not increase speed')
    m = copy(machine.machine)
    m.unbounded = False
    throttle = 1 if m.throttle < 1 else m.throttle
    rate = div(machine.num * throttle * (1 + m.bonus().speed), num)
    if stripExisting:
        m.beacons = []
    speedIncrease = rate - (1 + m._effect().speed)
    numBeacons = div(speedIncrease, beacon.effect().speed)
    if numBeacons <= 0:
        m.throttle = div(rate, 1 + m.bonus().speed)
    elif numBeacons > max:
        n = ceil(div(rate, 1 + m._effect().speed + max*beacon.effect().speed))
        return useSpeedBeacons(machine, beacon, num=n, roundUp=roundUp, stripExisting=stripExisting)
    elif roundUp:
        numBeacons = ceil(numBeacons)
        m.beacons = [*m.beacons, Mul(numBeacons, beacon)]
        m.throttle = div(rate, 1 + m.bonus().speed)
    else:
        m.throttle = 1
        m.beacons = [*m.beacons, Mul(numBeacons, beacon)]
    if num == 1:
        return m
    else:
        return Mul(num, m)

def useEffectivityBeacons(machine, beacon, roundUp=False):
    """Add enough effectivity beacons to reduce the energy consumption to the limit of -80%."""
    from .fracs import frac,div,ceil
    if isinstance(machine, Mul):
        return Mul(machine.num, useEffectivityBeacons(machine.machine, beacon, roundUp))
    if beacon.effect().consumption >= 0:
        raise ValueError('provided beacon does not decrease energy consumption')
    neededReduction = machine.bonus().consumption + frac('0.8')
    numBeacons = div(neededReduction, -beacon.effect().consumption)
    if numBeacons <= 0:
        return machine
    if roundUp:
        numBeacons = ceil(numBeacons)
    machine.beacons = [*machine.beacons, Mul(numBeacons, beacon)]
    return machine

def useBeacons(machine, speedBeacon = None, effectivityBeacon = None, *, roundUp=False, stripExisting=True):
    """Add enough speed beacons to reduce the number of machines needed to one
    and then enough effectivity beacons to bring the energy consumption to the
    limit of -80%."""
    if speedBeacon:
        machine = useSpeedBeacons(machine, speedBeacon, roundUp=roundUp, stripExisting=stripExisting)
    if effectivityBeacon:
        machine = useEffectivityBeacons(machine, effectivityBeacon, roundUp=roundUp)
    return machine
