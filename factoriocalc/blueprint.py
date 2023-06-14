from __future__ import annotations
from itertools import chain, repeat
from pathlib import Path
import math

from .core import *
from . import config, machine
from ._helper import getDefaultFuel

__all__ = ('Blueprint', 'BlueprintBook', 'decodeBlueprint')

class Blueprint:
    def __init__(self, bp):
        """Create a blueprint from a decoded JSON object.

        See also `decodeBlueprint`.
        """
        if 'blueprint' not in bp:
            raise ValueError('expected a blueprint')
        self.raw = bp
    def convert(self, *, burnerFuel=None, rocketSiloRecipe='space-science-pack') -> Group:
        """Convert a blueprint into a `Group`."""

        def as_int(x):
            if not x.is_integer():
                raise ValeuError
            return int(x)

        gameInfo = config.gameInfo.get()
        itmByName = gameInfo.itmByName
        mchByName = gameInfo.mchByName
        recipeMap = gameInfo.rcpByName
        
        if burnerFuel is None:
            burnerFuel = getDefaultFuel()
        
        machines = []
        machinesOnGrid = {}
        beacons = []

        for v in self.raw['blueprint']['entities']:
            try:
                cls = mchByName[v['name']]
            except KeyError:
                continue
            m = cls()
            m.blueprintInfo = v
            if isinstance(m, machine.RocketSilo):
                m.recipe = recipeMap[rocketSiloRecipe]
            elif 'recipe' in v:
                m.recipe = recipeMap[v['recipe']]
            if hasattr(m, 'fuel'):
                m.fuel = burnerFuel
            if 'items' in v:
                m.modules = [*chain.from_iterable(repeat(itmByName[item], num) for item, num in v['items'].items())]
            if isinstance(m, machine.Beacon):
                beacons.append(m)
            elif m :
                machines.append(m)
                if hasattr(m, 'beacons'):
                    x_min = as_int(m.blueprintInfo['position']['x'] - m.width/2)
                    x_max = as_int(m.blueprintInfo['position']['x'] + m.width/2) - 1
                    y_min = as_int(m.blueprintInfo['position']['y'] - m.height/2)
                    y_max = as_int(m.blueprintInfo['position']['y'] + m.height/2) - 1
                    machinesOnGrid.setdefault(x_min, {})[y_min] = m
                    machinesOnGrid.setdefault(x_min, {})[y_max] = m
                    machinesOnGrid.setdefault(x_max, {})[y_min] = m
                    machinesOnGrid.setdefault(x_max, {})[y_max] = m

        for beacon in beacons:
            x_min = as_int(beacon.blueprintInfo['position']['x'] - beacon.width/2) - beacon.supplyAreaDistance
            x_max = as_int(beacon.blueprintInfo['position']['x'] + beacon.width/2) + beacon.supplyAreaDistance - 1
            y_min = as_int(beacon.blueprintInfo['position']['y'] - beacon.height/2) - beacon.supplyAreaDistance
            y_max = as_int(beacon.blueprintInfo['position']['y'] + beacon.height/2) + beacon.supplyAreaDistance - 1
            seen = set()
            for x in range(x_min, x_max + 1):
                yp = machinesOnGrid.get(x, None)
                if yp is None:
                    continue
                for y in range(y_min,y_max + 1):
                    m = yp.get(y, None)
                    if m is None or id(m) in seen:
                        continue
                    m.beacons.append(beacon)
                    seen.add(id(m))

        return Group(Group(machines), Group(beacons))

class BlueprintBook:
    def __init__(self, bp):
        """Create a blueprint book from a decoded JSON object.

        See also :py:obj:`decodeBlueprint`.
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
    def convert(self, label, **convertArgs) -> Group:
        """Convert a blueprint with *label* into a `Group`"""
        return self.find(label).convert(**convertArgs)

# fixme: rename to importBlueprint
def decodeBlueprint(bp):
    """Decode a string or file (if `pathlib.Path <https://docs.python.org/3/library/pathlib.html>`_) to a blueprint or blueprint book.
    """
    import zlib
    from base64 import b64decode
    import json

    if isinstance(bp,Path):
        bpStr = bp.read_bytes()
    else:
        bpStr = bp

    decoded = b64decode(bpStr[1:])
    decompressed = zlib.decompress(decoded)
    json = json.loads(decompressed)

    if 'blueprint_book' in json:
        return BlueprintBook(json)
    else:
        return Blueprint(json)
    
