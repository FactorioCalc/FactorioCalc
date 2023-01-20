from __future__ import annotations
import draftsman.data.items as d_items
import draftsman.data.modules as d_modules
import draftsman.data.recipes as d_recipes
from . import itm,rcp,rcpinst,data,machines as mch
from .fracs import frac
from .core import *
from .data import *
from .data import CraftingHint, craftingHints
from .machines import *
from ._helper import toPythonName

def doit():
    addItem(Electricity, 'electricity', 'zzz')

    for (k,v) in d_modules.raw.items():
        pythonName = toPythonName(k)
        def get(what):
            return frac(v['effect'].get(what, {'bonus': 0})['bonus'], float_conv_method = 'round')
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
    rcpinst.byName[None] = {}
    rcpinst.byName[Mode.NORMAL] = {}
    rcpinst.byName[Mode.EXPENSIVE] = {}
    for (k,v) in d_recipes.raw.items():
        category = v.get('category','crafting')
        madeIn = categoryToMachine[category]
        def toRecipeComponent(d):
            if type(d) is dict:
                num = d['amount']*d.get('probability',1)
                if type(num) is float:
                    num = frac(num, float_conv_method = 'round')
                return RecipeComponent(item=lookupItem(d['name']), num = num)
            else:
                return RecipeComponent(item=lookupItem(d[0]),num=d[1])
        def toRecipe(d):
            inputs = tuple(toRecipeComponent(rc) for rc in d['ingredients'])
            try:
                results = d['results']
            except KeyError:
                results = [(d['result'], d.get('result_count', 1))]
            outputs = tuple(toRecipeComponent(rc) for rc in results)
            time = frac(d.get('energy_required', 0.5), float_conv_method = 'round')
            order = v.get('order',None)
            if order is None and len(outputs) == 1:
                order = outputs[0].item.order
            if order is None and 'main_product' in d:
                order = itm.byName[d['main_product']].order
            assert(order is not None)
            return Recipe(v['name'],madeIn,inputs,outputs,time,order)
        try:
            normal_recipe = toRecipe(v['normal'])
            expensive_recipe = toRecipe(v['expensive'])
        except KeyError:
            recipe = toRecipe(v)
            normal_recipe = recipe
            expensive_recipe = recipe
        addRecipe(normal_recipe, expensive_recipe)

    rp = rcpinst.byName[None]['rocket-part']
    rocket_parts_inputs = tuple(RecipeComponent(rc.num*100, rc.item) for rc in rp.inputs)
    rocket_parts_time = rp.time*100

    space_science_pack = RocketSilo.Recipe(
        name = 'space-science-pack',
        madeIn = RocketSilo,
        order = lookupItem('space-science-pack').order,
        inputs = rocket_parts_inputs,
        outputs = (RecipeComponent(num=1000,
                                   item=lookupItem('space-science-pack')),),
        time = rocket_parts_time,
        cargo = RecipeComponent(num=1,
                                item=itm.satellite))
    addRecipe(space_science_pack,space_science_pack)

    steam = Recipe(
        name = 'steam',
        madeIn = Boiler,
        inputs = (RecipeComponent(60, lookupItem('water')),),
        outputs = (RecipeComponent(60, lookupItem('steam')),),
        time = 1,
        order = '')
    addRecipe(steam,steam)

    researchHacks()

    for r in rcpinst.byName[Mode.NORMAL].values():
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

    data.entityToMachine = {
        cls.name: cls for cls in (CraftingMachine, Boiler,
                                  AssemblingMachine1, AssemblingMachine2, AssemblingMachine3,
                                  ChemicalPlant, OilRefinery, Centrifuge,
                                  StoneFurnance, SteelFurnance, ElectricFurnace,
                                  RocketSilo,
                                  Beacon)
    }


def researchHacks():
    from .helper import sciencePacks
    addResearch('_production_research', 'zz0', sciencePacks - {itm.military_science_pack})
    addResearch('_military_research', 'zz1', sciencePacks - {itm.production_science_pack})
    addResearch('_combined_research', 'zz2', sciencePacks)

def addResearch(name, order, inputs):
    from .helper import FakeLab
    item = addItem(Research, name, order)
    recipe = Recipe(name = name,
                    madeIn = FakeLab,
                    inputs = (RecipeComponent(1, i) for i in sorted(inputs, key = lambda k: k.order)),
                    outputs = (RecipeComponent(1, item),),
                    time = 1,
                    order = order)
    addRecipe(recipe, recipe)

def addItem(cls, name, order):
    item = cls(name, order)
    setattr(itm, name, item)
    itm.byName[name]=item
    return item

def translateEnergyString(s):
    if s is None:
        return None
    elif s == '':
        return 0
    elif s.endswith('kJ'):
        return int(float(s[0:-2])*1_000)
    elif s.endswith('MJ'):
        return int(float(s[0:-2])*1_000_000)
    elif s.endswith('GJ'):
        return int(float(s[0:-2])*1_000_000_000)
    else:
        raise ValueError

def lookupItem(name):
    try:
        return itm.byName[name]
    except KeyError:
        pass
    pythonName = toPythonName(name)
    try:
        d = d_items.raw[name]
        item = Item(name,d['order'],d['stack_size'],fuelValue = translateEnergyString(d.get('fuel_value','')),fuelCategory = d.get('fuel_category',''))
    except KeyError:
        item = Ingredient(name,'z-'+name)
    setattr(itm, pythonName, item)
    itm.byName[name] = item
    return item

def addRecipe(recipe, expensive_recipe):
    name = recipe.name
    pythonName = toPythonName(name)
    rcp_ = object.__new__(Rcp)
    object.__setattr__(rcp_, 'name', name)
    setattr(rcp, pythonName, rcp_)
    rcp.byName[name] = rcp_
    if recipe is expensive_recipe:
        rcpinst.byName[None][name] = recipe
    setattr(rcpinst, pythonName, recipe)
    setattr(rcpinst.expensive, pythonName, expensive_recipe)
    rcpinst.byName[Mode.NORMAL][name] = recipe
    rcpinst.byName[Mode.EXPENSIVE][name] = expensive_recipe

categoryToMachine = {
    'crafting': mch.AssemblingMachine,
    "advanced-crafting": mch.AssemblingMachine,
    'crafting-with-fluid': mch.FluidCapableAssemblingMachine,
    'centrifuging': mch.Centrifuge,
    'chemistry': mch.ChemicalPlant,
    'oil-processing': mch.OilRefinery,
    'rocket-building': None, # a special case
    'smelting': mch.Furnace,
}
