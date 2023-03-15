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

def _importGameInfo(gameInfo, includeDisabled = True):
    #with open(_dir / 'recipes-base.json') as f:
    #    d = json.load(f)
    rcpByName, itmByName, mchByName = {}, {}, {}
    translatedNames = {}
    categories = {}
    disabledRecipes = set()

    groups = gameInfo['groups']

    def getOrderKey(d):
        return (groups[d['group']]['order'],groups[d['subgroup']]['order'],d['order'])
    
    def addItem(item, descr = ''):
        name = item.name
        pythonName = toPythonName(name)
        itmByName[name] = item
        if descr:
            translatedNames[f'itm {item.name}'] = descr

    def lookupItem(name):
        try:
            return itmByName[name]
        except KeyError:
            pass
        pythonName = toPythonName(name)
        try:
            d = gameInfo['items'][name]
            item = Item(name, getOrderKey(d), d['stack_size'], fuelValue=d['fuel_value'], fuelCategory=d.get('fuel_category',''))
        except KeyError:
            d = gameInfo['fluids'][name]
            item = Fluid(name, getOrderKey(d))
        descr = d.get('translated_name', '')
        addItem(item, descr)
        return item

    def addRecipe(recipe, descr = ''):
        name = recipe.name
        pythonName = toPythonName(name)
        rcpByName[name] = recipe
        if descr:
            translatedNames[f'rcp {recipe.name}'] = descr

    addItem(Electricity('electricity', ('z','z','zzz')))

    # import machines
    for k,v in gameInfo['entities'].items():
        if 'hidden' in v.get('flags',[]): continue
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
                mchByName[cls.name] = cls
            continue
        dict = {'name': v['name'],
                'type': v['type'],
                'order': getOrderKey(v),
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
        mchByName[cls.name] = cls
        descr = v.get('translated_name','')
        if descr:
            translatedNames[f'mch {cls.name}'] = descr

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
        item = Module(k, getOrderKey(v), v['stack_size'], e, limitation)
        addItem(item, v.get('translated_name',''))

    # import recipes
    for (k,v) in gameInfo['recipes'].items():
        if not includeDisabled and not v.get('enabled', False):
            continue
        def toRecipeComponent(d):
            try:
                num = d['amount']*d.get('probability',1)
            except KeyError:
                num = d.get('probability',1) * (d['amount_max'] + d['amount_min']) / 2
            if type(num) is float:
                num = frac(num, float_conv_method = 'round')
            return RecipeComponent(item=lookupItem(d['name']), num = num)
        def toRecipe(d):
            inputs = tuple(toRecipeComponent(rc) for rc in d['ingredients'])
            outputs = tuple(toRecipeComponent(rc) for rc in d['products'])
            mainOutput = None
            if 'main_product' in d:
                mainOutput = lookupItem(d['main_product']['name'])
            if mainOutput is None:
                o = [o for o in outputs if o.item.name != 'empty-barrel']
                if len(o) == 1:
                    mainOutput = o[0].item
            time = frac(d.get('energy', 0.5), float_conv_method = 'round')
            order = getOrderKey(v)
            return Recipe(v['name'],categories.get(v['category'], None),inputs,outputs,time,order,mainOutput)
        recipe = toRecipe(v)
        addRecipe(recipe, v.get('translated_name', ''))
        if not v.get('enabled', False):
            disabledRecipes.add(v['name'])

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
        RocketSilo = mchByName['rocket-silo']
        recipe = RocketSilo.Recipe(
            name = name,
            category = RocketSilo.craftingCategory,
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
        category = Category('Boiler', [mchByName['boiler']]),
        inputs = (RecipeComponent(60, lookupItem('water')),),
        outputs = (RecipeComponent(60, lookupItem('steam')),),
        time = 1,
        order = ('','',''))
    addRecipe(steam)

    res = data.GameInfo(
        rcpByName = rcpByName,
        itmByName = itmByName,
        mchByName = mchByName,
        translatedNames = translatedNames,
        disabledRecipes = disabledRecipes,
    )

    return res

def _addResearchHacks(gi):
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
        order = ('z', 'z', order)
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

def standardCraftingHints(gi):
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

    return craftingHints

def standardAliasPass(gi):
    for name,obj in gi.itmByName.items():
        setattr(gi.itm, toPythonName(name), obj)
        gi.aliases[name] = toPythonName(name)
    
    for name,obj in gi.rcpByName.items():
        setattr(gi.rcp, toPythonName(name), obj)
        gi.aliases[name] = toPythonName(name)

    for name,obj in gi.mchByName.items():
        setattr(gi.mch, toClassName(name), obj)
        gi.aliases[name] = toClassName(name)

def importGameInfo(gameInfo, includeDisabled = True, researchHacks = False, aliasPass = standardAliasPass, craftingHints = None):
    from . import config
    
    if isinstance(gameInfo, Path):
        with open(gameInfo) as f:
            d = json.load(f)
    else:
        d = gameInfo

    res = _importGameInfo(d, includeDisabled)

    aliasPass(res)

    token = config.gameInfo.set(res)

    if researchHacks:
        _addResearchHacks(res)

    res.finalize()
    
    if craftingHints:
        res.craftingHints = craftingHints(res)
    else:
        res.craftingHints = {}

    return token

def defaultImport(expensiveMode = False):
    if expensiveMode:
        path = _dir / 'game-info-expensive.json'
    else:
        path = _dir / 'game-info-normal.json'
    
    return importGameInfo(path,
                          researchHacks = True,
                          craftingHints = standardCraftingHints)

__all__ = ('standardCraftingHints', 'importGameInfo', 'defaultImport')
