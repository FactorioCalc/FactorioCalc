import pdb

from factoriocalc import *
import tests.common as tc

#config.machinePrefs.set(MP_LATE_GAME)

import re

def toPythonName(name):
    return name.replace('-','_')

def toClassName(name):
    return name.title().replace('-','')

def seCraftingHints(gi):
    craftingHints = standardCraftingHints(gi)

    for r in gi.rcpByName.values():
        if r.name.startswith('se-recycle-'):
            craftingHints[r.name] = CraftingHint(priority = IGNORE)

    return craftingHints

def seAliasPass(gi):
    for name,obj in gi.itmByName.items():
        alias = re.sub('se-', '', name)
        if name != alias and alias in gi.itmByName:
            alias = alias + '-se'
            assert(alias not in gi.itmByName)
        setattr(gi.itm, toPythonName(alias), obj)
        gi.aliases[name] = toPythonName(alias)

    for name,obj in gi.rcpByName.items():
        alias = re.sub('se-', '', name)
        if name != alias and alias in gi.rcpByName:
            alias = alias + '-se'
            assert(alias not in gi.rcpByName)
        setattr(gi.rcp, toPythonName(alias), obj)
        if name in gi.aliases:
            assert(gi.aliases[name] == toPythonName(alias))
        else:
            gi.aliases[name] = toPythonName(alias)

    for name,cls in gi.mchByName.items():
        alias = re.sub('se-', '', name)
        if name != alias and alias in mchByName:
            alias = alias + '-se'
            assert(alias not in mchByName)
        clsName = toClassName(alias)
        cls.__name__ = clsName
        cls.__qualname__ = clsName
        setattr(gi.mch, clsName, cls)

from pathlib import Path
importGameInfo(Path('/srv/gamer/Users/kevina/AppData/Roaming/Factorio/script-output/recipes.json'),
               includeDisabled = True,
               aliasPass = seAliasPass,
               craftingHints = seCraftingHints)

MP_SPACE_1 = MachinePrefs(mch.AssemblingMachine3(),
                          mch.SpaceManufactory(),
#                         mch.SpaceThermodynamicsLaboratory(),
                          mch.SpaceSupercomputer1(),
#                         mch.CastingMachine(),
                          mch.SpaceRadiator(),
#                         mch.SpaceMechanicalLaboratory(),
#                         mch.SpaceRadiationLaboratory(),
#                         mch.SpaceBiochemicalLaboratory(),
)

config.machinePrefs.set(MP_SPACE_1)

#r = produce([itm.se_energy_science_pack_1@'0.5'],
#            [rcp.se_simulation_s,rcp.se_holmium_ingot,rcp.])

#produce([itm.electric_circuit])


#grp = tc.bpBook().find('circuits3').convert()

gi = config.gameInfo.get()

#r = produce([itm.energy_science_pack_1@'0.5'],
#            [rcp.simulation_s,
#             rcp.holmium_ingot,
#             rcp.iron_ingot,
#             rcp.copper_plate,
#             rcp.electronic_circuit,
#             rcp.advanced_circuit,
#             rcp.processing_unit,
#             rcp.radiating_space_coolant_normal],
#            abortOnMultiChoice=False, solve=False)

spaceScience = [
    rcp.space_science_pack(),
    rcp.space_transport_belt(),
]

utilityScience = [
    rcp.utility_science_pack(),
    rcp.solar_panel(),
    rcp.effectivity_module(),
]

productionScience = [
    rcp.production_science_pack(),
    rcp.productivity_module(),
]

decontamination = [
    rcp.scrap_decontamination(),
    rcp.space_water_decontamination(),
    rcp.bio_sludge_decontamination(),
]

coolant = [
    rcp.radiating_space_coolant_normal(),
    rcp.space_coolant_cold(),
    rcp.space_coolant(),
]

datacards = [
    rcp.empty_data(),
    rcp.data_storage_substrate_cleaned(),
    rcp.data_storage_substrate(),
    rcp.formatting_1(),
    rcp.broken_data_scrapping(),
]

fluids = [
    rcp.chemical_gel(),
    rcp.ion_stream(modules=2*itm.speed_module_3 + 2*itm.effectivity_module_4),
    rcp.plasma_stream(modules=2*itm.speed_module_4 + 2*itm.effectivity_module_4),
    rcp.space_water(),
]

energyScience = [
    rcp.energy_science_pack_1(),
    rcp.simulation_s(),
    rcp.energy_catalogue_1(),
    rcp.energy_insight_1(),
    rcp.conductivity_data(),
    rcp.electromagnetic_field_data(),
    rcp.polarisation_data(),
    rcp.radiation_data(),
    rcp.space_mirror(),
]

materialScience = [
    rcp.material_science_pack_1(),
    rcp.simulation_m(),
    rcp.material_catalogue_1(),
    rcp.material_insight_1(),
    rcp.compressive_strength_data(),
    rcp.tensile_strength_data(),
    rcp.hot_thermodynamics_data(),
    rcp.cold_thermodynamics_data(),

    rcp.material_testing_pack()
]


b = unboundedBox(spaceScience
                 + utilityScience
                 + productionScience
                 + [rcp.machine_learning_data()]
                 + energyScience
                 + materialScience
                 + datacards
                 + coolant
                 + fluids
                 + decontamination
                 + [rcp.iron_ingot_to_plate()]
                 ,
                 outputTouchups=[
                     itm.space_science_pack@'4/6',
                     itm.utility_science_pack@'1/2',
                     itm.production_science_pack@'1/2',
                     itm.energy_science_pack_1@'1/6',
                     itm.material_science_pack_1@'1/6'
                 ],
                 priorities={rcp.simulation_s:1},
#                 inputTouchups=[itm.space_water],
                 minSolveRes=SolveRes.PARTIAL,
)

b_m = unboundedBox(energyScience
                 + materialScience
                 + datacards
                 + coolant
                 + fluids
                 + decontamination,
                 outputTouchups=[itm.energy_science_pack_1@'1/6', itm.material_science_pack_1@'1/6'],
                 priorities={rcp.simulation_m:1},
#                 inputTouchups=[itm.space_water],
#                 minSolveRes=SolveRes.OK,
)


class FlowComparer(dict):
    def __init__(self, a, b):
        for f in a:
            self[f.item] = [f.rate(), 0, None, None]
        for f in b:
            self.setdefault(f.item, [0, 0, None, None])[1] = f.rate()
        for item, (a, b, _, _) in self.items():
            self[item][2] = div(b, a) if a != 0 and b != 0 else 0
            self[item][3] = a - b if a != 0 and b != 0 else 0
    def print(self):
        for item, (a, b, ratio, diff) in self.items():
            print(f'{item.alias:30s} {a:8.3g} {b:8.3g} {ratio:8.3g} {diff:8.3g}')

def compare_flows(a, b):
    return FlowComparer(a,b)


#     outputTouchups=[itm.space_water,itm.scrap],
#     inputTouchups=[itm.contaminated_scrap,itm.contaminated_bio_sludge,itm.contaminated_space_water]
# )

# be = UnboundedBox(1*rcp.energy_science_pack_1()
#                   + 1*rcp.simulation_s()
#                   + 1*rcp.energy_catalogue_1()
#                   + 1*rcp.energy_insight_1()
#                   + 1*rcp.conductivity_data()
#                   + 1*rcp.electromagnetic_field_data()
#                   + 1*rcp.polarisation_data()
#                   + 1*rcp.radiation_data()
#                   + 1*rcp.radiating_space_coolant_normal()
#                   + 1*rcp.space_coolant_cold()
#                   + 1*rcp.space_coolant()
#                   + 1*rcp.space_mirror()
#                   + 1*rcp.empty_data()
#                   + 1*rcp.data_storage_substrate_cleaned()
#                   + 1*rcp.data_storage_substrate()
#                   + decontamination
#                   ,
#                   outputTouchups={itm.energy_science_pack_1:'1/6'},
#                   inputTouchups=[itm.space_water],
# #                unconstrained = {itm.empty_data}
# )

bm = unboundedBox(1*rcp.material_science_pack_1()
                  + 1*rcp.simulation_m()
                  + 1*rcp.material_catalogue_1()
                  + 1*rcp.material_insight_1()
                  + 1*rcp.compressive_strength_data()
                  + 1*rcp.tensile_strength_data()
                  + 1*rcp.hot_thermodynamics_data()
                  + 1*rcp.cold_thermodynamics_data()

                  + 1*rcp.material_testing_pack()

                  + 1*rcp.radiating_space_coolant_normal()
                  + 1*rcp.space_coolant_cold()
                  + 1*rcp.space_coolant()
                  + 1*rcp.empty_data()
                  + 1*rcp.data_storage_substrate_cleaned()
                  + 1*rcp.data_storage_substrate()
                  + 1*rcp.formatting_1()

                  ,
                  outputTouchups={itm.material_science_pack_1:'1/2'},
#                 unconstrained = {itm.empty_data}
)

bb = unboundedBox(1*rcp.biological_science_pack_1()
                  + 1*rcp.simulation_b()
                  + 1*rcp.biological_catalogue_1()
                  + 1*rcp.biological_insight_1()
                  + 1*rcp.bio_combustion_data()
                  + 1*rcp.biochemical_data()
                  + 1*rcp.biomechanical_data()
                  + 1*rcp.genetic_data()

                  + 1*rcp.bio_sludge()

                  + 1*rcp.specimen()
                  + 1*rcp.bioculture()
                  + 1*rcp.nutrient_gel()
                  + 1*rcp.nutrient_vat()
                  + 1*rcp.bio_sludge_decontamination()
                  + 1*rcp.space_water_decontamination()

                  + 1*rcp.radiating_space_coolant_normal()
                  + 1*rcp.space_coolant_cold()
                  + 1*rcp.space_coolant()
                  + 1*rcp.empty_data()
                  + 1*rcp.data_storage_substrate_cleaned()
                  + 1*rcp.data_storage_substrate()
                  + 1*rcp.formatting_1()
                  ,
                  outputTouchups={itm.biological_science_pack_1:'1/6'},
                  inputTouchups=[itm.space_water],
)


ba =  UnboundedBox([rcp.astronomic_science_pack_1(),
                    rcp.simulation_a(),
                    rcp.astronomic_catalogue_1(),
                    rcp.astronomic_insight_1(),
                    rcp.infrared_observation_data(),
                    rcp.astrometric_analysis_multispectral_1(),
                    rcp.visible_observation_data(),
                    rcp.uv_observation_data(),
                    rcp.observation_frame_uv(),
                    rcp.observation_frame_visible(),
                    rcp.observation_frame_infrared()
],
                   outputTouchups={itm.astronomic_science_pack_1:'1/6'},
                   unconstrained = {itm.empty_data},
)
