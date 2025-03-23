from __future__ import annotations
from dataclasses import dataclass,field
from collections import defaultdict
from collections.abc import Mapping,Sequence
from copy import copy as _copy, deepcopy as _deepcopy
from numbers import Number
from typing import NamedTuple
import sys
import operator

from .fracs import frac, div, ceil, Inf
from .core import *
from .core import _MutableFlows,NetFlows
from ._helper import asItem
from . import itm

__all__ = ('BoxBase', 'Equal', 'AtLeast', 'Box', 'BlackBox', 'finalizeGroup')

class BoxFlows(NetFlows):
    def _showFlow(self, flow):
        return flow.rateOut != flow.rateIn or flow.rateOut == 0 == flow.rateIn

class BoxBase(MachineBase):
    @property
    def num(self):
        return 1

    @property
    def machine(self):
        return self

    @property
    def recipe(self):
        return None

    def _flowItems(self, inputs, outputs):
        for item in self.inputs:
            inputs.add(item)
        for item in self.outputs:
            outputs.add(item)
        for item in self.unconstrained:
            inputs.add(item)
            outputs.add(item)

    def _sortKey(self):
        return (3,)

    def __repr__(self):
        nameStr = f' ({self.name})' if self.name is not None else ''
        throttleStr = f' @{self.throttle:g}' if getattr(self, 'throttle', 1) != 1 else ''
        return f'<{self.__class__.__name__}{nameStr}{throttleStr} {self.outputs} <= {self.inputs}>'

    def __str__(self):
        name = self.name if self.name is not None else self._fallbackName
        throttleStr = f' @{self.throttle:g}' if getattr(self, 'throttle', 1) != 1 else ''
        return f'{name}{throttleStr}: {self.outputs} <= {self.inputs}'

    def _flatten(self, lst, num):
        if num == 1:
            lst.append(self)
        else:
            lst.append(Mul(self, num))

class Term(tuple):
    num = property(operator.itemgetter(0))
    num.__doc__ = None

    item = property(operator.itemgetter(1))
    item.__doc__ = None

    def __new__(cls, arg):
        if isinstance(arg, Number):
            return tuple.__new__(cls, (arg, None))
        elif isinstance(arg, Ingredient):
            return tuple.__new__(cls, (1, arg))
        elif isinstance(arg, str):
            return tuple.__new__(cls, (frac(arg), None))
        else:
            return tuple.__new__(cls, arg)

    def __repr__(self):
        if self.item is None:
            return repr(self.num)
        if self.num == 1:
            return repr(self.item)
        if self.num == -1:
            return f'-{self.item!r}'
        else:
            return f'{self.num!r}*{self.item!r}'

    def __str__(self):
        if self.item is None:
            return str(self.num)
        if self.num == 1:
            return str(self.item)
        if self.num == -1:
            return f'-{self.item}'
        else:
            return f'{self.num}*{self.item}'

class Constraint:
    __slots__ = ()

class Equal(Constraint):
    __slots__ = ('expressions')
    def __repr__(self):
        return 'Equal(' + ', '.join(repr(expr) for expr in self.expressions) + ')'
    def __str__(self):
        return ' = '.join(str(expr) for expr in self.expressions)
    def __getitem__(self, index):
        return self.expressions[index]
    def __len__(self):
        return len(self.expressions)
    def __init__(self, *args):
        self.expressions = [Term(arg) for arg in args]

class Inequality(Constraint):
    __slots__ = ('lhs', 'rhs')
    def __repr__(self):
        return f'{self.__class__.__name__}({self.lhs!r}, {self.rhs!r})'
    def __str__(self):
        return f'{self.lhs} {self.symbol} {self.rhs}'
    def __init__(self, lhs, rhs):
        self.lhs = Term(lhs)
        self.rhs = Term(rhs)

class AtLeast(Inequality):
    __slots__ = ()
    symbol = '>='

#class AtMost(Inequality):
#    __slots__ = ()
#    symbol = '<='

class Box(BoxBase):
    """Wraps a group to restrict inputs or outputs."""
    MIN_PRIORITY =  IGNORE # (-100)
    MAX_PRIORITY = -IGNORE #  (100)

    _fallbackName = '<box>'

    class _ExternalFlows(dict):
        __slots__ = ()
        def __init__(self, vals = None, priorities = None):
            self.update(vals, priorities)
        def update(self, vals = None, priorities = None):
            if vals is None:
                return
            for v in vals.items() if isinstance(vals, Mapping) else vals:
                if type(v) is tuple:
                    item, rate = v
                elif isinstance(v, OneWayFlow):
                    item, rate = v.item, v.rate
                elif isinstance(v, Flow):
                    item, rate = v.item, abs(v.rate())
                elif isinstance(v, RecipeComponent):
                    item, rate = v.item, None
                else:
                    item, rate = v, None
                try:
                    self[item] = rate
                except ValueError:
                    if isinstance(rate, str) and rate.startswith('p'):
                        i = 2 if rate.startswith('p:') else 1
                        self[item] = None
                        priorities[item] = frac(rate[i:])
                    else:
                        raise
        def add(self, item, rate = None):
            self[item] = rate
        def str(self, flows = None):
            if flows:
                return ', '.join(str(flows[item]) for item in sorted(self.keys()))
            else:
                return ', '.join(str(item) if self[item] is None else f'{item} @ {self[item]}' for item in sorted(self.keys()))
        __str__ = str
        def __setitem__(self, item, rate):
            raise NotImplementedError
        def _jsonObj(self):
            from .jsonconv import _jsonObj
            return {k.name: _jsonObj(v) for k,v in self.items()}

    class Outputs(_ExternalFlows):
        __slots__ = ()
        def __setitem__(self, item, rate):
            item = asItem(item)
            if rate is None:
                return dict.__setitem__(self, item, None)
            rate = frac(rate)
            if rate < 0:
                raise ValueError
            return dict.__setitem__(self, item, rate)


    class Inputs(_ExternalFlows):
        __slots__ = ()
        def __setitem__(self, item, rate):
            item = asItem(item)
            if rate is None:
                return dict.__setitem__(self, item, None)
            rate = frac(rate)
            if rate > 0:
                rate = -rate
            return dict.__setitem__(self, item, rate)

    class OtherFlows(_ExternalFlows):
        __slots__ = ()
        def __setitem__(self, item, rate):
            item = asItem(item)
            if rate is None:
                return dict.__setitem__(self, item, None)
            rate = frac(rate)
            return dict.__setitem__(self, item, rate)

    class _Dict(dict):
        __slots__ = ()
        def __init__(self, vals = None):
            if vals is None:
                return
            for k, v in vals.items() if isinstance(vals, Mapping) else vals:
                self[k] = v

    class SimpleConstraints(_Dict):
        __slots__ = ()
        def __str__(self):
            def fmtTerm(num, item):
                if num == 1:
                    return f'{item}'
                elif num == -1:
                    return f'-{item}'
                else:
                    return f'{item}*{rate}'
            return ', '.join(str(item) if rate is None
                             else f'{item} >= {rate}' if isinstance(rate, Number)
                             else f'{item} = {fmtTerm(*rate)}'
                             for item,rate in self.items())
        def __setitem__(self, item, rate):
            item = asItem(item)
            rate = frac(rate)
            return dict.__setitem__(self, item, rate)
        def _jsonObj(self):
            from .jsonconv import _jsonObj
            return {k.name: _jsonObj(v) for k,v in self.items()}

    class OtherConstraints(list):
        def __str__(self):
            return ', '.join(f'({c})' for c in self)
        pass

    class Priorities(_Dict):
        __slots__ = ()
        def __str__(self):
            def tostr(k):
                if isinstance(k, Ingredient):
                    return f'itm.{k}'
                elif isinstance(k, Recipe):
                    return f'rcp.{k}'
                else:
                    return str(k)
            return ', '.join(f'ignore {tostr(k)}' if p <= IGNORE else f'{tostr(k)}: {p}' for k, p in self.items())
        def __setitem__(self, key, priority):
            priority = frac(priority)
            if priority < Box.MIN_PRIORITY or priority > Box.MAX_PRIORITY:
                raise ValueError('priority must be between {Box.MIN_PRIORITY} and {Box.MAX_PRIORITY}, inclusive')
            if isinstance(key, Machine):
                b = key.bonus()
                key = Box._FakeMachine(key.recipe,
                                       getattr(key, 'fuel', None),
                                       Bonus(productivity = b.productivity, quality = b.quality))
            return dict.__setitem__(self, key, priority)
        def _jsonObj(self):
            from .jsonconv import _jsonObj
            return {f"{'i' if isinstance(k, Ingredient) else 'r'} {k.name}": _jsonObj(v) for k,v in self.items()}

    class _FakeMachine(NamedTuple):
        recipe: Recipe
        fuel: Ingredient
        bonus_: Bonus
        @property
        def machine(self):
            return self
        def bonus(self):
            return self.bonus_
        def __str__(self):
            parms = []
            if self.fuel:   parms.append(f"fuel={self.fuel}")
            if self.bonus_: parms.append(f"{self.bonus_}")
            parms = '; '.join(parms)
            return f"rcp.{self.recipe.alias}<{parms}>"

    def __init__(self, *args, name = None, inner = None,
                 outputs = None, extraOutputs = (), outputTouchups = (), outputsLoose = False,
                 inputs = None, extraInputs = (), inputTouchups = (), inputsLoose = True,
                 unconstrained = (),
                 constraints = (), priorities = None,
                 allowExtraInputs = False):
        """Create a new box.

        A box is a wrapper around a group with additional constraints to
        limit flows.  For example it is rare for satellite machine to be
        running 100% of the time.  This means that simply estimating the
        maximum flows will not give you an accurate picture of the resources
        needed, by grouping the satellite with a rocket silo, wrapping it
        in a box, and then solving it, you can can a better idea of the
        resources needed for creating space science packs.  After solving,
        the satellite machine will be throttled to produce just enough
        satellites for the rocket silo.

        Boxes can nest inside one another.

        Also see `box()`, which is a shortcut to both create a box and then
        solve it.

        *args*
            Positional arguments, can optically include, *name*, and/or *inner*
            (in that order).

        *name*
            A name for the box

        *inner*
            A `Group`.

        *outputs*, *extraOutputs*, *outputTouchups*, *inputs*, *extraInputs*, *inputTouchups*
            A sequence or mapping of outputs and inputs.  The key value can
            either be a rate in seconds, None, or a priority.  If a list,
            elements can either be an item, a tuple of the form (item, rate)
            (as generated with the `@` operator), or a flow.  If the rate is a
            string that starts with 'p' or 'p:' than the number after the
            prefix will be interpreted as a priority.

            If *outputs* or *inputs* is unspecified than they will be derived
            automatically based on if the flow is internal or not.  The
            *outputTouchups* and *inputTouchups* can be used to adjust the inputs
            or outputs afterwards.

            *extraOutputs* or *extraInputs* can be used to specify auxiliary
            flows and is equivalent to setting the priority to IGNORE.

        *outputsLoose*
            If True (default False) than all output rates will
            become constraints

        *inputsLoose*
            If True (the default) than all input rates will become
            constraints

        *unconstrained*
            Ignored flows.  Neither input or outputs and the exact values can
            be either postive or negative depending on the machine
            configuration.  The values are completly ignored by the solver.

        *constraints*
            Extra constraints for the solver.  It can either be a
            mapping of simple constraints, or a list of equations.

            If a mapping, then the flow for the item (the key) will need to be
            at least the given rate.  Positive values will constrain outputs
            and negative values will constrain inputs.  For example,
            {itm.plastic_bar: 2} will add a constraint to produce plastic bars
            at a rate of at least 2/s and {itm.plastic_bar: -2} will add a
            constraint to consume plastic bars at a rate of 2/s max
            (inclusive).

            If a list, then it a list of simple equations that must be true.
            An equation currently is one of `Equal(term1, term2, ...)<Equal>` or
            `AtLeast(lhs, rhs)<AtLeast>`.  Each term in either a number, an item, or a
            tuple.  For example:
            ``Equal(itm.uranium_fuel_cell, (-1, itm.used_up_uranium_fuel_cell))``

        *priorities*
            A mapping of priorities for the solver.  Can be either a `dict` or
            a list of key-value pairs.

            The key is an item, recipe, or machine.  The value in a number
            between -100 and 100 with larger values having a higher priority.

            The default priority for outputs is 0.  The constant `IGNORE` can
            be used for the lowest priority (-100) and has special meaning to
            the solver.  Input priorities are currently ignored unless the
            constant `IGNORE` is used.

            If the key is a recipe or machine: the priority should be
            positive.  If the key is a machine: the machine object must also
            have a recipe associated with it.  In addition, since machine
            objects are not hashable, machines must be passed in via a list of
            key-value pairs rather than a `dict`.

            When a recipe is specified, all machines with that recipe will be
            assigned that priority.  When a machine is specified instead, all
            machines with the same fuel, productivity bonus, and quality bonus
            will get assigned that priority.  The specific machine type is not
            taken into account.

        *allowExtraInputs*
            |nbsp|

        """
        if len(args) > 0 and isinstance(args[0], str):
            if name is None:
                name = args[0]
                args = args[1:]
            else:
                raise TypeError("'name' parameter provided as both a positional and keyword argument")

        if len(args) > 0:
            if inner is None:
                inner = args[0]
                args = args[1:]
            else:
                raise TypeError("'inner' parameter provided as both a positional and keyword argument")

        if len(args) > 0:
            raise TypeError('too many positional arguments provided')

        from .solver import SolveRes

        if not isinstance(inner, Group):
            inner = Group(inner)

        self.inner = inner
        """"""

        self.name = name
        """"""
        self.priorities = Box.Priorities(priorities)
        """"""
        self.outputs = Box.Outputs(outputs, self.priorities)
        """"""
        outputRates = {item: rate for item, rate in self.outputs.items() if rate is not None}
        self.inputs = Box.Inputs(inputs, self.priorities)
        """"""
        inputRates = {item: rate for item, rate in self.inputs.items() if rate is not None}
        self.simpleConstraints = Box.SimpleConstraints()
        """"""
        self.otherConstraints = Box.OtherConstraints()
        """"""
        self.unconstrained = Box.OtherFlows(unconstrained)
        """"""

        self.unconstrainedHints = set()
        """"""

        inputs_ = set()
        outputs_ = set()
        products_ = set()
        innerUnconstrained = set()
        for m in self.inner.flatten():
            inputs_ |= m.inputs.keys()
            outputs_ |= m.outputs.keys()
            products_ |= m.products.keys()
            if isinstance(m, Box):
                innerUnconstrained |= m.unconstrained.keys()
                self.unconstrainedHints |= m.unconstrained.keys()
                self.unconstrainedHints |= m.unconstrainedHints

        self.__flows = inputs_ | outputs_

        self.byproducts_ = frozenset(outputs_ - products_)

        self.unconstrainedHints |= self.byproducts_ & inputs_

        for item in (innerUnconstrained - inputs_ - outputs_):
            self.unconstrained.add(item)

        if outputs is None or inputs is None:
            common = inputs_ & outputs_
            if outputs is None:
                self.outputs = Box.Outputs(sorted(outputs_ - common - innerUnconstrained - self.unconstrained.keys()))
            if inputs is None:
                if allowExtraInputs:
                    self.inputs = Box.Inputs(inputs_ - self.outputs.keys() - innerUnconstrained - self.unconstrained.keys())
                    for item in self.inputs.keys() & common:
                        self.priorities[item] = IGNORE
                else:
                    self.inputs = Box.Inputs(sorted(inputs_ - common - self.unconstrained.keys()))

        for item in extraOutputs:
            self.outputs[item] = None
            self.priorities[item] = IGNORE

        for item in extraInputs:
            self.inputs[item] = None
            self.priorities[item] = IGNORE

        for item, rate in Box.Outputs(outputTouchups, self.priorities).items():
            if rate is None:
                self.outputs[item] = None
            else:
                self.outputs[item] = rate
                outputRates[item] = rate

        for item, rate in Box.Inputs(inputTouchups, self.priorities).items():
            if rate is None:
                self.inputs[item] = None
            else:
                self.inputs[item] = rate
                inputRates[item] = rate

        self.outputs = Box.Outputs((item,rate) for item, rate in self.outputs.items() if rate != 0)

        self.inputs = Box.Inputs((item,rate) for item, rate in self.inputs.items() if rate != 0)

        if outputsLoose:
            for item, rate in outputRates.items():
                self.simpleConstraints[item] = rate
                self.outputs[item] = None

        if inputsLoose:
            for item, rate in inputRates.items():
                self.simpleConstraints[item] = rate
                self.inputs[item] = None

        self.updateName_()

        if isinstance(constraints, Mapping):
            for item, rate in constraints.items():
                self.simpleConstraints[item] = rate
        else:
            for c in constraints:
                if isinstance(c, Equal):
                    self.otherConstraints.append(c)
                    # fixme, if one of the expressions is a constant, than turn
                    # the constrainst into fixed valuses for input and/or outputs
                elif isinstance(c, AtLeast):
                    if c.lhs.num > 0 and c.rhs.item is None:
                        self.simpleConstraints[c.lhs.item] = frac(c.rhs.num, c.lhs.num)
                    else:
                        self.otherConstraints.append(c)
                else:
                    raise ValueError(f'invalid constraint: {c}')

    def updateName_(self):
        products = self.products
        if len(products) == 1 and self.name is None:
            self.name = 'b-{}'.format(next(iter(products)).name)

    @property
    def products(self):
        return Box.Outputs((item,rate) for item,rate in self.outputs.items()
                           if item not in self.byproducts_ and self.priorities.get(item, 0) != IGNORE)

    @property
    def byproducts(self):
        return Box.Outputs((item,rate) for item,rate in self.outputs.items()
                           if item in self.byproducts_ or self.priorities.get(item, 0) == IGNORE)

    def internal(self):
        return self.__flows - self.inputs.keys() - self.outputs.keys()

    def _jsonObj(self, objs, **kwargs):
        from .jsonconv import _jsonObj
        if id(self) in objs:
            return objs[id(self)]
        obj = {}
        obj['name'] = self._fallbackName
        obj['id'] = objs.add(id(self))
        if self.name:
            obj['label'] = self.name
        obj['inner'] = self.inner._jsonObj(objs = objs, **kwargs)
        for k in ['outputs', 'inputs', 'simpleConstraints', 'otherConstraints', 'priorities']:
            v = getattr(self,k)
            if v:
                obj[k] = v._jsonObj()
        return obj

    def summarize(self):
        """:meta private:"""
        obj = _copy(self)
        obj.inner = obj.inner.summarize()
        return obj

    def print(self, out = None, prefix = ''):
        if out is None:
            out = sys.stdout
        self._header(out, prefix)
        prefix += '  '
        for m in self.inner.machines:
            m.print(out, prefix + '  ')
        self._footer(out, prefix)

    def summary(self, out = None, *, prefix = '', includeSolvedBoxFlows = True, includeMachineFlows = False, includeBoxDetails = True, flowsItemFilter = None):
        self._summary(out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter)

    def _summary(self, out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter, _namePrefix = ''):
        if out is None:
            out = sys.stdout
        self._header(out, prefix, _namePrefix)
        prefix += '  '
        self.inner._summary(out, prefix + '  ', includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter)
        flows = self.flows()
        if flows.state != FlowsState.OK:
            out.write(f'{prefix}{flows.state.name}\n')
        if flows.state.ok() and includeSolvedBoxFlows:
            pass
        else:
            flows = None
        self._footer(out, prefix, flows)

    def _header(self, out, prefix, namePrefix = ''):
        nameSuffix = ''
        if getattr(self, 'throttle', 1) != 1:
            nameSuffix = f' @{self.throttle:.6g}'
        if self.name is None:
            out.write(f'{prefix}{namePrefix}{self.__class__.__name__}{nameSuffix}:\n')
        else:
            out.write(f'{prefix}{namePrefix}{self.name}{nameSuffix}:\n')

    def _footer(self, out, prefix, flows = None):
        byproducts = self.byproducts
        if byproducts:
            products = self.products
            out.write(f'{prefix}Products: {products.str(flows)}\n')
            out.write(f'{prefix}Byproducts: {byproducts.str(flows)}\n')
        else:
            out.write(f'{prefix}Outputs: {self.outputs.str(flows)}\n')
        out.write(f'{prefix}Inputs: {self.inputs.str(flows)}\n')
        if self.unconstrained:
            out.write(f'{prefix}Unconstrained: {self.unconstrained.str(flows)}\n')
        if self.simpleConstraints or self.otherConstraints:
            out.write(f'{prefix}Constraints:')
            if self.simpleConstraints:
                out.write(f' {self.simpleConstraints}')
            if self.otherConstraints:
                out.write(f' {self.otherConstraints}')
            out.write('\n')
        if self.priorities:
            out.write(f'{prefix}Priorities: {self.priorities}\n')

    def solved(self):
        return self.flows().state == FlowsState.OK

    def solve(self):
        """Solve the box so all contraints are met.

        Returns a `SolveRes` enum with the result.  See the `SolveRes`
        documenation for meaning of the enum values.

        """
        from .solver import SolveRes
        solver = self.solver()
        solver.solve()
        res, _ = solver.apply()
        return res

    def solver(self, **kwargs):
        """Return a solver instance for debugging or more control over the solve process."""
        from . import solver
        return solver.Solver(solver.LinearEqSystem.fromBox(self, **kwargs))

    def _flows(self, throttle, _includeInner):
        res = _MutableFlows()
        orig = self.inner._flows(throttle = None, _includeInner = False)
        state = orig.state
        if throttle is None:
            throttle = 1
        else:
            throttle = frac(throttle)
        for item,rate in self.outputs.items():
            flow = orig[item]
            underflow = flow.underflow
            annotation = ''
            if flow.rate() < 0:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif rate is not None and flow.rate() < rate:
                underflow = True
            elif item in self.simpleConstraints and flow.rate() < self.simpleConstraints[item]:
                underflow = True
            elif rate is not None and flow.rate() > rate:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '*'
            if underflow:
                annotation = '!'
                state = max(state, FlowsState.UNDERFLOW)
            if _includeInner:
                res.byItem[item] = flow.copy(factor = throttle, adjusted = False, underflow = underflow, annotation = annotation)
            else:
                res.byItem[item] = Flow(item, rateOut = flow.rate() * throttle, underflow = underflow, annotation = annotation)
        for flow in orig:
            if flow.item in self.outputs or flow.item in self.inputs or flow.item is itm.electricity:
                continue
            if flow.rateIn == 0 == flow.rateOut:
                continue
            annotation = ''
            if flow.item not in self.unconstrained:
                if flow.rate() < 0:
                    state = max(state, FlowsState.UNSOLVED)
                    annotation = '!'
                elif flow.rate() > 0:
                    state = max(state, FlowsState.UNSOLVED)
                    annotation = '*'
            if _includeInner or flow.item in self.unconstrained:
                res.byItem[flow.item] = flow.copy(factor = throttle, adjusted = False, annotation = annotation)
            else:
                pass
        for item,rate in self.inputs.items():
            flow = orig[item]
            annotation = ''
            if flow.rate() > 0 or (rate is not None and flow.rate() < rate):
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif item in self.simpleConstraints and flow.rate() < self.simpleConstraints[item]:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif rate is not None and flow.rate() > rate:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '*'
            if flow.rateIn == 0 == flow.rateOut and annotation == '':
                continue
            if _includeInner:
                res.byItem[item] = flow.copy(factor = throttle, adjusted = False, annotation = annotation)
            else:
                res.byItem[item] = Flow(item, rateIn = -flow.rate() * throttle, underflow = underflow, annotation = annotation)
        res.byItem[itm.electricity] = orig[itm.electricity]
        res._byproducts = tuple(self.byproducts)
        if not _includeInner and not state.ok():
            res.byItem.clear()
        res.state = state
        res.reorder()
        return BoxFlows(res)

    def flowSummary(self, out = None, includeInner = False):
        if out is None:
            out = sys.stdout
        flowTally = defaultdict(lambda: defaultdict(lambda: 0))
        nameLookup = {}
        boxNum = 1
        for m in self.inner.flatten():
            m = m.machine
            if m.recipe:
                id_ = m.recipe
            elif isinstance(m, Box):
                id_ = id(m)
                if m.name:
                    name = m.name
                else:
                    name = f'box#{boxNum}'
                    boxNum += 1
                nameLookup[id_] = name
            else:
                name = 'unknown'
                id_ = id(m)
                nameLookup[id_] = name
            for flow in m.flows():
                rate = flow.rate()
                if rate != 0:
                    flowTally[flow.item][id_] += rate

        flows = self.flows()

        def printFlows(label, items):
            out.write(f'{label}:\n')
            for item in items:
                out.write(f'  {flows[item]}:')
                for id_,rate in flowTally[item].items():
                    if isinstance(id_, Recipe):
                        name = id_.alias
                    else:
                        name = nameLookup[id_]
                    out.write(f' {name} {rate:.3g},')
                out.write('\n')
            for item in list(items):
                del flowTally[item]

        byproducts = self.byproducts
        if byproducts:
            products = self.products
            printFlows('Products', products.keys())
            printFlows('Byproducts', byproducts.keys())
        else:
            printFlows('Outputs', self.outputs.keys())
        printFlows('Inputs', self.inputs.keys())
        if self.unconstrained:
            printFlows('Unconstrained', self.unconstrained)
        printFlows('Other', flowTally.keys())

    def internalFlows(self):
        res = _MutableFlows()
        orig = self.inner.flows()
        for flow in orig:
            if (flow.item in self.outputs
                or flow.item in self.inputs
                or flow.item in self.unconstrained
                or flow.item is itm.electricity):
                continue
            res.byItem[flow.item] = flow
        return res

    def bottlenecks(self):
        candidates = []
        for m in self.inner:
            try:
                throttle = m.machine.throttle
            except AttributeError:
                continue
            if throttle == 1:
                candidates.append(m)
        result = []
        for m1 in candidates:
            throttling = []
            for item in m1.outputs:
                for m2 in self.inner.find(input = item):
                    try:
                        throttle = m2.machine.throttle
                    except AttributeError:
                        continue
                    if throttle < 1:
                        throttling.append(m2)
            if throttling:
                result.append([m1, *throttling])
        return result
                    

    def find(self, *args, **kwargs):
        return self.inner.find(*args, **kwargs)

    def resetThrottle(self):
        self.inner.resetThrottle()

    def finalize(self, *, roundUp = True, recursive = True, _res = None):
        """Finalize the result.

        Finalize the result by turning unbounded throttles into `Mul`.  If the
        unbounded throttle is 0 the machine is removed.  If *roundUp* is True
        (the default) then also round up multiples of machines (i.e. `Mul`)
        and adjust the throttle to compensate.  If *recursive* is True
        (the default) than recurse into any inner boxes.

        Returns an instance of `FinalizeResult`.

        """
        res = FinalizeResult() if _res is None else _res
        res.factory = self
        _finalizeInner(self.inner, roundUp, recursive)
        flows = self.flows()
        for item in list(self.priorities):
            if self.priorities[item] == IGNORE:
                if flows[item].rate() == 0:
                    del self.priorities[item]
                    del self.outputs[item]
                else:
                    res.extraOutputs.append(item)
        filteredInputs = Box.Inputs()
        for item, rate in self.inputs.items():
            if flows[item].rate() == 0:
                res.unusedInputs.append(item)
            else:
                filteredInputs[item] = rate
        self.inputs = filteredInputs
        return res

    def finalizeAll(self, roundUp = True):
        """Finalize everything.

        Equivalent to ``self.finalize(roundUp, recursive = True)``
        """
        return self.finalize(roundUp = roundUp, recursive = True)


class BlackBox(BoxBase):
    """Wrap a box to hide it's internals.

    When used with the solver, the solver will treat the black box as a
    simple machines and throttle all internal machines uniformity.  This
    allows them to be used inside an unbounded box and can also simplify the
    solve process.

    """
    _fallbackName = '<black box>'
    def __init__(self, box, *, name = None):
        self.throttle = 1
        self.unbounded = False
        self._inner = box
        self.name = name if name is not None else self._inner.name

    def _flows(self, throttle, _includeInner):
        if throttle is None:
            throttle = self.throttle
        return self._inner._flows(throttle, False)

    @property
    def inputs(self):
        return self._inner.inputs

    @property
    def outputs(self):
        return self._inner.outputs

    @property
    def products(self):
        return self._inner.products

    @property
    def byproducts(self):
        return self._inner.byproducts

    def resetThrottle(self):
        self.throttle = 1

    def __invert__(self):
        # fixme: should likely make a copy ...
        self.unbounded = True
        return self

def _finalizeInner(m, roundUp, recursive):
    if isinstance(m, Box) and recursive:
        m.finalize(roundUp = roundUp, recursive = True)
        return m
    elif isinstance(m, Group):
        finalizeGroup(m, roundUp = roundUp, recursive = recursive)
        return m

    if isinstance(m, Machine) and m.unbounded:
        throttle = m.throttle
        if throttle == 0: return None
        m.throttle = 1
        m.unbounded = False
        m = Mul(throttle, m)

    if isinstance(m, Mul) and isinstance(m.machine, (Machine, BlackBox)):
        throttle = m.num * m.machine.throttle
        if throttle == 0: return None
        if roundUp:
            m.num = ceil(throttle)
            m.machine.throttle = div(throttle, m.num)
        else:
            m.num = throttle
            m.machine.throttle = 1
        m.unbounded = False
    elif isinstance(m, Mul):
        m0 = _finalizeInner(m.machine, roundUp, recursive)
        if m0 is None: return None
        m.machine = m0

    return m

def finalizeGroup(grp, *, roundUp = True, recursive = True):
    machines = []
    for m in grp:
        m = _finalizeInner(m, roundUp, recursive)
        if m is None: continue
        machines.append(m)
    grp.machines = machines

@dataclass
class FinalizeResult:
    factory: Box = None
    extraOutputs: list = field(default_factory=list)
    unusedInputs: list = field(default_factory=list)

class CantFinalizeError(ValueError):
    pass

