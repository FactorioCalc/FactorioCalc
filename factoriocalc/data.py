from __future__ import annotations
import dataclasses as _dc
from . import machines as mch

@_dc.dataclass
class CraftingHint:
    also: list = _dc.field(default_factory = list)
    priority: int = 0
    boxPriority: int = 0

recipes = []
recipesThatMake = {}
recipesThatUse = {}
craftingHints = {}

entityToMachine = {}

categoryToMachines = {
    'crafting': [mch.AssemblingMachine1, mch.AssemblingMachine2, mch.AssemblingMachine3],
    "advanced-crafting": [mch.AssemblingMachine1, mch.AssemblingMachine2, mch.AssemblingMachine3],
    'crafting-with-fluid': [mch.AssemblingMachine2, mch.AssemblingMachine3],
    'centrifuging': [mch.Centrifuge],
    'chemistry': [mch.ChemicalPlant],
    'oil-processing': [mch.OilRefinery],
    'rocket-building': [], # a special case
    'smelting': [mch.Furnace],
    '_rocket-silo': [mch.RocketSilo],
    '_steam': [mch.Boiler],
}

__all__ = [sym for sym in globals() if not sym.startswith('_') and sym not in ('annotations', 'CraftingHint', 'craftingHints')]
