"""Support for specific mods.

Each mod is it's own function.  To use just specify the name as the first
paramater to `~factoriocalc.setGameConfig`.  `~factoriocalc.setGameConfig`
convertes the name to lowercase and transforms ``-`` and spaces to ``_``.
So for example to use support for Krastorio 2 you can use any of ``Krastorio
2``, ``krastorio 2``, or ``krastorio_2``.
"""
from __future__ import annotations
from .import_ import *
from .core import MachinePrefs
import re

__all__ = ('krastorio_2', 'space_exploration', 'sek2')

def krastorio_2(gameInfo, **kwargs):
    """Support for the "Krastorio 2" mod.

    Removes the ``kr-`` prefix from internal names when converting them to
    alises. Also, ``loader``, ``fast_loader``, and ``express_loader`` refer to the
    Krastorio 2 versions and not the builtin versions.

    `~factoriocalc.produce` will still work in some cases, but special
    support for Krastorio 2 specific recipes has not yet been added.

    `presets.MP_EARLY_GAME`, `presets.MP_LATE_GAME`, `presets.MP_MAX_PROD`,
    and `presets.SPEED_BEACON` are provided.  In addition
    `presets.MP_MID_LATE_GAME` is provided for use before the three advanced
    versions of machines beacome available, and `presets.SPEED_BEACON_2`
    is provided as a shortcut for
    ``mch.SingularityBeacon(modules=2*itm.speed_module_3)``.

    """
    del gameInfo['recipes']['loader']
    del gameInfo['recipes']['fast-loader']
    del gameInfo['recipes']['express-loader']

    return importGameInfo(
        gameInfo,
        preAliasPasses = [_krastorio_2_fixups],
        nameTouchups = lambda name: re.sub('(^kr-|(?<=-)kr-)', '', name),
        byproducts = ['empty-barrel','stone','sand'],
        craftingHints = vanillaCraftingHints,
        rocketRecipeHints = _krastorio_2_rocket_recipe_hints,
        presets = _krastorio_2_presets,
        **kwargs
    )

def _krastorio_2_fixups(gi):
    recipesForItem = {}
    for r in gi.rcpByName.values():
        for _, _, item in r.outputs + r.inputs:
            recipesForItem.setdefault(item.name, []).append(r)
    items = [*gi.itmByName.keys()]
    for item in items:
        recipes = recipesForItem.get(item, [])
        if (len(recipes) == 1
            and len(recipes[0].inputs) == 1
            and len(recipes[0].outputs) == 1
            and recipes[0].outputs[0].item.name == 'kr-void'):
           del gi.itmByName[item]
           del gi.rcpByName[recipes[0].name]

_krastorio_2_rocket_recipe_hints = {
    'rocket-silo::space-research-data': 'default',
    'rocket-silo::raw-fish': '',
    'rocket-silo::dolphin-gun': '',
    'rocket-silo::teleportation-gps-module': '',
    'rocket-silo::spoiled-potato': '',
    'rocket-silo::kr-note-1': '',
    'rocket-silo::cyber-potato-equipment': '',
    'rocket-silo::poop': ''}

def _krastorio_2_presets():
    from . import mch, itm
    return {
        'MP_EARLY_GAME': MachinePrefs(mch.AssemblingMachine1(), mch.StoneFurnace(), mch.ChemicalPlant()),
        #'MP_MID_EARLY_GAME': MachinePrefs(mch.AssemblingMachine2(), mch.SteelFurnace(), mch.ChemicalPlant(), mch.ResearchServer()),
        'MP_MID_LATE_GAME': MachinePrefs(mch.AssemblingMachine3(), mch.ElectricFurnace(), mch.ChemicalPlant(), mch.QuantumComputer()),
        'MP_LATE_GAME': MachinePrefs(mch.AdvancedAssemblingMachine(), mch.AdvancedFurnace(), mch.AdvancedChemicalPlant(), mch.QuantumComputer()),
        'MP_MAX_PROD' : genMaxProd(
            3,
            mch.AdvancedAssemblingMachine, 
            mch.AdvancedFurnace,
            mch.AdvancedChemicalPlant,
            mch.OilRefinery,
            mch.RocketSilo,
            mch.Centrifuge,
            mch.ElectrolysisPlant,
            mch.FuelRefinery,
            mch.BioLab,
            mch.Crusher,
            mch.QuantumComputer,
        ),
        'SPEED_BEACON': mch.Beacon(modules=itm.speed_module_3),
        'SPEED_BEACON_2': mch.SingularityBeacon(modules=itm.speed_module_3),
        'advTechCards': {itm.production_science_pack,
                         itm.utility_science_pack,
                         itm.space_science_pack,
                         itm.matter_tech_card,
                         itm.advanced_tech_card,
                         itm.singularity_tech_card}
    }

def space_exploration(gameInfo, **kwargs):
    """Support for the "Space Exploration" mod.

    Removes the ``se-`` prefix from internal names when converting them to
    alises.

    Due to complexity of Space Exploration `~factoriocalc.produce`, as it is
    currently written is unlikely to ever work well. See
    :ref:`unbounded-throttles` in the overview guide.

    """
    return importGameInfo(
        gameInfo,
        nameTouchups = lambda name: re.sub('(^se-|(?<=-)se-)', '', name),
        byproducts = _space_exploration_byproducts,
        craftingHints = _space_exploration_crafting_hints,
        rocketRecipeHints = _space_exploration_rocket_recipe_hints,
        **kwargs,
    )

def _space_exploration_crafting_hints():
    from . import rcpByName, IGNORE

    craftingHints = vanillaCraftingHints()

    for r in rcpByName.values():
        if r.name.startswith('se-recycle-'):
            craftingHints[r.name] = CraftingHint(priority = IGNORE)

    return craftingHints

_space_exploration_byproducts = [
    ('empty-barrel', '*fluid*'),
    ('se-space-coolant-hot', 'se-space-coolant-warm'),
    ('se-broken-data', 'se-junk-data', 'se-empty-data'),
    ('se-contaminated-space-water', ('se-space-water', 'se-bio-sludge')),
    ('se-contaminated-bio-sludge', ('se-space-water', 'se-bio-sludge')),
    ('se-contaminated-scrap', ('se-scrap','se-space-water','se-bio-sludge')),
    ('se-scrap', 'stone'),
    'water', 'steam', 'stone', 'sand'
]

_space_exploration_rocket_recipe_hints = {
    'se-rocket-launch-pad-silo': 'skip',
    'rocket-silo::se-satellite-telemetry': 'default',
    'se-space-probe-rocket-silo::se-satellite-telemetry': '',
    'rocket-silo::raw-fish': '',
    'se-space-probe-rocket-silo::raw-fish': '',
    'rocket-silo::se-belt-probe-data': 'skip',
    'se-space-probe-rocket-silo::se-belt-probe-data': 'default',
    'rocket-silo::se-star-probe-data': 'skip',
    'se-space-probe-rocket-silo::se-star-probe-data': 'default',
    'rocket-silo::se-void-probe-data': 'skip',
    'se-space-probe-rocket-silo::se-void-probe-data': 'default',
    'rocket-silo::se-arcosphere': 'skip',
    'se-space-probe-rocket-silo::se-arcosphere': 'default'
}

def sek2(gameInfo, **kwargs):
    """Support for Space Exploration + Krastorio 2

    Removes both the ``kr-`` and ``se-`` prefixes except for the antimatter
    reactors and fuel refineries as a version exists in both mods.  The loader for
    the space transport belt aliases to ``space_loader``.
    """

    del gameInfo['recipes']['loader']
    del gameInfo['recipes']['fast-loader']
    del gameInfo['recipes']['express-loader']

    return importGameInfo(
        gameInfo,
        preAliasPasses = [_krastorio_2_fixups],
        nameTouchups = _sek2_name_touchups,
        byproducts = _space_exploration_byproducts,
        craftingHints = _space_exploration_crafting_hints,
        rocketRecipeHints = _sek2_rocket_recipe_hints,
        **kwargs,
    )

def _sek2_name_touchups(name):
    if name == 'kr-se-loader':
        return 'space-loader'
    elif name == 'kr-vc-kr-se-loader':
        return 'vc-space-loader'
    newName = re.sub('(^kr-|^se-|(?<=-)kr-|(?<=-)se-)', '', name)
    if newName in ('antimatter-reactor', 'fuel-refinery',
                   'vc-antimatter-reactor', 'vc-fuel-refinery'):
        return name
    return newName

_sek2_rocket_recipe_hints = {
    **_space_exploration_rocket_recipe_hints,
    **_krastorio_2_rocket_recipe_hints,
    'se-space-probe-rocket-silo::dolphin-gun': 'skip',
    'se-space-probe-rocket-silo::teleportation-gps-module': 'skip',
    'se-space-probe-rocket-silo::spoiled-potato': 'skip',
    'se-space-probe-rocket-silo::kr-note-1': 'skip',
    'se-space-probe-rocket-silo::cyber-potato-equipment': 'skip',
    'se-space-probe-rocket-silo::poop': 'skip',
}
