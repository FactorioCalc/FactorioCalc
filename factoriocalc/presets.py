"""Useful presets.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.
"""

def __getattr__(name):
    from .config import gameInfo
    gi = gameInfo.get(None)
    if gi is None:
        raise RuntimeError("config.gameInfo not defined: call setGameInfo first")

    if name == '__all__':
        return tuple(gi.presets.keys())

    try:
        return gi.presets[name]
    except KeyError:
        raise AttributeError(f"'{name}' not found in current presets") from None

def __dir__():
    from .config import gameInfo
    try:
        symbols = gameInfo.get().presets.keys()
    except LookupError:
        symbols = ()
    return ['__all__', *symbols]
