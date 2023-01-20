"""Symbols for recipes (`~factoriocalc.Rcp`) in factorio.

The name of the symbol is the same as the internal name but with ``-``
converted to ``_``.  For example, to refer to the recipe for an
"electronic-circuit" use `rcp.electronic_circuit`.

This module also provides some special recipes:

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

byName = {}

