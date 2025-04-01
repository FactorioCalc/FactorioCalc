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
  number of machines needed.

* Specify what you want, and let FactorioCalc determine both the recipes and
  the number of machines required.

* Combine factories, which were created using any of the above methods, to
  create a larger factory.

FactorioCalc has supports for using custom recipe data and mods.  The
companion mod, `Recipe Exporter
<https://mods.factorio.com/mod/RecipeExporter>`_, provides the recipe data.

FactorioCalc contains a custom simplex solver so it can easily handle complex
cases that involve recipes with more than one output, such as oil and uranium
processing.

I, the author, find designing my factory symbolically more natural than
using a spreadsheet and tools like FactorioLab.

Read the docs at https://factoriocalc.readthedocs.io/en/stable/

Examples
--------

::

  >>> from factoriocalc import setGameConfig, itm, rcp, mch, presets, config, produce
  >>> setGameConfig('v2.0')

Create a simple factory that creates electronic circuits from copper and iron plates::

  >>> config.machinePrefs.set(presets.MP_LATE_GAME)
  >>> circuits = 2*rcp.electronic_circuit() + 3*rcp.copper_cable()
  >>> circuits.summary()
      2x electronic_circuit: AssemblingMachine3:
            electronic_circuit 5/s, iron_plate -5/s, copper_cable -15/s, electricity -0.775 MW
      3x copper_cable: AssemblingMachine3:
            copper_cable 15/s, copper_plate -7.5/s, electricity -1.1625 MW
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
      11.1x rocket_fuel: AssemblingMachine3  +364% speed +40% prod. +914% energy +40% pollution
      4.67x solid_fuel_from_light_oil: ChemicalPlant  +379% speed +30% prod. +834% energy +30% pollution
      2.21x solid_fuel_from_petroleum_gas: ChemicalPlant  +379% speed +30% prod. +834% energy +30% pollution
      2.57x advanced_oil_processing: OilRefinery  +475% speed +30% prod. +967% energy +30% pollution
      1.00x heavy_oil_cracking: ChemicalPlant  +379% speed +30% prod. +834% energy +30% pollution
    Outputs: rocket_fuel 6/s
    Inputs: water -220.004/s, crude_oil -295.803/s

Figure out the best method to quality grind for legendary electronic circuits
by trying both productivity and quality modules and letting the solver figure
out the best combination::

  >>> setGameConfig('v2.0-sa')
  >>> config.machinePrefs.set(presets.MP_LEGENDARY)
  >>> legendaryElectronicCcircuits = box(
      [*~rcp.electronic_circuit.allQualities[0:4](modules=itm.legendary_quality_module_3),
       *~rcp.electronic_circuit.allQualities(beacons = 1*mch.LegendaryBeacon(itm.legendary_speed_module_3)),
       *~rcp.electronic_circuit_recycling.allQualities[0:4]()],
      inputs = rcp.electronic_circuit.inputs,
      outputs = [itm.legendary_electronic_circuit@1])
  >>> legendaryElectronicCcircuits.summary()
  b-legendary-electronic-circuit:
      (  0x)electronic_circuit: LegendaryElectromagneticPlant  -25% speed +50% prod. +31.0% quality
      (  0x)uncommon_electronic_circuit: LegendaryElectromagneticPlant  -25% speed +50% prod. +31.0% quality
      (  0x)rare_electronic_circuit: LegendaryElectromagneticPlant  -25% speed +50% prod. +31.0% quality
      (  0x)epic_electronic_circuit: LegendaryElectromagneticPlant  -25% speed +50% prod. +31.0% quality
      (0.450x)electronic_circuit: LegendaryElectromagneticPlant  +550% speed +175% prod. +750% energy +50% pollution
      (0.143x)uncommon_electronic_circuit: LegendaryElectromagneticPlant  +550% speed +175% prod. +750% energy +50% pollution
      (0.0597x)rare_electronic_circuit: LegendaryElectromagneticPlant  +550% speed +175% prod. +750% energy +50% pollution
      (0.0250x)epic_electronic_circuit: LegendaryElectromagneticPlant  +550% speed +175% prod. +750% energy +50% pollution
      (0.00559x)legendary_electronic_circuit: LegendaryElectromagneticPlant  +550% speed +175% prod. +750% energy +50% pollution
      (2.51x)electronic_circuit_recycling: LegendaryRecycler  -20% speed +24.8% quality
      (0.799x)uncommon_electronic_circuit_recycling: LegendaryRecycler  -20% speed +24.8% quality
      (0.334x)rare_electronic_circuit_recycling: LegendaryRecycler  -20% speed +24.8% quality
      (0.139x)epic_electronic_circuit_recycling: LegendaryRecycler  -20% speed +24.8% quality
    Outputs: legendary_electronic_circuit 1/s
    Inputs: iron_plate -14.1348/s (15.1298/s - 29.2647/s), copper_cable -42.4045/s (45.3895/s - 87.7940/s)

Installation
------------

FactorioCalc is available on PyPI so you can install it using pip::

  pip3 install factoriocalc

Status
------

FactorioCalc has been used by the author to help produce a factory that
produces around 2k science packs per minute with Factorio 1.1, beat Space
Exploration, beat Krastorio 2, create a Krastorio 2 factory that produces 3k
science packs per minute, and beat Factorio: Space Age.  The calculations, in
terms of the rate of items produced and consumed, should be accurate (which
includes tricky cases such as the Kovarex enrichment process).  The solver, in
nearly all cases, should produce optimal results in terms of materials used.
The API is subject to change but the core functionality *should be* stable.

Possible Bugs
.............

FactorioCalc uses a custom simplex solver written in pure python.  The solver
has no provisions to prevent cycling, so calls to `solve` could theoretical
loop and need to be killed with `control-c`; however, so far this has not
happened.

