""".. py:data:: displayUnit
  :type: ContextVar

  Display units, the value should be set to one of the `DU_* <factoriocalc.DU_SECONDS>` presets.

  Defaults to `~factoriocalc.DU_SECONDS`

.. py:data:: mode
  :type: ContextVar

  Either `Mode.NORMAL <factoriocalc.Mode.NORMAL>` (the default) or `Mode.EXPENSIVE <factoriocalc.Mode.EXPENSIVE>`.

.. py:data:: machinePrefs
  :type: ContextVar

  Machine to use when instantiating recipes, The value is a sequence of
  machines (with or without a recipe) to try.  The `MP_*
  <factoriocalc.MP_EARLY_GAME>` presets provide some common configuration.

  When selecting a machine to use the first best match is used.  If the
  machine has a matching recipe associated then that will be given priority.
  In addition a machine with compatible modules will be given priority.

  Does not have a default.  Must be set being calling a recipe to instantiate
  it or using `produce <factoricalc.produce>`.

.. py:data:: recipePrefs
  :type: ContextVar

.. py:data:: defaultFuel
  :type: ContextVar

  Defaults to `itm.coal`.

"""

from contextvars import ContextVar as _ContextVar
from .core import Mode as _Mode
from .units import DU_SECONDS as _DU_SECONDS,UNIT_SECONDS as _UNIT_SECONDS
from . import itm as _itm

displayUnit = _ContextVar('factoriocalc.displayUnit', default = _DU_SECONDS)
#inputUnit = _ContextVar('factoriocalc.inputUnit', default = _UNIT_SECONDS)
machinePrefs = _ContextVar('factoriocalc.machinePrefs')
mode = _ContextVar('factoriocalc.mode', default = _Mode.NORMAL)
recipePrefs = _ContextVar('factoriocalc.recipePrefs')
defaultFuel = _ContextVar('factoriocalc.defaultFuel', default = _itm.coal)

