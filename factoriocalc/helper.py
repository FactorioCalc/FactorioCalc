from dataclasses import dataclass
from contextvars import copy_context

from .core import CraftingMachine, Recipe, RecipeComponent
from . import itm

__all__ = ('withSettings','FakeLab')

def withSettings(settings, fun, *args, **kwargs):
    "helper function to locally set a ContextVar"
    ctx = copy_context()
    return ctx.run(_withSettings, settings, fun, *args, **kwargs)

def _withSettings(settings, fun, *args, **kwargs):
    for var, val in settings.items():
        var.set(val)
    return fun(*args, **kwargs)

@dataclass(init=False)
class FakeLab(CraftingMachine):
    pass

