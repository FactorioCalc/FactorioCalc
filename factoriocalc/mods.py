from __future__ import annotations
from .import_ import *
import re

def krastorio_2(gameInfo, **kwargs):
    del gameInfo['recipes']['loader']
    del gameInfo['recipes']['fast-loader']
    del gameInfo['recipes']['express-loader']

    return importGameInfo(
        gameInfo,
        preAliasPasses = [_krastorio_2_fixups],
        aliasPass = _krastorio_2_alias_pass,
        byproducts = ['empty-barrel','stone','sand'],
        craftingHints = vanillaCraftingHints,
        includeDisabled = True,
        rocketRecipeHints = {'rocket-silo::space-research-data': 'default'},
        **kwargs)

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


def _krastorio_2_alias_pass(gi):
    return standardAliasPass(gi, lambda name: re.sub('(^kr-|(?<=-)kr-)', '', name))

def space_exploration(gameInfo):
    return importGameInfo(
        gameInfo,
        aliasPass = _space_exploration_alias_pass,
        byproducts = [('empty-barrel', '*fluid*'),
                      ('se-space-coolant-hot', 'se-space-coolant-warm'),
                      ('se-broken-data', 'se-junk-data', 'se-empty-data'),
                      ('se-contaminated-space-water', ('se-space-water', 'se-bio-sludge')),
                      ('se-contaminated-bio-sludge', ('se-space-water', 'se-bio-sludge')),
                      ('se-contaminated-scrap', ('se-scrap','se-space-water','se-bio-sludge')),
                      ('se-scrap', 'stone'),
                      'water', 'steam', 'stone', 'sand'],
        craftingHints = _space_exploration_crafting_hints,
        rocketRecipeHints = {'se-rocket-launch-pad-silo': 'skip',
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
                             'se-space-probe-rocket-silo::se-arcosphere': 'default'},
        )

def _space_exploration_crafting_hints():
    from . import rcpByName, IGNORE

    craftingHints = vanillaCraftingHints()

    for r in rcpByName.values():
        if r.name.startswith('se-recycle-'):
            craftingHints[r.name] = CraftingHint(priority = IGNORE)

    return craftingHints

def _space_exploration_alias_pass(gi):
    return standardAliasPass(gi, lambda name: re.sub('(^se-|(?<=-)se-)', '', name))
