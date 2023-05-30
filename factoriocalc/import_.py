from __future__ import annotations
import json
from pathlib import Path
from . import itm,rcp,mch,data,machine
from .machine import Category
from .fracs import frac, frac_from_float_round
from .core import *
from .data import CraftingHint
from ._helper import toPythonName,toClassName
from collections import defaultdict

_dir = Path(__file__).parent.resolve()

def _importGameInfo(gameInfo, includeDisabled, commonByproducts_, rocketRecipeHints, logger):
    rcpByName, itmByName, mchByName = {}, {}, {}
    rocketSilos = []
    fixedRecipes = []
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

    # process commonByproducts_ param
    commonByproducts = set()
    byproductPriority = defaultdict(set)
    for d in commonByproducts_:
        if isinstance(d, str):
            commonByproducts.add(d)
        else:
            prev = None
            for n_ in d:
                if isinstance(n_, str):
                    n_ = [n_]
                for n in n_:
                    if prev:
                        byproductPriority[prev].add(n)
                    if n != '*fluid*':
                        commonByproducts.add(n)
                prev = n
    fluids = {n for n in commonByproducts if n in gameInfo['fluids']}
    for a,bs in byproductPriority.items():
        if '*fluid*' in bs:
            bs.remove('*fluid*')
            bs.update(fluids)
    # take that transitive closure that is if a > b and b > c then a > c
    again = True
    while again:
        again = False
        for a,bs in byproductPriority.items():
            for b in list(bs):
                if b in byproductPriority:
                    new = byproductPriority[b] - bs
                    if not new: continue
                    bs |= new
                    again = True

    # import machines
    for k,v in gameInfo['entities'].items():
        if 'hidden' in v.get('flags',[]): continue
        clsName = toClassName(v['name'])
        bases = []
        module_inventory_size = v.get('module_inventory_size', 0)
        if module_inventory_size > 0 and v['type'] != 'beacon':
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
        elif v['type'] == 'rocket-silo':
            isCraftingMachine = True
            bases.append(machine.RocketSilo)
        elif v['type'] == 'beacon':
            bases.append(machine.Beacon)
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
            cls.moduleInventorySize = module_inventory_size
            cls.allowdEffects = v['allowed_effects']
        if 'fixed_recipe' in v:
            fixedRecipes.append((cls, v['fixed_recipe']))
        if v['type'] == 'beacon':
            cls.distributionEffectivity = frac(v['distribution_effectivity'], float_conv_method = 'round')
            cls.supplyAreaDistance = frac(v['supply_area_distance'], float_conv_method = 'round')
            cls.__hash__ = machine.Beacon.__hash__
        if v['type'] == 'rocket-silo':
            cls.rocketPartsRequired = v['rocket_parts_required']
            rocketSilos.append(cls)
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
        limitation = v.get('limitations', None)
        if not limitation:
            limitation = None
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
        def toRecipeComponent(d, isProduct):
            try:
                num = d['amount']*d.get('probability',1)
            except KeyError:
                num = d.get('probability',1) * (d['amount_max'] + d['amount_min']) / 2
            if type(num) is float:
                num = frac(num, float_conv_method = 'round')
            if isProduct:
                catalyst = d.get('catalyst_amount', 0)
            else:
                catalyst = 0
            return RecipeComponent(item=lookupItem(d['name']), num = num, catalyst = catalyst)
        def toRecipe(d):
            inputs = tuple(toRecipeComponent(rc, False) for rc in d['ingredients'])
            products = []
            byproducts = []
            for product in d['products']:
                rc = toRecipeComponent(product, True)
                try:
                    amount = product['amount']
                except KeyError:
                    amount = product['amount_max']
                catalyst = rc.catalyst
                if catalyst == 0:
                    for rc0 in inputs:
                        if rc0.item == rc.item:
                            catalyst = rc0.num
                if amount - catalyst > 0:
                    products.append(rc)
                else:
                    byproducts.append(rc)
            if not products:
                products = byproducts
                byproducts = []
            if len(products) > 1:
                products_, byproducts_ = [], []
                if 'main_product' in d:
                    for o in products:
                        if o.item.name == d['main_product']['name']:
                            products_.append(o)
                        else:
                            byproducts_.append(o)
                    assert(len(products_) == 1)
                else:
                    for o in products:
                        if o.item.name in commonByproducts:
                            byproducts_.append(o)
                        else:
                            products_.append(o)
                    if len(products_) == 0:
                        byproductNames = {rc.item.name for rc in byproducts_}
                        newProducts = set()
                        for o in byproducts_:
                            name = o.item.name
                            if byproductPriority[name] & byproductNames:
                                newProducts |= byproductPriority[name] & byproductNames
                        if len(newProducts) == 0:
                            logger(f"{d['name']}: unable to determine main produce from byproducts {byproductNames}")
                        else:
                            products_ = tuple(rc for rc in byproducts_ if rc.item.name in newProducts)
                            byproducts_ = tuple(rc for rc in byproducts_ if rc.item.name not in newProducts)
                if len(products_) > 0:
                    products = products_
                    byproducts += byproducts_
            time = frac(d.get('energy', 0.5), float_conv_method = 'round')
            order = getOrderKey(v)
            return Recipe(v['name'],categories.get(v['category'], None),inputs,products,byproducts,time,order)
        recipe = toRecipe(v)
        addRecipe(recipe, v.get('translated_name', ''))
        if not v.get('enabled', False):
            disabledRecipes.add(v['name'])

    for cls, recipeName in fixedRecipes:
        cls.fixedRecipe = rcpByName[recipeName]

    # create recipes for rocket launch products
    for k,v in gameInfo['items'].items():
        rocket_launch_products = v.get('rocket_launch_products', None)
        if not rocket_launch_products: continue
        assert len(rocket_launch_products) == 1
        rocket_launch_product = rocket_launch_products[0]
        item = lookupItem(rocket_launch_product['name'])

        for rocketSilo in rocketSilos:
            if rocketRecipeHints.get(rocketSilo.name, '') == 'skip':
                continue
            key = f'{rocketSilo.name}::{item.name}'
            try:
                useHint = rocketRecipeHints[key]
            except KeyError:
                logger(f"no entry for '{key}' in rocketRecipeHints using anyway")
                useHint = ''
            if useHint == 'skip':
                continue
            recipe = getattr(rocketSilo, 'fixedRecipe', rcpByName['rocket-part'])
            # ^^FIXME: getattr default value a hack until JSON files are updated
            num = rocketSilo.rocketPartsRequired
            rocket_parts_inputs = tuple(RecipeComponent(rc.num*num, 0, rc.item) for rc in recipe.inputs)
            rocket_parts_time = recipe.time*num
            if useHint == '':
                name = f'{item.name}--{rocketSilo.name}'
            elif useHint == 'default':
                name = item.name
            else:
                raise ValueError(f"expected one of 'skip', 'default' ot '' for rocketRecipeHints['{name}'] but got '{useHint}'")
            recipe = rocketSilo.Recipe(
                name = name,
                category = categories['rocket-building'],
                origRecipe = recipe,
                order = item.order,
                inputs = rocket_parts_inputs,
                products = (RecipeComponent(num = rocket_launch_product['amount'] * rocket_launch_product.get('probability',1),
                                            catalyst = 0,
                                            item = item),),
                byproducts = (),
                time = rocket_parts_time,
                cargo = RecipeComponent(num=1, catalyst=0, item=lookupItem(k)),
            )
            addRecipe(recipe)

    steam = Recipe(
        name = 'steam',
        category = Category('Boiler', [mchByName['boiler']]),
        inputs = (RecipeComponent(60, 0, lookupItem('water')),),
        products = (RecipeComponent(60, 0, lookupItem('steam')),),
        byproducts = (),
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
                        inputs = (RecipeComponent(1, 0, i) for i in sorted(inputs, key = lambda k: k.order)),
                        products = (RecipeComponent(1, 0, item),),
                        byproducts = (),
                        time = 1,
                        order = order)
        addRecipe(recipe)

    addResearch('_production_research', 'zz0', sciencePacks - {itm.military_science_pack})
    addResearch('_military_research', 'zz1', sciencePacks - {itm.production_science_pack})
    addResearch('_combined_research', 'zz2', sciencePacks)

def standardCraftingHints(gi):
    craftingHints = {}
    
    for r in gi.rcpByName.values():       
        if any(item == gi.itm.empty_barrel for _, _, item in r.outputs) and len(r.outputs) > 1:
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

def importGameInfo(gameInfo, *, includeDisabled = True, researchHacks = False,
                   aliasPass = standardAliasPass, craftingHints = None, byproducts = ('empty-barrel',),
                   rocketRecipeHints = None,
                   logger = None):
    from . import config
    if logger is None:
        logger = lambda str: None
    if rocketRecipeHints is None:
        rocketRecipeHints = {}
    
    if isinstance(gameInfo, Path):
        with open(gameInfo) as f:
            d = json.load(f)
    else:
        d = gameInfo

    res = _importGameInfo(d, includeDisabled, set(byproducts), rocketRecipeHints, logger)

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
                          craftingHints = standardCraftingHints,
                          rocketRecipeHints = {'rocket-silo::space-science-pack': 'default'},
                          logger = lambda str: None)

__all__ = ('standardCraftingHints', 'importGameInfo', 'defaultImport')
