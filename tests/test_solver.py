import factoriocalc
from factoriocalc import *
from factoriocalc.solver import SolveRes
from contextlib import redirect_stdout
import io
import unittest
import os
import importlib
from types import MethodType
from typing import Callable
from copy import copy, deepcopy

from .common import *
from factoriocalc.presets import *
from factoriocalc.mch import AssemblingMachine3,ElectricFurnace,ChemicalPlant,OilRefinery,Centrifuge,Boiler

def _fromBlueprint(name, burnerFuel = None, **boxParams):
    grp = bpBook().find(name).convert(burnerFuel = burnerFuel)[0]
    return Box(grp, **boxParams)

class SolverTest:
    __slots__ = ('factory', 'res', 'flows', 'solution')
    def __init__(self, *args):
        idx = 0
        self.factory = args[idx]
        self.res = None
        self.flows = None
        self.solution = None
        idx += 1
        if idx >= len(args): return
        if type(args[idx]) is SolveRes:
            self.res = args[idx]
            idx += 1
        if idx >= len(args): return
        if type(args[idx]) is dict:
            self.flows = args[idx]
            idx += 1
        if idx >= len(args): return
        if type(args[idx]) is dict:
            self.solution = args[idx]
            idx += 1
        assert(idx == len(args))
    def __get__(self, instance, cls = None):
        if instance is None:
            return self
        return MethodType(self, instance)
    def solve(self):
        factory = self.factory()
        solver = factory.solver()
        solver.solve()
        res, solution = solver.apply()
        return factory, res, solution
    def __call__(self, outer):
        with redirect_stdout(io.StringIO()) as f:
            factory, res, solution = self.solve()
            testIfSolved = True
            if self.res is not None:
                if self.res is not res:
                    raise outer.failureException(f'expected {self.res} result, but got {res}')
                if self.res.notok():
                    testIfSolved = False
            elif res.notok():
                raise outer.failureException('res not ok')
            if testIfSolved and not factory.solved():
                raise outer.failureException('not solved')
            if self.flows:
                flows = factory.flows()
                for item, rate in self.flows.items():
                    if flows.flow(item).rate() != rate:
                        raise outer.failureException('{0}: expected {1} ({1:.9g}) but got {2} ({2:.9g})'
                                                     .format(item,rate,flows.flow(item).rate()))
            if self.solution:
                for var, rate in solution.items():
                    if var.name not in self.solution:
                        continue
                    if rate != self.solution[var.name]:
                        raise outer.failureException('{0}: expected {1} ({1:.9g}) but got {2} ({2:.9g})'
                                                     .format(var.name, self.solution[var.name], rate))

# fixme: this is a bit of a hack
class ProduceTest(SolverTest):
    def solve(self):
        res = self.factory()
        return res.factory, res.solveRes, None

class SolverTests(unittest.TestCase):
    testJustOil = SolverTest(lambda: Box(Group(
        110*OilRefinery(rcp.advanced_oil_processing),
        23*ChemicalPlant(rcp.heavy_oil_cracking),
        42*ChemicalPlant(rcp.light_oil_cracking),
    ), outputs = {itm.heavy_oil: 100, itm.light_oil: 688, itm.petroleum_gas: 1600}))

    testJustOilLackOfRefin = SolverTest(lambda: Box(Group(
        100*OilRefinery(rcp.advanced_oil_processing),
        23*ChemicalPlant(rcp.heavy_oil_cracking),
        42*ChemicalPlant(rcp.light_oil_cracking),
    ), outputs = {itm.heavy_oil: 100, itm.light_oil: 688, itm.petroleum_gas: 1600}), SolveRes.PARTIAL)

    testOilStuff = SolverTest(lambda: Box(Group(
        110*OilRefinery(rcp.advanced_oil_processing),
        23*ChemicalPlant(rcp.heavy_oil_cracking),
        42*ChemicalPlant(rcp.light_oil_cracking),
        10*ChemicalPlant(rcp.lubricant),
        80*ChemicalPlant(rcp.plastic_bar),
        125*ChemicalPlant(rcp.solid_fuel_from_light_oil),
        150*AssemblingMachine3(rcp.rocket_fuel),
    )))

    testMoreOilStuff = SolverTest(lambda: Box(Group(
        110*OilRefinery(rcp.advanced_oil_processing),
        25*ChemicalPlant(rcp.heavy_oil_cracking),
        45*ChemicalPlant(rcp.light_oil_cracking),
        10*ChemicalPlant(rcp.lubricant),
        72*ChemicalPlant(rcp.plastic_bar),
        7*ChemicalPlant(rcp.sulfur),
        125*ChemicalPlant(rcp.solid_fuel_from_light_oil),
        70*ChemicalPlant(rcp.solid_fuel_from_petroleum_gas),
        150*AssemblingMachine3(rcp.rocket_fuel),
    )))

    testOilStuffLackOfRefin = SolverTest(lambda: Box(Group(
        100*OilRefinery(rcp.advanced_oil_processing),
        23*ChemicalPlant(rcp.heavy_oil_cracking),
        42*ChemicalPlant(rcp.light_oil_cracking),
        10*ChemicalPlant(rcp.lubricant),
        80*ChemicalPlant(rcp.plastic_bar),
        125*ChemicalPlant(rcp.solid_fuel_from_light_oil),
        150*AssemblingMachine3(rcp.rocket_fuel),
    )),)

    testPlasticAndSulfer = SolverTest(lambda: _fromBlueprint(
        'plastic+sulfer'
    ), {itm.plastic_bar: frac(1703, 5), itm.sulfuric_acid: frac(1703, 2)})

    testPlastic = (lambda: _fromBlueprint(
        'plastic'
    ), {itm.plastic_bar: frac(1568463, 9250)})

    testComplicatedOilStuff = SolverTest(lambda: _fromBlueprint(
        'oil-stuff+lds',
        burnerFuel = itm.solid_fuel,
        outputTouchups = {itm.plastic_bar: None}
    ), {}, {'advanced-oil-processing-t': 1, 'coal-liquefaction-t': 1})

    testComplicatedOilStuff2 = SolverTest(lambda: _fromBlueprint(
        'oil-stuff+lds',
        burnerFuel = itm.solid_fuel,
        priorities = {rcp.plastic_bar: 1},
        outputTouchups = {itm.plastic_bar: None}
    ), {}, {'plastic-bar-t': 1, 'low-density-structure-t': 1,
            'advanced-oil-processing-t': 1, 'coal-liquefaction-t': 1})

    testComplicatedOilStuff3 = SolverTest(lambda: _fromBlueprint(
        'oil-stuff+lds',
        burnerFuel = itm.solid_fuel,
        outputs = {itm.lubricant_barrel: frac(487296, 136585),
                   itm.flamethrower_ammo: frac(1, 3),
                   itm.sulfur: frac(28858752, 682925),
                   itm.low_density_structure: frac(672, 25),
                   itm.rocket_fuel: frac(12088776, 682925),
                   itm.plastic_bar: frac(1448, 25)
        }
    ))

    testComplicatedOilStuff4 = SolverTest(
        lambda: Box(bpBook().find('oil-stuff+lds').convert(burnerFuel = itm.solid_fuel)[0]
                    + 10*OilRefinery(rcp.coal_liquefaction) + 24*Boiler(fuel=itm.solid_fuel),
                    outputTouchups = {itm.plastic_bar: frac(1448, 25),
                                      itm.low_density_structure: frac(672, 25)},
        ), {}, {'plastic-bar-t': 1, 'low-density-structure-t': 1,
                'rocket-fuel-1': 1, 'sulfer-t': 1, 'lubricant-t': 1,
                'flamethrower-ammo-t': 1})

    testCircuits = SolverTest(lambda: _fromBlueprint(
        'circuits3',
        outputs=[itm.electronic_circuit,itm.advanced_circuit,itm.processing_unit]
    ), {itm.electronic_circuit: frac(4429, 30), itm.advanced_circuit: frac(1936, 15), itm.processing_unit: frac(616, 25)})

    testNuclearStuff1 = SolverTest(lambda: withSettings(
        {config.machinePrefs: ((Centrifuge(modules=2*itm.productivity_module_3,beacons=4*SPEED_BEACON),) + MP_LATE_GAME)},
        lambda: Box(1*rcp.uranium_processing(beacons=5*SPEED_BEACON)
                    + 3*rcp.uranium_processing(beacons=5*SPEED_BEACON)
                    + 2*rcp.kovarex_enrichment_process(beacons=5*SPEED_BEACON)
                    + 1*rcp.kovarex_enrichment_process(beacons=4*SPEED_BEACON)
                    + 5*rcp.nuclear_fuel_reprocessing()
                    + rcp.uranium_fuel_cell(modules=4*itm.productivity_module_3,beacons=1*SPEED_BEACON)
                    + 3*rcp.nuclear_fuel()
                    + 4*rcp.uranium_rounds_magazine(modules=[],beacons=[]),
                    priorities={rcp.nuclear_fuel_reprocessing:2, itm.nuclear_fuel:1},
                    constraints=[Equal(itm.uranium_fuel_cell, (-1, itm.used_up_uranium_fuel_cell))],
                    outputTouchups = {itm.uranium_fuel_cell: 1})
    ), {itm.nuclear_fuel: frac(27,250), itm.uranium_rounds_magazine: frac(44227,175000),
        itm.uranium_fuel_cell: 1, itm.used_up_uranium_fuel_cell: -1})

    testNuclearStuff2 = SolverTest(lambda: withSettings(
        {config.machinePrefs: ((Centrifuge(modules=2*itm.productivity_module_3,beacons=4*SPEED_BEACON),) + MP_LATE_GAME)},
        lambda: Box(1*rcp.uranium_processing(beacons=6*SPEED_BEACON)
                    + 3*rcp.uranium_processing(beacons=7*SPEED_BEACON)
                    + 2*rcp.kovarex_enrichment_process(beacons=5*SPEED_BEACON)
                    + 1*rcp.kovarex_enrichment_process(beacons=4*SPEED_BEACON)
                    + 5*rcp.nuclear_fuel_reprocessing()
                    + rcp.uranium_fuel_cell(modules=4*itm.productivity_module_3,beacons=1*SPEED_BEACON)
                    + 3*rcp.nuclear_fuel()
                    + 4*rcp.uranium_rounds_magazine(modules=[],beacons=[]),
                    priorities={rcp.nuclear_fuel_reprocessing:2, itm.nuclear_fuel:1},
                    constraints=[Equal(itm.uranium_fuel_cell, (-1, itm.used_up_uranium_fuel_cell))])
    ), {itm.nuclear_fuel: frac(27,250), itm.uranium_rounds_magazine: frac(1,2),
        itm.uranium_fuel_cell: frac(9,8), itm.used_up_uranium_fuel_cell: frac(-9,8)})

    # NOTE:
    #  >>> both = produce([itm.plastic_bar@90, itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]).factory
    #  >>> plastic = produce([itm.plastic_bar@90], using=[rcp.advanced_oil_processing]).factory
    #  >>> rocketFuel = produce([itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]).factory
    #  >>> combined = union(both, plastic, rocketFuel)[0] # THE TEST CASE
    #  >>> s = combined.solver()
    #  >>> s.tableau.solve(zero=True) # get ride of artificial vars
    #  >>> s.tableau.addPendingObjective()
    #  >>> s.tableau.solve()
    #  >>> s.tableau.print()
    #          -0-    -1-    -2-    -3-    -4-   -5-  -6-  -7-  -8-  -9- -10-
    #        plasti light- solid- rocket solid-  s2   s3   s4   s5   s6   s7  |    rhs
    #     0:    0      0    0.320    0     *1*    0    0    0    0    1    0  |     1     | -4- solid-fuel-from-light-oil-t
    #     1:   *1*     0    0.173    0      0    1.8   0    0    0  -0.4   0  |     1     | -0- plastic-bar-t
    #     2:    0     *1*  -0.253    0      0    1.8   0    0    0  -0.8   0  |  0.573402 | -1- light-oil-cracking-t
    #     3:    0      0   -0.173    0      0   -1.8  *1*   0    0   0.4   0  |     0     | -6- s3
    #     4:    0      0    0.253    0      0   -1.8   0   *1*   0   0.8   0  |  0.426598 | -7- s4
    #     5:    0      0      1      0      0     0    0    0   *1*   0    0  |     1     | -8- s5
    #     6:    0      0      0     *1*     0     0    0    0    0    1    0  |     1     | -3- rocket-fuel-t
    #     7:    0      0   -0.320    0      0     0    0    0    0   -1   *1* |     0     | -10- s7
    #
    #     8:    0      0    0.173    0      0    1.8   0    0    0   0.5   0  |     2     | max (0-max)
    #     9:    0      0    0.173    0      0    1.8   0    0    0  -0.4   0  |     1     | aux (plastic-bar-t)
    #    10:    0      0      0      0      0     0    0    0    0    1    0  |     1     | aux (rocket-fuel-t)
    #
    #  At first glance it looks like the aux objective for plastic-bar-t is
    #  not optimal (due to the -0.4), however it is.  This test case is to
    #  make sure the solver correctly returns SolveRes.UNIQUE and not
    #  SolveRes.OK.
    testPreciseOilStuff = SolverTest(lambda: withSettings(
        {config.machinePrefs: MP_MAX_PROD().withBeacons(SPEED_BEACON, {AssemblingMachine3:8, ChemicalPlant:8, OilRefinery:12})},
        lambda: Box('9000/1183'*rcp.plastic_bar()
                    + '1800/77'*rcp.rocket_fuel()
                    + '739040000/142730133'*rcp.advanced_oil_processing()
                    + '2220000/363181'*rcp.light_oil_cracking()
                    + '18476000/7626801'*rcp.heavy_oil_cracking()
                    + '120000/8281'*rcp.solid_fuel_from_light_oil()
                    + '1193280/256711'*rcp.solid_fuel_from_petroleum_gas())
    ), SolveRes.UNIQUE, {itm.plastic_bar: 90, itm.rocket_fuel: 6})

class SolverTests2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origMachinePrefs = config.machinePrefs.set((
            ElectricFurnace(modules=2*itm.effectivity_module_2),
            *MP_MAX_PROD().withBeacons(SPEED_BEACON, {AssemblingMachine3:8, OilRefinery:12, ChemicalPlant:8})))

        cb = circuitsBpBook()
        g0 = BlackBox(box(cb.find('green0').convert()[0]), name='green')
        r0 = BlackBox(box(cb.find('red0').convert()[0]), name='red')

        cls.circuits6 = Box(3*copy(g0) + 3*copy(r0) + 12*rcp.processing_unit(),
                        outputs=[itm.electronic_circuit, itm.advanced_circuit, itm.processing_unit],
                        inputTouchups = [itm.iron_plate@(45*4), itm.copper_plate@(45*6)])

        cls.speedModules = Box(rcp.speed_module_3(modules=2*itm.speed_module_3,beacons=[])
                               + ~rcp.speed_module_2(beacons=[])
                               + ~rcp.speed_module(beacons=[]))

        cls.rocketControlUnits6 = rocketControlUnits6 = box(12*rcp.rocket_control_unit(beacons=8*SPEED_BEACON)
                                                            + 4*rcp.rocket_control_unit(beacons=10*SPEED_BEACON)
                                                            + 38*rcp.speed_module(beacons=[]))

    @classmethod
    def tearDownClass(cls):
        config.machinePrefs.reset(cls.origMachinePrefs)

    testInnerBlackBoxes = SolverTest(lambda: SolverTests2.circuits6,
        {itm.electronic_circuit: frac('31.8'),
         itm.advanced_circuit: frac('48.4'),
         itm.processing_unit: frac('9.24')})

    testInnerUnboundedBoxes = SolverTest(lambda: SolverTests2.speedModules,
        {itm.speed_module_3: frac(1,24), itm.speed_module_2: 0, itm.speed_module: 0})

    testNested = SolverTest(lambda: Box(SolverTests2.circuits6
                                        + SolverTests2.rocketControlUnits6
                                        + 6*box(SolverTests2.speedModules).finalize().factory,
                                        outputs=[*SolverTests2.circuits6.outputs, itm.speed_module_3, itm.rocket_control_unit @ 2],
                                        priorities={itm.speed_module_3:1}),
        {itm.speed_module_3: frac(1,4), itm.rocket_control_unit: 2})

# _science = _fromBlueprint('science3')

def _populate(cls, scienceGrp):
    maxOutputs = {itm.automation_science_pack: frac(1449, 80),
                  itm.logistic_science_pack: frac(272, 15),
                  itm.military_science_pack: frac(217, 12),
                  itm.chemical_science_pack: frac(8659, 480),
                  itm.production_science_pack: frac(1443, 80),
                  itm.utility_science_pack: frac(144501, 8000),
                  itm.space_science_pack: frac(10829, 600)}

    inputs = science3inputs

    cls.testRaw = SolverTest(lambda: Box(
        scienceGrp()
    ), maxOutputs)

    cls.testAll7NoResearch = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs
    )) # the exact output rates depends on implementation details

    cls.testAll7_12l = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputsLoose = True,
        outputTouchups = {item: 12 for item in sciencePacks},
    )) # the exact output rates depends on implementation details

    cls.testAll7_18 = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputTouchups = {item: 18 for item in sciencePacks},
    ), SolveRes.PARTIAL) # the exact output rates depends on implementation details

    cls.testAll7_18l = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputTouchups = {item: 18 for item in sciencePacks},
        outputsLoose = True,
    ), SolveRes.PARTIAL) # the exact output rates depends on implementation details

    cls.testProdNoResearch = SolverTest(lambda: Box(
        scienceGrp(),
        outputTouchups = {itm.military_science_pack: 0},
        inputs = inputs
    ), SolveRes.UNIQUE, {item: rate for item, rate in maxOutputs.items() if item is not itm.military_science_pack})

    cls.testMilNoResearch = SolverTest(lambda: Box(
        scienceGrp(),
        outputTouchups = {itm.production_science_pack: 0},
        inputs = inputs
    ), SolveRes.UNIQUE, {item: rate for item, rate in maxOutputs.items() if item is not itm.production_science_pack})

    cls.testProdPriority = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        priorities = {itm.military_science_pack: -1},
    ), {item: rate for item, rate in maxOutputs.items() if item is not itm.military_science_pack})

    cls.testMilPriority = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        priorities = {itm.production_science_pack: -1},
    ), {item: rate for item, rate in maxOutputs.items() if item is not itm.production_science_pack})

    cls.testProd18 = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputTouchups = {item: 18 for item in sciencePacks if item is not itm.military_science_pack},
    ), SolveRes.UNIQUE,
       {itm.automation_science_pack: 18,
        itm.logistic_science_pack: 18,
        itm.military_science_pack: frac(13317677, 1152480),
        itm.chemical_science_pack: 18,
        itm.production_science_pack: 18,
        itm.utility_science_pack: 18,
        itm.space_science_pack: 18})

    cls.testProd18l = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputTouchups = {item: 18 for item in sciencePacks if item is not itm.military_science_pack},
        outputsLoose = True,
    )) # the exact output rates depends on implementation details

    cls.testMil18 = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputTouchups = {item: 18 for item in sciencePacks if item is not itm.production_science_pack},
    ), SolveRes.UNIQUE,
       {itm.automation_science_pack: 18,
        itm.logistic_science_pack: 18,
        itm.military_science_pack: 18,
        itm.chemical_science_pack: 18,
        itm.production_science_pack: frac(2415111, 1372000),
        itm.utility_science_pack: 18,
        itm.space_science_pack: 18})

    cls.testMil18l = SolverTest(lambda: Box(
        scienceGrp(),
        inputs = inputs,
        outputTouchups = {item: 18 for item in sciencePacks if item is not itm.production_science_pack},
        outputsLoose = True,
    )) # the exact output rates depends on implementation details

    cls.testAll7 = SolverTest(lambda: Box(
        scienceGrp() + 20*FakeLab(rcp._combined_research),
        outputs = [itm._combined_research, itm.empty_barrel],
        inputs = inputs,
    ), SolveRes.UNIQUE, {itm._combined_research: frac(378, 25)})

    cls.testProd = SolverTest(lambda: Box(
        scienceGrp() + 20*FakeLab(rcp._production_research),
        outputs = [itm._production_research, itm.empty_barrel],
        inputs = inputs
    ), SolveRes.UNIQUE, {itm._production_research: frac(1443, 80)})

    cls.testMil = SolverTest(lambda: Box(
        scienceGrp() + 20*FakeLab(rcp._military_research),
        outputs = [itm._military_research, itm.empty_barrel],
        inputs = inputs
    ), SolveRes.UNIQUE, {itm._military_research: frac(8659, 480)})

class TestScience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.science = bpBook().find('science3').convert()[0].summarize()

    @classmethod
    def getScience(cls):
        return deepcopy(cls.science)

_populate(TestScience, TestScience.getScience)

class TestScienceB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.science = science3Boxed().summarize()

    @classmethod
    def getScience(cls):
        return deepcopy(cls.science)

_populate(TestScienceB, TestScienceB.getScience)

class ProduceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origMachinePrefs = config.machinePrefs.set(MP_LATE_GAME + (mch.RocketSilo(modules=4*itm.productivity_module_3),))

    @classmethod
    def tearDownClass(cls):
        config.machinePrefs.reset(cls.origMachinePrefs)

    testElectronicCircuit = ProduceTest(
        lambda: produce([itm.electronic_circuit@30]),
        {itm.electronic_circuit: 30, itm.copper_ore: -45, itm.iron_ore: -30})

    testJustOil = ProduceTest(
        lambda: produce([itm.petroleum_gas@60], using=[rcp.advanced_oil_processing]),
        {itm.petroleum_gas: 60, itm.crude_oil: frac(-800,13)})

    testPlasticFromCoal = ProduceTest(
        lambda: produce([itm.plastic_bar@30], using=[rcp.coal_liquefaction]),
        {itm.plastic_bar: 30, itm.coal: frac(-4740,67)})

    testRocketFuel = ProduceTest(
        lambda: produce([itm.rocket_fuel@6], using=[rcp.advanced_oil_processing]),
        {itm.rocket_fuel: 6, itm.crude_oil: frac(-52800,73)})

    testUranium238 = ProduceTest(
        lambda: produce([itm.uranium_fuel_cell@1],[rcp.uranium_processing, rcp.kovarex_enrichment_process,
                                                   itm.used_up_uranium_fuel_cell@1]),
        {itm.uranium_fuel_cell: 1, itm.used_up_uranium_fuel_cell: -1,
         itm.uranium_ore: frac(-8000,507), itm.uranium_238: 0})

    testSpaceSciencePack = ProduceTest(
        lambda: produce([itm.space_science_pack@1],recursive=False),
        {itm.space_science_pack:1, itm.rocket_control_unit: frac(-5,7), itm.satellite: frac(-1,1000)})

origGameConfig = config.gameInfo.set(saGameConfig)

class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origGameInfo = config.gameInfo.set(saGameConfig)
        cls.origMachinePrefs = config.machinePrefs.set(presets.MP_LEGENDARY)

    @classmethod
    def tearDownClass(cls):
        config.machinePrefs.reset(cls.origMachinePrefs)
        config.gameInfo.reset(cls.origGameInfo)

    testLegendaryElectronicCircuitWithProd = SolverTest(
        lambda: Box([*~rcp.electronic_circuit.allQualities(),
                     *~rcp.electronic_circuit_recycling.allQualities[0:4]()],
                    inputs = rcp.electronic_circuit.inputs,
                    outputs = [itm.legendary_electronic_circuit@1]),
        {itm.legendary_electronic_circuit: 1,
         itm.iron_plate: frac(-1032035698176,73013623859),
         itm.copper_cable: frac(-3096107094528,73013623859)}
    )

    testLegendaryElectronicCircuitWithQuality = SolverTest(
        lambda: Box([*~rcp.electronic_circuit.allQualities(modules=itm.legendary_quality_module_3)[0:4],
                     ~rcp.legendary_electronic_circuit(),
                     *~rcp.electronic_circuit_recycling.allQualities[0:4]()],
                    inputs = rcp.electronic_circuit.inputs, outputs = [itm.legendary_electronic_circuit@1]),
        {itm.legendary_electronic_circuit: 1,
         itm.iron_plate: frac(-1346603122378414326272,57354060737264781873),
         itm.copper_cable: frac(-1346603122378414326272,19118020245754927291)}
    )

    testLegendaryElectronicCircuitWithBoth = SolverTest(
        lambda: Box([*~rcp.electronic_circuit.allQualities(),
                     *~rcp.electronic_circuit.allQualities(modules=itm.legendary_quality_module_3)[0:4],
                     *~rcp.electronic_circuit_recycling.allQualities[0:4]()],
                    inputs = rcp.electronic_circuit.inputs,
                    outputs = [itm.legendary_electronic_circuit@1]),
        {itm.legendary_electronic_circuit: 1,
         itm.iron_plate: frac(-1032035698176,73013623859),
         itm.copper_cable: frac(-3096107094528,73013623859)}
    )

    testPreferMachinesWithProdOverQualityModules = SolverTest(
        lambda: Box([~rcp.molten_iron(),
                     2*rcp.casting_iron(),
                     rcp.casting_iron(modules=itm.legendary_quality_module_3)],
                    outputTouchups = [itm.iron_plate@15],
                    priorities = [(rcp.casting_iron(),1)]),
        {itm.iron_plate: 15, itm.uncommon_iron_plate: frac(279,376), itm.legendary_iron_plate: frac(31,37600),
         itm.iron_ore: frac(-407,141)}
    )

    testPreferMachinesWithQualityOverProdModules = SolverTest(
        lambda: Box([~rcp.molten_iron(),
                     2*rcp.casting_iron(),
                     rcp.casting_iron(modules=itm.legendary_quality_module_3)],
                    outputTouchups = [itm.iron_plate@15],
                    priorities = [(rcp.casting_iron(modules=itm.legendary_quality_module_3),1)]),
        {itm.iron_plate: 15, itm.uncommon_iron_plate: frac(837,500), itm.legendary_iron_plate: frac(93,50000),
         itm.iron_ore: frac(-2186,625)}
    )

config.gameInfo.reset(origGameConfig)
