.. highlight:: none
.. default-role:: py:obj
.. py:currentmodule:: factoriocalc

Comparison to Other Tools
-------------------------

FactorioCalc provides similar functionally (although with a different
interface) to many other tools, including `Max Rate Calculator
<https://mods.factorio.com/mod/MaxRateCalculator>`_, `Factory Planner
<https://mods.factorio.com/mod/factoryplanner>`_, and `FactorioLab
<https://factoriolab.github.io/>`_.

Max Rate Calculator
...................

FactorioCalc can analyses most blueprint and determine what they produce.
This provides similar functionally to in game tools such as `Max Rate
Calculator <https://mods.factorio.com/mod/MaxRateCalculator>`_ and `Rate
Calculator <https://mods.factorio.com/mod/RateCalculator>`_.  It is admittedly
less convenient to use, but is able to take account that some machines 
will not running 100% of the time, therefore making it more accurate.

Note that FactorioCalc can't analyses blueprint that smelt more then one type
of item (for example a steel factory that starts with iron ore) due to the
lack of recipe information in the blueprint.

Factory Planner
...............

FactorioCalc provides similar functionally to the `Factory Planner
<https://mods.factorio.com/mod/factoryplanner>`_ mod and `Helmod
<https://mods.factorio.com/mod/helmod>`_, however the interface is very
different.

Like Factory Planner, FactorioCalc let's you build your factory by specifying
the recipes you want to use and letting the solver figure out how many
machines you need.  In FactorioCalc you specify what you want symbolically, as
Python code.  This gives you far more flexibility than any GUI can provide.

FactorioLab
...........

FactorioCalc provides similar functionally to `FactorioLab
<https://factoriolab.github.io/>`_ via the `produce` function, but it works
slightly differently.

When there are multiple choices of recipes that can be used `produce` requires
you to specify which one you want, rather than just chose one based on some
metric.  This gives you more control over the process.

FactorioLab will work with most mods.  However, I found using it with Space
Exploitation a frustrating experience mid-game as it kept using recipes that
where not researched yet and I gave up trying to blacklist them all.

The `produce` function can be made to work with mods that don't have too many
choices for recipes such as Krastorio 2, but this has not been done yet.
`produce`, as it is currently written, is unlikely to ever work well with more
complex mods such as Space Exploration, but I do not see that as a downside as
with so many choices it is easier to build your factory by combining the
recipes you want to use, and letting the solver figure out how many machines
you need.


