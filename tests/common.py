from pathlib import Path
from collections import defaultdict

from factoriocalc import *
setGameConfig('v1.1')
origGameConfig = setGameConfig('v2.0-sa')
saGameConfig = config.gameInfo.get()
config.gameInfo.reset(origGameConfig)
del origGameConfig

testDir = Path(__file__).parent.resolve()

_bpBook = None
def bpBook():
    global _bpBook
    if _bpBook:
        return _bpBook
    p = testDir / 'blueprint-book.txt'
    with open(p) as f:
        bp_str = f.read()
        _bpBook = importBlueprint(bp_str)
    return _bpBook

_circuitsBpBook = None
def circuitsBpBook():
    global _circuitsBpBook
    if _circuitsBpBook:
        return _circuitsBpBook
    p = testDir / 'circuits.txt'
    with open(p) as f:
        bp_str = f.read()
        _circuitsBpBook = importBlueprint(bp_str)
    return _circuitsBpBook

science3inputs = {itm.lubricant_barrel: None,
                  itm.iron_plate: -45*4,
                  itm.copper_plate: -45*2,
                  itm.steel_plate: -45*3,
                  itm.electronic_circuit: -45*3,
                  itm.advanced_circuit: -45*3,
                  itm.processing_unit: -30,
                  itm.stone: -45*2,
                  itm.stone_brick: -45*2,
                  itm.coal: -45*2,
                  itm.sulfur: '-7.5',
                  itm.sulfuric_acid: None,
                  itm.low_density_structure: -30,
                  itm.rocket_fuel: -15}

def science3Boxed():
    grp0 = bpBook().find('science3').convert()
    grp = grp0[0]
    tally=defaultdict(list)
    for m in grp:
        tally[(m.blueprintInfo['position']['x'],m.recipe)].append(m)

    def extract(f):
        res = []
        keys = [k for k in tally.keys() if f(k)]
        for k in keys:
            res += tally[k]
            del tally[k]
        return res

    def extractByPos(minX, maxX = None):
        if maxX is None:
            maxX = minX
        return extract(lambda k: k[0] >= minX and k[0] <= maxX)

    bA = Box(Group(extractByPos(-188.5)))
    bL = Box(Group(extractByPos(-178.5)))
    bM = Box(Group(extractByPos(-168.5,-158.5)))
    bC = Box(Group(extract(lambda k: k[1] == rcp.chemical_science_pack)))
    engineB = Box(Group(extractByPos(-136.5,-126.5)))
    bU = Box(Group(extractByPos(-116.5,-106.5)))
    bP = Box(Group(extractByPos(-96.5,-70.5)))
    batteryB = Box(Group(extract(lambda k: k[1] == rcp.battery)))
    bS = Box(Group(extract(lambda k: True)))

    return Group(Group(bA,bL,bM,bC,engineB,bU,bP,batteryB,bS),
                 grp0[1])


