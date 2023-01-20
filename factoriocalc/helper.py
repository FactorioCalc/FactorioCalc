from dataclasses import dataclass

from .core import CraftingMachine, Recipe, RecipeComponent
from . import itm


__all__ = ('sciencePacks','FakeLab')

sciencePacks = {itm.automation_science_pack,
                itm.logistic_science_pack,
                itm.chemical_science_pack,
                itm.production_science_pack,
                itm.utility_science_pack,
                itm.space_science_pack,
                itm.military_science_pack}

@dataclass(init=False)
class FakeLab(CraftingMachine):
    pass

