"""Classes for factorio entities.

Only entities needed in manufacturing something are included.  For example,
assmebling machines and beacons are included but power poles are not.

The class name is the same as the internal name but converted to title case
with any ``-`` removed.  For example, `mch.AssemblingMachine3`.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.

"""

from . import data as _data

def _find(toFind):
    from .config import gameInfo
    gi = gameInfo.get(None)
    if gi is None:
        raise RuntimeError("config.gameInfo not defined: call setGameInfo first")
    return gi.mch._find(toFind)

_find.__doc__ = _data.Objs._find.__doc__

def __getattr__(name):
    from .config import gameInfo
    gi = gameInfo.get(None)
    if gi is None:
        raise RuntimeError("config.gameInfo not defined: call setGameInfo first")

    if name == '__all__':
        return tuple(gi.mch.__dict__.keys())

    try:
        return gi.mch.__dict__[name]
    except KeyError:
        raise AttributeError(f"current 'mch' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    try:
        symbols = gameInfo.get().mch.__dict__.keys()
    except LookupError:
        symbols = ()
    return ['_find', '__all__', *symbols]
