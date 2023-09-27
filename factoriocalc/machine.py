from __future__ import annotations
from dataclasses import dataclass,FrozenInstanceError
from collections import defaultdict
from collections.abc import Sequence

from .fracs import frac,div,diva,Inf
from .core import *
from .core import Uniq,_MutableFlows,_toRecipe,InvalidRecipe
from . import itm, rcp

class Category(Uniq):
    def __init__(self, name, members):
        self.name = name
        self.members = members
    def __repr__(self):
        return f'<Category: {self.name}>'

@dataclass(init=False,repr=False)
class _BurnerMixin:
    energyType = 'burner'
    fuel: Item = None

    def __init__(self, *args, fuel = None, **kws):
        from ._helper import asItem
        super().__init__(*args, **kws)
        fuel = asItem(fuel)
        self.fuel = fuel

    def _repr_parts(self, lst):
        lst.append(f'fuel={self.fuel!r}')

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        obj['fuel'] = self.fuel.name if self.fuel else None
        return obj

    def __setattr__(self, prop, val):
        if prop == 'fuel':
            if val is not None and val.fuelCategory != 'chemical':
                raise ValueError(f'invalid item for fuel: {val}')
        super().__setattr__(prop, val)

    def _calc_flows(self, throttle):
        flows = super()._calc_flows(throttle)
        fuelRate = div(self.energyUsage(throttle), self.fuel.fuelValue)
        flows.addFlow(self.fuel, rateIn = fuelRate, adjusted = self.throttle != 1)
        return flows

@dataclass(init=False,repr=False)
class _ElectricMixin:
    energyType = 'electric'

    def _calc_flows(self, throttle):
        flows = super()._calc_flows(throttle)
        flows.addFlow(itm.electricity, rateIn = div(self.energyUsage(throttle), 1_000_000))
        return flows

def _repr_modules_part(prefix, modules, lst):
    if len(modules) > 0:
        tally = {}
        for m in modules:
            tally[m] = tally.get(m, 0) + 1
        lst.append(prefix + '+'.join(f'{tally[m]}*{m!r}' for m in sorted(tally.keys())))

@dataclass(init=False,repr=False)
class _ModulesMixin:
    modules: tuple[Module, ...]
    beacons: list[Beacon]

    def __init__(self, *args, modules = None, beacons = None, beacon = None, **kws):
        super().__init__(*args, **kws)
        self.modules = () if modules is None else modules
        if beacon is None and beacons is None:
            self.beacons = []
        elif beacon is None:
            self.beacons = beacons
        elif beacons is None:
            self.beacons = [beacon]
        else:
            raise ValueError("both 'beacon' and 'beacons' can not be provided at the same time")

    def _repr_parts(self, lst):
        _repr_modules_part('modules=', self.modules, lst)
        if len(self.beacons) > 0:
            lst.append('beacons=' + '+'.join(repr(b) for b in self.beacons))

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        if self.modules:
            obj['modules'] = [m._jsonObj() for m in self.modules]
        if self.beacons:
            obj['beacons'] = [(b.num, b.machine._jsonObj(**kwargs)) for b in self.beacons]
        return obj

    def _checkModules(self, recipe, modules):
        invalid = set()
        for m in modules:
            if m.limitation is None: continue
            if recipe.name in m.limitation: continue
            try:
                if recipe.origRecipe.name in m.limitation: continue
            except AttributeError:
                pass
            invalid.add(m)
        if invalid:
            raise InvalidModulesError(invalid)

    def __setattr__(self, prop, val):
        if prop == 'recipe':
            modules = getattr(self, 'modules', None)
            if modules:
                self._checkModules(val, modules)
        elif prop == 'modules':
            if isinstance(val, Module):
                modules = self.moduleInventorySize * val
            elif val is None:
                modules = []
            else:
                modules = []
                for v in val:
                    if isinstance(v, Sequence):
                        for m in v:
                            modules.append(m)
                    else:
                        modules.append(v)
                if len(modules) > self.moduleInventorySize:
                    raise ValueError(f'too many modules for {self.alias}: {len(modules)} > {self.moduleInventorySize}')
            if self.recipe is not None:
                self._checkModules(self.recipe, modules)
            val = tuple(modules)
        elif prop == 'beacon':
            raise AttributeError
        elif prop == 'beacons':
            if isinstance(val, Mul):
                val = [val]
            beacons = defaultdict(lambda: 0)
            def asBeacon(b):
                if isinstance(b, Beacon):
                    return b
                if isinstance(b, str):
                    return UnresolvedBeacon(b)
                else:
                    raise TypeError('expected Beacon type')
            for v in val:
                if isinstance(v, Mul):
                    num = v.num
                    beacon = asBeacon(v.machine)
                else:
                    num = 1
                    beacon = asBeacon(v)
                beacons[beacon] += num
            val = [Mul(num, beacon) for beacon, num in beacons.items()]
        return super().__setattr__(prop, val)

    def _modulesStr(self):
        def fmt_w_num(num, obj):
            if num == 1:
                return str(obj)
            else:
                return f'{num:g} {obj}'
        modules = defaultdict(lambda: 0)
        for m in self.modules:
            modules[m] += 1
        modulesStr = ', '.join(fmt_w_num(num, m) for m, num in modules.items())
        beaconsStr = ', '.join(str(b) for b in self.beacons)
        if modulesStr and beaconsStr:
            return f'{modulesStr}; {beaconsStr}'
        elif modulesStr:
            return modulesStr
        elif beaconsStr:
            return beaconsStr
        else:
            return ''

    def bonus(self):
        if len(self.modules) == 1 and len(self.beacons) == 0:
            # special case in case we have a FakeModule
            return Bonus(self.modules[0].effect)
        return Bonus(sum([m.effect for m in self.modules],Effect()) + sum([b.num*b.machine.effect() for b in self.beacons],Effect()))

@dataclass(init=False,repr=False)
class Beacon(Machine):
    name = 'beacon'
    width = 3
    height = 3
    moduleInventorySize = Inf
    distributionEffectivity = frac(1,2)
    supplyAreaDistance = 3

    id: str
    modules: tuple[Module, ...]
    _frozen: bool = False

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

    def __init__(self, id = None, *, modules = None, freeze = True, **kws):
        super().__init__(**kws)
        if isinstance(id, (type(None), str)):
            pass
        else:
            modules = id
            id = None
        self.id = id
        self.modules = [] if modules is None else modules
        if freeze:
            self._frozen = True

    def __setattr__(self, prop, val):
        if prop == 'throttle':
            if val != 1:
                raise ValueError('beacons can not be throttled')
        elif self._frozen and prop.find('__') == -1:
            raise FrozenInstanceError()
        if hasattr(self,  'moduleInventorySize') and prop == 'modules':
            if isinstance(val, Module):
                modules = self.moduleInventorySize * val
            else:
                modules = val
                if len(modules) > self.moduleInventorySize:
                    raise ValueError(f'too many modules for {self.alias}: {len(modules)} > {self.moduleInventorySize}')
            val = tuple(modules)
        return super().__setattr__(prop, val)

    def __delattr__(self, prop):
        if self._frozen:
            raise FrozenInstanceError()
        return super().__delattr__(prop, val)

    def _repr_parts(self, lst):
        _repr_modules_part('', self.modules, lst)
    
    def effect(self):
        return sum([m.effect for m in self.modules],Effect()) * self.distributionEffectivity

    def _modulesStr(self):
        modules = defaultdict(lambda: 0)
        for m in self.modules:
            modules[m] += 1
        return ', '.join(str(m) if num == 1 else f'{num:g} {m}' for m, num in modules.items())

class UnresolvedBeacon:
    __slots__ = ('id')
    def __init__(self, id):
        self.id = id

class Boiler(_BurnerMixin,CraftingMachine):
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
        def __init__(self, name, category, origRecipe, inputs, products, byproducts, time, order, cargo):
            super().__init__(name, category, inputs, products, byproducts, time, order)
            object.__setattr__(self, 'origRecipe', origRecipe)
            object.__setattr__(self, 'cargo', cargo)
        
    delay = frac(2420 + 13, 60)

    def _calc_flows(self, throttle):
        recipe = self.recipe
        cargo = recipe.cargo
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


