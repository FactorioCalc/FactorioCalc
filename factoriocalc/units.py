from __future__ import annotations
from typing import NamedTuple as _NamedTuple

from .core import Electricity as _Electricity, Item as _Item
from .fracs import frac as _frac, div as _div

class Unit(_NamedTuple):
    abbr: str
    sep: str
    conv: Rational

def wagonsPerUnit(item, rate, conv):
    from .fracs import div
    try:
        wagonCapacity = item.stackSize*40
    except AttributeError:
        # assume item is a fluid
        wagonCapacity = 25000
    return div(conv * rate, wagonCapacity)

def wagonsPerMinute(*args):
    if len(args) == 1:
        flow = args[0]
        return wagonsPerUnit(flow.item, flow.rate(), 60)
    elif len(args) == 2:
        return wagonsPerUnit(args[0], args[1], 60)
    else:
        raise ValueError('usage: wagonsPerMinute(flow) or waginsPerMinute(item, rate)')

def rocketsPerUnit(item, rate, conv):
    from .fracs import div
    if item.weight == 0:
        return 0
    perRocket = div(1000000 , item.weight)
    if perRocket < 1:
        return 0
    return div(conv * rate, perRocket)

def rocketsPerMinute(*args):
    if len(args) == 1:
        flow = args[0]
        return rocketsPerUnit(flow.item, flow.rate(), 60)
    elif len(args) == 2:
        return rocketsPerUnit(args[0], args[1], 60)
    else:
        raise ValueError('usage: rocketsPerMinute(flow) or rocketsPerMinute(item, rate)')

# Units for the base game

UNIT_SECONDS        = Unit('s', '/',  1)
UNIT_MINUTES        = Unit('m', '/',  60)
UNIT_HOURS          = Unit('h',  '/', 3600)
UNIT_EXPRESS_BELTS  = Unit('eb', ' ', _frac(1, 45))
UNIT_FAST_BELTS     = Unit('fb', ' ', _frac(1, 30))
UNIT_TRANSFER_BELTS = Unit('tb', ' ', _frac(1, 15))
UNIT_MEGAWATT       = Unit('MW', ' ', 1)
UNIT_STACKS_PER_SEC = Unit('s/s', ' ', lambda item, rate: _div(rate,item.stackSize))
UNIT_STACKS_PER_MIN = Unit('s/m', ' ', lambda item, rate: 60*_div(rate,item.stackSize))
UNIT_WAGONS_PER_MIN = Unit('w/m', ' ', wagonsPerMinute)

DU_SECONDS =  ((_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_MINUTES =  ((_Electricity, UNIT_MEGAWATT), (None, UNIT_MINUTES))
DU_HOURS   =  ((_Electricity, UNIT_MEGAWATT), (None, UNIT_HOURS))
DU_EXPRESS_BELTS  = ((_Item, UNIT_EXPRESS_BELTS),  (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_FAST_BELTS     = ((_Item, UNIT_FAST_BELTS),     (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_TRANSFER_BELTS = ((_Item, UNIT_TRANSFER_BELTS), (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_STACKS_PER_SEC = ((_Item, UNIT_STACKS_PER_SEC), (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_STACKS_PER_MIN = ((_Item, UNIT_STACKS_PER_MIN), (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_WAGONS_PER_MIN = ((_Electricity, UNIT_MEGAWATT), (None, UNIT_WAGONS_PER_MIN))

# Units for Space Age

UNIT_TURBO_BELTS = Unit('tb', ' ', _frac(1, 60))
UNIT_STACKED_TURBO_BELTS    = Unit('stb', ' ', _frac(1, 60*4))
UNIT_STACKED_EXPRESS_BELTS  = Unit('seb', ' ', _frac(1, 45*4))
UNIT_STACKED_FAST_BELTS     = Unit('sfb', ' ', _frac(1, 30*4))
UNIT_STACKED_TRANSFER_BELTS = Unit('stb', ' ', _frac(1, 15*4))

DU_TURBO_BELTS = ((_Item, UNIT_TURBO_BELTS), (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_STACKED_TURBO_BELTS    = ((_Item, UNIT_STACKED_TURBO_BELTS),    (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_STACKED_EXPRESS_BELTS  = ((_Item, UNIT_STACKED_EXPRESS_BELTS),  (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_STACKED_FAST_BELTS     = ((_Item, UNIT_STACKED_FAST_BELTS),     (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))
DU_STACKED_TRANSFER_BELTS = ((_Item, UNIT_STACKED_TRANSFER_BELTS), (_Electricity, UNIT_MEGAWATT), (None, UNIT_SECONDS))

UNIT_ROCKETS_PER_MIN = Unit('r/m', ' ', rocketsPerMinute)
DU_ROCKETS_PER_MIN = ((_Item, UNIT_ROCKETS_PER_MIN), (_Electricity, UNIT_MEGAWATT), (None, UNIT_MINUTES))

__all__ = [sym for sym in globals() if not sym.startswith('_') and sym not in ('annotations')]
