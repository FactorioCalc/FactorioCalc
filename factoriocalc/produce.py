from typing import Any
from collections import deque
from collections.abc import Mapping
import math
from copy import copy
from dataclasses import dataclass,field
from warnings import warn
import operator

from . import itm,rcp,config
from .fracs import frac, div
from .core import *
from .box import *
from .solver import LinearEqSystem,Solver,SolveRes
from .data import *
from .data import craftingHints

__all__ = ('box', 'produce', 'merge', 'union',
           'ProduceResult', 'MultipleChoiceError', 'SolveFailedError', 'NonUniqueSolutionError')

def _box(args, minSolveRes, kwargs):
    if minSolveRes is None:
        minSolveRes = SolveRes.MULTI
    b = Box(*args, **kwargs)
    res = b.solve()
    if res > minSolveRes:
        if res.ok():
            raise NonUniqueSolutionError(_BoxFailedInfo(b, res))
        else:
            raise SolveFailedError(_BoxFailedInfo(b, res))
    return b

def box(*args, minSolveRes = None, **kwargs):
    """Create a `Box` and then solve it.

    Will raise `NonUniqueSolutionError` if the solver returned a result larger
    than *minSolveRes* (default `SolveRes.MULTI`) or `SolveFailedError` if the
    solve failed.

    All other parameters are passed to `Box`.

    """
    return _box(args, minSolveRes, kwargs)

def blackBox(*args, minSolveRes = None, **kwargs):
    """Create a `BlackBox` and then solve it.

    See `box`.
    """
    b = _box(args, minSolveRes, kwargs)
    return BlackBox(b)

@dataclass
class _BoxFailedInfo:
    factory: Box = None
    solveRes: SolveRes = SolveRes.UNSOLVED


def produce(outputs, using = (), *,
            stopAt = (), fuel = None, constraints = (),
            name = None, abortOnMultiChoice = True,
            recursive = True, roundUp = False, minSolveRes = SolveRes.MULTI, solve = True):
    """Create a factory to produce outputs.

    It works in two stages the first is select appropriate recipes and
    machines to produce the given outputs and the second is to determine the
    nunber of machines needed using the same solver used by the solve method
    in Box.

    The paramaters are:

    *outputs*
      sequence or mapping of outputs, rates are per second and can be
      `None` if inputs are well specified.

    *using*
      an optional mixed type sequence used to guide the selection of
      what recipes to use and when to stop.

      If an item is given it will try and select recipes that use that item
      and stop once it is used.  If paired with a rate (using the '@'
      operator) then will use that item at the given rate.

      If a recipe is given the solver will attempt to use that recipe if
      possible and keep going.  If more than one recipe is specified for a
      given output both will be used and the solver step will attemt to
      determine the best combination.

      If a machine instance is given that machine configuration will be used
      when applicable.  If a machine instance recipe is not None that
      machine configuration will only be used for the given recipe.  If a
      matching machine is not found, `produce` will use
      `config.machinePrefs`.

    *fuel*
      item to use as fuel when applicable, if None will use
      `config.defaultFuel`

    *recursive*
      |nbsp|

    *roundUp*
      Round up multiple of machines to integer values and adjust the
      throttle to compensate.

    *minSolveRes*
      The minimum acceptable solver result.  Defaults to
      `SolveRes.MULTI`.

    The result is a dataclass with the following fields:

    factory
      the resulting factory as an instance of Box

    solveRes
      the result of the second stage solver

    extraOutputs
      list of auxiliary outputs; if these outputs are not consumed
      somehow than the entiry factory is likely to grind to a halt

    extraInputs
      list of inputs used not specified in `using` if no inputs are
      specified this list will be empty

    unusedInputs
      list of unused inputs

    May also throw the following errors (all subclass ValueError)

    * `MultipleChoiceError`
    * `SolveFailedError`
    * `NonUniqueSolutionError`

    """
    outputs = Box.Outputs(outputs)
    inputs = Box.Inputs()
    if fuel is None:
        fuel = Default
    recipePrefs = {}
    machinePrefs = []
    for v in using.items() if isinstance(using, Mapping) else using:
        if isinstance(v, Ingredient):
            inputs[v] = None
        elif isinstance(v, Recipe):
            recipePrefs[v.name] = 1000
        elif isinstance(v, Machine):
            machinePrefs.append(v)
        elif isinstance(v, OneWayFlow):
            inputs[v.item] = v.rate
        elif type(v) is tuple:
            item, rate = v
            if not isinstance(item, Ingredient):
                raise ValueError
            inputs[item] = rate
        else:
            raise ValueError(f"don't know how to use {v}")
    stopAt = set(stopAt)
    stopAt |= inputs.keys()
    machinePrefs += config.machinePrefs.get([])
    l = list(inputs.keys())
    origLen = len(l)
    i = 0
    while i < len(l):
        priority = 1000 if i < origLen else 800
        item = l[i]
        i += 1
        rs = [r.name for r in recipesThatUse.get(item, ())]
        if len(rs) == 1:
            r = rs[0]
            recipePrefs[r] = max(recipePrefs.get(r, priority), priority)
            recipe = rcpByName[r]
            m = recipe(machinePrefs = machinePrefs, fuel = fuel)
            for flow in m.flows():
                if flow.rate() > 0 and flow.item not in l:
                    l.append(flow.item)
        else:
            for r in rs:
                try:
                    adj = craftingHints[r].priority
                    if adj <= IGNORE:
                        continue
                except KeyError:
                    adj = 0
                p = priority - 100 + adj
                recipePrefs[r] = max(recipePrefs.get(r, p), p)
    machines = {}
    toResolve = deque(outputs.keys())
    while toResolve:
        item = toResolve.popleft()
        try:
            recipes = [r.name for r in recipesThatMake[item]]
        except KeyError:
            continue
        maxPriority = None
        bestRecipes = []
        for r in recipes:
            try:
                priority = recipePrefs[r]
            except KeyError:
                try:
                    priority = craftingHints[r].priority
                except KeyError:
                    priority = 0
            if maxPriority is None or priority > maxPriority:
                maxPriority = priority
                bestRecipes = [r]
            elif priority == maxPriority:
                bestRecipes.append(r)
        else:
            if maxPriority <= IGNORE:
                continue
        if len(bestRecipes) == 1 or (len(bestRecipes) > 1 and maxPriority >= 1000):
            recipes = bestRecipes
        else:
            recipes = []
            err = MultipleChoiceError('multiple ways to produce {}: {}'.format(item, ' '.join(bestRecipes)))
            if abortOnMultiChoice:
                raise err
            else:
                warn(err)
        recipes = [r for r in recipes if r not in machines]
        if not recipes:
            continue
        try:
            recipes += craftingHints[recipes[0]].also
        except KeyError:
            pass
        for r in recipes:
            if r in machines:
                continue
            recipe = rcpByName[r]
            m = recipe(machinePrefs = machinePrefs, fuel = fuel)
            machines[r] = m
            if recursive:
                for flow in m.flows():
                    if flow.rate() < 0 and flow.item not in stopAt:
                        toResolve.append(flow.item)
    res = ProduceResult()
    if not machines:
        return res
    boxOutputs = dict(outputs)
    boxPriorities = {}
    for recipe, m in machines.items():
        try:
            if craftingHints[recipe].boxPriority != 0:
                boxPriorities[m.recipe] = craftingHints[recipe].boxPriority
        except KeyError:
            pass
        m_outputs = m.outputs
        if len(m_outputs) > 1:
            for item in m_outputs.keys():
                if item not in boxOutputs:
                    boxOutputs[item] = None
    b = res.factory = Box(name = name,
                          inner = Group([~m for m in machines.values()]),
                          outputs = boxOutputs, inputTouchups = inputs,
                          priorities = boxPriorities,
                          constraints = constraints)
    someOutputRatesSpecified = any(r != None for r in outputs.values())
    for item in b.outputs.keys():
        if item not in outputs:
            b.priorities[item] = IGNORE
        elif someOutputRatesSpecified and outputs[item] is None:
            b.priorities[item] = IGNORE
    b.updateName_()
    if inputs:
        for item in b.inputs.keys():
            if item not in inputs:
                res.extraInputs.append(item)
    if not solve or (all(rate is None for rate in outputs.values()) and all(rate is None for rate in inputs.values())):
        return res
    res.solveRes = b.solve()
    b.finalize(roundUp = roundUp, _res = res, recursive = False)
    if res.solveRes > minSolveRes:
        if not res.solveRes.ok():
            raise SolveFailedError(res)
        raise NonUniqueSolutionError(res)
    return res

@dataclass
class ProduceResult:
    factory: Box = None
    solveRes: SolveRes = SolveRes.UNSOLVED
    extraOutputs: list = field(default_factory=list)
    extraInputs: list = field(default_factory=list)
    unusedInputs: list = field(default_factory=list)

class MultipleChoiceError(ValueError):
    pass

class SolveFailedError(ValueError):
    def __init__(self, res):
        self.res = res
        super().__init__(res.solveRes)

class NonUniqueSolutionError(ValueError):
    def __init__(self, res):
        self.res = res
        super().__init__(res.solveRes)

def merge(*args, mergeFun = operator.add):
    if len(args) < 2:
        raise ValueError
    res = _merge(args[0], args[1], mergeFun)
    for i in range(2, len(args)):
        res = _merge(res, args[i], mergeFun)
    views = []
    for b in args:
        view = copy(b)
        view.__class__ = Box
        view.inner = res.inner
        views.append(view)
    return (res,*views)

def union(*args):
    return merge(*args, mergeFun = max)

def _merge(b1, b2, mergeFun):
    combined = {}
    for m in b1.inner:
        num = m.num
        if getattr(m, 'unbounded', False):
            num *= m.throttle
        m = m.machine
        if isinstance(m, Box):
            combined[id(m)] = (num, m)
        else:
            combined[m.recipe] = (num, m)
    for m in b2.inner:
        num = m.num
        if getattr(m, 'unbounded', False):
            num *= m.throttle
        m = m.machine
        if isinstance(m, Box):
            existing = combined.get(id(m), (0, None))
            combined[id(m)] = (mergeFun(existing[0], num), m)
        else:
            existing = combined.get(m.recipe, (0, None))
            if existing[1]:
                assert type(m) is type(existing[1])
                assert m.bonus() == existing[1].bonus()
            combined[m.recipe] = (mergeFun(existing[0], num), m)

    outputs = dict()
    outputs.update((item, None) for item in b1.outputs.keys())
    outputs.update((item, None) for item in b2.outputs.keys())
    for item in outputs.keys():
        o1 = b1.outputs.get(item, None)
        o2 = b2.outputs.get(item, None)
        if o1 == o2:
            outputs[item] = o1

    inputs = dict()
    inputs.update((item, None) for item in b1.inputs.keys())
    inputs.update((item, None) for item in b2.inputs.keys())
    for item in inputs.keys():
        o1 = b1.inputs.get(item, None)
        o2 = b2.inputs.get(item, None)
        if o1 == o2:
            inputs[item] = o1
    return Box(Group(num*copy(m) for num,m in combined.values()), outputs=outputs, inputs=inputs)
