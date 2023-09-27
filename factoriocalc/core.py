from __future__ import annotations
from dataclasses import dataclass,field
from collections import defaultdict
from typing import NamedTuple
from itertools import chain
# from numbers import Rational
from collections.abc import Sequence,Iterator,Mapping
from enum import Enum
from .ordenum import OrdEnum
from .fracs import Frac,frac,Inf,div,diva,isfinite,isnan,isinf
from copy import copy
import sys
from . import itm, rcp

__all__ = ('Default',
           'Ingredient', 'Item', 'Fluid', 'Research', 'Electricity', 'Module', 'FakeModule',
           'MachineBase', 'Machine', 'CraftingMachine', 'Mul', 'Group',
           'Flow', 'OneWayFlow', 'FlowsState', 'Flows', 'SimpleFlows', 'NetFlows', 'EffectBase', 'Effect', 'Bonus',
           'Recipe', 'RecipeComponent', 'IGNORE', 'InvalidModulesError',
           'maxInputs', 'MachinePrefs',
           )

class Uniq:
    def __copy__(self):
        return self
    def __deepcopy__(self,memo):
        return self
    def __eq__(self, other):
        # we want to compare by identity but also give other.__eq__ a chance
        # to be called if defined, so return NotImplemented...
        return NotImplemented 
    def __ne__(self, other):
        return NotImplemented
    def __hash__(self):
        return object.__hash__(self)

class Immutable:
    def __setattr__(self, name, value):
        raise TypeError
    def __delattr__(self, name):
        raise TypeError

class DefaultType(Uniq):
    __slots__ = ()
    def __repr__(self):
        return 'Default'
    def __new__(cls):
        return DEFAULT
    def __copy__(self):
        return self
    def __deepcopy__(self, _):
        return self

Default = object.__new__(DefaultType)

class _SortByOrderKey:
    def __lt__(self, other):
        if not isinstance(other, Ingredient):
            return NotImplemented
        return self.order < other.order
    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)
    def __gt__(self, other):
        if not isinstance(other, Ingredient):
            return NotImplemented
        return self.order > other.order
    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

class RecipesForItems(NamedTuple):
    products: list
    byproducts: list
    inputs: list
    
class Ingredient(_SortByOrderKey,Uniq,Immutable):
    """Base class for all items."""
    __slots__ = ('name', 'order')
    def __init__(self, name, order):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'order', order)
    @property
    def alias(self):
        from .config import gameInfo
        return gameInfo.get().aliases.get(self.name, self.name)
    @property
    def descr(self):
        from .config import gameInfo
        return gameInfo.get().translatedNames.get(f'itm {self.name}', self.name)
    def __str__(self):
        return self.alias
    def __repr__(self):
        alias = self.alias
        if getattr(itm, alias, None) is self:
            return 'itm.'+alias
        else:
            return f'<{type(self).__name__}: {alias}>'
    def __matmul__(self, rate):
        return OneWayFlow(self, _rate(rate))
    def recipes(self):
        from .config import gameInfo
        gi = gameInfo.get()
        products, byproducts = [], []
        for rcp in gi.recipesThatMake[self]:
            for rc in rcp.products:
                if self == rc.item:
                    products.append(rcp)
            for rc in rcp.byproducts:
                if self == rc.item:
                    byproducts.append(rcp)
        return RecipesForItems(products, byproducts,  gi.recipesThatUse[self])

def _rate(r):
    if isinstance(r, str):
        if r.endswith('/s'):
            return frac(r[:-2])
        elif r.endswith('/m'):
            return frac(r[:-2],60)
        elif r.endswith('/h'):
            return frac(r[:-2],360)
    return frac(r)

class Item(Ingredient):
    __slots__ = ('stackSize', 'fuelValue', 'fuelCategory')
    def __init__(self, name, order, stackSize, fuelValue = 0, fuelCategory = ''):
        super().__init__(name, order)
        object.__setattr__(self, 'stackSize', stackSize)
        object.__setattr__(self, 'fuelValue', fuelValue)
        object.__setattr__(self, 'fuelCategory', fuelCategory)

class Fluid(Ingredient):
    __slots__ = ()
    pass

class Research(Ingredient):
    __slots__ = ()
    pass

class Electricity(Ingredient):
    __slots__ = ()
    pass

class Module(Item):
    __slots__ = ('effect','limitation')
    def __init__(self,name,order,stackSize,effect,limitation=None,limitationBlacklist=None):
        super().__init__(name,order,stackSize)
        object.__setattr__(self, 'effect', effect)
        object.__setattr__(self, 'limitation', limitation)
    def _jsonObj(self):
        return self.name
    def __mul__(self, num):
        return num*[self]
    __rmul__ = __mul__

class FakeModule(Module):
    def __init__(self, speed=0, productivity=0, consumption=0, pollution=0):
        super().__init__('fake-module', '', 0, Bonus(speed, productivity, consumption, pollution))
    def __repr__(self):
        return 'FakeModule({})'.format(', '.join(f'{k}={getattr(self.effect,k)!r}' for k in self.effect._fields if getattr(self.effect,k) != 0))
    def __str__(self):
        return f'module: {self.effect}'
    def _jsonObj(self):
        from .jsonconv import _jsonObj
        return {k: _jsonObj(getattr(self.effect, k)) for k in self.effect._fields if getattr(self.effect,k) != 0}
    def __eq__(self, other):
        return type(self) == type(other) and self.effect == other.effect
    def __ne__(self, other):
        return type(self) != type(other) or  self.effect != other.effect
    def __hash__(self, other):
        raise NotImplementedError

@dataclass
class MachineBase:
    def _flows(self, throttle, _includeInner):
        raise NotImplementedError

    def flows(self, throttle = None, includeInner = True):
        return self._flows(throttle, includeInner)

    def flow(self, item, throttle = None):
        return self.flows(throttle).flow(item)

    def __mul__(self, fac):
        return Mul(self,fac)

    def __rmul__(self, fac):
        return Mul(self,fac)

    def __add__(self, other):
        return Group(self,other)

    def print(self, out = None, prefix = '', suffix = '\n'):
        if out is None:
            out = sys.stdout
        out.write(str(self))

    def pprint(self, out = None, prefix = '', suffix = '\n'):
        if out is None:
            out = sys.stdout
        out.write(repr(self))

    def __new__(cls, *args, **kwargs):
        if getattr(cls, 'abstract', None) == cls:
            raise TypeError(f"can't create {cls.__name__}")
        return object.__new__(cls)

class MachineMeta(type):
    @property
    def descr(self):
        from .config import gameInfo
        return gameInfo.get().translatedNames.get(f'mch {self.name}', self.name)
    @property
    def alias(self):
        return self.__name__

@dataclass(init=False,repr=False)
class Machine(MachineBase, metaclass=MachineMeta):
    """A entity that used directly or indirectly to produce something."""
    throttle: Rational
    unbounded: bool = False
    blueprintInfo: dict = None
    __flows1: Flows = field(default = None, compare = False)
    __flows: Flows = field(default = None, compare = False)

    def __init__(self, *, throttle = 1):
        self.throttle = throttle

    @property
    def machine(self):
        return self

    @property 
    def num(self): 
        return 1

    @property
    def recipe(self):
        return None

    @property
    def descr(self):
        return self.__class__.descr

    @property
    def alias(self):
        return self.__class__.alias

    def resetThrottle(self):
        self.throttle = 1

    def __invert__(self):
        # fixme: should likely make a copy ...
        self.unbounded = True
        return self

    def __setattr__(self, prop, val):
        if prop == 'throttle':
            val = frac(val)
            if val < 0:
                raise ValueError('throttle must be positive')
        if prop != '_Machine__flows' and  prop != '_Machine__flows1' and prop != 'blueprintInfo':
            self.__flows = None
            if prop != 'throttle':
                self.__flows1 = None
        super().__setattr__(prop, val)

    def _flatten(self, lst, factor):
        if factor == 1:
            lst.append(self)
        else:
            lst.append(Mul(self, factor))

    def summarize(self):
        return self

    def __repr__(self):
        name = type(self).__name__
        parts = []
        if self.recipe:
            parts.append(repr(self.recipe))
        if self.throttle != 1:
            parts.append(f'throttle={self.throttle!r}')
        self._repr_parts(parts)
        if self.blueprintInfo is not None:
            parts.append(f'blueprintInfo=...')
        prefix = '~' if self.unbounded else ''
        return '{}mch.{}({})'.format(prefix, name, ', '.join(parts))

    def _repr_parts(self, lst):
        pass

    def __str__(self):
        name = type(self).__name__
        parts = []
        if self.recipe:
            parts.append(self.recipe.alias)
        if self.throttle != 1:
            parts.append(f'@{self.throttle:g}')
        prefix = '~' if self.unbounded else ''
        modulesStr = self._modulesStr()
        if modulesStr:
            parts.append(modulesStr)
        if parts:
            return '{}{}({})'.format(prefix, name, '; '.join(parts))
        else:
            return name

    def _modulesStr(self):
        return ''

    def _jsonObj(self, objs, **kwargs):
        from .jsonconv import _jsonObj
        if id(self) in objs:
            return objs[id(self)]
        obj = {}
        obj['name'] = self.name
        obj['id'] = objs.add(id(self))
        if self.throttle and self.throttle != 1:
            obj['throttle'] = _jsonObj(self.throttle)
        if self.recipe is not None:
            obj['recipe'] = self.recipe._jsonObj(**kwargs)
        return obj

    def flatten(self):
        return self

    @property
    def inputs(self):
        return {flow.item: None for flow in self.flows(1) if flow.rate() < 0 and flow.item is not itm.electricity}

    @property
    def outputs(self):
        return {flow.item: None for flow in self.flows(1) if flow.rate() > 0}

    @property
    def products(self):
        return {flow.item: None for flow in self.flows(1).products()}

    @property
    def byproducts(self):
        return {flow.item: None for flow in self.flows(1).byproducts()}

    def _calc_flows(self, throttle):
        return _MutableFlows()

    def _flows(self, throttle, _includeInner):
        if throttle is None:
            throttle = self.throttle
        else:
            throttle = frac(throttle)
        if throttle == 1 and self.__flows1 is not None:
            return self.__flows1
        if throttle == self.throttle and self.__flows is not None:
            return self.__flows
        res = self._calc_flows(throttle)
        if isinstance(res, _MutableFlows):
            res = SimpleFlows(res)
        if throttle == 1:
            self.__flows1 = res
        if throttle == self.throttle:
            self.__flows = res
        return res

    def bonus(self) -> Bonus:
        return Bonus()

    def energyUsage(self, throttle):
        if throttle is None:
            throttle = self.throttle
        return self.energyDrain + throttle * self.baseEnergyUsage * (1 + self.bonus().consumption)

def _toRecipe(val):
    if val is None or isinstance(val, Recipe):
        return val
    if isinstance(val, Rcp):
        return val.inst()
    if isinstance(val, str):
        from .config import gameInfo
        return gameInfo.get().rcpByName[str].inst()
    raise TypeError(f'unexpected type for recipe: {type(val)}')

@dataclass(init=False, repr=False)
class CraftingMachine(Machine):
    """An entity that produce something."""
    recipe: Recipe = None
    name = 'crafting-machine'
    craftingSpeed = 1
    baseEnergyUsage = 0
    energyDrain = 0
    pollution = 0
    craftingCategories = set()

    def __init__(self, recipe = None, **kws):
        super().__init__(**kws)
        self.recipe = recipe

    def __setattr__(self, prop, val):
        if prop == 'recipe':
            val = _toRecipe(val)
        super().__setattr__(prop, val)

    def _calc_flows(self, throttle):
        flows = _MutableFlows()
        if self.recipe is None: return flows
        inOut = defaultdict(lambda: [RecipeComponent(0,0,None), RecipeComponent(0,0,None)])
        for rc in self.recipe.inputs:
            inOut[rc.item][0] = rc
        for rc in self.recipe.outputs:
            inOut[rc.item][1] = rc
        b = self.bonus()
        time = diva(self.recipe.time, self.craftingSpeed, 1 + b.speed)
        for item, (in_, out_) in inOut.items():
            rateIn = div(in_.num, time)
            bonusOut = out_.product() * b.productivity
            rateOut = div(out_.num + bonusOut, time)
            flows.addFlow(item, rateIn = throttle*rateIn, rateOut = throttle*rateOut, adjusted = throttle != 1)
        flows._byproducts = tuple(rc.item for rc in self.recipe.byproducts)
        return flows

@dataclass(repr=False)
class Mul(MachineBase):
    """A group of identical machines.

    num must be positive but fractional values are permitted.

    """
    num: Rational
    machine: MachineBase

    def __init__(self, *args):
        if isinstance(args[0], MachineBase):
            self.machine = args[0]
            self.num = args[1]
        else:
            self.num = args[0]
            self.machine = args[1]

    def __setattr__(self, prop, val):
        if prop == 'num':
            val = frac(val)
            if val < 0:
                raise ValueError('Mul.num must be positive')
        super().__setattr__(prop, val)

    def __str__(self):
        return f'{self.num} {self.machine}'

    def __repr__(self):
        return repr(self.num) + '*' + repr(self.machine)

    def _jsonObj(self, objs, **kwargs):
        from .jsonconv import _jsonObj
        if id(self) in objs:
            return objs[id(self)]
        obj = {}
        obj['name'] = '<mul>'
        obj['id'] = objs.add(id(self))
        obj['num'] = _jsonObj(self.num)
        obj['machine'] = self.machine._jsonObj(objs = objs, **kwargs)
        return obj

    @property
    def inputs(self):
        return self.machine.inputs

    @property
    def outputs(self):
        return self.machine.outputs

    @property
    def products(self):
        return self.machine.products

    @property
    def byproducts(self):
        return self.machine.byproducts
    

    @property
    def recipe(self):
        return self.machine.recipe

    def resetThrottle(self):
        self.machine.resetThrottle()

    def _flows(self, throttle, _includeInner):
        return self.machine._flows(throttle, _includeInner) * self.num

    def _flatten(self, lst, num):
        self.machine._flatten(lst, num * self.num)

    def flatten(self):
        lst = []
        self._flatten(lst, 1)
        if isinstance(self.machine,Group) or len(lst) > 1:
            return Group(lst)
        else:
            return lst[0]

    def summarize(self):
        return Mul(self.num, self.machine.summarize())
        

@dataclass(repr=False,init=False)
class Group(Sequence,MachineBase):
    """A group of machines."""
    machines: List[MachineBase]
    def __init__(self, *machines):
        from .machine import Beacon, UnresolvedBeacon
        
        super().__init__()
        if len(machines) == 1 and isinstance(machines[0], Sequence) and not isinstance(machines[0], Group):
            self.machines = list(machines[0])
        elif len(machines) == 1 and isinstance(machines[0], Iterator):
            self.machines = list(machines[0])
        else:
            self.machines = list(machines)
        beaconMap = {}
        unresolved = []
        for m in self.machines:
            if isinstance(m.machine, Beacon) and m.machine.id is not None:
                beaconMap[b.id] = b
                continue
            try:
                beacons = m.machine.beacons
            except AttributeError:
                continue
            haveUnresolved = False
            for b in beacons:
                if isinstance(b.machine, Beacon) and b.machine.id is not None:
                    beaconMap[b.machine.id] = b.machine
                elif isinstance(b.machine, UnresolvedBeacon):
                    haveUnresolved = True
            if haveUnresolved:
                unresolved.append(m)
        for m in unresolved:
            for i, b in enumerate(m.machine.beacons):
                if isinstance(b.machine, UnresolvedBeacon):
                    m.machine.beacons[i].machine = beaconMap[b.machine.id]

    @property
    def machine(self):
        return self

    @property 
    def num(self): 
        return 1
    
    def _flatten(self, lst, num):
        for m in self.machines:
            m._flatten(lst, num)

    def flatten(self):
        lst = []
        self._flatten(lst, 1)
        return Group(lst)

    def __iter__(self):
        return iter(self.machines)

    def __getitem__(self, idx):
        return self.machines[idx]

    def __len__(self):
        return len(self.machines)

    def __repr__(self):
        return 'Group(' + ', '.join(repr(m) for m in self) + ')'

    def __str__(self):
        res = '('
        res += ' + '.join(str(m) for m in self.machines)
        res += ')'
        return res

    def _jsonObj(self, objs, **kwargs):
        from .jsonconv import _jsonObj
        if id(self) in objs:
            return objs[id(self)]
        obj = {}
        obj['name'] = '<group>'
        obj['id'] = objs.add(id(self))
        obj['machines'] = [m._jsonObj(objs = objs, **kwargs) for m in self.machines]
        return obj

    def __add__(self, other):
        return Group(*self,other)

    def print(self, out = None, prefix = '', suffix = '\n'):
        if out is None:
            out = sys.stdout
        out.write('(')
        prefix += '  '
        if len(self.machines) > 0:
            self.machines[0].print(out, prefix, '')
        for m in self.machines[1:]:
            out.write(f'\n')
            out.write(prefix)
            out.write('+ ')
            m.print(out, prefix, '')
        out.write(')')
        out.write(suffix)

    def pprint(self, out = None, prefix = '', suffix = '\n'):
        if out is None:
            out = sys.stdout
        prefix += '      '
        out.write('Group(')
        if len(self.machines) > 0:
            self.machines[0].pprint(out, prefix, '')
        for m in self.machines[1:]:
            out.write(f',\n')
            out.write(prefix)
            m.pprint(out, prefix, '')
        out.write(')')
        out.write(suffix)

    def summary(self, out = sys.stdout, *, prefix = '',
                includeSolvedBoxFlows = True, includeMachineFlows = True, includeBoxDetails = True,
                flowsItemFilter = None):
        self._summary(out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter)

    def summarize(self):
        from .box import BoxBase
        class Tally:
            __slots__ = ('num', 'rateIn', 'rateOut', 'consumption', 'pollution', 'throttle')
            def __init__(self):
                self.num = 0
                self.rateIn = 0
                self.rateOut = 0
                self.consumption = 0
                self.pollution = 0
                self.throttle = 0
        tally = defaultdict(Tally)
        for m in self:
            num = 1
            if isinstance(m, Mul):
                num = m.num
                m = m.machine
            if isinstance(m, BoxBase):
                if id(m) in tally:
                    tally[id(m)].num += num
                else:
                    tally[id(m)] = Mul(num, m.summarize())
            elif isinstance(m, Group):
                if id(m) in tally:
                    tally[id(m)].num += num
                else:
                    tally[id(m)] = Mul(num, m.summarize())
            else:
                recipe = m.recipe
                fuel = m.fuel if hasattr(m, 'fuel') else None
                x = tally[(type(m), recipe, fuel)]
                x.num += num
                x.throttle += num*m.throttle
                if recipe is None: continue
                # We can't just average the speed and productivity bonus, so,
                # instead we average the rateIn and rateOut for abstract items
                # in which the machine's recipe produces and consumes exactly
                # one of.  We them derive the required speed and productivity
                # bonus from those numbers.
                b = m.bonus()
                t = diva(m.recipe.time, m.craftingSpeed, 1 + b.speed, 1 + b.productivity) + getattr(m, 'delay', 0)
                x.rateIn += diva(1, t, 1 + b.productivity)
                x.rateOut += div(1, t)
                x.consumption += b.consumption
                x.pollution += b.pollution
        grp = []
        for k, v in tally.items():
            if type(k) is int:
                if v.num == 1:
                    grp.append(v.machine)
                else:
                    grp.append(v)
            else:
                cls, recipe, fuel = k
                num = v.num
                m = cls()
                if v.throttle != 1:
                    m.throttle = div(v.throttle, num)
                if recipe:
                    m.recipe = recipe
                if fuel:
                    m.fuel = fuel
                # Given:
                #   time = recipeTime / craftingSpeed / (1 + speed) / (1 + productivity) + delay
                #   rateIn = 1 / time / (1 + productivity)
                #   rateOut = 1 / time
                # To derive the required speed and productivity we 
                # need to solve for speed and productivity
                if v.rateIn > 0 and v.rateOut > 0:
                    craftingSpeed, delay = m.craftingSpeed, getattr(m, 'delay', 0)
                    rateIn, rateOut = div(v.rateIn, num), div(v.rateOut, num)
                    speed = div(craftingSpeed - craftingSpeed*delay*rateOut - rateIn*recipe.time, craftingSpeed*(delay*rateOut - 1))
                    productivity = div(rateOut - rateIn, rateIn)
                    consumption = div(v.consumption, num)
                    pollution = div(v.pollution, num)
                    if speed != 0 or productivity != 0 or consumption != 0 or pollution != 0:
                        m.modules = [FakeModule(speed, productivity, consumption, pollution)]
                if num > 1:
                    m = Mul(m, num)
                grp.append(m)
        return Group(grp)
 
    def _summary(self, out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter):
        from .box import BoxBase, Box
        byRecipe = defaultdict(list)
        grpNum = 0
        for m in self.machines:
            if isinstance(m.machine, Group) or isinstance(m.machine, BoxBase):
                byRecipe[grpNum] = m
                grpNum += 1
            elif m.machine.recipe:
                byRecipe[m.machine.recipe].append(m)
            else:
                byRecipe[type(m.machine)].append(m)
        prevIsGroup = False
        for key, val in byRecipe.items():
            orig = val
            namePrefix = ''
            if isinstance(val, Mul):
                namePrefix = f'{val.num:.3g}x '
                val = val.machine
            if isinstance(val, Group):
                out.write(prefix)
                out.write(f'{namePrefix}Group: \n')
                val._summary(out, prefix + '    ', includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter)
                prevIsGroup = True
            elif isinstance(val, BoxBase):
                if includeBoxDetails and isinstance(val, Box):
                    val._summary(out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter, namePrefix)
                else:
                    out.write(f'{prefix}{namePrefix}{val}')
                    if includeSolvedBoxFlows or includeMachineFlows:
                        flows = orig.flows()
                        if flows.state.ok():
                            out.write(':\n')
                            out.write('{}         {}\n'.format(prefix, flows.filter(items = flowsItemFilter)))
                        else:
                            out.write('\n')
                    else:
                        out.write('\n')
            elif isinstance(key, Recipe):
                if (prevIsGroup and includeMachineFlows):
                    out.write('{}\n'.format(prefix))
                num = 0
                byMachine = {}
                for m in val:
                    num += m.num
                    x = byMachine.setdefault(type(m.machine), {'num': 0, 'bonus': Bonus(), 'throttle': 0})
                    x['num'] += m.num
                    x['bonus'] += m.num*m.machine.bonus()
                    x['throttle'] += m.num*m.machine.throttle
                g = Group(val)
                unbounded = num == 1 and len(val) == 1 and getattr(val[0].machine, 'unbounded', False)
                if unbounded:
                    out.write('{}({: >3.3g}x){}: '.format(prefix, val[0].machine.throttle, key.alias))
                else:
                    out.write('{}{: >4.3g}x {}: '.format(prefix, num, key.alias))
                pos = 0
                for k, v in byMachine.items():
                    if v['num'] ==  0:
                        continue
                    if pos > 0:
                        out.write('; ')
                    if v['num'] != num:
                        out.write('{}x '.format(v['num']))
                    out.write(k.alias)
                    throttle = 1 if unbounded else div(v['throttle'], v['num'])
                    if throttle != 1:
                        out.write('  @{:.6g}'.format(throttle))
                    if throttle > 1:
                        out.write('!')
                    if x['bonus']:
                        out.write('  {}'.format(x['bonus'] / v['num']))
                    pos += 1
                if includeMachineFlows:
                    out.write(':\n')
                    out.write('{}         {}\n'.format(prefix, g.flows().filter(items = flowsItemFilter)))
                else:
                    out.write('\n')
                prevIsGroup = False
            else:
                num = 0
                for m in val:
                    num += m.num
                out.write('{}{: >4.3g}x {}\n'.format(prefix, num, key.__name__))
                prevIsGroup = False

    def _flows(self, throttle, _includeInner):
        res = _MutableFlows()
        state = FlowsState.OK
        for m in self.flatten():
            flows = m._flows(throttle, _includeInner)
            for flow in flows:
                res.merge(flow)
            if not flows.state.ok():
                state = FlowsState.INVALID
        res.reorder()
        res.state = state
        return NetFlows(res)

    def setThrottle(self, throttle, filter = lambda _: True):
        for m in self.flatten():
            if filter(m.machine):
                m.machine.throttle = throttle

    def adjThrottle(self, factor, filter = lambda _: True):
        seen = set()
        for m in self.flatten():
            m = m.machine
            if filter(m) and id(m) not in seen:
                m.machine.throttle *= factor
                seen.add(id(m))

    def resetThrottle(self):
        for m in self.flatten():
            m.resetThrottle()

    def find(self, *,
             input = None, output = None, recipe = None, machine = None,
             inputs = (), outputs = (), recipes = (), machines = ()):
        if input is not None:
            if inputs:
                raise ValueError('both input and inputs can not be defined')
            inputs = {input}
        else:
            inputs = set(inputs)
        if output is not None:
            if outputs:
                raise ValueError('both output and outputs can not be defined')
            outputs = {output}
        else:
            outputs = set(outputs)
        if recipe is not None:
            if recipes:
                raise ValueError('both recipe and recipes can not be defined')
            recipes = {recipe}
        else:
            recipes = set(recipes)
        if machine is not None:
            if machines:
                raise ValueError('both machine and machines can not be defined')
            machines = {machine}
        else:
            machines = tuple(machines)
        res = []
        for m in self.machines:
            if not inputs.isdisjoint(m.inputs):
                res.append(m)
            elif not outputs.isdisjoint(m.outputs):
                res.append(m)
            elif m.recipe in recipes:
                res.append(m)
            elif machines and isinstance(m.machine, machines):
                res.append(m)
        return Group(res)

def _unitForItem(item):
    from . import config
    for cls, unit in config.displayUnit.get():
        if cls is None or isinstance(item, cls):
            return unit
    raise ValueError

def _fmt_rate(item, rate, unit):
    if unit is None:
        from .units import UNIT_SECONDS
        unit = UNIT_SECONDS
    if type(rate) is int or isfinite(rate):
        if callable(unit.conv):
            rate = unit.conv(item, rate)
        else:
            rate = rate * unit.conv
        return '{:,.6g}{}{}'.format(rate,unit.sep,unit.abbr)
    elif isnan(rate):
        return 'Unknown'
    elif isinf(rate):
        if rate < 0:
            return 'Negative'
        else:
            return 'Positive'
    else:
        raise ValueError

class OneWayFlow(NamedTuple):
    item: Ingredient
    rate: Rational = 0
    annotations: str = ''
    def __str__(self):
        return '{}{} {}'.format(self.item, self.annotations, _fmt_rate(self.item, self.rate, _unitForItem(self.item)))
    def __neg__(self):
        return OneWayFlow(self.item, -self.rate, self.annotations)
    def __repr__(self):
        return '<{}>'.format(str(self))
    def asFlow(self):
        if self.annotations != '':
            raise ValueError("can't convert OneWayFlow with annotations to Flow'")
        if self.rate <= 0:
            return Flow(self.item, rateIn = -self.rate)
        else:
            return Flow(self.item, rateOut = self.rate)

class Flow(NamedTuple):
    item: Ingredient
    rateOut: Rational = 0
    rateIn: Rational = 0
    rateSelf: Rational = 0
    adjusted: bool = False
    underflow: bool = False
    annotation: str = None
    def __bool__(self):
        return self.rateOut == 0 and self.rateIn == 0
    def rate(self):
        return self.rateOut - self.rateIn
    def annotations(self):
        s = ''
        if self.adjusted:
            s += '~'
        if self.annotation is None:
            if self.rateOut > self.rateIn and self.rateIn > 0:
                s += '*'
            elif self.rateOut < self.rateIn and self.rateOut - self.rateSelf > 0:
                s += '!'
        else:
            s += self.annotation
        return s
    def netFlow(self):
        return OneWayFlow(self.item, self.rate(), self.annotations())
    def __str__(self):
        unit = _unitForItem(self.item)
        s = '{}{} '.format(self.item, self.annotations())
        s += '{}'.format(_fmt_rate(self.item, self.rate(), unit))
        if self.rateIn > 0 and self.rateOut > 0:
            s += ' ({}'.format(_fmt_rate(self.item, self.rateOut - self.rateSelf, unit))
            s += ' - {}'.format(_fmt_rate(self.item, self.rateIn - self.rateSelf, unit))
            if self.rateSelf > 0:
                s += ', {} self'.format(_fmt_rate(self.item, self.rateSelf, unit))
            s += ')'
        return s
    def print(self, out = None, prefix = ''):
        out.write(prefix)
        out.write(str(self))
        out.write('\n')
    def __repr__(self):
        return '<{}>'.format(self.__str__())
    def __mul__(self, factor):
        if factor == 1:
            return self
        else:
            return self.copy(factor = factor)
    __rmul__ = __mul__
    def copy(self, *, factor = 1, adjusted = None, underflow = None, annotation = None):
        return Flow(self.item,
                    self.rateOut * factor,
                    self.rateIn * factor,
                    self.rateSelf * factor,
                    adjusted if adjusted is not None else self.adjusted,
                    underflow if underflow is not None else self.underflow,
                    annotation if annotation is not None else self.annotation)

class FlowsState(OrdEnum):
    OK = 0
    UNDERFLOW = 1
    UNSOLVED = 2
    INVALID = 3
    def ok(self):
        return self.value < FlowsState.UNSOLVED.value

class Flows:
    __slots__ = ('byItem', '_byproducts', 'state')
    # self.byItem and self._byproducts and self.state are expected to be defined
    def flow(self, item):
        if isinstance(item, Ingredient):
            return self.byItem.get(item,Flow(item))
        else:
            raise KeyError(item)
    def rate(self, item):
        return self.flow(item).rate()
    def __iter__(self):
        return iter(self.byItem.values())
    def _showFlow(self, flow):
        return True
    def __repr__(self):
        flowsStr = ' '.join(repr(flow) for flow in self.byItem.values() if self._showFlow(flow))
        if self.state:
            return '<{} {}>'.format(self.state.name, flowsStr)
        else:
            return '<{}>'.format(flowsStr)
    def __str__(self):
        flowsStr = ', '.join(str(flow) for flow in self.byItem.values() if self._showFlow(flow))
        if self.state:
            return '({}) {}'.format(self.state.name, flowsStr)
        else:
            return flowsStr
    def items(self):
        return self.byItem.keys()
    def print(self, out = None, prefix = '  '):
        if out is None:
            out = sys.stdout
        for flow in self.byItem.values():
            if not self._showFlow(flow): continue
            flow.print(out, prefix)
        if self.state:
            out.write(f'{prefix}{self.state.name}\n')
    __getitem__ = flow
    def __len__(self):
        return len(self.byItem)
    def products(self):
        return [flow for flow in self.outputs() if flow.item not in self._byproducts]
    def byproducts(self):
        return [flow for flow in self.outputs() if flow.item in self._byproducts]
    def mul(self,num,markAsAdjusted=False): 
        flows = _MutableFlows(initFrom = self)
        for f in self:
            flows.merge(f,num,markAsAdjusted)
        if not isinstance(self, _MutableFlows):
            flows = self.__class__(flows)
        return flows
    def filter(self, *, items):
        if items is None:
            return self
        flows = _MutableFlows(initFrom = self)
        for item in items:
            try:
                flows.byItem[item] = self.byItem[item]
            except KeyError:
                pass
        if not isinstance(self, _MutableFlows):
            flows = self.__class__(flows)
        return flows
    def __add__(self, obj):
        flows = _MutableFlows(initFrom = self)
        if isinstance(obj, Flow):
            flows.merge(obj)
        elif isinstance(obj, OneWayFlow):
            flows.merge(obj.asFlow())
        elif isinstance(obj, Flows):
            for f in obj:
                flows.merge(f)
        else:
            return NotImplemented
        for f in self:
            flows.merge(f)
        flows.reorder()
        if not isinstance(self, _MutableFlows):
            flows = self.__class__(flows)
        return flows
    __radd__ = __add__
    def __mul__(self,num):
        return self.mul(num)
    def __rmul__(self,num):
        return self.mul(num)
    def __eq__(self, other):
        if not isinstance(other, Flows):
            return False
        return self.byItem == other.byItem and self._byproducts == other._byproducts and self.state == other.state

def _mergeFlows(f, *args):
    tally = {}
    for flows in args:
        print('.')
        for flow in flows:
            tally[flow.item] = f(tally.get(flow.item, 0), flow.rate())
    res = _MutableFlows()
    for item, rate in tally.items():
        if rate != 0:
            res.byItem[item] = OneWayFlow(item, rate)
    return SimpleFlows(res)

def maxInputs(*args):
    return _mergeFlows(min, *args)

class _MutableFlows(Flows):
    __slots__ = ('byItem', '_byproducts', 'state')
    def __init__(self, *, initFrom = None):
        self.byItem = {}
        if initFrom is not None:
            self._byproducts = initFrom._byproducts
            self.state = initFrom.state
        else:
            self._byproducts = ()
            self.state = FlowsState.OK
    def _merge(self, flow, num, markAsAdjusted, singleFacility):
        singleFacility = False # fixme: hack
        if flow.item in self.byItem:
            f = self.byItem[flow.item]
            rateOut = f.rateOut + flow.rateOut*num
            rateIn = f.rateIn + flow.rateIn*num
            if singleFacility:
                rateSelf = rateOut if rateOut < rateIn and rateOut > 0 else 0
            else:
                rateSelf = f.rateSelf + flow.rateSelf*num
            adjusted = markAsAdjusted or f.adjusted or flow.adjusted
            underflow = f.underflow or flow.underflow
            self.byItem[flow.item] = Flow(flow.item,rateOut,rateIn,rateSelf,adjusted,underflow)
        else:
            self.byItem[flow.item] = num * flow
    def addFlow(self, item, **kws):
        self._merge(Flow(item, **kws), 1, False, True)
    def merge(self,flow,num=1,markAsAdjusted = False):
        self._merge(flow, num, markAsAdjusted, False)
    def reorder(self):
        def sort(flows):
            return sorted(flows, key=lambda flow: (flow.item.order))
        flows = chain(
            sort(flow for flow in self if flow.rateOut != 0 and flow.rateIn == 0),
            sort(flow for flow in self if flow.rateOut != 0 and flow.rateIn != 0),
            sort(flow for flow in self if flow.rateOut == 0 and flow.rateIn == 0),
            sort(flow for flow in self if flow.rateOut == 0 and flow.rateIn != 0),
        )
        self.byItem = {}
        for f in flows:
            self.byItem[f.item] = f

class SimpleFlows(Flows):
    def __init__(self, _mutableFlows = None):
        if _mutableFlows is None:
            _mutableFlows = _MutableFlows()
        self.byItem = _mutableFlows.byItem
        self._byproducts = _mutableFlows._byproducts
        self.state = _mutableFlows.state
    def output(self, item):
        return self.flow(item).rateOut
    def input(self, item):
        return self.flow(item).rateIn
    def outputs(self):
        return [OneWayFlow(flow.item, flow.rateOut) for flow in self if flow.rateOut > 0]
    def inputs(self):
        return [OneWayFlow(flow.item, flow.rateIn) for flow in self if flow.rateIn > 0]

class NetFlows(Flows):
   def __init__(self, _mutableFlows = None):
       if _mutableFlows is None:
           _mutableFlows = _MutableFlows()
       self.byItem = _mutableFlows.byItem
       self._byproducts = _mutableFlows._byproducts
       self.state = _mutableFlows.state
   def output(self, item):
       rate = self.flow(item).rate()
       if rate <= 0: return 0
       return rate
   def input(self, item):
       rate = self.flow(item).rate()
       if rate >= 0: return 0
       return -rate
   def outputs(self):
       return [flow.netFlow() for flow in self if flow.rate() > 0]
   def inputs(self):
       return [-flow.netFlow() for flow in self if flow.rate() < 0]
   def internal(self):
       return [f for f in self if f.rateIn > 0 and f.rateOut > 0]
   def surplus(self):
       return [f for f in self if '*' in f.annotations()]
   def lackof(self):
       return [f for f in self if '!' in f.annotations()]

class EffectBase(NamedTuple):
    speed: Rational = 0
    productivity: Rational = 0
    consumption: Rational = 0 # energy used 
    pollution: Rational = 0

    def __str__(self):
        parts = []
        if self.speed != 0:
            parts.append('{:+.0%} speed'.format(self.speed))
        if self.productivity != 0:
            parts.append('{:+.0%} prod.'.format(self.productivity))
        if self.consumption != 0: 
            parts.append('{:+.0%} energy'.format(self.consumption))
        if self.pollution != 0:
            parts.append('{:+.0%} pollution'.format(self.pollution))
        return ' '.join(parts)

    def __repr__(self):
        return f'<{type(self).__name__}: {str(self)}>'

    def __bool__(self):
        return self.speed != 0 or self.productivity != 0 or self.consumption != 0 or self.pollution != 0

    def __add__(self, other):
        if type(self) is not type(other):
            raise TypeError
        return EffectBase.__new__(type(self),
                                  self.speed + other.speed,
                                  self.productivity + other.productivity,
                                  self.consumption + other.consumption,
                                  self.pollution + other.pollution)

    def __mul__(self, n):
        return EffectBase.__new__(type(self),
                                  self.speed*n,
                                  self.productivity*n,
                                  self.consumption*n,
                                  self.pollution*n)

    def __rmul__(self, n):
        return EffectBase.__new__(type(self),
                                  self.speed*n,
                                  self.productivity*n,
                                  self.consumption*n,
                                  self.pollution*n)

    def __truediv__(self, n):
        return EffectBase.__new__(type(self),
                                  div(self.speed, n),
                                  div(self.productivity, n),
                                  div(self.consumption, n),
                                  div(self.pollution, n))

class Effect(EffectBase):
    pass

class Bonus(EffectBase):
    def __new__(cls, *args, **kwargs):
        if len(args) <= 1 and len(kwargs) == 0:
            if len(args) == 0:
                return EffectBase.__new__(cls)
            other = args[0]
            if type(other) is Bonus:
                return other
            elif type(other) is Effect:
                speed = other.speed if other.speed > frac(-4, 5) else frac(-4, 5)
                consumption =  other.consumption if other.consumption > frac(-4, 5) else frac(-4, 5)
                pollution = other.pollution if other.pollution > frac(-4, 5) else frac(-4, 5)
                return EffectBase.__new__(cls, speed, other.productivity, consumption, pollution)
        else:
            return EffectBase.__new__(cls, *args, **kwargs)

class RecipeComponent(NamedTuple):
    num: Rational
    catalyst: Rational
    item: Item
    def product(self):
        product = self.num-self.catalyst
        return 0 if product <= 0 else product
    def __str__(self):
        if self.catalyst == 0:
            return f'{self.num:g} {self.item}'.format(float(self.num), self.item)
        else:
            return f'{self.num:g} ({self.product():g}) {self.item}'.format(float(self.num), self.item)


class Recipe(_SortByOrderKey,Uniq,Immutable):
    """A recipe to produce something.

    """
    __slots__ = ('name', 'category', 'inputs', 'products', 'byproducts', 'time', 'order')
    def __init__(self, name, category, inputs, products, byproducts, time, order):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'category', category)
        object.__setattr__(self, 'inputs', tuple(inputs))
        object.__setattr__(self, 'products', tuple(products))
        object.__setattr__(self, 'byproducts', tuple(byproducts))
        object.__setattr__(self, 'time', time)
        object.__setattr__(self, 'order', order)
    @property
    def alias(self):
        from .config import gameInfo
        return gameInfo.get().aliases.get(self.name, self.name)
    @property
    def descr(self):
        from .config import gameInfo
        return gameInfo.get().translatedNames.get(f'rcp {self.name}', self.name)
    @property
    def enabled(self):
        from .config import gameInfo
        return self.name not in gameInfo.get().disabledRecipes
    @property
    def origRecipe(self):
        return self
    @property
    def outputs(self):
        return self.products + self.byproducts
    def __eq__(self, other):
        return object.__eq__(self, other)
    def __ne__(self, other):
        return object.__ne__(self, other)
    def __hash__(self):
        return hash(self.name)
    def __str__(self):
        return self.alias
    def __repr__(self):
        alias = self.alias
        if getattr(rcp, alias, None) is self:
            return 'rcp.' + alias
        else:
            return f'<{type(self).__name__}: {alias}>'
    def str(self):
        return '{} <={:n}s= {}'.format(
            ', '.join(map(str, self.outputs)),
            float(self.time),
            ', '.join(map(str, self.inputs)),
        )
    def _jsonObj(self, customRecipes, **kwards):
        from .jsonconv import _jsonObj
        from .config import gameInfo
        if gameInfo.get().rcpByName.get(self.name, None) is self:
            return self.name
        elif customRecipes.get(self.name, None) is self:
            return f'{self.name} custom'
        if self.name in customRecipes:
            raise ValueError(f'recipe name conflict: {self.name}')
        customRecipes[self.name] = self
        return f'{self.name} custom'
    def eqv(self, other):
        """Returns true if other is equivalent to self and not just the same object."""
        return (type(self) == type(other)
                and self.name == other.name
                and self.category == other.category
                and self.inputs == other.inputs
                and self.products == other.products
                and self.byproducts == other.byproducts
                and self.time == other.time
                and self.order == other.order)
    def produce(self, machinePrefs = Default, fuel = None, machine = None,
                modules = (), beacons = (), beacon = Default, rate = None):
        if beacon is None:
            beacons = []
        elif beacon is not Default:
            beacons = [beacon]
        from collections import deque
        from . import config, data
        if machinePrefs is Default:
            machinePrefs = config.machinePrefs.get()
        candidates = deque()
        for m in machinePrefs:
            if (((machine is None and self.category in m.craftingCategories)
                 or (machine is not None and type(m) == machine))
                and (m.recipe is None or m.recipe.name == self.name)):
                candidates.append(copy(m))
        if not candidates:
            if machine is None:
                machines = self.category.members
                machines = [m for m in machines if not hasattr(m, 'fixedRecipe') or m.fixedRecipe is self.origRecipe]
                if len(machines) == 1:
                    candidates.append(machines[0]())
                elif len(machines) == 0:
                    raise ValueError(f'No matching machine for "{self.alias}".')
                else:
                    candidatesStr = ' '.join(c.alias for c in machines)
                    raise ValueError(f'Multiple matching machines for "{self.alias}": {candidatesStr}')
            else:
                 candidates.append(machine())
        maybe = None
        while candidates:
            m = candidates.popleft()
            try:
                m.recipe = self
                break
            except InvalidModulesError:
                maybe = m
            except InvalidRecipe:
                pass
        else:
            if maybe:
                try:
                    m.recipe = self
                except InvalidModulesError as err:
                    m.modules = tuple(m for m in m.modules if m not in err.invalid)
                    m.recipe = self
            else:
                raise ValueError(f'No matching machine for "{self.alias}". [2]')
        if modules is not Default:
            m.modules = modules
        if beacons is not Default:
            m.beacons = beacons
        if hasattr(m, 'fuel'):
            if fuel is Default:
                m.fuel = config.defaultFuel.get()
            else:
                m.fuel = fuel
        if rate is not None:
            if len(self.products) != 1:
                raise ValueError('can not specify rate for "{self.alias}" as it produces more than one product')
            m = Mul(div(frac(rate), m.flow(self.products[0].item).rate()), m)
        return m
    def __call__(self, machinePrefs = Default, fuel = Default, machine = None,
                 modules = Default, beacon = Default, beacons = Default, rate = None):
        return self.produce(machinePrefs = machinePrefs, fuel = fuel, machine = machine,
                            modules = modules, beacons = beacons, beacon = beacon, rate = rate)

class InvalidModulesError(ValueError):
    def __init__(self, m):
        self.invalid = m
    pass

class InvalidRecipe(ValueError):
    pass

IGNORE = -100

class MachinePrefs(tuple):
    def __repr__(self):
        return 'MachinePrefs' + super().__repr__()
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
        from .preset import SPEED_BEACON
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

