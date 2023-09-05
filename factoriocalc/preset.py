"""Useful presets.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.
"""

def __getattr__(name):
    from .config import gameInfo

    if name == '__all__':
        return tuple(gameInfo.get().presets.keys())

    try:
        return gameInfo.get().presets[name]
    except KeyError:
        raise AttributeError(f"'{name}' not found in current presets") from None

def __dir__():
    from .config import gameInfo
    return ['__all__', *gameInfo.get().presets.keys()]
