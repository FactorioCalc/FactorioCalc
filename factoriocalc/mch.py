def __getattr__(name):
    from .config import gameInfo
    try:
        return getattr(gameInfo.get().mch, name)
    except AttributeError:
        raise AttributeError(f"current 'mch' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    return gameInfo.get().mch.__dir__()

