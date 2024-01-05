import factoriocalc
from factoriocalc import *
from factoriocalc.presets import *
from pathlib import Path
import unittest

_dir = Path(__file__).parent.resolve()

class KrastorioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origGameInfo = setGameConfig('Krastorio 2', _dir / 'kr-recipes.json')

    @classmethod
    def tearDownClass(cls):
        config.gameInfo.reset(cls.origGameInfo)

    @staticmethod
    def ironSteelFactory():
        return Group(
            mch.MatterAssembler(rcp.matter_to_coal, modules=4*itm.effectivity_module_3,
                                beacons=(3*mch.SingularityBeacon(2*itm.speed_module_3)
                                         +4*mch.SingularityBeacon(2*itm.effectivity_module_3)+1*mch.Beacon(2*itm.speed_module_3))),
            mch.AdvancedChemicalPlant(rcp.enriched_iron, modules=4*itm.productivity_module_3,
                                      beacons=12*mch.SingularityBeacon(2*itm.speed_module_3)+1*mch.Beacon(2*itm.speed_module_3)),
            mch.AdvancedChemicalPlant(rcp.enriched_iron, modules=4*itm.productivity_module_3,
                                      beacons=11*mch.SingularityBeacon(2*itm.speed_module_3)),
            mch.MatterPlant(rcp.stone_to_matter, modules=4*itm.effectivity_module_3,
                            beacons=(2*mch.SingularityBeacon(2*itm.speed_module_3)
                                     +2*mch.SingularityBeacon(1*itm.speed_module_3+1*itm.effectivity_module_3)
                                     +2*mch.SingularityBeacon(2*itm.effectivity_module_3))),
            26*mch.FiltrationPlant(rcp.dirty_water_filtration_1, modules=2*itm.effectivity_module_2),
            mch.MatterPlant(rcp.wood_to_matter, modules=4*itm.effectivity_module_3,
                            beacons=(4*mch.SingularityBeacon(2*itm.speed_module_3)
                                     +4*mch.SingularityBeacon(2*itm.effectivity_module_3)
                                     +4*mch.Beacon(2*itm.speed_module_3)+6*mch.Beacon(2*itm.effectivity_module_3))),
            mch.MatterPlant(rcp.wood_to_matter, modules=4*itm.effectivity_module_3,
                            beacons=(4*mch.SingularityBeacon(2*itm.speed_module_3)
                                     +6*mch.SingularityBeacon(2*itm.effectivity_module_3)
                                     +3*mch.Beacon(2*itm.effectivity_module_3)+4*mch.Beacon(2*itm.speed_module_3))),
            mch.MatterAssembler(rcp.matter_to_iron_ore, modules=4*itm.effectivity_module_3,
                                beacons=(3*mch.SingularityBeacon(1*itm.speed_module_3+1*itm.effectivity_module_3)
                                         +7*mch.SingularityBeacon(2*itm.speed_module_3)
                                         +9*mch.SingularityBeacon(2*itm.effectivity_module_3))),
            5*mch.MatterAssembler(rcp.matter_to_iron_ore, modules=4*itm.effectivity_module_3,
                                  beacons=(2*mch.SingularityBeacon(1*itm.speed_module_3+1*itm.effectivity_module_3)
                                           +8*mch.SingularityBeacon(2*itm.speed_module_3)
                                           +10*mch.SingularityBeacon(2*itm.effectivity_module_3))),
            12*mch.Greenhouse(rcp.grow_wood_with_water, modules=3*itm.speed_module_3,
                              beacons=10*mch.SingularityBeacon(2*itm.speed_module_3)+10*mch.Beacon(2*itm.speed_module_3)),
            mch.AdvancedFurnace(rcp.coke, modules=4*itm.productivity_module_3,
                                beacons=4*mch.SingularityBeacon(2*itm.speed_module_3)+10*mch.Beacon(2*itm.speed_module_3)),
            14*mch.AdvancedFurnace(rcp.enriched_iron_plate, modules=4*itm.productivity_module_3, beacons=10*mch.Beacon(2*itm.speed_module_3)),
            2*mch.AdvancedFurnace(rcp.enriched_iron_plate, modules=4*itm.productivity_module_3,
                                  beacons=4*mch.SingularityBeacon(2*itm.speed_module_3)+9*mch.Beacon(2*itm.speed_module_3)),
            mch.AdvancedFurnace(rcp.enriched_iron_plate, modules=4*itm.productivity_module_3, beacons=8*mch.Beacon(2*itm.speed_module_3)),
            2*mch.AdvancedFurnace(rcp.steel_plate, modules=4*itm.productivity_module_3,
                                  beacons=1*mch.SingularityBeacon(2*itm.speed_module_3)+5*mch.Beacon(2*itm.speed_module_3)),
            4*mch.AdvancedFurnace(rcp.steel_plate, modules=4*itm.productivity_module_3, beacons=10*mch.Beacon(2*itm.speed_module_3)),
            2*mch.AdvancedFurnace(rcp.steel_plate, modules=4*itm.productivity_module_3, beacons=5*mch.Beacon(2*itm.speed_module_3)),
            2*mch.AdvancedFurnace(rcp.enriched_iron_plate, modules=4*itm.productivity_module_3, beacons=9*mch.Beacon(2*itm.speed_module_3)),
            mch.AdvancedFurnace(rcp.enriched_iron_plate, modules=4*itm.productivity_module_3, beacons=6*mch.Beacon(2*itm.speed_module_3)),
            mch.MatterPlant(rcp.matter_cube_to_matter, modules=4*itm.effectivity_module_3,
                            beacons=(2*mch.SingularityBeacon(2*itm.speed_module_3)
                                     +2*mch.SingularityBeacon(2*itm.effectivity_module_3)
                                     +4*mch.SingularityBeacon(1*itm.speed_module_3+1*itm.effectivity_module_3))),
            mch.StabilizerChargingStation(rcp.charge_stabilizer, modules=2*itm.effectivity_module_2),
            mch.MatterAssembler(rcp.matter_to_matter_cube, modules=4*itm.effectivity_module_3,
                                beacons=(2*mch.SingularityBeacon(1*itm.speed_module_3+1*itm.effectivity_module_3)
                                         +3*mch.SingularityBeacon(2*itm.speed_module_3)
                                         +3*mch.SingularityBeacon(2*itm.effectivity_module_3)))
    )

    def testIronSteelFactory(self):
        # test blueprint conversion and simplify() method
        factory = importBlueprint(_dir / 'bp-iron-k.txt').convert(recipes={mch.StabilizerChargingStation: rcp.charge_stabilizer})[0].simplify()
        # make sure result of simplfy() is correct
        self.assertEqual(factory, self.ironSteelFactory())
        # test conversion to a box with priority given to steel output
        b = box(factory,outputs=[itm.steel_plate@'p1',itm.iron_plate],inputs=[itm.matter_cube,itm.sulfuric_acid], unconstrained = [itm.water])
        self.assertEqual(b.flow(itm.matter_cube).rate(), Frac(-1913281, 8960000))
        self.assertEqual(b.flow(itm.water).rate(), -600)
        self.assertEqual(b.flow(itm.iron_plate).rate(), 312)
        self.assertEqual(b.flow(itm.steel_plate).rate(), Frac(7287, 40))
    
    def testLithiumFactory1(self):
        factory = importBlueprint(file='tests/bp-lithium-k.txt').convert(recipes={mch.FluidBurner:rcp.burn_chlorine})[0]
        b = box(factory)
        self.assertEqual(b.flow(itm.lithium).rate(), Frac(4464, 125))
        self.assertEqual(b.flow(itm.chlorine_barrel).rate(), 0)

    def testLithiumFactory2(self):
        factory = importBlueprint(file='tests/bp-lithium-k.txt').convert(recipes={mch.FluidBurner:rcp.burn_chlorine})[0]
        b = box(factory, outputs=[itm.lithium,itm.chlorine_barrel@'p -1'],inputs=[itm.water, itm.mineral_water, itm.empty_barrel])
        self.assertEqual(b.flow(itm.lithium).rate(), Frac(4464, 125))
        self.assertEqual(b.flow(itm.chlorine_barrel).rate(), Frac(125736, 153125))
