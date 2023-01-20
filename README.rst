.. default-role:: literal

FactorioCalc Readme
===================

FactorioCalc is a python module to help you symbolically plan your factory for
Factorio.

With FactorioCalc you can either: specify the machines individually and ask it
what the resulting inputs and outputs are, specify what you want and call
`produce` to determine the machines needed, or any combination of the two.  It
contains a custom simplex solver so `produce` has the same power of online
calculators such as `FactorioLab <https://factoriolab.github.io/>`_, but gives
you more controller over the process.

FactorioCalc can also analyses most blueprint and determine what they produce.
Unlike in game tools, such as `Max Rate Calculator
<https://mods.factorio.com/mod/MaxRateCalculator>`_, it will take into account
that some machines may not be running 100% of the time.  However, at the
moment the it can't analyses blueprint with furnaces due to the lack of a
fixed recipe.

I, the author, find designing my factory symbolically more natural than
using a spreadsheet and tools like FactorioLab.
 
Read the docs at https://factoriocalc.readthedocs.io/en/latest/

Examples
--------

::

  >>> import factoriocalc as fc
  >>> from factoriocalc import itm, rcp, produce


Create a simple factory that creates electronic circuits from copper and iron plates::

  >>> fc.config.machinePrefs.set(fc.MP_LATE_GAME)
  >>> circuits = 2*rcp.electronic_circuit() + 3*rcp.copper_cable()
  >>> circuits.summary()
     2x electronic-circuit: assembling-machine-3:
           electronic-circuit 5/s, copper-cable -15/s, iron-plate -5/s, electricity -0.775 MW
     3x copper-cable: assembling-machine-3:
           copper-cable 15/s, copper-plate -7.5/s, electricity -1.1625 MW
  >>> print(circuits.flows())
  electronic-circuit 5/s, copper-cable 0/s (15/s - 15/s), iron-plate -5/s, copper-plate -7.5/s, electricity -1.9375 MW

Use `produce` to create a factory that produces rocket fuel::

  >>> fc.config.machinePrefs.set(fc.MP_MAX_PROD.withSpeedBeacons({fc.AssemblingMachine3:8, fc.ChemicalPlant:8, fc.OilRefinery:12}))
  >>> rocketFuel = produce([itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]).factory
  >>> rocketFuel.summary()
  Box:
      23.4x rocket-fuel: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      9.84x solid-fuel-from-light-oil: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      4.65x solid-fuel-from-petroleum-gas: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      2.26x advanced-oil-processing: oil-refinery  +555% speed +30% prod. +1080% energy +30% pollution
      1.06x heavy-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: rocket-fuel 6/s
    Inputs: crude-oil -295.803/s, water -220.004/s

Installation
------------

FactorioCalc is available on PyPi so you can install it using pip::

  pip3 install factoriocalc

FactorioCalc currently depends on factorio-draftsman, but only to get the
standard set of items and recipes.

Status
------

FactorioCalc has been used by the author to help produce a factory that
produces around 2k science packs per minute.  The calculations, in terms of
the rate of items produced and consumed, should be accurate (which includes
tricky cases such as the Kovarex enrichment process).  The solver, in nearly
all cases, should produce optimal results in terms of materials used.  The API
is subject to change but the core functionality *should be* stable.

Possible Bugs
.............

FactorioCalc uses a custom simplex solver written in pure python.  The solver
has no provisions to prevent cycling, so calls to `solve` could theoretical
loop and need to be killed with `control-c`; however, so far this has not
happened.

