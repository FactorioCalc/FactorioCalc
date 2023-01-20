from __future__ import annotations
from dataclasses import dataclass,field
from collections.abc import Mapping
from copy import copy as _copy
from numbers import Number
import sys

from .fracs import frac, div, ceil, Inf
from .core import *
from .core import _MutableFlows,NetFlows
from ._helper import asItem
from . import itm

__all__ = ('BoxBase', 'Box', 'UnboundedBox', 'BlackBox')

class BoxFlows(NetFlows):
    def _showFlow(self, flow):
        return flow.rateOut != flow.rateIn or flow.rateOut == 0 == flow.rateIn

@dataclass(init=False)
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

class Box(BoxBase):
    """Wrap a group to restrict inputs or outputs."""
    MIN_PRIORITY =  IGNORE # (-100)
    MAX_PRIORITY = -IGNORE #  (100)

    _fallbackName = '<box>'

    class _ExternalFlows(dict):
        __slots__ = ()
        def __init__(self, vals = None):
            self.update(vals)
        def update(self, vals = None):
            if vals is None:
                return
            for v in vals.items() if isinstance(vals, Mapping) else vals:
                if type(v) is tuple:
                    item, rate = v
                elif isinstance(v, OneWayFlow):
                    item, rate = v.item, v.rate
                elif isinstance(v, Flow):
                    item, rate = v.item, abs(v.rate())
                else:
                    item, rate = v, None
                self[item] = rate
        def add(self, item, rate = None):
            self[item] = rate
        def str(self, flows = None):
            if flows:
                return ', '.join(str(flows[item]) for item in self.keys())
            else:
                return ', '.join(str(item) if rate is None else f'{item} @ {rate}' for item,rate in self.items())
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
    

    class _Dict(dict):
        __slots__ = ()
        def __init__(self, vals = None):
            if vals is None:
                return
            for k, v in vals.items() if isinstance(vals, Mapping) else vals:
                self[k] = v

    class Constraints(_Dict):
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
            if isinstance(rate, Ingredient):
                rate = (1, rate)
            if type(rate) is tuple:
                if len(rate) != 2:
                    raise AttributeError('rate tuple length must be 2')
                rate = (frac(rate[0]), asItem(rate[1]))
            else:
                rate = frac(rate)
            return dict.__setitem__(self, item, rate)
        def _jsonObj(self):
            from .jsonconv import _jsonObj
            return {k.name: _jsonObj(v) for k,v in self.items()}

    class Priorities(_Dict):
        __slots__ = ()
        def __str__(self):
            def tostr(k):
                return str(k) if isinstance(k, Ingredient) else f'recipe {k.name}'
            return ', '.join(f'ignore {tostr(k)}' if p <= IGNORE else f'{tostr(k)}: {p}' for k, p in self.items())
        def __setitem__(self, key, priority):
            priority = frac(priority)
            if priority < Box.MIN_PRIORITY or priority > Box.MAX_PRIORITY:
                raise ValueError('priority must be between {Box.MIN_PRIORITY} and {Box.MAX_PRIORITY}, inclusive')
            return dict.__setitem__(self, key, priority)
        def _jsonObj(self):
            from .jsonconv import _jsonObj
            return {f"{'i' if isinstance(k, Ingredient) else 'r'} {k.name}": _jsonObj(v) for k,v in self.items()}

    name: str
    inner: Group
    outputs: Outputs
    inputs: Inputs
    constraints: Constraints
    priorities: Priorities

    def __init__(self, inner, *, name = None,
                 outputs = None, extraOutputs = (), outputTouchups = {}, outputsLoose = False,
                 inputs = None, extraInputs = (), inputTouchups = {}, inputsLoose = True,
                 constraints = None, priorities = None,
                 allowExtraInput = False):
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

        *inner*
            A `Group`.

        *name*
            A name for the box

        *outputs*, *extraOutputs*, *outputTouchups*, *inputs*, *extraInputs*, *inputTouchups*
            A sequence or mapping of outputs and inputs.  The key value can
            either be a rate in seconds or None.  If a list, elements can
            either be an item, a tuple of the form (item, rate) (as generated
            with the `@` operator), or a flow.

            If *outputs* or *inputs* is unspecified than they will be derived
            automatically based on if the flow is internal or not.  The
            *outputTouchups* and *inputTouchups* can be used to adjust the inputs
            or outputs afterwards.

            *extraOutputs* or *extraInputs* can be used to specify auxiliary
            flows, which have special meaning to the solver.

        *outputsLoose* 
            If True (default False) than all output rates will
            become constraints

        *inputsLoose* 
            If True (the default) than all input rates will become
            constraints
        
        *constraints*
            A mapping of extra constraints for the solver.  The key
            is an item.  If the value is a rate, with input rates being
            negative, than that flow will need to be at least the given rate.
            If the value is another item or a tuple of the form (num, item)
            that then a constraints is added of the form::

              <key-item> = <num> * <item>

        *priority* 
            A mapping of priories for the solver.  The key is either a
            recipe or an item.  The value in a number between -100 and 100
            with larger values having a higher priority.  The default priority
            is 0.  The constant `IGNORE` can be used for the lowest priority
            (-100) and has special meaning to the solver.

        *allowExtraInputs*
            |nbsp|

        """
        from .solver import SolveRes
        if not isinstance(inner, Group):
            inner = Group(inner)
        self.inner = inner
        self.name = name
        self.outputs = Box.Outputs(outputs)
        self.inputs = Box.Inputs(inputs)
        self.priorities = Box.Priorities(priorities)
        self.constraints = Box.Constraints(constraints)
        if outputs is None or inputs is None:
            inputs_ = set()
            outputs_ = set()
            for m in self.inner.flatten():
                inputs_ |= m.inputs.keys()
                outputs_ |= m.outputs.keys()
            common = inputs_ & outputs_
            if outputs is None:
                self.outputs = Box.Outputs(outputs_ - common)
            if inputs is None:
                if allowExtraInput:
                    self.inputs = Box.Inputs(inputs_ - self.outputs.keys())
                    for item in self.inputs.keys() & common:
                        self.priorities[item] = IGNORE
                else:
                    self.inputs = Box.Inputs(inputs_ - common)
        mainOutput = [item for item in self.outputs if item is not itm.empty_barrel]
        if len(mainOutput) == 1 and self.name is None:
            self.name = 'b-{}'.format(mainOutput[0].name)
        for item in extraOutputs:
            self.outputs[item] = None
            self.priorities[item] = IGNORE
        for item in extraInputs:
            self.inputs[item] = None
            self.priorities[item] = IGNORE
        for item, rate in Box.Outputs(outputTouchups).items():
            self.outputs[item] = rate
        for item, rate in Box.Inputs(inputTouchups).items():
            self.inputs[item] = rate
        if outputsLoose:
            for item, rate in self.outputs.items():
                if rate is not None:
                    self.constraints[item] = rate
                    self.outputs[item] = None
        if inputsLoose:
            for item, rate in self.inputs.items():
                if rate is not None:
                    self.constraints[item] = rate
                    self.inputs[item] = None

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
        for k in ['outputs', 'inputs', 'constraints', 'priorities']:
            v = getattr(self,k)
            if v:
                obj[k] = v._jsonObj()
        return obj

    def summarize(self):
        """:meta private:"""
        obj = _copy(self)
        obj.inner = obj.inner.summarize()
        return obj
    
    def summary(self, out = None, *, prefix = '', includeSolvedBoxFlows = True, includeMachineFlows = False, includeBoxDetails = True, flowsItemFilter = None):
        self._summary(out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter)

    def _summary(self, out, prefix, includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter, _namePrefix = ''):
        if out is None:
            out = sys.stdout
        out.write(prefix)
        nameSuffix = ''
        if getattr(self, 'throttle', 1) != 1:
            nameSuffix = f' @{self.throttle:.6g}'
        if self.name is None:
            out.write(f'{_namePrefix}Box{nameSuffix}:\n')
        else:
            out.write(f'{_namePrefix}{self.name}{nameSuffix}:\n')
        prefix = prefix + '  '
        self.inner._summary(out, prefix + '  ', includeSolvedBoxFlows, includeMachineFlows, includeBoxDetails, flowsItemFilter)
        flows = self.flows()
        if flows.state != FlowsState.OK:
            out.write(f'{prefix}{flows.state.name}\n')
        if flows.state.ok() and includeSolvedBoxFlows:
            pass
        else:
            flows = None
        out.write(f'{prefix}Outputs: {self.outputs.str(flows)}\n')
        out.write(f'{prefix}Inputs: {self.inputs.str(flows)}\n')
        if self.constraints:
            out.write(f'{prefix}Constraints: {self.constraints}\n')
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
        for item,rate in self.outputs.items():
            flow = orig[item]
            underflow = flow.underflow
            annotation = ''
            if flow.rate() < 0:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif rate is not None and flow.rate() < rate:
                underflow = True
            elif item in self.constraints and isinstance(self.constraints[item], Number) and flow.rate() < self.constraints[item]:
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
            if flow.rate() < 0:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif flow.rate() > 0:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '*'
            if _includeInner:
                res.byItem[flow.item] = flow.copy(factor = throttle, adjusted = False, annotation = annotation)
            else:
                pass
        for item,rate in self.inputs.items():
            flow = orig[item]
            annotation = ''
            if -flow.rate() < 0 or (rate is not None and -flow.rate() < rate):
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif item in self.constraints and flow.rate() < self.constraints[item]:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '!'
            elif rate is not None and -flow.rate() > rate:
                state = max(state, FlowsState.UNSOLVED)
                annotation = '*'
            if flow.rateIn == 0 == flow.rateOut and annotation == '':
                continue
            if _includeInner:
                res.byItem[item] = flow.copy(factor = throttle, adjusted = False, annotation = annotation)
            else:
                res.byItem[item] = Flow(item, rateIn = -flow.rate() * throttle, underflow = underflow, annotation = annotation)                
        res.byItem[itm.electricity] = orig[itm.electricity]
        if not _includeInner and not state.ok():
            res.byItem.clear()
        res.state = state
        return BoxFlows(res)

    def find(self, **kwargs):
        return self.inner.find(**kwargs)
    
    def resetThrottle(self):
        self.inner.resetThrottle()

    def finalize(self, *, roundUp = True, recursive = True, _res = None):
        """Finalize the result.

        Finalize the result by converting `UnboundedBox`'es into a normal ones
        and if *roundUp* is True (the default) also round up multiples of
        machines and adjusting the throttle to compensate.  If *recursive* is
        True (default False) than recurse into any inner boxes, otherwise
        the contents of inner boxes are left alone.  `UnboundedBox`'es one
        level deep are always converted.

        Returns an instance of `FinalizeResult`.

        """
        res = FinalizeResult() if _res is None else _res
        res.factory = self
        _finalizeInner(self.inner, roundUp, recursive)
        flows = self.flows()
        filteredOutputs = Box.Outputs()
        for item, rate in self.outputs.items():
            if self.priorities.get(item,None) == IGNORE:
                if flows[item].rate() == 0:
                    del self.priorities[item]
                    continue
                res.extraOutputs.append(item)
            filteredOutputs[item] = rate
        self.outputs = filteredOutputs
        filteredInputs = Box.Inputs()
        for item, rate in self.inputs.items():
            if flows[item].rate() == 0:
                res.unusedInputs.append(item)
            else:
                filteredInputs[item] = rate
        self.inputs = filteredInputs
        if self.__class__ is UnboundedBox:
            self.__class__ = Box
        return res

    def finalizeAll(self, roundUp = True):
        """Finalize everything.

        Equivalent to ``self.finalize(roundUp, recursive = True)``
        """
        return self.finalize(roundUp = roundUp, recursive = True)

class UnboundedBox(Box):
    """A special type of box for use with the solver.
        
    When used with the solver, the solver will adjust the number of machines
    rather then the machine's throttle.

    The inner parameter must be a machine or a group of the form::

       Group(Mul(1,machine1), Mul(1,machine2), ...)

    i.e::

       1*machine1 + 1*machine2 + ...

    The inner `Mul` is important to give the solver a number to adjust.  The
    actual number is unimportant.

    An UnboundedBox can nest instead a normal box, which is useful to let
    the solver tell you the number of machines you need to support another
    machine.
    """
    _fallbackName = '<unbounded box>'
    def __init__(self, inner, **kwargs):
        """Create a new `UnboundedBox`, the parameters are the same as `Box`."""
        if not isinstance(inner, (Group, Mul)):
            inner = Group(Mul(1,inner))
        super().__init__(inner, **kwargs)
    def scale(self, factor):
        """Adjust the number of machines uniformly."""
        factor = frac(factor)
        for m in self.inner:
            m.num *= factor

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

    def resetThrottle(self):
        self.throttle = 1

def _finalizeInner(m, roundUp, recursive):
    if isinstance(m, Box) and recursive:
        m.finalize(roundUp = roundUp, recursive = True)
    elif isinstance(m, Group):
        _finalizeGroup(m, roundUp, recursive)
    elif isinstance(m, Mul) and isinstance(m.machine, (Machine, BlackBox)):
        throttle = m.num * m.machine.throttle
        if throttle == 0: return None
        if roundUp:
            m.num = ceil(throttle)
            m.machine.throttle = div(throttle, m.num)
        else:
            m.num = throttle
            m.machine.throttle = 1
    elif isinstance(m, Mul):
        m0 = _finalizeInner(m.machine, roundUp, recursive)
        if m0 is None: return None
        m.machine = m0
    return m

def _finalizeGroup(grp, roundUp, recursive):
    machines = []
    for m in grp:
        wasUnboundedBox = isinstance(m, UnboundedBox)
        m = _finalizeInner(m, roundUp, recursive)
        if m is None: continue
        # fixme: if recursive and wasUnboundedBox with a single machine
        # and no constraints then remove the box as is now unnecessary
        machines.append(m)
    grp.machines = machines

@dataclass
class FinalizeResult:
    factory: Box = None
    extraOutputs: list = field(default_factory=list)
    unusedInputs: list = field(default_factory=list)

class CantFinalizeError(ValueError):
    pass
    
