from __future__ import annotations
from dataclasses import dataclass
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

@dataclass(init=False,repr=False)
class _ModulesMixin:
    modules: tuple[Module, ...]
    beacons: list[Beacon]

    def __init__(self, *args, modules = None, beacons = None, **kws):
        super().__init__(*args, **kws)
        self.modules = () if modules is None else modules
        self.beacons = [] if beacons is None else beacons

    def _repr_parts(self, lst):
        if len(self.modules) > 0:
            lst.append(f'modules={self.modules!r}')
        if len(self.beacons) > 0:
            lst.append(f'beacons={self.beacons!r}')

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        if self.modules:
            obj['modules'] = [m._jsonObj() for m in self.modules]
        if self.beacons:
            obj['beacons'] = [b._jsonObj(**kwargs) for b in self.beacons]
        return obj

    def _checkModules(self, recipe, modules):
        invalid = set()
        for m in modules:
            if m.limitation is not None and recipe.name not in m.limitation:
                invalid.add(m)
        if invalid:
            raise InvalidModulesError(invalid)

    def __setattr__(self, prop, val):
        if prop == 'recipe':
            modules = getattr(self, 'modules', None)
            if modules:
                self._checkModules(val, modules)
        elif prop == 'modules' and self.recipe is not None:
            modules = []
            for v in val:
                if isinstance(v, Sequence):
                    for m in v:
                        modules.append(m)
                else:
                    modules.append(v)
            self._checkModules(self.recipe, modules)
            val = tuple(modules)
        elif prop == 'beacons' and isinstance(val, Mul):
            val = val.num*[val.machine]
        elif prop == 'beacons':
            if isinstance(val, Beacon):
                val = [val]
            else:
                beacons = []
                for v in val:
                    if isinstance(v, Mul):
                        beacons += v.num*[v.machine]
                    else:
                        beacons.append(v)
                val = beacons
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
        beacons = defaultdict(lambda: 0)
        for b in self.beacons:
            beacons[b] += 1
        beaconsStr = ', '.join(fmt_w_num(num, b) for b, num in beacons.items())
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
        return Bonus(sum([m.effect for m in self.modules],Effect()) + sum([b.effect() for b in self.beacons],Effect()))

@dataclass(init=False,repr=False)
class Beacon(Machine):
    name = 'beacon'
    width = 3
    height = 3
    moduleInventorySize = Inf
    distributionEffectivity = frac(1,2)
    supplyAreaDistance = 3

    modules: list[Module]

    def __hash__(self):
        return hash((self.__class__, *self.modules))

    def _jsonObj(self, **kwargs):
        obj = super()._jsonObj(**kwargs)
        if type(obj) is int:
            return obj
        obj['modules'] = [m._jsonObj() for m in self.modules]
        return obj

    def __init__(self, modules = None, **kws):
        super().__init__(**kws)
        self.modules = [] if modules is None else modules

    def _repr_parts(self, lst):
        if len(self.modules) > 0:
            lst.append(f'{self.modules!r}')
    
    def effect(self):
        return sum([m.effect for m in self.modules],Effect()) * self.distributionEffectivity

    def _modulesStr(self):
        modules = defaultdict(lambda: 0)
        for m in self.modules:
            modules[m] += 1
        return ', '.join(str(m) if num == 1 else f'{num:g} {m}' for m, num in modules.items())

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


