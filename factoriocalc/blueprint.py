from __future__ import annotations
from collections import defaultdict
from itertools import chain, repeat
from pathlib import Path
import math

from .core import *
from . import config, machine

__all__ = ('Blueprint', 'BlueprintBook', 'importBlueprint')

def _getNameWithQuality(name, quality):
    if quality is None or quality == 'normal':
        return name
    else:
        return f'{quality}-{name}'

class Blueprint:
    def __init__(self, bp):
        """Create a blueprint from a decoded JSON object.

        See also `importBlueprint`.
        """
        if 'blueprint' not in bp:
            raise ValueError('expected a blueprint')
        self.raw = bp
    def convert(self, *, burnerFuel=None, recipes=None) -> Group:
        """Convert a blueprint into a nested `Group`.

        The outer group contained two inner groups.  The first inner group is
        the factory, and the second is the beacons the factory used.

        If *burnerFuel* is defined than use that item for machines that
        require a fuel source, otherwise `config.defaultFuel` is used.  If
        *recipes* are defined it is expected to be a mapping of machines
        classes to recipes and will be used as the recipe for that machine if
        none is defined.

        The original blueprint info for each machine is stored in the
        `~Group.blueprintInfo` field.

        """
        gameInfo = config.gameInfo.get()
        itmByName = gameInfo.itmByName
        mchByName = gameInfo.mchByName
        recipeMap = gameInfo.rcpByName

        if recipes is None:
            recipes = {}
        else:
            recipes = recipes.copy()

        def recipeForMachine(m):
            if m.__class__ in recipes:
                return recipes[m.__class__]
            for c in m.__class__.__mro__:
                if c in recipes:
                    r = recipes[c]
                    recipes[m.__class__] = r
                    return r
            recipes[m.__class__] = None
            return None

        def as_int(x):
            if not x.is_integer():
                raise ValueError
            return int(x)

        machines = []
        machinesOnGrid = defaultdict(list)
        beacons = []

        version = self.raw['blueprint']['version']
        VERSION2_BP = 562949954273281

        for v in self.raw['blueprint']['entities']:
            try:
                cls = mchByName[_getNameWithQuality(v['name'], v.get('quality', None))]
            except KeyError:
                continue
            if issubclass(cls, machine.Beacon):
                m = cls(freeze=False)
            else:
                m = cls()
            m.blueprintInfo = v
            if isinstance(m, machine.RocketSilo):
                m.recipe = recipeForMachine(m)
                if m.recipe is None:
                    m.recipe = m.defaultProduct()
            elif 'recipe' in v:
                m.recipe = recipeMap[_getNameWithQuality(v['recipe'], v.get('recipe_quality', None))]
            else:
                r = recipeForMachine(m)
                if r:
                    m.recipe = r
            if hasattr(m, 'fuel'):
                if 'chemical' in m.fuelCategories and burnerFuel:
                    m.fuel = burnerFuel
                else:
                    m.fuel = m.defaultFuel()
            if 'items' in v:
                if version < VERSION2_BP:
                    m.modules = [*chain.from_iterable(repeat(itmByName[item], num) for item, num in v['items'].items())]
                else:
                    modules = []
                    for item in v['items']:
                        module = itmByName[_getNameWithQuality(item['id']['name'], item['id'].get('quality', None))]
                        # fixme: is this right
                        num = len(item['items']['in_inventory'])
                        modules += repeat(module, num)
                    m.modules = modules
            if isinstance(m, machine.Beacon):
                m._frozen = True
                beacons.append(m)
                continue
            if m:
                machines.append(m)
            if m and hasattr(m, 'beacons'):
                position = m.blueprintInfo['position']
                try:
                    x_min = as_int(position['x'] - m.width/2)
                    x_max = as_int(position['x'] + m.width/2) - 1
                    y_min = as_int(position['y'] - m.height/2)
                    y_max = as_int(position['y'] + m.height/2) - 1
                    machinesOnGrid[(x_min, x_max)].append((y_min, y_max, m))
                except ValueError as exc:
                    raise ValueError(f"Invalid position for {m.name}: ({position['x']}, {position['y']})") from exc

        machinesById = {}
        beaconsForMachine = defaultdict(list)
        for beacon in beacons:
            position = beacon.blueprintInfo['position']
            try:
                b_x_min = as_int(position['x'] - beacon.width/2) - beacon.supplyAreaDistance
                b_x_max = as_int(position['x'] + beacon.width/2) + beacon.supplyAreaDistance - 1
                b_y_min = as_int(position['y'] - beacon.height/2) - beacon.supplyAreaDistance
                b_y_max = as_int(position['y'] + beacon.height/2) + beacon.supplyAreaDistance - 1
            except ValueError as exc:
                raise ValueError(f"Invalid position for {beacon.name}: ({position['x']}, {position['y']})") from exc

            for (m_x_min, m_x_max), yp in machinesOnGrid.items():
                if b_x_min <= m_x_max and m_x_min <= b_x_max:
                    for m_y_min, m_y_max, m in yp:
                        if b_y_min <= m_y_max and m_y_min <= b_y_max:
                            machinesById[id(m)] = m
                            beaconsForMachine[id(m)].append(beacon)

        for m_id, m_beacons in beaconsForMachine.items():
            machinesById[m_id].beacons = m_beacons

        b = Group(beacons)

        return Group(Group(machines), Group(beacons))

    def group(self, **convertArgs) -> Group:
        """Shorthand for ``self.convert(**convertArgs)[0].simplify().sorted()``"""
        return self.convert(**convertArgs)[0].simplify().sorted()

class BlueprintBook:
    def __init__(self, bp):
        """Create a blueprint book from a decoded JSON object.

        See also :py:obj:`importBlueprint`.
        """
        if 'blueprint_book' not in bp:
            raise ValueError('expected a blueprint book')
        self.raw = bp
    def __getitem__(self, idx):
        return Blueprint(self.raw['blueprint_book']['blueprints'][idx])
    def __len__(self):
        return len(self.raw['blueprint_book']['blueprints'])
    def find(self, label) -> Blueprint:
        """Find the blueprint with *label*."""
        return BlueprintBook._find(self.raw, label)
    @staticmethod
    def _find(bp, label):
        if 'blueprint' in bp:
            if bp['blueprint'].get('label',None) == label:
                return Blueprint(bp)
        elif 'blueprint_book' in bp:
            for b in bp['blueprint_book']['blueprints']:
                try:
                    return BlueprintBook._find(b, label)
                except KeyError:
                    pass
        raise KeyError(label)
    def labels(self) -> list[str]:
        lst = []
        BlueprintBook._labels(self.raw, lst)
        return lst
    @staticmethod
    def _labels(bp, lst):
        if 'blueprint' in bp:
            lst.append(bp['blueprint'].get('label',None))
        elif 'blueprint_book' in bp:
            for b in bp['blueprint_book']['blueprints']:
                BlueprintBook._labels(b, lst)

def importBlueprint(arg = None, *, file = None):
    """Decode *arg* to a blueprint or blueprint book.  If *arg* is a `pathlib.Path
    <https://docs.python.org/3/library/pathlib.html>`_ or the *file* argument
    is provided than read the contents from a file, otherwise decode the
    string provided."""
    import zlib
    from base64 import b64decode
    import json

    if arg is None:
        if file is None:
            raise TypeError('either arg or file must be defined')
        arg = Path(file)
    elif file is not None:
        raise TypeError('both arg and file cannot be be defined at the same time')

    if isinstance(arg, Path):
        bpStr = arg.read_bytes()
    else:
        bpStr = arg

    decoded = b64decode(bpStr[1:])
    decompressed = zlib.decompress(decoded)
    json = json.loads(decompressed)

    if 'blueprint_book' in json:
        return BlueprintBook(json)
    else:
        return Blueprint(json)

