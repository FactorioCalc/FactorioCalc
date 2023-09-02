"""Symbols for recipes (`~factoriocalc.Rcp`) in factorio.

The name of the symbol is the same as the internal name but with ``-``
converted to ``_``.  For example, to refer to the recipe for an
"electronic-circuit" use `rcp.electronic_circuit`.

The contents of this module are dynamic and controlled via the `config.gameInfo`
context variable.

When the gameInfo context variable is configured for the base game this module
also provides some special recipes:

.. py:data:: space_science_pack

Recipe to produce 1000 `itm.space_science_pack` in a `RocketSilo <factoriocalc.RocketSilo>`.

.. py:data:: _combined_research

Recipe to consume all 7 science packs at a rate of 1/s in a `FakeLab <factoriocalc.FakeLab>`.

.. py:data:: _military_research

Recipe to consume all but the production science pack at a rate of 1/s in a
`FakeLab <factoriocalc.FakeLab>`.

.. py:data:: _production_research

Recipe to consume all but the military science pack at a rate of 1/s in a
`FakeLab <factoriocalc.FakeLab>`.

"""

def __getattr__(name):
    from .config import gameInfo
    try:
        return getattr(gameInfo.get().rcp, name)
    except AttributeError:
        raise AttributeError(f"current 'rcp' object has no attribute '{name}'") from None

def __dir__():
    from .config import gameInfo
    return gameInfo.get().rcp.__dir__()

