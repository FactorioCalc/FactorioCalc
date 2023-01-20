.. default-role:: py:obj
.. highlight:: none

.. py:currentmodule:: factoriocalc

Overview
********

This guide is meant to give you an overview of all the important parts of
FactoriCalc.  It does not spell out all the details for every function
introduced and assumes the examples provided are sufficient.  For complete
documentation see the API docs.  A decent knowledge of how to play Factorio is
assumed.

Basics
======

All symbols you need are exported into the main `factoriocalc` namespace so it
is rare you will need to import from a sub-module.  FactorioCalc is meant to
be used interactively via a REPL, with details of your overall factory
collected in a simple script.  For this reason it is acceptable to use ``from
factoricalc import *`` and the rest of the documentation will assume you have
done so.

For lack of a better term, *factory*, will be used thoughout this document to
refer to any group of machines that work together to produce one or more
products.  The term *overall factory* will be used to refer to all the
factories on the map.

Factoricalc uses exact fractions internally.  For speed a custom fraction
class is used.  This class does not allow converstion from floats, as 0.12
as a float is not 12/100 but really 1080863910568919/9007199254740992, which
is almost certainly not what was intended.  There are various heuristics
that can be used to give a better conversion, but for now it is easier to
disallow them.  In almost any place that expects a number a string can be
used instead, in the rare case a number is needed the `frac` function can be
used to create a `Frac`.  For example: ``frac('0.12')``, ``frac('1/3')``,
``frac(1,3)``.

Each machine is a class and is the same as the internal name but converted to
TitleCase.  The first argument of the constructor is the recipe.  For example,
to create an "assembling-machine-3" that produces electronic circuits you
could use ``AssemblingMachine3(rcp.electronic_circuit)``.  Additional keyword
arguments can be provided to specify the fuel used, beacons, or modules when
applicable.

Recipes are in the runtime generated `rcp` package and are the same as the
internal names but with ``-`` (dashes) converted to ``_`` (underscores).
Items are in `itm`.

Within FactorioCalc the items a machine produces or consumes is cosidered a
*flow*.  The rate of the flow is positive for items produced and negative
for items consumed.

To get the flow of items for a machine use the `flows` method, for example
``print(AssemblingMachine3(rcp.electronic_circuit).flows())`` will output::

  electronic-circuit 2.5/s, iron-plate -2.5/s, copper-cable -7.5/s, electricity -0.3875 MW

Electricity used is also tracked as a flow.

Multiple machines can be grouped together using the `+` operator which will
create a `Group`.  For example::

  >>> ec = AssemblingMachine3(rcp.electronic_circuit) + AssemblingMachine3(rcp.electronic_circuit)

We can then get the flows of the group by using ``print(ec.flows())``::

  electronic-circuit 2.5/s, copper-cable! -2.5/s (5/s - 7.5/s), iron-plate -2.5/s, copper-plate -2.5/s, electricity -0.775 MW

This is showing us the maxium rates for the group, but there is a problem:
we are creating copper cables at a rate of 5/s but consuming them at -7.5/s.
The ``!`` after copper cables indicates a lack of an ingredient.  We can fix
this by using the correct ratios or by slowing down the machine that creates
electronic circuits by adjusting it's *throttle*.

To fix the ratios we can use the `*` operator to create multiple identical
machines.  For example, to combine the two recipes above using the correct
ratio::

  >>> ec2 = 2*AssemblingMachine3(rcp.electronic_circuit) + 3*AssemblingMachine3(rcp.copper_cable)

If we ask for the flows of the new `Group` we now get::

  electronic-circuit 5/s, copper-cable 0/s (15/s - 15/s), iron-plate -5/s, copper-plate -7.5/s, electricity -1.9375 MW

To instead slow down the machines we need to adjust the *throttle*.  We can do
this manually, but it's best to let the solver determine it for us.  To do so,
we first need to wrap the group in a *box*::

  >>> b = Box(ec)

and then solve it::

  >>> b.solve()
  <SolveRes.UNIQUE: 2>

The result of solve tells us a single unique solution was found.  Now if we
call ``b.flows()`` we get::

  electronic-circuit 1.66667/s, iron-plate -1.66667/s, copper-plate -2.5/s, electricity -0.65 MW

Copper-cable is not in the list beacuase it's net flow is now zero.  Boxes,
unlike groups, do not include internal flows unless the net flow is non-zero.
An *internal flow* is simply a flow in which there are both producers and
consumers within the same box.

As creating a box and then solving it is a very common operation the `box`
shortcut function is provided to do just that, it usage is the same as the
`Box` constructor.  For example, we could of instead used::

  >>> b = box(ec)

To determine what the solver did we can use the `summary` method.  Calling
it gives us::

  b-electronic-circuit:
	 1x electronic-circuit: assembling-machine-3  @0.666667
	 1x copper-cable: assembling-machine-3
    Outputs: electronic-circuit 1.66667/s
    Inputs: iron-plate -1.66667/s, copper-plate -2.5/s

The ``@0.66667`` indiactes that the assembling machine for the
electronic-circuit is throttled and only running at 2/3 it's capacity.

Modules And Beacons
===================

Having to spell out the type of machine you want each time will get tedious
very fast so FactorioCalc provides a shortcut.  However, before you can use
the shortcut, you need to specify what type of assembling machine you want to
use.  This is done by setting `config.machinePrefs`, which is a python
`ContextVar <https://docs.python.org/3/library/contextvars.html>`_.  For now
we will set it to `MP_LATE_GAME` which will use the most advanced machines
possible for a recipe::

  >>> config.machinePrefs.set(MP_LATE_GAME)

With that we can simply call a recipe to produce a machine that will use the
given recipe.  Now to create electronic circuits from copper and iron plates
we can instead use::

  >>> ec2 = 2*rcp.electronic_circuit() + 3*rcp.copper_cable()

Of cource in the late game we are going to want to use productivity-3
modules with beacons stuffed with speed-3 modules.  You can pass modules and
beacons to the call above or include them in the `machinePrefs`.

For example, to make electronic circuits with 4 productivity-3 modules
and 8 beacons with speed-3 modules you would use::

  rcp.electronic_circuit(modules=4*itm.productivity_module_3,
                         beacons=8*Beacon(modules=2*itm.speed_module_3))

As a beacons with 2 speed-3 modules is a very common thing the shortcut
`SPEED_BEACON` is provied so the above can become::

  rcp.electronic_circuit(modules=4*itm.productivity_module_3,
                         beacons=8*SPEED_BEACON)

However, specifying the modules and becons configuration for each machine
can be tedious so it's best to include them as part of the `machinePrefs`.  If
all we cared about is assmebling machines we could just use::

  >>> config.machinePrefs.set([AssemblingMachine3(modules=4*itm.productivity_module_3,
                                                  beacons=8*SPEED_BEACON)])

However we most likely want all machines to have the maxium number of
productivity-3 modules and at least some speed beacons.  To make this easier
the `MP_MAX_PROD` preset can used to indicate that we want all machines to
have to maxium number of productivity-3 modules.  There is no preset for
beacons as the number the beacons often various.  Instead use the
`withSpeedBeacons` method to modify the preset by adding `SPEED_BEACON`'s for
specific machines.  For example::

  >>> config.machinePrefs.set(MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8}))

will give all machines the maxium number of productivity-3 modules possble
and assembling machine 3 with 8 `SPEED_BEACON`'s.  With `machinePrefs` set we can get
an assembling machine 3, with 4 productivity-3 modules, and 8 speed beacons
that creates electronic circuits by just using ``rcp.electronic_circuit()``.

Now lets try and combine electronic circuits with copper cables with maxium
productivity.  We could calculate the exact ratios or just guess and let
the solver do most of the math for use::

  >>> ec3 = box(rcp.electronic_circuit() + rcp.copper_cable())
  >>> ec3.summary(includeMachineFlows=True)
  b-electronic-circuit:
	 1x electronic-circuit: assembling-machine-3  @0.933333  +340% speed +40% prod. +880% energy +40% pollution:
	       electronic-circuit~ 14.3733/s, copper-cable~ -30.8/s, iron-plate~ -10.2667/s, electricity -3.4425 MW
	 1x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution:
	       copper-cable 30.8/s, copper-plate -11/s, electricity -3.6875 MW
    Outputs: electronic-circuit 14.3733/s
    Inputs: iron-plate -10.2667/s, copper-plate -11/s

The `includeMachineFlows` parameter will include the flows of individual
machine groups in the summary.  The ``~`` after an item in the flows indictates
the flow has been adjusted due to throttling.

Looking at the above summary the electronic circuit are throttled at 93%, so
a 1:1 ratio is fairly close.  We could increase the number of machines, but
given the high flow of items, doing so will likely be difficult.  Maybe
we can decrease the number of beacons for the electronic circuits::

  >>> ec3 = box(rcp.electronic_circuit(beacons=7*SPEED_BEACON) + rcp.copper_cable())
  >>> ec3.summary()
  b-electronic-circuit:
	 1x electronic-circuit: assembling-machine-3  +290% speed +40% prod. +810% energy +40% pollution
	 1x copper-cable: assembling-machine-3  @0.949675  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 13.65/s
    Inputs: iron-plate -9.75/s, copper-plate -10.4464/s

That is only sligtly better, but instead of not producing enough copper
cables we are producing more than enough, which is generally a better thing
to do.

Using produce
=============

Basic Usage
-----------

In the previous section we manually combined the machines.  It is also
possible to use the `produce` function to automatically determine the
required machines.  For example to produce electronic circuits at 30/s::

  >>> ec4 = produce([itm.electronic_circuit @ 30]).factory
  >>> ec4.summary()
  b-electronic-circuit:
    1.95x electronic-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    40.8x iron-plate: electric-furnace  -30% speed +20% prod. +160% energy +20% pollution
    2.09x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    43.7x copper-plate: electric-furnace  -30% speed +20% prod. +160% energy +20% pollution
  Outputs: electronic-circuit 30/s
  Inputs: copper-ore -19.1327/s, iron-ore -17.8571/s

The `@` operator pairs an item with a rate and returns a tuple.  The
``.factory`` at the end of produce is necessary beacuse `produce` returns a
class with additional information about the solution it found, but for now we
only are interested in the result.

And, oops we forgot to include speed beacons for electric furnaces in the
previous section.  I personally don't find it worth it to use modules for
basic smelting even in the late game so instead let's just change
`machinePrefs` to that effect::

  >>> config.machinePrefs.set([ElectricFurnace(), 
                              *MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8})])
  >>> ec4 = produce([itm.electronic_circuit @ 30]).factory
  >>> ec4.summary()
  b-electronic-circuit:
      1.95x electronic-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      34.3x iron-plate: electric-furnace
      2.09x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      36.7x copper-plate: electric-furnace
    Outputs: electronic-circuit 30/s
    Inputs: copper-ore -22.9592/s, iron-ore -21.4286/s

Ok, we still need a lot of electronic furnaces, but I normally smelt in a
separate factory.  So let's instead create electronic circuits from just
iron and copper plates by using the `using` keyword argument::

  >>> ec5 = produce([itm.electronic_circuit @ 30], using = [itm.iron_plate, itm.copper_plate]).factory
  >>> ec5.summary()
  b-electronic-circuit:
       1.95x electronic-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
       2.09x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
     Outputs: electronic-circuit 30/s
     Inputs: iron-plate -21.4286/s, copper-plate -22.9592/s

The `using` keyword argument is a list that guides the machine selection
process: if the element is an item `produce` will attemt to use that item and
then stop once it does, if the element is a recipe than `produce` will
prefer that recipe over another when there are multiple possibles.

.. _constraints first used:

Inputs can also be paired with a rate to use up to that amount of items.  When
rates are specified for the inputs, they can be left off of the outputs.  For
example, to determine the rate of electronic circuit we can create from a full
fast belt (30/s) of iron and copper plates::

  >>> ec6 = produce([itm.electronic_circuit], using = [itm.iron_plate @ 30, itm.copper_plate @ 30]).factory
  >>> ec6.summary()
  b-electronic-circuit:
      2.55x electronic-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      2.73x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 39.2/s
    Inputs: iron-plate -28/s, copper-plate -30/s
    Constraints: iron-plate >= -30, copper-plate >= -30

Which tells use we can produce electronic-circuit at 39.2/s.

By default `produce` will create a box with fractional number of machines.  If
you prefer that it just rounds up, set the `roundUp` argument to `True`, for
example::

   >>> ec7 = produce([itm.electronic_circuit], using = [itm.iron_plate @ 30, itm.copper_plate @ 30], roundUp=True).factory
   >>> ec7.summary()
   b-electronic-circuit:
	  3x electronic-circuit: assembling-machine-3  @0.848485  +340% speed +40% prod. +880% energy +40% pollution
	  3x copper-cable: assembling-machine-3  @0.909091  +340% speed +40% prod. +880% energy +40% pollution
     Outputs: electronic-circuit 39.2/s
     Inputs: iron-plate -28/s, copper-plate -30/s
     Constraints: iron-plate >= -30, copper-plate >= -30

.. _oil processing:

Oil Processing
--------------

FactoriCalc includes a simplex solver so it is able to handle complex cases,
such as producing items from cruid oil using advanced oil processing or coal
liquefaction.  Since oil produced can be produced from either process you have
to specify which one to use with the `using` paramater.  For example, to make
plastic from cruid oil::

  >> config.machinePrefs.set(MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8, ChemicalPlant:8, OilRefinery:12}))
  >> plastic1 = produce([itm.plastic_bar@90], using=[rcp.advanced_oil_processing]).factory
  >> plastic1.summary()
      7.61x plastic-bar: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      3.53x advanced-oil-processing: oil-refinery  +555% speed +30% prod. +1080% energy +30% pollution
      6.11x light-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      1.65x heavy-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: plastic-bar 90/s
    Inputs: coal -34.6154/s, crude-oil -462.579/s, water -761.232/s

And it will tell how many chemical plants you need for light and heavy oil
cracking.  If you rather use coal liquefaction::

  >> plastic2 = produce([itm.plastic_bar@90], using=[rcp.coal_liquefaction], fuel=itm.solid_fuel).factory
  >> plastic2.summary()
    7.61x plastic-bar: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    4.98x coal-liquefaction: oil-refinery  +555% speed +30% prod. +1080% energy +30% pollution
    10.3x light-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    6.06x heavy-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    5.44x steam: boiler
    0.276x solid-fuel-from-light-oil: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
  Outputs: plastic-bar 90/s
  Inputs: coal -99.8643/s, water -1,440.70/s

The `fuel` parameter specifies the fuel to use.  It defaults to the value of
`config.defaultFuel` which defaults to `itm.coal`.

It is just as easy to create rocket fuel::

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

In this case there is no light oil cracking but some heavy oil cracking
as it more efficient to first convert heavy oil to light oil when creating
soild fuel.  The conversion of petroleum gas to light oil is unavoidable as
there is nothing else to do with the gas.

We can just as easily plastic and rocket fuel at the same time, which will
avoid the need to convert petroleum gas to soild fuel, but the entire
factory will grind to a halt if both products are not being created at the
same time.  FactoriCalc can fairly easy let you know what you need to
produce either plastic or rocket fuel, or both at the same time.  This will
be covered in a later section.

Using Boxes
===========

Basic Usage
-----------

A box is a wrapper around a group with additional constraints to limit flows.
So far we have been letting FactoriCalc determine the constraints
automatically.  For example ``Box(rcp.electronic_circuit() +
rcp.copper_cable())`` will automatically set the external flow of copper
cables to zero as it is an internal flow.  Sometimes you may want to limit the
external flows or allow an internal flow to become external.  For this reason
the `Box` constructor, and corresponding `box` function, has a number of
arguments to let you fine tune the inputs and outputs.  For example to create
both electric circuits and advanced circuits we need to explicitly list the
outputs::

  >>> config.machinePrefs.set(MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8, ChemicalPlant:8, OilRefinery:12}))
  >>> circuits1 = box(rcp.electronic_circuit() + 2*rcp.copper_cable() + 2*rcp.advanced_circuit(),
		      outputs = [itm.electronic_circuit, itm.advanced_circuit])
  >>> circuits1.summary()	    
  Box:
	 1x electronic-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
	 2x copper-cable: assembling-machine-3  @0.654762  +340% speed +40% prod. +880% energy +40% pollution
	 2x advanced-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 11.7333/s (15.4/s - 3.66667/s), advanced-circuit 2.56667/s
    Inputs: plastic-bar -3.66667/s, iron-plate -11/s, copper-plate -14.4048/s

If there are not quite enough machines `box` can fail with `SolveRes.OK`.
This result means that a solution was found but it is not considered optimal.
A solution is generally considered optimal if all machines that produce an
output item are running at there maximum capacity.  If, in the previous
example we where to reduce numbers of copper cables machines to 1 either the
electronic circuits or the advanced circuit machines can run at full capacity
but not both.  To fix this we can use the `priorities` argument to specify
that a particular output should get priorty over another.  For example::

  >>> circuits2 = box(rcp.electronic_circuit() + rcp.copper_cable() + 2*rcp.advanced_circuit(),
                      outputs = [itm.electronic_circuit, itm.advanced_circuit],
		      priorities = {itm.advanced_circuit:1})
  >>> circuits2.summary()
  Box:
	 1x electronic-circuit: assembling-machine-3  @0.711111  +340% speed +40% prod. +880% energy +40% pollution
	 1x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
	 2x advanced-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 7.28444/s (10.9511/s - 3.66667/s), advanced-circuit 2.56667/s
    Inputs: plastic-bar -3.66667/s, iron-plate -7.82222/s, copper-plate -11/s
    Priorities: advanced-circuit: 1

will give priory to the advanced circuits and output whatever it can of the
electronic circuits.  The values for the `priorities` argument mapping
needs to be between -100 and 100.

Another way to avoid `SolveRes.OK` is to specify rates for some of the
outputs, for example if we wanted electronic circuits at 8/s::

  >>> circuits3 = box(rcp.electronic_circuit() + rcp.copper_cable() + 2*rcp.advanced_circuit(),
                      outputs = [itm.electronic_circuit @ 8, itm.advanced_circuit])
  >>> circuits3.summary()
  Box:
	 1x electronic-circuit: assembling-machine-3  @0.733542  +340% speed +40% prod. +880% energy +40% pollution
	 1x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
	 2x advanced-circuit: assembling-machine-3  @0.899060  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 8/s (11.2966/s - 3.29655/s), advanced-circuit 2.30759/s
    Inputs: plastic-bar -3.29655/s, iron-plate -8.06897/s, copper-plate -11/s

Boxes can also have a set of constraints associated with it.  Constraints are
specified via the `constraints` parameters and is a mapping of items to
values.  When the value is a number than the rate for that item will be at
least that value.  If the number is positive than the box will produce at
least that amount, when it is negative the box will consume at most that
amount.  For example, to limit the number of iron plates in the above example
to just 8/s::

  >>> circuits4 = box(rcp.electronic_circuit() + rcp.copper_cable() + 2*rcp.advanced_circuit(),
                      outputs = [itm.electronic_circuit @ 8, itm.advanced_circuit],
                      constraints = {itm.iron_plate: -8})
  >>> circuits4.summary()
  Box:
         1x electronic-circuit: assembling-machine-3  @0.727273  +340% speed +40% prod. +880% energy +40% pollution
         1x copper-cable: assembling-machine-3  @0.987013  +340% speed +40% prod. +880% energy +40% pollution
         2x advanced-circuit: assembling-machine-3  @0.872727  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 8/s (11.2/s - 3.2/s), advanced-circuit 2.24/s
    Inputs: iron-plate -8/s, plastic-bar -3.2/s, copper-plate -10.8571/s
    Constraints: iron-plate >= -8

By default input values of boxes are converted to constraints, so instead of
``constraints = {itm.iron_plate: -8}`` we could of just used ``inputs =
[itm.iron_plate @ 8]``.

Input constraints are most useful when the number of machines is not fixed, as
is the case with `produce`.  In fact, constraints were first used
:ref:`when setting the input rate <constraints first used>`, in the section on
`produce`, but not explicitly mentioned.

UnboundedBox's
--------------

An `UnboundedBox` is a special type of box in which the solver adjusts the
number of machines rather than the machines throttle.  It is used internally
by `produce`.  For example, if we wanted to produce electronic circuits at
28/s from copper and iron plates we could do::
  
  >> config.machinePrefs.set(MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8}))
  >> circuits0 = unboundedBox(1*rcp.electronic_circuit()+1*rcp.copper_cable(),
                             outputs={itm.electronic_circuit@28})
  >> circuits0.summary()
  b-electronic-circuit:
      1.82x electronic-circuit: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      1.95x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 28/s
    Inputs: iron-plate -20/s, copper-plate -21.4286/s

Like `box`, `unboundedBox` is a helper function for `UnboundedBox` which will
create a unbounded box and then solve it.  The ``1*`` is needed because an
`UnboundedBox` must be a `Group` of `Mul` so that the solver has something to
adjust.

An `UnboundedBox` can be converted into a regular box by using the `finalize`
method.  For example::

  >> circuits = circuits0.finalize().factory
  >> circuits.summary()
  b-electronic-circuit:
         2x electronic-circuit: assembling-machine-3  @0.909091  +340% speed +40% prod. +880% energy +40% pollution
         2x copper-cable: assembling-machine-3  @0.974026  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 28/s
    Inputs: iron-plate -20/s, copper-plate -21.4286/s

The result of `finalize` is similar to `produce`.  As we are only interested
in the main results, so we just extract the `factory` field.  Unlike,
`produce`, finalize defaults to rounding up, to not round up use
`roundUp=False`.  To see that this is now a normal box, we can remove the
output constraints and solve again::

  >> circuits.outputs[itm.electronic_circuit] = None
  >> circuits.solve()
  >> circuits.summary()
  b-electronic-circuit:
         2x electronic-circuit: assembling-machine-3  @0.933333  +340% speed +40% prod. +880% energy +40% pollution
         2x copper-cable: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
    Outputs: electronic-circuit 28.7467/s
    Inputs: iron-plate -20.5333/s, copper-plate -22/s
 
and the solver adjusted the throttles to give us just a little more electronic
circuits.

`UnboundedBox`'s are most useful when they are nested instead other boxes.
For example::

  >> config.machinePrefs.set([AssemblingMachine3(modules=1*itm.speed_module_3 + 3*itm.productivity_module_3)])
  >> modules = box(rcp.speed_module_3() + UnboundedBox(rcp.speed_module_2()) + UnboundedBox(rcp.speed_module()))
  >> modules.summary()
  b-speed-module-3:
         1x speed-module-3: assembling-machine-3  +50% speed +70% energy
      b-speed-module-2:
           2.5x speed-module-2: assembling-machine-3  +50% speed +70% energy
        Outputs: speed-module-2 0.15625/s
        Inputs: advanced-circuit -0.78125/s, processing-unit -0.78125/s, speed-module -0.625/s
      b-speed-module:
             5x speed-module: assembling-machine-3  +50% speed +70% energy
        Outputs: speed-module 0.625/s
        Inputs: electronic-circuit -3.125/s, advanced-circuit -3.125/s
    Outputs: speed-module-3 0.03125/s
    Inputs: electronic-circuit -3.125/s, processing-unit -0.9375/s, advanced-circuit -4.0625/s

The results are a bit messy, but it is telling us we need 2.5x machines
producing speed-2 modules and 5x machines producing speed-1 modules to support
one machine producing speed-3 modules.

As shown above and as a convenience, the `UnboundedBox` constructor will
accept a single machine and convert it into the proper form for you.

Using union
-----------

Getting back to our oil processing example from a :ref:`previous section <oil
processing>`.  In that section we wanted to produce both plastic and rocket
fuel.  A naive solution is to just use ``produce([itm.plastic_bar@90,
itm.rocket_fuel@6], ...)`` but the resulting factory will only work if both
plastic bars and rocket fuel are being consumed.  If one of them is not being
consumed fast enough the oil refineries will eventually back up with excuses
petroleum gas or light oil.  We could simply combine the factory that produces
only plastic bar with one that only produces rocket fuel but this is
non-optimal as some of the petroleum gas will be used to create solid fuel and
some of the light oil needlessly being converted to petroleum gas.  Instead we
only want the petroleum gas to be converted to solid fuel and the light oil to
be converted to petroleum gas if there is an overflow.  To insure we have
enough machines to do so we need to take the union of three factories: one
that produces both optimally, one that produces just plastic, and one that
produces just rocket fuel.  We can do so with using the `union` function::

  >>> config.machinePrefs.set(MP_MAX_PROD.withSpeedBeacons({AssemblingMachine3:8, ChemicalPlant:8, OilRefinery:12}))
  >>> both = produce([itm.plastic_bar@90, itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]).factory
  >>> plastic = produce([itm.plastic_bar@90], using=[rcp.advanced_oil_processing]).factory
  >>> rocketFuel = produce([itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]).factory
  >>> res = union(both, plastic, rocketFuel)
  >>> combined = res[0]
  >>> combined.solve()
  >>> combined.summary()
  Box:
      7.61x plastic-bar: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      23.4x rocket-fuel: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      5.18x advanced-oil-processing: oil-refinery  +555% speed +30% prod. +1080% energy +30% pollution
      6.11x light-oil-cracking: chemical-plant  @0.573402  +355% speed +30% prod. +800% energy +30% pollution
      2.42x heavy-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      14.5x solid-fuel-from-light-oil: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      4.65x solid-fuel-from-petroleum-gas: chemical-plant  @0  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: plastic-bar 90/s, rocket-fuel 6/s
    Inputs: water -743.704/s, crude-oil -678.303/s, coal -34.6154/s

As you can see from the summary, when producing both items, the
light-oil-cracking chemical plant is not being fully utilized and the
solid-fuel-from-petroleum-gas chemical plant is not being used at all.
However, when just plastic or just rocket fuel are consumed they will be used.
To see how the machines are utilized when just one of the outputs are consumed
we can use the other values returned by `union`.

`union` returns a tuple with several factories: the first one is the result;
the others are views of the first one, which once solved, will change the
first result to have the same flows as the arguments, respectively.  For
example::

  >>> plastic = res[2]
  >>> plastic.solve()
  >>> combined.summary()
  Box:
      7.61x plastic-bar: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      23.4x rocket-fuel: assembling-machine-3  @0  +340% speed +40% prod. +880% energy +40% pollution
      5.18x advanced-oil-processing: oil-refinery  @0.681966  +555% speed +30% prod. +1080% energy +30% pollution
      6.11x light-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      2.42x heavy-oil-cracking: chemical-plant  @0.681966  +355% speed +30% prod. +800% energy +30% pollution
      14.5x solid-fuel-from-light-oil: chemical-plant  @0  +355% speed +30% prod. +800% energy +30% pollution
      4.65x solid-fuel-from-petroleum-gas: chemical-plant  @0  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: plastic-bar 90/s, rocket-fuel 0/s
    Inputs: water -761.232/s, crude-oil -462.579/s, coal -34.6154/s
 
And as shown in the summary, when producing plastic the the light-oil-cracking
chemical plants are fully utilized.

It should be noted that in order for this factory to work as intended the flow
of fluids into the light-oil-cracking and solid-fuel-from-petroleum-gas
chemical plants will need to be controlled via circuits.  We can get an idea
of what might happen if we don't use circuits by adjusting the priorities.
For example, to see what will happen if the petroleum gas is converted to
light oil we can up the priority for that chemical plant::

  >>> combined.priorities[rcp.solid_fuel_from_petroleum_gas] = 2
  >>> combined.solve()
  <SolveRes.OK: 4>
  Box:
      7.61x plastic-bar: chemical-plant  @0.826884  +355% speed +30% prod. +800% energy +30% pollution
      23.4x rocket-fuel: assembling-machine-3  +340% speed +40% prod. +880% energy +40% pollution
      5.18x advanced-oil-processing: oil-refinery  +555% speed +30% prod. +1080% energy +30% pollution
      6.11x light-oil-cracking: chemical-plant  @0.826884  +355% speed +30% prod. +800% energy +30% pollution
      2.42x heavy-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      14.5x solid-fuel-from-light-oil: chemical-plant  @0.679226  +355% speed +30% prod. +800% energy +30% pollution
      4.65x solid-fuel-from-petroleum-gas: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: plastic-bar 74.4195/s, rocket-fuel 6/s
    Inputs: water -849.454/s, crude-oil -678.303/s, coal -28.6229/s
    Priorities: recipe solid-fuel-from-petroleum-gas: 2
    
And as a result the plastic output suffers as there is not enough petroleum
gas.  When solving we only got `SolveRes.OK`, which means that other solutions
are possible.  For example we can try and get more plastic by uping it's priority::

  >> combined.priorities[rcp.plastic_bar] = 1
  >> combined.solve()
  <SolveRes.UNIQUE: 2>
  Box:
      7.61x plastic-bar: chemical-plant  @0.917295  +355% speed +30% prod. +800% energy +30% pollution
      23.4x rocket-fuel: assembling-machine-3  @0.806129  +340% speed +40% prod. +880% energy +40% pollution
      5.18x advanced-oil-processing: oil-refinery  +555% speed +30% prod. +1080% energy +30% pollution
      6.11x light-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      2.42x heavy-oil-cracking: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
      14.5x solid-fuel-from-light-oil: chemical-plant  @0.485355  +355% speed +30% prod. +800% energy +30% pollution
      4.65x solid-fuel-from-petroleum-gas: chemical-plant  +355% speed +30% prod. +800% energy +30% pollution
    Outputs: plastic-bar 82.5566/s, rocket-fuel 4.83678/s
    Inputs: water -921.676/s, crude-oil -678.303/s, coal -31.7525/s
    Priorities: recipe solid-fuel-from-petroleum-gas: 2, recipe plastic-bar: 1

And we increased the plastic output but rocket fuel output then suffers.
Hence, we need some circuits to prevent any conversion of petroleum gas to
solid fuel unless we have an overflow.

Nuclear Processing
------------------

Like oil processing, processing of uranium ore is tricky.  You will eventually
need to use the Kovarex enrichment process, but you can't overdue it,
otherwise you will have too much Uranium-235 and not enough Uranium-238.  In
addition you will also want to dispose of the used fuel cells by reprocessing
it back into a small amount of Uranium-238.  Fortunately FactoriCalc is up to
the task.  For example, here is a factory that provides the needs of nuclear
related produces for a fairly large overall factory::

  nuclearStuff = withSettings(
      {config.machinePrefs: ((Centrifuge(modules=2*itm.productivity_module_3,beacons=4*SPEED_BEACON),) + MP_LATE_GAME)},
      lambda: box(1*rcp.uranium_processing(beacons=5*SPEED_BEACON)
                  + 3*rcp.uranium_processing(beacons=5*SPEED_BEACON)
                  + 2*rcp.kovarex_enrichment_process(beacons=5*SPEED_BEACON)
                  + 1*rcp.kovarex_enrichment_process(beacons=4*SPEED_BEACON)
                  + 5*rcp.nuclear_fuel_reprocessing()
                  + rcp.uranium_fuel_cell(modules=4*itm.productivity_module_3,beacons=1*SPEED_BEACON)
                  + 3*rcp.nuclear_fuel()
                  + 4*rcp.uranium_rounds_magazine(modules=[],beacons=[]),
                  priorities={rcp.nuclear_fuel_reprocessing:2,itm.nuclear_fuel:1},
                  constraints={itm.uranium_fuel_cell: (-1, itm.used_up_uranium_fuel_cell)}))

In this factory, `withSettings` is a helper functional to set a context
variables to a different value locally.  An advanced feature of the
`constraints` parameter is also used so that the output of uranium fuel cells
matches the input of used up ones.

The exact amount of machines was determined mostly by trail and error.  Here
is a summary of the solved factory::

  >>> nuclearStuff.summary()
  Box:
         4x uranium-processing: centrifuge  +220% speed +20% prod. +510% energy +20% pollution
         3x kovarex-enrichment-process: centrifuge  @0.886797  +203% speed +20% prod. +487% energy +20% pollution
         5x nuclear-fuel-reprocessing: centrifuge  +170% speed +20% prod. +440% energy +20% pollution
         1x uranium-fuel-cell: assembling-machine-3  @0.714286  -10% speed +40% prod. +390% energy +40% pollution
         3x nuclear-fuel: centrifuge  +170% speed +20% prod. +440% energy +20% pollution
         4x uranium-rounds-magazine: assembling-machine-3  @0.301523
    Outputs: uranium-rounds-magazine 0.150761/s, uranium-fuel-cell 1.125/s, nuclear-fuel 0.108/s
    Inputs: uranium-ore -10.6667/s, piercing-rounds-magazine -0.150761/s, rocket-fuel -0.09/s, used-up-uranium-fuel-cell -1.125/s, iron-plate -0.803571/s
    Constraints: uranium-fuel-cell = -used-up-uranium-fuel-cell
    Priorities: recipe nuclear-fuel-reprocessing: 2, nuclear-fuel: 1

Working with Blueprints
=======================

FactoroCalc provides limited support for converting a blueprint of a factory
into a `Group` for further analysis:  Furnaces will be converted, but since
they don't have a fixed recipe, you will need to manually set the recipe
afterwards.  Rocket silos are assumed to be creating space
science, by default.

See :ref:`blueprints`.
