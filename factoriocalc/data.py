from __future__ import annotations
import dataclasses as _dc

@_dc.dataclass
class CraftingHint:
    also: list = _dc.field(default_factory = list)
    priority: int = 0
    boxPriority: int = 0

class Objs:
    def _find(self, toFind):
        """
        Perform a case insensitive search of any occurrence of the substring
        `toFind` in the `descr` field of members.
        """
        toFind = toFind.lower()
        res = []
        for obj in self.__dict__.values():
            if obj.descr.lower().find(toFind) >= 0:
                res.append(obj)
        return res
    pass

@_dc.dataclass
class GameInfo:
    gameVersion: string
    rcp: Objs = _dc.field(default_factory = Objs)
    rcpByName: dict = None
    itm: Objs = _dc.field(default_factory = Objs)
    itmByName: dict = None
    mch: Objs = _dc.field(default_factory = Objs)
    mchByName: dict = None
    emptyBarrel: Item = None
    presets: dict = None
    recipesThatMake: dict = None
    recipesThatUse: dict = None
    craftingHints: dict = None
    rocketSiloDefaultProduct: dict = _dc.field(default_factory = dict)
    translatedNames: dict = None
    aliases: dict = _dc.field(default_factory = dict)
    disabledRecipes: set = _dc.field(default_factory = set)
    qualityLevels: list[str] =  _dc.field(default_factory = list)
    maxQualityIdx: int = 0
    recipeProductivityBonus: dict = _dc.field(default_factory = dict)
    fuelPreferences: list[Item] = None

    @_dc.dataclass
    class Modules:
        class List(list):
            __slots__ = ('best')
        speed: dict = _dc.field(default_factory = List)
        productivity: dict = _dc.field(default_factory = List)
        effectivity: dict = _dc.field(default_factory = List)
        other: dict = _dc.field(default_factory = List)

    modules: Modules = _dc.field(default_factory = Modules)

    def finalize(self):
        self.recipesThatMake = {}
        self.recipesThatUse = {}

        for r in self.rcpByName.values():
            for _, _, item in r.outputs:
                self.recipesThatMake.setdefault(item, []).append(r)
            for _, _, item in r.inputs:
                self.recipesThatUse.setdefault(item, []).append(r)

        from .core import Module
        for m in self.itmByName.values():
            if not isinstance(m, Module):
                continue
            me = m.effect
            if me.speed > 0 and me.productivity == 0 and me.consumption >= 0 and me.pollution >= 0:
                self.modules.speed.append(m)
            elif me.speed <= 0 and me.productivity > 0 and me.consumption >= 0 and me.pollution >= 0:
                self.modules.productivity.append(m)
            elif me.speed == 0 and me.productivity == 0 and me.consumption < 0 and me.pollution <= 0:
                self.modules.effectivity.append(m)
            else:
                self.modules.other.append(m)
            self.modules.speed.sort(key = lambda m: m.effect.speed)
            self.modules.productivity.sort(key = lambda m: m.effect.productivity)
            self.modules.effectivity.sort(key = lambda m: (-m.effect.consumption, -m.effect.pollution))
            self.modules.other.sort()

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
    def items(self):
        from .config import gameInfo
        return getattr(gameInfo.get(), self.field).items()
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
translatedNames = DictProxy('translatedNames')

__all__ = ['rcpByName','itmByName','mchByName', 'recipesThatMake', 'recipesThatUse']
