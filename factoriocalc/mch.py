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
    return gameInfo.get().mch._find(toFind)
_find.__doc__ = _data.Objs._find.__doc__

def __getattr__(name):
    from .config import gameInfo
    obj = gameInfo.get().mch
    try:
        return obj.__dict__[name]
    except KeyError:
        if name == '__all__':
            return tuple(obj.__dict__.keys())
        raise AttributeError(f"current 'mch' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    return ['_find', '__all__', *gameInfo.get().mch.__dict__.keys()]

