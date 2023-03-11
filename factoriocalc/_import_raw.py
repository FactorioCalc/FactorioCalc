from __future__ import annotations
import json
from pathlib import Path
from . import itm,rcp,mch,data,machines
from .fracs import frac, frac_from_float_round
from .core import *
from .data import *
from .data import CraftingHint, craftingHints
from .machines import *
from ._helper import toPythonName,toClassName

_dir = Path(__file__).parent.resolve()

def doit():
    with open(_dir / 'recipes-base.json') as f:
        d = json.load(f)
    addItem(Electricity, 'electricity', 'zzz')
    items = d['items']

    # import machines
    for k,v in d['entities'].items():
        clsName = toClassName(v['name'])
        bases = []
        module_inventory_size = v.get('module_inventory_size', 0)
        if module_inventory_size > 0:
            bases.append(machines._ModulesMixin)
        energy_source = v.get('energy_source', None)
        if energy_source == 'burner':
            bases.append(machines._BurnerMixin)
        elif energy_source == 'electric':
            bases.append(machines._ElectricMixin)
        isCraftingMachine = False
        if v['type'] == 'assembling-machine':
            isCraftingMachine = True
            bases.append(machines.AssemblingMachine)
        elif v['type'] == 'furnace':
            isCraftingMachine = True
            bases.append(machines.Furnace)
        else:
            cls = getattr(machines, clsName, None)
            if cls is not None:
                setattr(mch, clsName, cls)
                data.entityToMachine[cls.name] = cls
            continue
            #bases.append(Machine)
        dict = {'name': v['name'],
                'type': v['type'],
                'order': v['order'],
                'group': v['group'],
                'subgroup': v['group'],
                'width': frac(v['width']),
                'height': frac(v['height'])}
        cls = type(clsName, tuple(bases), dict)
        cls.__module__ = mch
        if energy_source is not None:
            cls.baseEnergyUsage = frac(v['energy_consumption'], float_conv_method = 'round')
            cls.energyDrain = frac(v['drain'], float_conv_method = 'round')
            cls.pollution = frac(v['pollution'], float_conv_method = 'round')
        if isCraftingMachine:
            cls.craftingSpeed = frac(v['crafting_speed'], float_conv_method = 'round')
            cls.craftingCategories = v['crafting_categories']
            for c in cls.craftingCategories:
                data.categoryToMachines.setdefault(c, [])
                data.categoryToMachines[c].append(cls)
        if module_inventory_size > 0:
            cls.allowdEffects = v['allowed_effects']
        setattr(mch, clsName, cls)
        data.entityToMachine[cls.name] = cls
    
    # import modules
    for k,v in items.items():
        if v['type'] != 'module': continue
        pythonName = toPythonName(k)
        def get(what):
            return frac_from_float_round(v['module_effects'].get(what, {'bonus': 0})['bonus'], precision = 6)
        e = Effect(speed = get('speed'),
                   productivity = get('productivity'),
                   consumption = get('consumption'),
                   pollution = get('pollution'))
        limitation = v.get('limitation', None)
        if limitation is not None:
            limitation = set(limitation)
            if 'rocket-part' in limitation:
                limitation.add('space-science-pack')
        item = Module(k, v['order'], v['stack_size'], e, limitation)
        setattr(itm, pythonName, item)
        itm.byName[k]=item

    # import recipes
    rcp.byName = {}
    for (k,v) in d['recipes'].items():
        category = v.get('category','crafting')
        def toRecipeComponent(d):
            num = d['amount']*d.get('probability',1)
            if type(num) is float:
                num = frac(num, float_conv_method = 'round')
            return RecipeComponent(item=lookupItem(items, d['name']), num = num)
        def toRecipe(d):
            inputs = tuple(toRecipeComponent(rc) for rc in d['ingredients'])
            outputs = tuple(toRecipeComponent(rc) for rc in d['products'])
            time = frac(d.get('energy', 0.5), float_conv_method = 'round')
            order = v.get('order',None)
            if order is None and len(outputs) == 1:
                order = outputs[0].item.order
            if order is None and 'main_product' in d:
                order = itm.byName[d['main_product']].order
            assert(order is not None)
            return Recipe(v['name'],v['category'],inputs,outputs,time,order)
        try:
            normal_recipe = toRecipe(v['normal'])
        except KeyError:
            recipe = toRecipe(v)
            normal_recipe = recipe
        addRecipe(normal_recipe)

    rp = rcp.byName['rocket-part']
    rocket_parts_inputs = tuple(RecipeComponent(rc.num*100, rc.item) for rc in rp.inputs)
    rocket_parts_time = rp.time*100

    space_science_pack = RocketSilo.Recipe(
        name = 'space-science-pack',
        category = '_rocketSilo',
        order = lookupItem(items, 'space-science-pack').order,
        inputs = rocket_parts_inputs,
        outputs = (RecipeComponent(num=1000,
                                   item=lookupItem(items, 'space-science-pack')),),
        time = rocket_parts_time,
        cargo = RecipeComponent(num=1,
                                item=itm.satellite))
    addRecipe(space_science_pack)
    data.categoryToMachines['_rocket-silo'] = mch.RocketSilo

    steam = Recipe(
        name = 'steam',
        category = '_steam',
        inputs = (RecipeComponent(60, lookupItem(items, 'water')),),
        outputs = (RecipeComponent(60, lookupItem(items, 'steam')),),
        time = 1,
        order = '')
    addRecipe(steam)
    data.categoryToMachines['_steam'] = [mch.Boiler]

    researchHacks()

    for r in rcp.byName.values():
        for _, item in r.outputs:
            recipesThatMake.setdefault(item, []).append(r.name)
        for _, item in r.inputs:
            recipesThatUse.setdefault(item, []).append(r.name)
        if any(item == itm.empty_barrel for _, item in r.outputs) and len(r.outputs) > 1:
            craftingHints[r.name] = CraftingHint(priority = IGNORE)

    craftingHints['advanced-oil-processing'] = CraftingHint(also=['light-oil-cracking','heavy-oil-cracking'])
    craftingHints['coal-liquefaction']       = CraftingHint(also=['light-oil-cracking','heavy-oil-cracking'])

    craftingHints['light-oil-cracking'] = CraftingHint(priority=-1)
    craftingHints['heavy-oil-cracking'] = CraftingHint(priority=-1)

    craftingHints['solid-fuel-from-light-oil']     = CraftingHint(priority =0, also=['solid-fuel-from-petroleum-gas'])
    craftingHints['solid-fuel-from-petroleum-gas'] = CraftingHint(priority=-1)
    craftingHints['solid-fuel-from-heavy-oil']     = CraftingHint(priority=-2)

    craftingHints['nuclear-fuel-reprocessing']     = CraftingHint(boxPriority = 90)

    craftingHints['kovarex-enrichment-process']    = CraftingHint(priority = IGNORE)
    
    craftingHints['rocket-part'] = CraftingHint(priority = IGNORE)

    # data.entityToMachine = {
    #     cls.name: cls for cls in (CraftingMachine, Boiler,
    #                               AssemblingMachine1, AssemblingMachine2, AssemblingMachine3,
    #                               ChemicalPlant, OilRefinery, Centrifuge,
    #                               StoneFurnance, SteelFurnance, ElectricFurnace,
    #                               RocketSilo,
    #                               Beacon)
    # }


def researchHacks():
    from .helper import sciencePacks
    addResearch('_production_research', 'zz0', sciencePacks - {itm.military_science_pack})
    addResearch('_military_research', 'zz1', sciencePacks - {itm.production_science_pack})
    addResearch('_combined_research', 'zz2', sciencePacks)

def addResearch(name, order, inputs):
    from . import helper
    item = addItem(Research, name, order)
    recipe = Recipe(name = name,
                    category = '_fakelab',
                    inputs = (RecipeComponent(1, i) for i in sorted(inputs, key = lambda k: k.order)),
                    outputs = (RecipeComponent(1, item),),
                    time = 1,
                    order = order)
    categoryToMachines['_fakelab'] = [helper.FakeLab]
    addRecipe(recipe)

def addItem(cls, name, order):
    item = cls(name, order)
    setattr(itm, name, item)
    itm.byName[name]=item
    return item

def lookupItem(items, name):
    try:
        return itm.byName[name]
    except KeyError:
        pass
    pythonName = toPythonName(name)
    try:
        d = items[name]
        item = Item(name, d['order'], d['stack_size'], fuelValue=d['fuel_value'], fuelCategory=d.get('fuel_category',''))
    except KeyError:
        item = Ingredient(name,'z-'+name)
    setattr(itm, pythonName, item)
    itm.byName[name] = item
    return item

def addRecipe(recipe):
    name = recipe.name
    pythonName = toPythonName(name)
    setattr(rcp, pythonName, recipe)
    rcp.byName[name] = recipe

