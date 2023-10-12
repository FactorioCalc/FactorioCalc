from factoriocalc import *
from factoriocalc.mch import AssemblingMachine3, RocketSilo, OilRefinery, Centrifuge
from factoriocalc.presets import *
from unittest import TestCase

class RateTests(TestCase):
    def rateTest(self, machine, recipe, *, modules = [], beacons = [], rates = {}):
        m = machine(recipe, modules = modules, beacons = beacons)
        with self.subTest(str(m)):
            for item, rate in rates.items():
                self.assertEqual(m.flow(item).rate(), frac(rate), msg = str(item))

    def testElectronicCircuit(self):
        self.rateTest(AssemblingMachine3, rcp.electronic_circuit,
                      rates={itm.electronic_circuit: '2.5',
                             itm.iron_plate: '-2.5',
                             itm.copper_cable: '-7.5'})
        self.rateTest(AssemblingMachine3, rcp.electronic_circuit,
                      modules=4*itm.productivity_module_3,
                      rates={itm.electronic_circuit: '1.4',
                             itm.iron_plate: '-1',
                             itm.copper_cable: '-3'})
        self.rateTest(AssemblingMachine3, rcp.electronic_circuit,
                      modules=4*itm.productivity_module_3, beacons = 4*SPEED_BEACON,
                      rates={itm.electronic_circuit: '8.4',
                             itm.iron_plate: '-6',
                             itm.copper_cable: '-18'})
        self.rateTest(AssemblingMachine3, rcp.electronic_circuit,
                      beacons = 4*SPEED_BEACON,
                      rates={itm.electronic_circuit: '7.5',
                             itm.iron_plate: '-7.5',
                             itm.copper_cable: '-22.5'})

    def testSpaceSciencePack(self):
        self.rateTest(RocketSilo, rcp.space_science_pack,
                      rates={itm.space_science_pack: frac(20000, 6811),
                             itm.rocket_control_unit: frac(-20000, 6811),
                             itm.low_density_structure: frac(-20000, 6811),
                             itm.rocket_fuel: frac(-20000, 6811),
                             itm.satellite: frac(-20, 6811)})
        self.rateTest(RocketSilo, rcp.space_science_pack,
                      modules=4*itm.productivity_module_3,
                      rates={itm.space_science_pack: frac(140000, 80677),
                             itm.rocket_control_unit: frac(-100000, 80677),
                             itm.low_density_structure: frac(-100000, 80677),
                             itm.rocket_fuel: frac(-100000, 80677),
                             itm.satellite: frac(-140, 80677)})
        self.rateTest(RocketSilo, rcp.space_science_pack, beacons = 4*SPEED_BEACON,
                      modules=4*itm.productivity_module_3,
                      rates={itm.space_science_pack: frac(140000, 18177),
                             itm.rocket_control_unit: frac(-100000, 18177),
                             itm.low_density_structure: frac(-100000, 18177),
                             itm.rocket_fuel: frac(-100000, 18177),
                             itm.satellite: frac(-140, 18177)})
        self.rateTest(RocketSilo, rcp.space_science_pack,
                      beacons = 4*SPEED_BEACON,
                      rates={itm.space_science_pack: frac(20000, 2811),
                             itm.rocket_control_unit: frac(-20000, 2811),
                             itm.low_density_structure: frac(-20000, 2811),
                             itm.rocket_fuel: frac(-20000, 2811),
                             itm.satellite: frac(-20, 2811)})

    def testCoalLiquefaction(self):
        self.rateTest(OilRefinery, rcp.coal_liquefaction,
                      rates={itm.heavy_oil: 13,
                             itm.light_oil: 4,
                             itm.petroleum_gas: 2,
                             itm.coal: -2,
                             itm.steam: -10})
        self.rateTest(OilRefinery, rcp.coal_liquefaction,
                      modules=3*itm.productivity_module_3,
                      rates={itm.heavy_oil: '9.295',
                             itm.light_oil: '2.86',
                             itm.petroleum_gas: '1.43',
                             itm.coal: '-1.1',
                             itm.steam: '-5.5'})

    def testKovarexEnrichmentProcess(self):
        self.rateTest(Centrifuge, rcp.kovarex_enrichment_process,
                      rates={itm.uranium_235: '1/60',
                             itm.uranium_238: '-0.05'})
        self.rateTest(Centrifuge, rcp.kovarex_enrichment_process,
                      modules=2*itm.productivity_module_3,
                      rates={itm.uranium_235: '0.014',
                             itm.uranium_238: '-0.035'})
        self.rateTest(Centrifuge, rcp.kovarex_enrichment_process,
                      modules=2*itm.productivity_module_3, beacons = 4*SPEED_BEACON,
                      rates={itm.uranium_235: '0.054',
                             itm.uranium_238: '-0.135'})
        self.rateTest(Centrifuge, rcp.kovarex_enrichment_process,
                      beacons = 4*SPEED_BEACON,
                      rates={itm.uranium_235: '1/20',
                             itm.uranium_238: '-0.15'})




