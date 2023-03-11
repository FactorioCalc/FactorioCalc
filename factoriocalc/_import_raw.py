from __future__ import annotations
import json
from pathlib import Path
from . import itm,rcp,mch,data,machine
from .machine import Category
from .fracs import frac, frac_from_float_round
from .core import *
from .data import CraftingHint
from ._helper import toPythonName,toClassName

_dir = Path(__file__).parent.resolve()

def importGameInfo(gameInfo, includeHidden = True):
    #with open(_dir / 'recipes-base.json') as f:
    #    d = json.load(f)
    rcp, itm, mch = data.Objs(), data.Objs(), data.Objs()
    rcpByName, itmByName, mchByName = {}, {}, {}
    categories = {}
    
    def addItem(cls, name, order):
        item = cls(name, order)
        setattr(itm, name, item)
        itmByName[name]=item
        return item

    def lookupItem(name):
        try:
            return itmByName[name]
        except KeyError:
            pass
        pythonName = toPythonName(name)
        try:
            d = gameInfo['items'][name]
            item = Item(name, d['order'], d['stack_size'], fuelValue=d['fuel_value'], fuelCategory=d.get('fuel_category',''))
        except KeyError:
            item = Ingredient(name,'z-'+name)
        setattr(itm, pythonName, item)
        itmByName[name] = item
        return item

    def addRecipe(recipe):
        name = recipe.name
        pythonName = toPythonName(name)
        setattr(rcp, pythonName, recipe)
        rcpByName[name] = recipe

    addItem(Electricity, 'electricity', 'zzz')

    # import mchByName
    for k,v in gameInfo['entities'].items():
        clsName = toClassName(v['name'])
        bases = []
        module_inventory_size = v.get('module_inventory_size', 0)
        if module_inventory_size > 0:
            bases.append(machine._ModulesMixin)
        energy_source = v.get('energy_source', None)
        if energy_source == 'burner':
            bases.append(machine._BurnerMixin)
        elif energy_source == 'electric':
            bases.append(machine._ElectricMixin)
        isCraftingMachine = False
        if v['type'] == 'assembling-machine':
            isCraftingMachine = True
            bases.append(machine.AssemblingMachine)
        elif v['type'] == 'furnace':
            isCraftingMachine = True
            bases.append(machine.Furnace)
        else:
            existing = getattr(machine, clsName, None)
            if existing is not None:
                cls = existing
                #cls = type(clsName, (existing,), {})
                #cls.__module__ = mch
                setattr(mch, clsName, cls)
                mchByName[cls.name] = cls
            continue
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
            for c in v['crafting_categories']:
                if c in categories:
                    categories[c].members.append(cls)
                else:
                    categories[c] = Category(c, [cls])
            cls.craftingCategories = {categories[c] for c in v['crafting_categories']}
        if module_inventory_size > 0:
            cls.allowdEffects = v['allowed_effects']
        setattr(mch, clsName, cls)
        mchByName[cls.name] = cls

    # import modules
    for k,v in gameInfo['items'].items():
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
        itmByName[k]=item

    # import recipes
    for (k,v) in gameInfo['recipes'].items():
        def toRecipeComponent(d):
            num = d['amount']*d.get('probability',1)
            if type(num) is float:
                num = frac(num, float_conv_method = 'round')
            return RecipeComponent(item=lookupItem(d['name']), num = num)
        def toRecipe(d):
            inputs = tuple(toRecipeComponent(rc) for rc in d['ingredients'])
            outputs = tuple(toRecipeComponent(rc) for rc in d['products'])
            time = frac(d.get('energy', 0.5), float_conv_method = 'round')
            order = v.get('order',None)
            if order is None and len(outputs) == 1:
                order = outputs[0].item.order
            if order is None and 'main_product' in d:
                order = itmByName[d['main_product']].order
            assert(order is not None)
            return Recipe(v['name'],categories.get(v['category'], None),inputs,outputs,time,order)
        try:
            normal_recipe = toRecipe(v['normal'])
        except KeyError:
            recipe = toRecipe(v)
            normal_recipe = recipe
        addRecipe(normal_recipe)

    rp = rcpByName['rocket-part']
    rocket_parts_inputs = tuple(RecipeComponent(rc.num*100, rc.item) for rc in rp.inputs)
    rocket_parts_time = rp.time*100

    # create recipes for rocket launch products
    for k,v in gameInfo['items'].items():
        rocket_launch_products = v.get('rocket_launch_products', None)
        if not rocket_launch_products: continue
        assert len(rocket_launch_products) == 1
        rocket_launch_product = rocket_launch_products[0]
        item = lookupItem(rocket_launch_product['name'])
        if item.name not in gameInfo['recipes']:
            name = f'{item.name}'
        else:
            name = f'{item.name}-'
        recipe = mch.RocketSilo.Recipe(
            name = name,
            category = mch.RocketSilo.craftingCategory,
            order = item.order,
            inputs = rocket_parts_inputs,
            outputs = (RecipeComponent(num = rocket_launch_product['amount'] * rocket_launch_product.get('probability',1),
                                       item = item),),
            time = rocket_parts_time,
            cargo = RecipeComponent(num=1, item=lookupItem(k)),
        )
        addRecipe(recipe)

    steam = Recipe(
        name = 'steam',
        category = Category('Boiler', [mch.Boiler]),
        inputs = (RecipeComponent(60, lookupItem('water')),),
        outputs = (RecipeComponent(60, lookupItem('steam')),),
        time = 1,
        order = '')
    addRecipe(steam)

    res = data.GameInfo(
        rcp = rcp,
        rcpByName = rcpByName,
        itm = itm,
        itmByName = itmByName,
        mch = mch,
        mchByName = mchByName,
    )

    return res

def _add_research_hacks(gi):
    def addItem(cls, name, order):
        item = cls(name, order)
        setattr(gi.itm, name, item)
        gi.itmByName[name]=item
        return item

    def addRecipe(recipe):
        name = recipe.name
        pythonName = toPythonName(name)
        setattr(gi.rcp, pythonName, recipe)
        gi.rcpByName[name] = recipe

    from .helper import FakeLab, sciencePacks
    
    def addResearch(name, order, inputs):
        from . import helper
        item = addItem(Research, name, order)
        recipe = Recipe(name = name,
                        category = Category('FakeLab', [FakeLab]),
                        inputs = (RecipeComponent(1, i) for i in sorted(inputs, key = lambda k: k.order)),
                        outputs = (RecipeComponent(1, item),),
                        time = 1,
                        order = order)
        addRecipe(recipe)

    addResearch('_production_research', 'zz0', sciencePacks - {itm.military_science_pack})
    addResearch('_military_research', 'zz1', sciencePacks - {itm.production_science_pack})
    addResearch('_combined_research', 'zz2', sciencePacks)


def _add_crafting_hints(gi):
    craftingHints = {}
    
    for r in gi.rcpByName.values():       
        if any(item == gi.itm.empty_barrel for _, item in r.outputs) and len(r.outputs) > 1:
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

    gi.craftingHints = craftingHints


def doit():
    with open(_dir / 'recipes-base.json') as f:
        d = json.load(f)

    res = importGameInfo(d)
    
    from . import config

    config.gameInfo.set(res)
    config.defaultFuel.set(res.itm.coal)

    _add_research_hacks(res)
    
    _add_crafting_hints(res)

    res.finalize()

    
