"""Symbols for recipes (`~factoriocalc.Rcp`) in factorio.

The name of the symbol is the same as the internal name but with ``-``
converted to ``_``.  For example, to refer to the recipe for an
"electronic-circuit" use `rcp.electronic_circuit`.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.

"""

from . import data as _data

def _find(toFind):
    from .config import gameInfo
    return gameInfo.get().rcp._find(toFind)
_find.__doc__ = _data.Objs._find.__doc__

def __getattr__(name):
    from .config import gameInfo
    try:
        return gameInfo.get().rcp.__dict__[name]
    except KeyError:
        raise AttributeError(f"current 'rcp' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    return ['_find', *gameInfo.get().rcp.__dict__.keys()]

