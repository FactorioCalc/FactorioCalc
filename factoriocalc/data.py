from __future__ import annotations
import dataclasses as _dc

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

__all__ = [sym for sym in globals() if not sym.startswith('_') and sym not in ('annotations', 'CraftingHint', 'craftingHints')]
