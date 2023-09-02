"""Classes for factorio entities.

Only entities needed in manufacturing something are included.  For example,
assmebling machines and beacons are included but power poles are not.

The class name is the same as the internal name but converted to title case
with any ``-`` removed.  For example, `mch.AssemblingMachine3`.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.

"""

def __getattr__(name):
    from .config import gameInfo
    try:
        return getattr(gameInfo.get().mch, name)
    except AttributeError:
        raise AttributeError(f"current 'mch' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    return gameInfo.get().mch.__dir__()
