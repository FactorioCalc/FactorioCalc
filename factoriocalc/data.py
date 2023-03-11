from __future__ import annotations
import dataclasses as _dc

@_dc.dataclass
class CraftingHint:
    also: list = _dc.field(default_factory = list)
    priority: int = 0
    boxPriority: int = 0

class Objs:
    pass

@_dc.dataclass
class GameInfo:
    rcp: Objs
    rcpByName: dict
    itm: Objs
    itmByName: dict
    mch: Objs
    mchByName: dict
    recipesThatMake: dict = None
    recipesThatUse: dict = None
    craftingHints: dict = None

    def finalize(self):
        self.recipesThatMake = {}
        self.recipesThatUse = {}
        
        for r in self.rcpByName.values():
            for _, item in r.outputs:
                self.recipesThatMake.setdefault(item, []).append(r.name)
            for _, item in r.inputs:
                self.recipesThatUse.setdefault(item, []).append(r.name)


class DictProxy:
    __slots__ = ('field')
    def __init__(self, field):
        self.field = field
    def __len__(self):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).__len__()
    def __getitem__(self, key):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).__getitem__(key)
    def __contains__(self, key):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).__contains__(key)
    def get(self, key, default = None):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).get(key, default)
    def __iter__(self):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).__iter__()
    def keys(self):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).keys()
    def values(self):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).values()

rcpByName = DictProxy('rcpByName')
itmByName = DictProxy('itmByName')
mchByName = DictProxy('mchByName')
recipesThatMake = DictProxy('recipesThatMake')
recipesThatUse = DictProxy('recipesThatUse')
craftingHints = DictProxy('craftingHints')

__all__ = ['rcpByName','itmByName','mchByName', 'recipesThatMake', 'recipesThatUse']
