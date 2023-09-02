"""Symbols for items and fluids in factorio.

The name of the symbol is the same as the internal name but with ``-``
converted to ``_``.  For example, to refer to an "electronic-circuit" use
`itm.electronic_circuit`.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.

When the gameInfo context variable is configured for the base game this module
also provides a few special items.

.. py:data:: _combined_research

Result of `rcp._combined_research <factoriocalc.rcp._combined_research>`.

.. py:data:: _military_research

Result of `rcp._military_research <factoriocalc.rcp._military_research>`.

.. py:data:: _production_research

Result of `rcp._production_research <factoriocalc.rcp._production_research>`.

"""

def __getattr__(name):
    from .config import gameInfo
    try:
        return getattr(gameInfo.get().itm, name)
    except AttributeError:
        raise AttributeError(f"current 'itm' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    return gameInfo.get().itm.__dir__()
