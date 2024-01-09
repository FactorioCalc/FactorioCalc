.. default-role:: literal

FactorioCalc Readme
===================

FactorioCalc is a Python module to help you symbolically plan your factory for
Factorio.

With FactorioCalc you can:

* Symbolically express your exact machine configuration and ask it what the
  resulting inputs and outputs is.

* Import a blueprint and determine what it produces.

* Specify the recipes you want to use and let FactorioCalc determine the exact
  number of machines to produce a given output.

* Specify what you want, and let FactorioCalc determine both the recipes and
  the number of machines required.

FactorioCalc has supports for using custom recipe data and mods.  The
companion mod, `Recipe Exporter
<https://mods.factorio.com/mod/RecipeExporter>`_, provides the recipe data.

I, the author, find designing my factory symbolically more natural than
using a spreadsheet and tools like FactorioLab.

Read the docs at https://factoriocalc.readthedocs.io/en/stable/

Examples
--------

::

  >>> from factoriocalc import itm, rcp, mch, presets, config, produce

Create a simple factory that creates electronic circuits from copper and iron plates::

  >>> config.machinePrefs.set(presets.MP_LATE_GAME)
  >>> circuits = 2*rcp.electronic_circuit() + 3*rcp.copper_cable()
  >>> circuits.summary()
     2x electronic-circuit: assembling-machine-3:
           electronic-circuit 5/s, copper-cable -15/s, iron-plate -5/s, electricity -0.775 MW
     3x copper-cable: assembling-machine-3:
           copper-cable 15/s, copper-plate -7.5/s, electricity -1.1625 MW
  >>> circuits.flows().print()
  electronic_circuit 5/s
  copper_cable 0/s (15/s - 15/s)
  iron_plate -5/s
  copper_plate -7.5/s
  electricity -1.9375 MW


Use `produce` to create a factory that produces rocket fuel::

  >>> config.machinePrefs.set(presets.MP_MAX_PROD().withBeacons(presets.SPEED_BEACON,
          {mch.AssemblingMachine3:8, mch.ChemicalPlant:8, mch.OilRefinery:12}))
  >>> rocketFuel = produce([itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]).factory
  >>> rocketFuel.summary()
  b-rocket-fuel:
      23.4x rocket_fuel: AssemblingMachine3  +340% speed +40% prod. +880% energy +40% pollution
      9.84x solid_fuel_from_light_oil: ChemicalPlant  +355% speed +30% prod. +800% energy +30% pollution
      4.65x solid_fuel_from_petroleum_gas: ChemicalPlant  +355% speed +30% prod. +800% energy +30% pollution
      2.26x advanced_oil_processing: OilRefinery  +555% speed +30% prod. +1080% energy +30% pollution
      1.06x heavy_oil_cracking: ChemicalPlant  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: rocket_fuel 6/s
    Inputs: water -220.004/s, crude_oil -295.803/s



Installation
------------

FactorioCalc is available on PyPi so you can install it using pip::

  pip3 install factoriocalc

Status
------

FactorioCalc has been used by the author to help produce a factory that
produces around 2k science packs per minute.  It has also been used to help
beat both Space Exploration and Krastorio 2.  The calculations, in terms of
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

