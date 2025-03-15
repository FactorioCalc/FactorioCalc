"""Symbols for items and fluids in factorio.

The name of the symbol is the same as the internal name but with ``-``
converted to ``_``.  For example, to refer to an "electronic-circuit" use
`itm.electronic_circuit`.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.
"""

from . import data as _data

def _find(toFind):
    from .config import gameInfo
    gi = gameInfo.get(None)
    if gi is None:
        raise RuntimeError("config.gameInfo not defined: call setGameInfo first")
    return gi.itm._find(toFind)

_find.__doc__ = _data.Objs._find.__doc__

def __getattr__(name):
    from .config import gameInfo
    gi = gameInfo.get(None)
    if gi is None:
        raise RuntimeError("config.gameInfo not defined: call setGameInfo first")

    try:
        return gi.itm.__dict__[name]
    except KeyError:
        raise AttributeError(f"current 'itm' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    try:
        symbols = gameInfo.get().itm.__dict__.keys()
    except LookupError:
        symbols = ()
    return ['_find', *symbols]
