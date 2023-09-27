from .fracs import Frac, frac
from .core import *
from .box import *
from .data import *

__all__ = ('toJsonObj', 'fromJsonObj')

def _jsonObj(obj):
    if isinstance(obj, Frac):
        return str(obj)
    if hasattr(obj, '_jsonObj'):
        return obj._jsonObj()
    return obj

class _ObjsEncodeDict(dict):
    __slots__ = ('idx')
    def __init__(self):
        self.idx = 0
    def add(self, id):
        assert(id not in self)
        self.idx += 1
        self[id] = self.idx
        return self.idx

def toJsonObj(other, customRecipeCache = None):
    """Convert a factory to a dict that can then be converted to JSON

    INCOMPLETE.  Do a round trip test before using for anything serious.
    """
    customRecipes = {}
    factory = other._jsonObj(objs = _ObjsEncodeDict(), customRecipes = customRecipes)
    obj = {'factory': factory}
    if customRecipes:
        obj['custom-recipes'] = {
            r.name: {'name': r.name,
                     'madeIn': r.madeIn.name,
                     'inputs': [(_jsonObj(num), item.name) for num, item in r.inputs],
                     'outputs': [(_jsonObj(num), item.name) for num, item in r.outputs],
                     'time': _jsonObj(r.time),
                     'order': r.order} for r in customRecipes.values()}
        if customRecipeCache is not None:
            customRecipeCache.update(customRecipes)
    return obj

def fromJsonObj(jsonObj, customRecipeCache = None):
    """Convert a dict (presumably created from JSON) to a factory"""
    customRecipes = {}
    for ro in jsonObj.get('custom-recipes', {}).values():
        r = _decodeCustomRecipe(ro)
        if customRecipeCache and r.name in customRecipeCache:
            if not r.eqv(customRecipeCache[r.name]):
                raise ValueError(f'recipe {r.name} does not match provided')
            r = customRecipeCache[r.name]
        customRecipes[r.name] = r
    from .config import gameInfo
    return _fromJsonObj(gameInfo.get(), jsonObj['factory'], {}, customRecipes)

def _fromJsonObj(gi, jsonObj, objs, customRecipes):
    if type(jsonObj) is int:
        return objs[jsonObj]
    if jsonObj['name'] == '<group>':
        machines = [_fromJsonObj(gi, m, objs, customRecipes) for m in jsonObj['machines']]
        obj = Group(machines)
    elif jsonObj['name'] == '<mul>':
        machine = _fromJsonObj(gi, jsonObj['machine'], objs, customRecipes)
        num = _decodeNum(jsonObj['num'])
        obj = Mul(machine, num)
    elif jsonObj['name'] == '<box>':
        inner = _fromJsonObj(gi, jsonObj['inner'], objs, customRecipes)
        args = {'name': jsonObj.get('label', None)}
        if 'outputs' in jsonObj:
            args['outputs'] = {gi.itmByName[k]: _decodeNum(v) for k,v in jsonObj['outputs'].items()}
        if 'inputs' in jsonObj:
            args['inputs'] = {gi.itmByName[k]: _decodeNum(v) for k,v in jsonObj['inputs'].items()}
        if 'constraints' in jsonObj:
            args['constraints'] = {gi.itmByName[k]: _decodeNum(v) for k,v in jsonObj['constraints'].items()}
        if 'priority' in jsonObj:
            args['priority'] = {_decodeItemOrRecipe(gi, k, customRecipes): _decodeNum(v) for k,v in jsonObj['priority'].items()}
        obj = Box(inner, **args)
    else:
        cls = gi.mchByName[jsonObj['name']]
        obj = cls()
        if 'recipe' in jsonObj:
            obj.recipe = _decodeRecipe(gi, jsonObj['recipe'], customRecipes)
        if 'modules' in jsonObj:
            obj.modules = [_decodeModule(gi, m) for m in jsonObj['modules']]
        if 'beacons' in jsonObj:
            obj.beacons = [Mul(num, _fromJsonObj(gi, b, objs, customRecipes)) for (num, b) in jsonObj['beacons']]
        if 'fuel' in jsonObj:
            obj.fuel = gi.itmByName[jsonObj['fuel']]
    if 'id' in jsonObj:
        objs[jsonObj['id']] = obj
    return obj

def _decodeNum(num):
    if num is None:
        return None
    else:
        return frac(num)

def _decodeRecipe(gi, recipeStr, customRecipes, **kwargs):
    name, _, qual = recipeStr.partition(' ')
    if qual == 'custom':
        return customRecipes[name]
    elif qual != '':
        raise ValueError('unknown qualifier for recipe: {qual}')
    return gi.rcpByName[name]

def _decodeCustomRecipe(gi, jsonObj):
    return Recipe(
        name = jsonObj['name'],
        madeIn = entityToMachine[jsonObj['madeIn']],
        inputs = tuple(RecipeComponent(_decodeNum(num), gi.itmByName[item]) for num, item in jsonObj['inputs']),
        outputs = tuple(RecipeComponent(_decodeNum(num), gi.itmByName[item]) for num, item in jsonObj['outputs']),
        time = _decodeNum(jsonObj['time']),
        order = jsonObj['order']
    )

def _decodeItemOrRecipe(gi, s, customRecipes):
    typ, _, rest = s.partition(' ')
    if typ == 'i':
        return gi.itmByName[rest]
    elif typ == 'r':
        return _decodeRecipe(gi, rest, customRecipes)

def _decodeModule(gi, s):
    if type(s) is str:
        return gi.itmByName[s]
    else:
        args = {k: _decodeNum(v) for k,v in s.items()}
        return FakeModule(**args)

