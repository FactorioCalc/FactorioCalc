"""Base classes for machines in `~factoriocalc.mch`.  Do not use directly."""

from __future__ import annotations
from dataclasses import dataclass,FrozenInstanceError
from collections import defaultdict
from collections.abc import Sequence
from math import sqrt,trunc

from .fracs import frac,div,diva,Inf
from .core import *
from .core import Immutable,_MutableFlows,_toRecipe,InvalidRecipe
from . import itm, rcp, config

class Category(Immutable):
    def __init__(self, name, members):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'members', members)
    def __repr__(self):
        return f'<Category: {self.name}>'

@dataclass(init=False,repr=False)
class BurnerMixin:
    energyType = 'burner'
    fuelCategories = {'chemical'}
    fuel: Item = None

    @classmethod
    def defaultFuel(cls):
        if 'chemical' in cls.fuelCategories:
            fuel = config.defaultFuel.get(None)
            if fuel:
                return fuel
        for fuel in config.gameInfo.get().fuelPreferences:
            if fuel.fuelCategory in cls.fuelCategories:
                return fuel
        raise ValueError('unable to find compatible fuel')

    def __init__(self, *args, fuel = None, **kws):
        from ._helper import asItem
        super().__init__(*args, **kws)
        fuel = asItem(fuel)
        self.fuel = fuel

    def _reprParts(self, lst):
        super()._reprParts(lst)
        lst.append(f'fuel={self.fuel!r}')

    def _keyParts(self, lst):
        super()._keyParts(lst)
        lst.append('fuel', self.fuel)

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        obj['fuel'] = self.fuel.name if self.fuel else None
        return obj

    def __setattr__(self, prop, val):
        if prop == 'fuel':
            if val is not None and val.fuelCategory not in self.fuelCategories:
                raise ValueError(f'invalid item for fuel: {val}')
        super().__setattr__(prop, val)

    def _calc_flows(self, throttle):
        flows = super()._calc_flows(throttle)
        fuelRate = div(self.energyUsage(throttle), self.fuel.fuelValue)
        flows.addFlow(self.fuel, rateIn = fuelRate, adjusted = self.throttle != 1)
        return flows

@dataclass(init=False,repr=False)
class ElectricMixin:
    energyType = 'electric'

    def _calc_flows(self, throttle):
        flows = super()._calc_flows(throttle)
        flows.addFlow(itm.electricity, rateIn = div(self.energyUsage(throttle), 1_000_000))
        return flows

@dataclass(init=False,repr=False)
class _ModulesHelperMixin:
    def _fmtModulesRepr(self, prefix, lst):
        if len(self.modules) > 0:
            tally = {}
            for m in self.modules:
                tally[m] = tally.get(m, 0) + 1
            lst.append(prefix + '+'.join(f'{tally[m]}*{m!r}' for m in sorted(tally.keys())))

    def _fmtModulesStr(self, lst):
        modules = defaultdict(lambda: 0)
        for m in self.modules:
            modules[m] += 1
        if modules:
            lst.append(' + '.join(str(m) if num == 1 else f'{num}x {m}' for m, num in modules.items()))

    def _fixupModules(self, val):
        if isinstance(val, Module):
            modules = self.moduleInventorySize * val
        elif val is None:
            modules = []
        else:
            modules = []
            for m in val:
                if isinstance(m, Sequence):
                    modules += m
                else:
                    modules.append(m)
            if len(modules) > self.moduleInventorySize:
                raise ValueError(f'too many modules for {self.alias}: {len(modules)} > {self.moduleInventorySize}')
        return tuple(modules)

    def _checkModules(self, recipe, modules):
        invalid = set()
        for m in modules:
            if (m.effect.speed != 0 and not recipe.allowedEffects.speed
                  or m.effect.productivity != 0 and not recipe.allowedEffects.productivity
                  or m.effect.consumption != 0 and not recipe.allowedEffects.consumption
                  or m.effect.pollution != 0 and not recipe.allowedEffects.pollution
                  or m.effect.quality != 0 and not recipe.allowedEffects.quality):
                invalid.add(m)
                continue
            if m.limitation is None: continue
            if recipe.name in m.limitation: continue
            try:
                if recipe.origRecipe.name in m.limitation: continue
            except AttributeError:
                pass
            invalid.add(m)
        if invalid:
            raise InvalidModulesError(invalid)

@dataclass(init=False,repr=False)
class ModulesMixin(_ModulesHelperMixin):
    modules: tuple[Module, ...]
    beacons: tuple

    def __init__(self, *args, modules = None, beacons = None, beacon = None, **kws):
        """Set modules and beacons for a machine.

        *modules* can either be a list of modules or a single module to fill
        the machine with the maxium amount of the given module.

        When setting beacons the special string ``counter`` can be used to
        create a `~factoriocalc.FakeBeacon` that will counter the negative
        effects of any modules present.
        """
        super().__init__(*args, **kws)
        self.modules = modules
        if beacon is None and beacons is None:
            beacons = []
        elif beacon is None:
            pass
        elif beacons is None:
            beacons = [beacon]
        else:
            raise ValueError("both 'beacon' and 'beacons' can not be provided at the same time")
        self.beacons = beacons

    def __setattr__(self, prop, val):
        if prop == 'recipe':
            modules = getattr(self, 'modules', None)
            if modules:
                self._checkModules(val, modules)
        elif prop == 'modules':
            modules = self._fixupModules(val)
            if modules and self.recipe is not None:
                self._checkModules(self.recipe, modules)
            val = tuple(sorted(modules))
        elif prop == 'beacon':
            raise AttributeError
        elif prop == 'beacons':
            if isinstance(val, Mul):
                val = [val]
            beacons = defaultdict(lambda: 0)
            def asBeacon(b):
                if isinstance(b, Beacon):
                    return b
                elif b == 'counter':
                    from .helper import FakeBeacon
                    effect = sum((m.effect for m in self.modules), Effect())
                    return FakeBeacon(speed = -100*effect.speed if effect.speed < 0 else 0,
                                      productivity = -100*effect.productivity if effect.productivity < 0 else 0,
                                      energy = -100*effect.consumption if effect.consumption > 0 else 0,
                                      pollution = -100*effect.pollution if effect.pollution > 0 else 0)
                elif isinstance(b, str):
                    return UnresolvedBeacon(b)
                else:
                    raise TypeError('expected Beacon type')
            for v in val:
                if isinstance(v, tuple):
                    num = v[0]
                    if isinstance(v[1], type) or len(v) > 2:
                        beacon = v[1](*v[2:])
                    else:
                        beacon = v[1]
                elif isinstance(v, Mul):
                    num = v.num
                    beacon = asBeacon(v.machine)
                else:
                    num = 1
                    beacon = asBeacon(v)
                beacons[beacon] += num
            val = tuple((num, beacon) for beacon, num in sorted(beacons.items()))
        return super().__setattr__(prop, val)

    def _extraSortKeys(self):
        return (self.modules, self.beacons)

    def _reprParts(self, lst):
        super()._reprParts(lst)
        self._fmtModulesRepr('modules=', lst)
        if len(self.beacons) > 0:
            lst.append('beacons=' + '+'.join(f'{num!r}*{b!r}' for num,b in self.beacons))

    def _strParts(self, lst):
        super()._strParts(lst)
        self._fmtModulesStr(lst)
        if self.beacons:
            lst.append(' + '.join(str(b) if num == 1 else f'{num:.3g}x {b}' for num,b in self.beacons))

    def _keyParts(self, lst):
        super()._keyParts(lst)
        lst.append(('modules', self.modules))
        beacons = defaultdict(lambda: 0)
        for num, b in self.beacons:
            beacons[(b.__class__, tuple(sorted(b.modules)))] += num
        lst.append(('beacons', tuple((num, cls, modules) for (cls, modules), num in sorted(beacons.items()))))

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        if self.modules:
            obj['modules'] = [m._jsonObj() for m in self.modules]
        if self.beacons:
            obj['beacons'] = [(b.num, b.machine._jsonObj(**kwargs)) for b in self.beacons]
        return obj

    def _effect(self):
        if self.gameVersion == '1.1':
            return (sum((m.effect for m in self.modules), Effect())
                    + sum((num*b.effect() for num,b in self.beacons), Effect()))
        else:
            moduleEffect = sum((m.effect for m in self.modules), Effect())
            numBeacons = 0
            beaconEffect = Effect()
            for num, beacon in self.beacons:
                numBeacons += num
                beaconEffect += num*beacon.effect()
            if numBeacons > 0:
                beaconEffect = beaconEffect * frac(1/sqrt(numBeacons),float_conv_method='exact')
            return moduleEffect + beaconEffect
                
    def bonus(self):
        return self._bonus(self._effect())

@dataclass(init=False,repr=False)
class Beacon(_ModulesHelperMixin,Machine):
    name = 'beacon'
    width = 3
    height = 3
    moduleInventorySize = Inf
    distributionEffectivity = frac(1,2)
    supplyAreaDistance = 3

    id: str
    modules: tuple[Module, ...]
    _frozen: bool = False

    def __init__(self, *args, id = None, modules = None, freeze = True, **kws):
        super().__init__(**kws)
        if id is None:
            if len(args) > 0 and isinstance(args[0], str):
                self.id = args[0]
                args = args[1:]
            else:
                self.id = None
        else:
            if len(args) > 0 and isinstance(args[0], str):
                raise TypeError("'id' parameter provided as both a positional and keyword argument")
            self.id = id
        if modules is None:
            if len(args) > 0:
                self.modules = args[0]
                args = args[1:]
            else:
                self.modules = []
        else:
            if len(args) > 0:
                raise TypeError("'modules' parameter provided as both a positional and keyword argument")
            self.modules = modules
        if freeze:
            self._frozen = True
        if len(args) > 0:
            raise TypeError('too many positional arguments provided')

    def __setattr__(self, prop, val):
        if prop == 'throttle':
            if val != 1:
                raise ValueError('beacons can not be throttled')
        elif self._frozen and prop.find('__') == -1:
            raise FrozenInstanceError()
        if prop == 'modules':
            val = self._fixupModules(val)
        return super().__setattr__(prop, val)

    def __delattr__(self, prop):
        if self._frozen:
            raise FrozenInstanceError()
        return super().__delattr__(prop, val)

    def _extraSortKeys(self):
        return (self.modules, self.id, id(self.blueprintInfo))

    def _reprParts(self, lst):
        super()._reprParts(lst)
        if self.id is not None:
            lst.append(repr(self.id))
        self._fmtModulesRepr('', lst)
        if not self._frozen:
            lst.append('frozen=False')

    def _strParts(self, lst):
        super()._strParts(lst)
        if self.id is not None:
            lst.append(repr(self.id))
        self._fmtModulesStr(lst)

    def _keyParts(self, lst):
        super()._keyParts(lst)
        lst.append(('modules', self.modules))

    def __hash__(self):
        if not self._frozen:
            raise ValueError("can't take hash of non-frozen Beacon")
        return hash((self.__class__,
                     self.id,
                     -1 if self.blueprintInfo == {} else id(self.blueprintInfo),
                     *self.modules))

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        obj['modules'] = [m._jsonObj() for m in self.modules]
        return obj

    def effect(self):
        return sum([m.effect for m in self.modules],Effect()) * self.distributionEffectivity

class UnresolvedBeacon:
    __slots__ = ('id')
    def __init__(self, id):
        self.id = id

class Boiler(BurnerMixin,CraftingMachine):
    name = "boiler"
    baseEnergyUsage = 1_800_000
    energyDrain = 0
    pollution = 30

    def __init__(self, **kws):
        super().__init__(**kws)
        self.recipe = rcp.steam

class AssemblingMachine(CraftingMachine):
    pass

class Furnace(CraftingMachine):
    pass

@dataclass(init=False, repr=False)
class RocketSilo(CraftingMachine):
    class Recipe(Recipe):
        __slots__ = ('origRecipe', 'cargo')
        def __init__(self, name, category, origRecipe, inputs, products, byproducts, time, allowedEffects, maxProductivity, order, cargo):
            super().__init__(name, None, 0, [None], category, inputs, products, byproducts, time,
                             allowedEffects, maxProductivity, order)
            object.__setattr__(self, 'origRecipe', origRecipe)
            object.__setattr__(self, 'cargo', cargo)
            self._otherQualities[0] = self

    delay = frac(2420 + 13, 60)

    def _calc_flows(self, throttle):
        recipe = self.recipe
        cargo = getattr(recipe, 'cargo', None)
        if cargo is None:
            return super()._calc_flows(throttle)
        b = self.bonus()
        time = diva(recipe.time, self.craftingSpeed, 1 + b.speed, 1 + b.productivity) + self.delay
        flows = _MutableFlows()
        for rc in self.recipe.inputs:
            rate = div(rc.num, time * (1 + b.productivity))
            flows.addFlow(rc.item, rateIn = throttle*rate, adjusted = throttle != 1)
        for rc in self.recipe.outputs:
            rate = div(rc.num, time)
            flows.addFlow(rc.item, rateOut = throttle*rate, adjusted = throttle != 1)
        flows.addFlow(cargo.item,
                      rateIn = div(throttle*cargo.num, time),
                      adjusted = throttle != 1)
        return flows

    @classmethod
    def defaultProduct(cls):
        from . import config
        rocketSiloDefaultProduct = config.gameInfo.get().rocketSiloDefaultProduct
        for c in cls.__mro__:
            if c in rocketSiloDefaultProduct:
                return rocketSiloDefaultProduct[c]
        return None


