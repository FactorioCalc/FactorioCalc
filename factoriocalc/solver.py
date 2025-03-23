"""Solver intervals.

Example::

  >>> from factoriocalc import *
  >>> config.machinePrefs.set(MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8, ChemicalPlant:8, OilRefinery:12}))
  >>> rocketFuel = UnboundedBox(1*rcp.advanced_oil_processing()
                                + 1*rcp.heavy_oil_cracking()
                                + 1*rcp.light_oil_cracking()
                                + 1*rcp.solid_fuel_from_light_oil()
                                + 1*rcp.solid_fuel_from_petroleum_gas()
                                + 1*rcp.rocket_fuel(),
                                outputs = [itm.rocket_fuel@6])
  >>> solver = rocketFuel.solver()
  >>> solver.reset()
  <SolveRes.UNSOLVED: -2>
  >>> solver.print()
  +113.258*light-oil-cracking-m -45.5*solid-fuel-from-petroleum-gas-m +18.0360*solid-fuel-from-light-oil-m +1.45345*rocket-fuel-m = 0 (140251354372976-petroleum-gas)
  +2.9575*solid-fuel-from-light-oil-m +2.9575*solid-fuel-from-petroleum-gas-m -1.83333*rocket-fuel-m = 0 (140251354372976-solid-fuel)
  +0.256667*rocket-fuel-m = 6 (140251354372976-rocket-fuel)
  advanced-oil-processing-m = +0.577677*light-oil-cracking-m +0.192559*solid-fuel-from-light-oil-m +0.0155176*rocket-fuel-m
  heavy-oil-cracking-m = +0.270270*light-oil-cracking-m +0.0900901*solid-fuel-from-light-oil-m +0.00726001*rocket-fuel-m
  max (inputs): -200.209*light-oil-cracking-m -43.9865*solid-fuel-from-light-oil-m -3.54470*rocket-fuel-m
    aux (water): -124.534*light-oil-cracking-m -18.7613*solid-fuel-from-light-oil-m -1.51190*rocket-fuel-m
    aux (crude-oil): -75.6757*light-oil-cracking-m -25.2252*solid-fuel-from-light-oil-m -2.03280*rocket-fuel-m
  >>> solver.tableau.print()
        -0-    -1-    -2-    -3-   -4-  -5-  -6-
      light- solid- solid- rocket  a0   a1   p2  |    rhs
   0:  0.635 -0.255  0.101  0.008  *1*   0    0  |     0     | -4- a0
   1:    0    0.381  0.381 -0.236   0   *1*   0  |     0     | -5- a1
   2:    0      0      0      1     0    0   *1* |  23.3766  | -6- p2

   3: -0.635 -0.126 -0.482  0.228   0    0    0  |     0     | max
   4:    0      0      0     -1     0    0    0  | -23.3766  | max
  >>> solver.tableau.solve(zero=True)
  <SolveRes.OPTIMAL: 1>
  >>> solver.tableau.solve(zero=True)
  <SolveRes.OPTIMAL: 1>
  >>> solver.tableau.addPendingObjective()
  >>> solver.tableau.print()
        -0-    -1-    -2-    -3-
      light- solid- solid- rocket |    rhs
   0:   *1*     0    0.560    0   |  5.52158  | -0- light-oil-cracking-m
   1:    0     *1*     1      0   |  14.4910  | -1- solid-fuel-from-petroleum-gas-m
   2:    0      0      0     *1*  |  23.3766  | -3- rocket-fuel-m

   3:    0      0   -68.32    0   | -1188.34  | max (inputs)
   4:    0      0   -51.10    0   | -722.966  | aux (water)
   5:    0      0   -17.22    0   | -465.369  | aux (crude-oil)
  >>> solver.tableau.solve()
  <SolveRes.UNIQUE: 2>
  >>> solver.tableau.print()
        -0-    -1-    -2-    -3-
      light- solid- solid- rocket |    rhs
   0:  1.782    0     *1*     0   |  9.84266  | -2- solid-fuel-from-light-oil-m
   1: -1.782   *1*     0      0   |  4.64834  | -1- solid-fuel-from-petroleum-gas-m
   2:    0      0      0     *1*  |  23.3766  | -3- rocket-fuel-m

   3:  121.8    0      0      0   | -515.807  | max (inputs)
   4:  91.09    0      0      0   | -220.004  | aux (water)
   5:  30.70    0      0      0   | -295.803  | aux (crude-oil)
  >>> solver.tableau.solution().print()
  Solution:
    light-oil-cracking-m = 0
    solid-fuel-from-petroleum-gas-m = 4.64833996
    solid-fuel-from-light-oil-m = 9.84266354
    rocket-fuel-m = 23.3766234
  Other:

"""

from __future__ import annotations
from enum import Enum,Flag
import operator
from random import Random
from copy import deepcopy
from numbers import Number
from types import SimpleNamespace
from functools import partialmethod
from collections import defaultdict
from collections.abc import Mapping
import io
import os
import itertools
from typing import NamedTuple
from dataclasses import dataclass,field
import sys

from . import itm,config
from .fracs import Inf,NaN,frac,div,isfinite
from .ordenum import OrdEnum
from .core import *
from .box import *
from .core import _fmt_rate

__all__ = ('Var', 'Term', 'SolveRes', 'Cond', 'EQ', 'GE', 'LE',
           'LinearEqId', 'Terms', 'LinearEq', 'VarGroup', 'LinearEqSystem',
           'Solver', 'SlackVar', 'ArtificialVar', 'PartialVar', 'OptFun',
           'Tableau', 'Solution')

class Var:
    __slots__ = ('id', 'name', 'max')
    def __init__(self, id, name = None, max = 1):
        if name is None:
            name = id
        if type(name) is not str:
            raise ValueError
        self.id = id
        self.name = name
        self.max = max
    def __eq__(self, other):
        if type(other) is Var:
            return self.id == other.id
        else:
            return self.id == other
    def __hash__(self):
        return hash(self.id)
    def __str__(self):
        return self.name
    def __repr__(self):
        return f'<var: {self.name}>'

class Term(tuple):
    """Term(var, rate)"""
    __slots__ = ()
    var = property(operator.itemgetter(0))
    var.__doc__ = None
    rate = property(operator.itemgetter(1))
    rate.__doc__ = None
    def __new__(cls, *args):
        l = len(args)
        if l == 0:
            args = (None, 0)
        elif l == 1:
            args = (None, args[0])
        return tuple.__new__(cls, args)
    def __str__(self):
        rate = f'{self.rate:.6g}'
        if self.var == None:
            return rate
        else:
            return f'{self.var}*{rate}'
    def __repr__(self):
        return f'Term({self.var!r}, {self.rate!r})'

class SolveRes(OrdEnum):
    """Result of solving a linear equation system.

    The values of the enum are subject to change, but the relative order should be stable.

    """

    #: not yet solved
    UNSOLVED = -2

    #: already solved
    NOOP = -1

    #: a solution was found, no test for uniqueness was done
    OPTIMAL = 1

    #: all output machines are at there maxium giving the constraints
    UNIQUE = 2

    #: output machines are at there maxium giving the constraints
    #: but there are multiple possible configurations
    MULTI = 3

    #: a solution was found but some machines are not at there maxium output,
    #: to make the solution unique add additional constraints or priorities
    OK = 4

    #: a partial solution was found by removing constraints
    PARTIAL = 5

    #: the system is unbounded, a partial solution was found by setting
    #: unbounded vars to 0
    UNBOUNDED = 6

    # #: no solution was found (unused)
    # ERROR = 9

    # fixme ?: maybe use flags to return more information as a solution can be
    #   both partial and unique
    # SOLVED = 1
    # UNIQUE = 2
    # MULTI  = 4
    # PARTIAL = 8
    # UNBOUNDED = 16

    def ok(self):
        return self < SolveRes.PARTIAL
    def notok(self):
        return self >= SolveRes.PARTIAL
    def failed(self):
        return self >= SolveRes.UNBOUNDED

class Cond(NamedTuple):
    order: int
    symbol: str
    fun: Callable[[Rational, Rational], bool]
    def __call__(self, x, y = 0):
        return self.fun(x,y)
    def __repr__(self):
        return '<Cond "{}">'.format(self.symbol)
    def __eq__(self, other):
        return id(self) == id(other)
    def __ne__(self, other):
        return id(self) != id(other)
    def __copy__(self):
        return self
    def __deepcopy__(self, memo):
        return self

EQ = Cond(1, '=', operator.eq)
GE = Cond(2, '>=', operator.ge)
LE = Cond(3, '<=', operator.le)
Cond.NONE = Cond(5, '?', None)

class LinearEqId(NamedTuple):
    boxid: int
    item: Union[Var,Ingredient]
    qualifier: str = ''
    def __str__(self):
        if self.qualifier:
            return f'{self.boxid}_{self.item}_{self.qualifier}'
        else:
            return f'{self.boxid}_{self.item}'
    def __repr__(self):
        return f'<eqid: {self}>'

@dataclass
class Terms(dict):
    def __init__(self, terms = ()):
        if isinstance(terms, Mapping):
            super().__init__(terms)
        else:
            for vals in terms:
                self.__iadd__(vals)

    def __getitem__(self):
        return self.get(other.var, 0)

    def asSeq(self):
        return tuple(Term(var, rate) for var, rate in self.items())

    def add(self, var, rate):
        rate = self.get(var, 0) + rate
        if rate == 0:
            self.pop(var)
        else:
            self[var] = rate

    def merge(self, other, mul = 1):
        if isinstance(other, Term):
            self.add(other.var, mul*other.rate)
            return self
        if isinstance(other, Mapping):
            itr = other.items()
        else:
            itr = iter(other)
        for var, rate in itr:
            self.add(var, mul*rate)
        return self

    def apply(self, values = None):
        if values is None:
            values = {}
        res = 0
        for var, rate in self.items():
            res += rate * values.get(var, var.max)
        return res

    def sub(self, var, repl):
        factor = self.pop(var, 0)
        if factor == 0:
            return self
        return self.merge(repl, factor)

    def subAll(self, repl):
        vars = [var for var in self.keys() if var in repl]
        for var in vars:
            self.sub(var, repl[var])
        return self

    def neg(self):
        for var, rate in self.items():
            self[var] = -rate
        return self

    def __str__(self):
        return fmt_terms(self.items())
    __iadd__ = merge
    __isub__ = partialmethod(merge, mul = -1)
    def __imul__(self, other):
        if not isinstance(other, Number):
            return NotImplemented
        for var in self.keys():
            self[var] *= other
        return self
    def __itruediv__(self, other):
        if not isinstance(other, Number):
            return NotImplemented
        for var, rate in self.items():
            self[var] = div(rate, other)
        return self

def _asTerms(terms):
    if isinstance(terms, Terms):
        return terms
    else:
        return Terms(terms)

def fmt_terms(terms):
    return ' '.join('{}{}'.format('+' if rate == 1 else '-' if rate == -1 else f'{rate:+.6g}*', var) for var, rate in terms)

@dataclass(frozen = True)
class LinearEq:
    # the linear equation is: terms... <cond> rate
    # i.e if cond is EQ then: terms... = rate
    id: LinearEqId
    terms: tuple
    cond: Cond = None
    rate: Rational = None
    def __post_init__(self):
        assert(type(self.terms) is tuple)
    def _replace(self, **changes):
        import dataclasses as dc
        return dc.replace(self, **changes)
    def flow(self, solution, default = Inf):
        rateOut = 0
        rateIn = 0
        for term in self.terms:
            if term.rate > 0:
                rateOut += term.rate*solution.get(term.var, default)
            elif term.rate < 0:
                rateIn -= term.rate*solution.get(term.var, default)
        return Flow(self.id, rateOut = rateOut, rateIn = rateIn)
    def solved(self, solution, default = Inf):
        rate = self.flow(solution, default).rate()
        return self.cond(rate, self.rate) is True
    def __str__(self):
        return f'{fmt_terms(self.terms)} {self.cond.symbol} {self.rate:.6g} ({self.id})'
    def sympify(self):
        from sympy import Number,Symbol,Eq,Ge,Le
        terms = sum(Number(term.rate) * Symbol(term.var.name) for term in self.terms)
        if self.cond is EQ:
            return Eq(terms, Number(self.rate))
        elif self.cond is GE:
            return Ge(terms, Number(self.rate))
        elif self.cond is LE:
            return Le(terms, Number(self.rate))
        else:
            raise ValueError

class _Target(NamedTuple):
    cond: Cond
    rate: Rational

@dataclass
class _LinearEq:
    id: Ingredient
    terms: list[Term] = field(default_factory = list)
    target: list[_Target] = field(default_factory = list)

class _Eqs(dict):
    def __missing__(self, id):
        val = self[id] = _LinearEq(id)
        return val

class VarGroup(Group):
    def __init__(self, var):
        super().__init__([])
        self.var = var

class LinearEqSystem:
    def print(self, out = None, prefix=''):
        out = sys.stdout if out is None else out
        for eq in self.eqs.values():
            out.write(f'{prefix}{eq}\n')
        byPrior = defaultdict(list)
        for var, p in self.priorities.items():
            byPrior[p].append(var)
        for p in sorted(byPrior.keys(), reverse = True):
            vars = ', '.join(str(var) for var in byPrior[p])
            out.write(f'{prefix}{vars} (priorities = {p})\n')
        outputs = sorted(self.outputs.keys(),
                         key = lambda item: self.outputPriorities.get(item, 0),
                         reverse = True)
        for item in outputs:
            terms = self.outputs[item]
            priorities = self.outputPriorities.get(item, None)
            if priorities is None:
                out.write(f'{prefix}{item} = {fmt_terms(terms)} (output)\n')
            else:
                out.write(f'{prefix}{item} = {fmt_terms(terms)} (output; priorities = {priorities})\n')
        for item, terms in self.inputs.items():
            out.write(f'{prefix}{item} = {fmt_terms(terms)} (input)\n')
        for item, terms in self.other.items():
            out.write(f'{prefix}{item} = {fmt_terms(terms)} (other)\n')


    @classmethod
    def fromBox(cls, box, *, _tally = None):
        byVar = {}
        eqs = _Eqs()
        priorities = {}
        outputPriorities = {}
        inputPriorities = {}

        machines = box.inner.flatten().machines

        def varInfo(m):
            m = m.machine
            if isinstance(m, BlackBox):
                return ((id(box), id(m)), 'BOX' if m.name is None else m.name)
            if m.recipe is None:
                return (None, 'unknown')
            name = m.recipe.alias
            b = m.bonus()
            productivity = b.productivity
            if productivity > 0:
                productivity = int(productivity*100)
                name = f'{name}_p{productivity:02d}'
            else:
                productivity = None
            quality = b.quality
            if quality > 0:
                quality = int(quality*1000)
                name = f'{name}_q{quality:03d}'
            else:
                quality = None
            fuel = getattr(m, 'fuel', None)
            if fuel is None:
                return ((id(box), m.recipe, productivity, quality), name)
            else:
                return ((id(box), m.recipe, productivity, quality, m.fuel), f'{name}_u_{fuel}')

        tally = _tally
        if tally is None:
            tally = defaultdict(dict)
        tally[''][id(box)] = len(tally['']) + 1

        for m in machines:
            (key, name) = varInfo(m)
            tally[name][key] = len(tally[name]) + 1

        inners = []
        for idx, m in enumerate(machines):
            if not isinstance(m.machine, Box):
                continue
            l = cls.fromBox(m.machine, _tally = tally)
            l.box = m.machine
            l *= m.num
            priorities.update(l.priorities) # fixme is this right
            inners.append(l)
            machines[idx] = None

        for m in machines:
            if m is None: continue # was a box, will handle latter
            (key, name) = varInfo(m)
            unbounded = getattr(m.machine, 'unbounded', False)
            suffix = 'm' if unbounded else 't'
            if len(tally[name]) > 1:
                num = tally[name][key]
                name = f'{name}_{num-1}_{suffix}'
            else:
                name = f'{name}_{suffix}'
            var = Var(key,name,Inf if unbounded else 1)
            if var not in byVar:
                byVar[var] = VarGroup(var)
            byVar[var].machines.append(m)

        for var, grp in byVar.items():
            grp.flows = grp.flows(throttle = 1)
            for flow in grp.flows:
                #assert(flow.rate() != 0)
                if flow.rate() == 0:
                    continue
                term = Term(var, flow.rate())
                eqs[flow.item].terms.append(term)

        for l in inners:
            for item, terms in l.external():
                eqs[item].terms += terms
            byVar.update(l.byVar)

        for (item,rate) in box.outputs.items():
            row = eqs[item]
            if rate is None:
                if any(term.rate < 0 for term in row.terms):
                    row.target.append(_Target(GE, 0))
            else:
                row.target.append(_Target(EQ, rate))
            if rate != 0:
                row.target.append(_Target(Cond.NONE, 1))
        for (item,rate) in box.inputs.items():
            assert(item not in box.outputs)
            row = eqs[item]
            if rate is None:
                if any(term.rate > 0 for term in row.terms):
                    row.target.append(_Target(LE, 0))
            else:
                row.target.append(_Target(EQ, rate))
            if rate != 0:
                row.target.append(_Target(Cond.NONE, -1))
        for item in box.unconstrained:
            eqs[item].target = [_Target(Cond.NONE, 0)]
        for row in eqs.values():
            if not row.target and row.id is not itm.electricity:
                row.target = [_Target(EQ, 0)]
        for item, rate in box.simpleConstraints.items():
            row = eqs[item]
            row.target.append(_Target(GE, rate))
            if rate < 0 and any(term.rate > 0 for term in row.terms):
                row.target.append(_Target(LE, 0))

        ###

        emptyBarrel = config.gameInfo.get().emptyBarrel

        for (var, grp) in byVar.items():
            for flow in grp.flows:
                if flow.item in box.priorities and flow.item in box.outputs:
                    outputPriorities[flow.item] = box.priorities[flow.item]
                elif flow.item in box.priorities and flow.item in box.inputs:
                    inputPriorities[flow.item] = box.priorities[flow.item]
                elif flow.item in box.outputs and box.outputs[flow.item] is None and flow.item != emptyBarrel:
                    outputPriorities[flow.item] = 0

        byRecipe = {}
        for var in byVar:
            if var.id is None: continue
            byRecipe.setdefault(var.id[0:2], []).append(var)
        byId = {}
        for var in byVar:
            byId[var.id] = var

        for key0, prior in box.priorities.items():
            if isinstance(key0, Ingredient):
                pass
            elif isinstance(key0, Recipe):
                key = (id(box), key0)
                for var in byRecipe.get(key, []):
                    priorities[var] = prior
            elif isinstance(key0, Box._FakeMachine):
                key, _ = varInfo(key0)
                if key in byId:
                    priorities[byId[key]] = prior
            else:
                raise ValueError(key0)

        # fixme: still needed?
        toDel = [var for var, priority in priorities.items() if priority <= IGNORE]
        for var in toDel:
            del priorities[var]

        ###

        origEqs = eqs
        eqs = {}
        external = {1: {}, -1: {}, 0: {}, None: {}}
        for eq in sorted(origEqs.values(), key = lambda v: v.target):
          if not eq.terms:
              continue
          for target in eq.target:
              if target.cond is Cond.NONE:
                  external[target.rate][eq.id] = tuple(eq.terms)
                  external[None][eq.id] = tuple(eq.terms)
                  continue
              q = ''
              if target.cond is GE:
                  q = 'ge'
              elif target.cond is LE:
                  q = 'le'
              eqId = LinearEqId(id(box), eq.id, q)
              eqs[eqId] = LinearEq(eqId, tuple(eq.terms), target.cond, target.rate)

        for i, c in enumerate(box.otherConstraints):
            if isinstance(c, AtLeast):
                raise NotImplementedError
            elif isinstance(c, Equal):
                for j in range(len(c)-1):
                   mul1, item1 = c[j]
                   mul2, item2 = c[j+1]
                   eqId = LinearEqId(id(box), item1, f'c{i}')
                   eqs[eqId] = LinearEq(eqId,
                                        (*(Term(v, r*mul1) for v, r in external[None][item1]),
                                         *(Term(v, -r*mul2) for v, r in external[None][item2])),
                                        EQ, 0)

        #sortedEqs = sorted(eqs.values(), key = lambda v: v.target)
        #eqs = {row.id: row for row in sortedEqs}

        ###

        for l in inners:
            for eqId, eq in l.eqs.items():
                if eqId.qualifier == '':
                    eqId = eqId._replace(qualifier = 'b{}'.format(str(tally[''][id(l.box)] - 1)))
                eqs[eqId] = eq._replace(id = eqId)

        obj = LinearEqSystem()
        obj.eqs = eqs
        obj.byVar = byVar
        obj.outputs = external[1]
        obj.inputs = external[-1]
        obj.other = external[0]
        obj.priorities = priorities
        obj.outputPriorities = outputPriorities
        obj.inputPriorities = inputPriorities
        return obj

    def __imul__(self, num):
        if num == 1:
            return self
        for eqId, eq in self.eqs.items():
            self.eqs[eqId] = eq._replace(terms = tuple(Term(var, rate*num) for var, rate in eq.terms),
                                         rate = eq.rate * num)
        for io in (self.outputs, self.inputs, self.other):
            for item, terms in io.items():
                io[item] = tuple(Term(var, rate*num) for var, rate in terms)
        return self

    def external(self):
        return [*self.outputs.items(), *self.inputs.items(), *self.other.items()]

    def sympify(self):
        from sympy import Symbol
        return {'eqs': [eq.sympify() for eq in self.eqs.values()],
                'vars': [Symbol(var.name) for var in self.byVar.keys()]}

    def solver(self):
        return Solver(self)

@dataclass
class _Equation:
    id: LinearEqId
    terms: Terms
    cond: Cond
    rhs: Term
    def __str__(self):
        return f'{self.terms} {self.cond.symbol} {self.rhs} ({self.id})'

def _simplify(leq):
    eqs = []
    for eq in leq.eqs.values():
        eqs.append(_Equation(eq.id, Terms(eq.terms), eq.cond, Term(eq.rate)))
    ZERO = 0
    while True:
        candidates = {}
        for eq in eqs:
            if eq.rhs.rate != 0: continue
            posVars = [var for var, rate in eq.terms.items() if rate > 0]
            allPositive = len(posVars) == len(eq.terms) and (eq.cond is EQ or eq.cond is LE)
            allNegative = len(posVars) == 0             and (eq.cond is EQ or eq.cond is GE)
            if allPositive or allNegative:
                # the only possible solution to an allPositive or allNegative
                # equation is to set all the variables to zero
                for var in eq.terms.keys():
                    candidates[var] = ZERO
            elif eq.cond is EQ and len(posVars) == 1:
                # if there is only one positive term then tentatively use
                # substitution to eliminate that variable, but only if the
                # substitution is unique
                var = posVars[0]
                if var not in candidates:
                    candidates[var] = eq
                elif candidates[var] is not ZERO:
                    # if `var` is already in candidates (and not ZERO) than that
                    # means the substitution is not unique, so mark it as such
                    candidates[var] = None
        for var in list(candidates.keys()):
            if candidates[var] is None:
                del candidates[var]
        if not candidates:
            break
        for var, eq in candidates.items():
            # first rewrite the equation in the form:
            #   terms = var
            if eq is ZERO:
                eqs.append(_Equation(None, Terms(), EQ, Term(var,1)))
                terms = ()
            elif eq.terms:
                factor = -eq.terms.pop(var)
                eq.terms /= factor
                eq.rhs = Term(var, 1)
                terms = eq.terms
            else: # empty eq - it can happen, see KrastorioTests.testLithiumFactory1
                eq.rhs = Term(var, 1)
                terms = eq.terms
            # then use substitution to eliminate var from all other equations
            for eq2 in eqs:
                eq2.terms.sub(var, terms)
    return eqs

class Solver:
    def __init__(self, leqs):
        self.leqs = leqs
        self.eqs = None

    def reset(self, simplify = True):
        """Reset the state and does preliminary work for solving.

        Called automatically by solve().  But can be called manually to get
        access to the underlying tableau.

        """
        self.subs = {}
        self._result = SolveRes.UNSOLVED
        self._invalidEqs = []
        if simplify:
            self.eqs = []
            eqs = _simplify(self.leqs)
            for eq in eqs:
                if eq.rhs.var is None:
                    if eq.terms:
                        if eq.cond is GE and eq.rhs.rate == 0 and all(rate >= 0 for rate in eq.terms.values()):
                            # always true
                            pass
                        else:
                            self.eqs.append(LinearEq(eq.id, eq.terms.asSeq(), eq.cond, eq.rhs.rate))
                    elif not eq.cond(0, eq.rhs.rate):
                        self._invalidEqs.append(eq)
                        self._result |= SolveRes.PARTIAL
                    else:
                        pass
                else:
                    assert(eq.cond is EQ)
                    assert(eq.rhs.rate == 1)
                    var = eq.rhs.var
                    self.subs[var] = eq.terms
                    if var.max != Inf and eq.terms.apply() > var.max:
                        self.eqs.append(LinearEq(eq.id, eq.terms.asSeq(), LE, var.max))
        else:
            self.eqs = self.leqs.eqs.values()

        priorities = defaultdict(dict)
        for item, terms in self.leqs.outputs.items():
            try:
                p = self.leqs.outputPriorities[item]
            except KeyError:
                continue
            if p <= IGNORE:
                continue
            for term in terms:
                if term.rate > 0:
                    priorities[p][term.var] = 1
                elif term.rate < 0 and term.var not in priorities[p]:
                    priorities[p][term.var] = -1

        for var, p in self.leqs.priorities.items():
            priorities[p][var] = 1

        objectives = []
        for p in sorted(priorities.keys(), reverse=True):
            toMax, toMin = [], []
            for var, direction in priorities[p].items():
                if direction > 0:
                    toMax.append(var)
                else:
                    toMin.append(var)
            if toMax:
                # maximize all vars
                objtv = [OptFun(defaultdict(dict), f'{p}_max')]
                for var in toMax:
                    objtv[0].terms[var] = 1
                    objtv.append(OptFun({var: 1}, var))
                objectives.append(objtv)
            if toMin:
                # minimize all vars
                objtv = [OptFun(defaultdict(dict), f'{p}_min')]
                for var in toMin:
                    objtv[0].terms[var] = -1
                    objtv.append(OptFun({var: -1}, var))
                objectives.append(objtv)

        # minimize the amount of extra output
        alsoOutput = [item for item, p in self.leqs.outputPriorities.items() if p <= IGNORE]
        if alsoOutput:
           also = [OptFun(Terms(self.leqs.outputs[item] for item in alsoOutput).neg(), 'also-output')]
           for item in alsoOutput:
               also.append(OptFun(Terms(self.leqs.outputs[item]).neg(), item))
           objectives.append(also)

        ignoredInputs, inputs = {}, {}
        for item, terms in self.leqs.inputs.items():
            if self.leqs.inputPriorities.get(item, Inf) <= IGNORE:
                ignoredInputs[item] = terms
            else:
                inputs[item] = terms

        # maximize the machines that produce an ignored input
        if ignoredInputs:
            also = [OptFun(defaultdict(dict), 'ignored-inputs')]
            for item, terms in ignoredInputs.items():
                also.append(OptFun(Terms(terms), item))
                for term in terms:
                    if term.rate > 0:
                        also[0].terms[term.var] = 1
            objectives.append(also)

        # minimize the amount of input by maximizing the total input flow as
        # input valaues are always negative
        if inputs:
            also = [OptFun(Terms(inputs.values()), 'inputs')]
            for item, terms in inputs.items():
                also.append(OptFun(Terms(terms), item))
            objectives.append(also)

        self.objectives = [*map(lambda objs: [*map(lambda obj: OptFun(_asTerms(obj.terms).subAll(self.subs), obj.note),
                                                   objs)],
                                objectives)]

        self.tableau = Tableau(self.eqs, self.objectives)
        return self._result

    prep = reset

    def print(self, out = None):
        out = sys.stdout if out is None else out
        if self.eqs is None:
            out.write('<<uninitialized>>\n')
            return
        for eq in self.eqs:
            out.write(f'{eq}\n')
        for var, terms in self.subs.items():
            out.write(f'{var} = {terms}\n')
        for objective in self.objectives:
            out.write(f'max ({objective[0].note}): {fmt_terms(objective[0].terms.items())}\n')
            for i in range(1,len(objective)):
                out.write(f'  aux ({objective[i].note}): {fmt_terms(objective[i].terms.items())}\n')

    def solve(self):
        """Solve the linear equation system."""
        if self.eqs is None or self.subs is None:
            self.reset()
        self._result |= self.tableau.solveAll()

    def _sanity(self):
        solution, other = self.tableau.solution()
        for eq in self.eqs:
            assert(eq.solved(solution))

    def solution(self):
        """Return the solution to the solved linear equation.

        Return a tuple pair. The first component is a SolveRes.  The second
        component is a `dict` with the solution to the system.
        """
        solution, other = self.tableau.solution()
        res = self._result
        if res.ok() and other:
            for value in other.values():
                if value != 0:
                    res = SolveRes.PARTIAL
        for var, terms in self.subs.items():
            rate = 0
            for v, r in terms.items():
                try:
                    rate += r * solution[v]
                except KeyError:
                    if isfinite(v.max):
                        rate += r * v.max
                    else:
                        res |= SolveRes.UNBOUNDED
            solution[var] = rate
        return res, solution

    def apply(self):
        """Apply the solution the the underlying box.

        Returns the same value as solution().
        """
        res, solution = self.solution()
        if res.failed():
            return res, solution
        for var,grp in self.leqs.byVar.items():
            grp.setThrottle(solution.get(var, 1))
        return res, solution


@dataclass(frozen=True)
class SlackVar:
    __slots__ = ('rowIdx')
    rowIdx: int
    def __str__(self):
        return f's{self.rowIdx}'

@dataclass(frozen=True)
class ArtificialVar:
    __slots__ = ('rowIdx')
    rowIdx: int
    def __str__(self):
        return f'a{self.rowIdx}'

@dataclass(frozen=True)
class PartialVar(ArtificialVar):
    __slots__ = ()
    def __str__(self):
        return f'p{self.rowIdx}'

class OptFun(NamedTuple):
    terms: Any
    note: Any = None

@dataclass
class _OptFun:
    label: str # 'max' or 'aux'
    terms: Any
    note: Any = None
    nonOptimal: bool = False

class Tableau:
    def __init__(self, eqs, objectives):
        cols = []
        eqs0 = eqs
        eqs = {}

        def addEq(terms, minv, maxv, id = None):
            #assert(minv <= maxv)
            factor = 0
            for var, rate in terms:
                factor += abs(rate)
                if var not in cols:
                    cols.append(var)
            assert(factor != 0)
            if minv <= 0 and maxv == Inf:
                factor *= -1
            terms = frozenset(Term(var, div(rate, factor)) for var, rate in terms)
            minv = div(minv, factor)
            maxv = div(maxv, factor)
            if factor < 0:
                minv, maxv = maxv, minv
            orig = eqs.get(terms, None)
            if orig is None:
                combined = (minv, maxv, [id])
            else:
                combined = (max(orig[0], minv),
                            min(orig[1], maxv),
                            orig[2] + [id])
            eqs[terms] = combined

        for eq in eqs0:
            if eq.cond is EQ:
                addEq(eq.terms, eq.rate, eq.rate, eq.id)
            elif eq.cond is LE:
                addEq(eq.terms, -Inf, eq.rate, eq.id)
            elif eq.cond is GE:
                addEq(eq.terms, eq.rate, Inf, eq.id)
            else:
                raise ValueError

        for var in cols:
            if var.max != Inf:
                t = (Term(var, 1),)
                addEq(t, -Inf, var.max)

        eql = []
        self.rowInfo = []
        for rowIdx, (terms, (minv,maxv,ids)) in enumerate(eqs.items()):
            self.rowInfo.append({'ids': ids})
            if minv == maxv:
                eql.append((terms, EQ, minv))
                continue
            #assert(minv < maxv)
            if minv > -Inf:
                terms0 = frozenset(Term(var, -rate) for var, rate in terms)
                max0 = -minv
                eql.append((terms0, LE, max0))
            if maxv < Inf:
                eql.append((terms, LE, maxv))

        self.cols = cols

        slackVarsOffset = len(cols)
        slackVars = {}
        for rowIdx, (_, cond, _) in enumerate(eql):
            if cond is LE:
                slackVars[rowIdx] = slackVarsOffset + len(slackVars)
                cols.append(SlackVar(rowIdx))

        artificialVarsOffset = len(cols)
        artificialVars = {}
        for rowIdx, (_, cond, rhs) in enumerate(eql):
            if rhs < 0 or cond is EQ:
                artificialVars[rowIdx] = artificialVarsOffset + len(artificialVars)
                if rhs == 0:
                    cols.append(ArtificialVar(rowIdx))
                else:
                    cols.append(PartialVar(rowIdx))

        self.zeroed = [False]*len(cols)
        self.colsByVar = colsByVar = {var: idx for idx, var in enumerate(cols)}
        self._unboundedVars = []

        self.tableau = []
        self.basic = []
        self._cleared = None
        for rowIdx, (terms, cond, rhs) in enumerate(eql):
            sign = 1 if rhs >= 0 else -1
            row = [0] * (len(cols) + 1)
            for term in terms:
                row[colsByVar[term.var]] = sign*term.rate
            if rowIdx in slackVars:
                assert(cond is LE)
                colIdx = slackVars[rowIdx]
                row[colIdx] = sign
            if rowIdx in artificialVars:
                colIdx = artificialVars[rowIdx]
                row[colIdx] = 1
            # a row must have an slackVars or artificialVars so colIdx must be defined
            self.basic.append(self.cols[colIdx])
            row[-1] = sign*rhs
            self.tableau.append(row)
        self.optFunBegin = len(self.tableau)
        self.optFunInfo = [None]*len(self.tableau)
        self.allOptFuns = []
        if artificialVars:
            objective1 = {}
            objective2 = {}
            for rowIdx, colIdx in artificialVars.items():
                if type(self.cols[colIdx]) is not PartialVar:
                    objective1[colIdx] = -1
                else:
                    objective2[colIdx] = -1
            if objective1:
                self.addObjective(objective1)
            if objective2:
                self.addObjective(objective2)

        self.pendingObjectives = objectives

    def print(self, out = None, ratioCol = None):
        if out is None:
            out = sys.stdout
        out.write('    ')
        for idx, var in enumerate(self.cols):
            s = f'-{idx}-'
            if type(var) is Var:
                out.write(f'{s:^7}')
            else:
                out.write(f'{s:^5}')
        out.write('\n')
        out.write('    ')
        for var in self.cols:
            if type(var) is Var:
                out.write(f'{var!s:^7.6}')
            else:
                out.write(f'{var!s:^5.4}')
        out.write('|    rhs    ')
        if ratioCol is not None:
            out.write(f'|   /{ratioCol}')
        out.write('\n')
        for rowIdx, row in enumerate(self.tableau):
            if rowIdx == self.optFunBegin:
                out.write('\n')
            rhs = row[-1]
            out.write(f'{rowIdx:2}: ')
            basic = self.basic[rowIdx] if rowIdx < len(self.basic) else None
            for var, rate in zip(self.cols, row):
                if type(var) is Var:
                    width = 7
                else:
                    width = 5
                if var == basic:
                    s = f'*{rate:.{width-3}g}*'
                else:
                    s = f'{rate: .{width-1}g}'
                out.write(f'{s:^{width}.{width-1}}')
            s = f'{rhs: .6g}'
            out.write(f'|{s:^11.11}')
            if rowIdx < self.optFunBegin:
                num = self.colsByVar[self.basic[rowIdx]]
                out.write(f'| -{num}- {basic}')
            else:
                out.write(f'| {self.optFunInfo[rowIdx].label}')
                if self.optFunInfo[rowIdx].note is not None:
                    out.write(f' ({self.optFunInfo[rowIdx].note})')
            out.write('\n')

    def normalize(self, rowIdx, colIdx):
        row = self.tableau[rowIdx]
        r = row[colIdx]
        if r == 1:
            return
        if r == 0:
            raise ZeroDivisionError
        for i, rate in enumerate(row):
            row[i] = div(rate, r)

    def clear(self, rowIdx, colIdx):
        self._cleared = None
        self.normalize(rowIdx, colIdx)
        for i, row in enumerate(self.tableau):
            if i == rowIdx: continue
            factor = row[colIdx]
            if factor == 0: continue
            for j, val in enumerate(self.tableau[rowIdx]):
                row[j] -= factor*val
        self.basic[rowIdx] = self.cols[colIdx]
        #assert(self.tableau[rowIdx][colIdx] == 1)

    def fixClearedCol(self, rowIdx, colIdx, rowIdxToFix):
        #assert(self.tableau[rowIdx][colIdx] == 1)
        row = self.tableau[rowIdxToFix]
        factor = row[colIdx]
        for j, val in enumerate(self.tableau[rowIdx]):
            row[j] -= factor*val

    def clearCol(self, colIdx):
        rowIdx = self.bestRow(colIdx)
        if rowIdx is not None:
            self.clear(rowIdx, colIdx)
        return rowIdx

    def zeroCol(self, colIdx):
        for row in self.tableau:
            row[colIdx] = 0
        self.zeroed[colIdx] = True

    def solution(self):
        res = {var: 0 for var in self.cols if type(var) is Var}
        other = {}
        for rowIdx, var in enumerate(self.basic):
            colIdx = self.colsByVar[var]
            assert self.tableau[rowIdx][colIdx] == 1
            sol = self.tableau[rowIdx][-1]
            if type(var) is Var:
                res[var] = sol
            elif type(var) is SlackVar and sol < 0:
                other[var] = sol
            elif isinstance(var, ArtificialVar):
                other[var] = sol
        return Solution(res,other)

    def allSolutions(self):
        assert self.optFunBegin == len(self.tableau)
        prev = {}
        sols = []
        # FIXME: Is this guaranteed to find all solutions?
        while True:
            encoding = self.encoding()
            if encoding in prev:
                colIdx = prev[encoding]
            else:
                sols.append(self.solution())
                colIdx = -1
            try:
                colIdx = self.cleared().index(-1, colIdx + 1)
            except ValueError:
                break
            prev[encoding] = colIdx
            self.clearCol(colIdx)
        return sols

    def ratios(self, colIdx):
        res = {}
        for i, row in enumerate(self.tableau[:self.optFunBegin]):
            #if row[-1] >= 0 and row[colIdx] > 0:
            if row[colIdx] > 0:
                r = div(row[-1], row[colIdx])
                if r >= 0:
                    res[i] = r
        return res

    def bestRow(self, colIdx, start = 0):
        try:
            row, ratio = min(self.ratios(colIdx).items(), key=operator.itemgetter(1))
        except ValueError:
            return None
        else:
            return row

    def cleared(self):
        if self._cleared:
            return self._cleared
        """-2: all zero, -1: not cleared, >= 0: colIdx"""
        cleared = [-2]*len(self.cols)
        for rowIdx, var in enumerate(self.basic):
            colIdx = self.colsByVar[var]
            cleared[colIdx] = rowIdx
        for colIdx, c in enumerate(cleared):
            if c == -2:
                for rowIdx in range(len(self.basic)):
                    if self.tableau[rowIdx][colIdx] != 0:
                        cleared[colIdx] = -1
        self._cleared = cleared
        return cleared

    def encoding(self):
        cleared = self.cleared()
        l = len(cleared) - 1
        return sum(0 if c < 0 else 1<<(l-i) for i,c in enumerate(cleared))

    #def copy(self): # broken, needs updating
    #    other = object.__new__(type(self))
    #    other.cols = self.cols
    #    other.colsByVar = self.colsByVar
    #    other.tableau = [row.copy() for row in self.tableau]
    #    other.optFunBegin = self.optFunBegin
    #    other.cleared = self.cleared.copy()
    #    return other

    def addObjective(self, terms, note = None, label = 'max'):
        if label not in ('max', 'aux'):
            raise ValueError("label must be 'max' or 'aux'")
        row = [0]*(len(self.cols) + 1)
        cleared = self.cleared()
        toClear = []
        for var, rate in terms.items():
            if type(var) is int:
                colIdx = var
            else:
                try:
                    colIdx = self.colsByVar[var]
                except KeyError:
                    continue
            if self.zeroed[colIdx]:
                continue
            row[colIdx] = -rate
            if cleared[colIdx] >= 0:
                toClear.append(colIdx)
        self.tableau.append(row)
        optFun = _OptFun(label, terms, note)
        self.optFunInfo.append(optFun)
        self.allOptFuns.append(optFun)
        for colIdx in toClear:
            self.fixClearedCol(cleared[colIdx], colIdx, -1)

    def max(self, rowIdx):
        if rowIdx < self.optFunBegin:
            raise ValueError(f'row {rowIdx} not an objective function')
        opt = self.tableau[rowIdx]
        res = SolveRes.NOOP
        while True:
            col, val = None, 0
            for j in range(0, len(opt) - 1):
                if opt[j] < val:
                    col = j
                    val = opt[j]
            if val == 0:
                break
            res |= SolveRes.OPTIMAL
            row = self.clearCol(col)
            if row is None:
                # The solution is likely unbounded, set the var to 0 to find a
                # partial solution
                self.zeroCol(col)
                self._unboundedVars.append(self.cols[col])
                res |= SolveRes.UNBOUNDED
        return res

    def solve(self, rowIdx = None, *, zero = False):
        if rowIdx is None:
            rowIdx = self.optFunBegin
            if rowIdx == len(self.tableau):
                return SolveRes.NOOP
        if rowIdx < self.optFunBegin:
            raise ValueError(f'row {rowIdx} not an objective function')

        opt = self.tableau[rowIdx]
        res = SolveRes.OPTIMAL
        if sum(v != 0 for v in opt) == 1:
            res = SolveRes.UNIQUE
        res |= self.max(rowIdx)

        unique = None
        # first determine the maxium value for each aux function
        i = rowIdx + 1
        while i < len(self.optFunInfo) and self.optFunInfo[i].label == 'aux':
            res0 = self.max(i)
            assert(res0.ok())
            self.optFunInfo[i].max = self.tableau[i][-1]
            i += 1
        # now fix the result
        res0 = self.max(rowIdx)
        assert(res0.ok())
        # now check that each aux function is at it's max
        i = rowIdx + 1
        while i < len(self.optFunInfo) and self.optFunInfo[i].label == 'aux':
            if self.optFunInfo[i].max > self.tableau[i][-1]:
                unique = False
                self.optFunInfo[i].optimal = False
                print(f'warning: non optimal: {self.optFunInfo[rowIdx].note}: {self.optFunInfo[i].note}')
                # ^fixme: find a better way to convey this information
            elif unique is None:
                unique = True
            i += 1
        if unique is True:
            res |= SolveRes.UNIQUE
        elif unique is False:
            res |= SolveRes.OK

        if zero:
            toClear = []
            for colIdx in range(0, len(opt) - 1):
                if type(self.cols[colIdx]) is Var:
                    if opt[colIdx] != 0:
                        self.zeroCol(colIdx)
                else:
                    if self.zeroed[colIdx] or opt[colIdx] != 0:
                        self.zeroed[colIdx] = False
                        toClear.append(colIdx)
            delStop = rowIdx + 1
            while delStop < len(self.optFunInfo) and self.optFunInfo[delStop].label == 'aux':
                delStop += 1
            del self.tableau[rowIdx:delStop]
            del self.optFunInfo[rowIdx:delStop]
            if toClear:
                _multiDel(self.cols, toClear)
                for row in self.tableau:
                    _multiDel(row, toClear)
            self.colsByVar = {var: idx for idx, var in enumerate(self.cols)}
        return res

    def addPendingObjective(self):
        lst = self.pendingObjectives.pop(0)
        itr = iter(lst)
        self.addObjective(*next(itr))
        for aux in itr:
            self.addObjective(*aux,'aux')

    def solveAll(self):
        res = SolveRes.NOOP
        while len(self.tableau) > self.optFunBegin:
            res |= self.solve(zero = True)
        while self.pendingObjectives:
            self.addPendingObjective()
            res |= self.solve(zero = True)
        if any(c == -1 for c in self.cleared()):
            res |= SolveRes.MULTI
        return res

def _multiDel(lst, idxsToDel):
    try:
        nextToDel = idxsToDel[0]
    except IndexError:
        return
    origIdx, newIdx = nextToDel, nextToDel
    i = 1
    origLen = len(lst)
    while origIdx < origLen:
        if origIdx == nextToDel:
            if i < len(idxsToDel):
                nextToDel = idxsToDel[i]
                i += 1
            else:
                nextToDel = -1
            origIdx += 1
        else:
            lst[newIdx] = lst[origIdx]
            origIdx += 1
            newIdx += 1
    del lst[newIdx:]

class Solution(NamedTuple):
    solution: dict
    other: dict
    def print(self, out = None):
        if out is None:
            out = sys.stdout
        out.write('Solution:\n')
        for var, rate in self.solution.items():
            out.write(f'  {var} = {rate:.9g}\n')
        out.write('Other:\n')
        for var, rate in self.other.items():
            out.write(f'  {var} = {rate:.9g}\n')

def walk(t):
    # note: likely broken
    prev = set()
    solutions = set()
    colLen, rowLen = len(t.cols), len(t.tableau)
    cnt = 0
    def step():
        nonlocal t, cnt
        cnt += 1
        prev.add(t.encoding())
        #print(f'{t.encoding():0{colLen}b} {cnt}')
        sol = t.solution()
        if not sol[1] and all(rate >= 0 for rate in sol[0].values()):
        #if all(rate >= 0 and rate <= 1 for rate in sol[0].values()):
            print(*(f'{rate:g}' for rate in sol[0].values()))
            solutions.add(tuple(sol[0].values()))
        for colIdx in range(colLen):
            if t.cleared[colIdx] > 0:
                continue
            for rowIdx in range(rowLen):
                if t.tableau[rowIdx][colIdx] != 0:
                    t1 = t.copy()
                    t1.clear(rowIdx, colIdx)
                    if t1.encoding() not in prev:
                        t = t1
                        return True
        return False
    while step():
        pass
    return solutions


