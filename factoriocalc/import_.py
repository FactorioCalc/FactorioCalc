from __future__ import annotations
import json
from pathlib import Path
from . import data,machine
from .machine import Category
from .fracs import frac, frac_from_float_round, div
from math import trunc
from .core import *
from .data import CraftingHint,GameInfo
from ._helper import toPythonName,toClassName
from collections import defaultdict
from itertools import repeat
import os

_dir = Path(__file__).parent.resolve()

def userRecipesFile():
    """Attempt to determine the location of the JSON file created by the "Recipe
     Exporter" mod."""

    appData = os.environ.get('APPDATA', None)
    if appData is not None:
        return Path(appData) / 'Factorio/script-output/recipes.json'
    elif 'HOME' in os.environ:
        return Path(os.environ['HOME']) / '.factorio/script-output/recipes.json'
    else:
        return None

def setGameConfig(mode, path=None, includeDisabled=True, importBonuses=None):
    """Sets or changes the current game configuration.

    *mode*
        One of: ``'v2.0'`` for Factorio 2.0; ``'v2.0-sa'`` for Factorio Space
        Age; ``'v1.1'`` for Factorio 1.1; ``'v1.1-expansive'`` for expansive
        mode in Factorio 1.1; ``'custom'`` for vanilla gameplay but using a
        custom configuration; ``'custom-sa'`` for Space Age but using a
        custom configuration; ``'mod'`` for overhaul mods; or a string
        specifying a custom mod with builtin support.  See the `mods` module
        for currently supported mods.

    *path*
        Path to a JSON file created by the `Recipe Exporter
        <https://mods.factorio.com/mod/RecipeExporter>`_ mod.  Ignored when
        loading a built-in configuration, required otherwise.

    *includeDisabled*
        If false, skip recipes marked as disabled.  Disabled recipes include
        those that are not yet researched.

    *importBonuses*
        Import recipe productivity bonuses if true.  If `None` than only
        import bonuses if a path is also provided.

    Note that changing the game configuration creates a new set of symbols in
    the `itm`, `rcp`, `mch`, and `presets` modules.  Any non-symbolic
    references to symboles created before calling this function are unlikely
    to work.

    The game configuration is stored in a context varable `config.gameInfo` to
    make it possible to use different game configurations within the same
    python program.

    Returns a `contextvars.Token` that can be used to restore the previous
    configuration.

    """
    if importBonuses is None:
        importBonuses = False if path is None else True

    if mode == 'v1.1':
        importFun = vanillaImport
        path = _dir / 'game-info-v_1_1-normal.json'
    elif mode == 'v1.1-expensive':
        importFun = vanillaImport
        path = _dir / 'game-info-v_1_1-expensive.json'
    elif mode == 'v2.0':
        importFun = vanillaImport
        path = _dir / 'game-info-v_2_0.json'
    elif mode == 'v2.0-sa':
        importFun = saImport
        path = _dir / 'game-info-v_2_0-sa.json'
    elif mode == 'custom':
        importFun = vanillaImport
    elif mode == 'custom-sa':
        importFun = saImport
    elif mode == 'mod':
        importFun = basicImport
    elif isinstance(mode, str):
        from . import mods
        fname = mode.translate(str.maketrans({' ': '_', '-': '_'})).lower()
        importFun = getattr(mods, fname)
    else:
        importFun = mode

    with open(path) as f:
        gameInfo = json.load(f)

    return importFun(gameInfo,
                     includeDisabled = includeDisabled,
                     importBonuses = importBonuses)

def vanillaImport(gameInfo, **kwargs):
    return importGameInfo(gameInfo,
                          presets = vanillaPresets,
                          extraPasses = [vanillaResearchHacks],
                          craftingHints = vanillaCraftingHints,
                          rocketRecipeHints = {'rocket-silo::space-science-pack': 'default'},
                          **kwargs)

def saImport(gameInfo, **kwargs):
    return importGameInfo(gameInfo,
                          presets = saPresets,
                          craftingHints = vanillaCraftingHints,
                          fuelPreferences = ('coal', 'nutrients', 'bioflux'),
                          **kwargs)

def basicImport(gameInfo, **kwargs):
    return importGameInfo(gameInfo, **kwargs)

def _importGameInfo(gameInfo, includeDisabled, importBonuses,
                    commonByproducts_, rocketRecipeHints,
                    logger):
    from . import mch

    rcpByName, itmByName, mchByName = {}, {}, {}
    rocketSilos = []
    fixedRecipes = []
    translatedNames = {}
    categories = {}
    disabledRecipes = set()

    gameVersion = gameInfo.get('game_version', '1.1')
    if gameVersion == '1.1':
        qualityNames = [None]
    else:
        qualityNames = gameInfo['quality_names']

    groups = gameInfo['groups']

    def getOrderKey(d, qualityIdx):
        assert(isinstance(qualityIdx, int))
        return (groups[d['group']]['order'],groups[d['subgroup']]['order'],d['order'],qualityIdx)

    def addItem(item, descr = ''):
        name = item.name
        pythonName = toPythonName(name)
        itmByName[name] = item
        if descr:
            translatedNames[f'itm {item.name}'] = descr

    def lookupItem(name, quality = None, qualityIdx = 0):
        if quality is None or quality == 'normal':
            assert qualityIdx == 0
            nameWithQuality = name
        else:
            assert qualityIdx > 0
            nameWithQuality = f"{quality}-{name}"
        item = itmByName.get(nameWithQuality, None)
        if item:
            return item
        fluid = itmByName.get(name, None)
        if fluid and isinstance(fluid, Fluid):
            return fluid
        #pythonName = toPythonName(name)
        d = gameInfo['items'].get(name, None)
        if d:
            if qualityIdx == 0:
                _otherQualities = []
            else:
                baseItem = itmByName[name]
                _otherQualities = baseItem._otherQualities
            item = Item(nameWithQuality,
                        order=getOrderKey(d,qualityIdx),
                        stackSize=d['stack_size'], weight=frac(d.get('weight',0), float_conv_method = 'round'),
                        quality=quality, qualityIdx=qualityIdx, _otherQualities=_otherQualities,
                        fuelValue=d['fuel_value'], fuelCategory=d.get('fuel_category',''))
            topad = qualityIdx - len(_otherQualities) + 1
            _otherQualities.extend(repeat(None,topad))
            _otherQualities[qualityIdx] = item
        else:
            d = gameInfo['fluids'][name]
            item = Fluid(name, getOrderKey(d,0))
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
    for _,v in gameInfo['entities'].items():
        if 'hidden' in v.get('flags',[]): continue
        for (qi, q) in enumerate(qualityNames):
            if q is None or q == 'normal':
                name = v['name']
                clsName = toClassName(v['name'])
            else:
                name = f"{q}-{v['name']}"
                clsName = q.title()+toClassName(v['name'])
            bases = []
            module_inventory_size = v.get('module_inventory_size', 0)
            if module_inventory_size > 0 and v['type'] != 'beacon':
                bases.append(machine.ModulesMixin)
            energy_source = v.get('energy_source', None)
            if energy_source == 'burner':
                bases.append(machine.BurnerMixin)
            elif energy_source == 'electric':
                bases.append(machine.ElectricMixin)
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
            dict = {'name': name,
                    'type': v['type'],
                    'order': getOrderKey(v,qi),
                    'group': v['group'],
                    'subgroup': v['group'],
                    'width': frac(v['width']),
                    'height': frac(v['height']),
                    'gameVersion': gameVersion,
                    'quality': q}
            cls = type(clsName, tuple(bases), dict)
            cls.__module__ = mch
            if energy_source is not None:
                cls.baseEnergyUsage = frac(v['energy_consumption'], float_conv_method = 'round')
                cls.energyDrain = frac(v['drain'], float_conv_method = 'round')
                try:
                    cls.pollution = frac(v['pollution'], float_conv_method = 'round')
                except KeyError:
                    cls.pollution = 0
            if energy_source == 'burner':
                try:
                    cls.fuelCategories = set(v['fuel_categories'])
                except KeyError:
                    pass
            if isCraftingMachine:
                if q is None:
                    cls.craftingSpeed = frac(v['crafting_speed'], float_conv_method = 'round')
                else:
                    cls.craftingSpeed = frac(v['crafting_speed'][q], float_conv_method = 'round')
                effectReceiver = v.get('effect_receiver', None)
                baseEffect = effectReceiver.get('base_effect', None) if effectReceiver else None
                if baseEffect:
                    # fixme: do this properly
                    cls.baseEffect = Effect(productivity = frac_from_float_round(baseEffect['productivity'], precision = 6))
                else:
                    cls.baseEffect = Effect()
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
                distributionEffectivity = frac(v['distribution_effectivity'], float_conv_method = 'round')
                if q is None:
                    cls.distributionEffectivity = distributionEffectivity
                else:
                    qualityBonus = frac(v['distribution_effectivity_bonus_per_quality_level'], float_conv_method = 'round')
                    level = gameInfo['quality'][q]['level']
                    cls.distributionEffectivity = distributionEffectivity + level * qualityBonus
                if q is None:
                    cls.supplyAreaDistance = frac(v['supply_area_distance'], float_conv_method = 'round')
                else:
                    cls.supplyAreaDistance = frac(v['supply_area_distance'][q], float_conv_method = 'round')
                cls.baseEffect = Effect()
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
        if gameVersion == '1.1':
            def get(what):
                return frac_from_float_round(v['module_effects'].get(what, {'bonus': 0})['bonus'], precision = 6)
            e = Effect(speed = get('speed'),
                       productivity = get('productivity'),
                       consumption = get('consumption'),
                       pollution = get('pollution'))
        else:
            def get(what):
                return frac_from_float_round(v['module_effects'].get(what, 0), precision = 6)
            e = Effect(speed = get('speed'),
                       productivity = get('productivity'),
                       consumption = get('consumption'),
                       pollution = get('pollution'),
                       quality = div(get('quality'),10))
            
        limitation = v.get('limitations', None)
        if not limitation:
            limitation = None
        if limitation is not None:
            limitation = set(limitation)
        _otherQualities = []
        for (qi, q) in enumerate(qualityNames):
            if q is None or q == 'normal':
                name = k
                level = 0
            else:
                name = f'{q}-{k}'
                level = gameInfo['quality'][q]['level']
            def qualityAdj(base,precision):
                return div(trunc(precision*base*(1+level*frac(3,10))),precision)
            adjEffect = Effect(speed = qualityAdj(e.speed, 100) if e.speed > 0 else e.speed,
                               productivity = qualityAdj(e.productivity, 100) if e.productivity > 0 else e.productivity,
                               consumption = qualityAdj(e.consumption, 100) if e.consumption < 0 else e.consumption,
                               pollution = qualityAdj(e.pollution, 100) if e.pollution < 0 else e.pollution,
                               quality = qualityAdj(e.quality, 1000) if e.quality > 0 else e.quality)
            item = Module(name, order = getOrderKey(v,qi),
                          stackSize = v['stack_size'], weight = frac(v.get('weight',0), float_conv_method='round'),
                          quality = q, qualityIdx = len(_otherQualities), _otherQualities = _otherQualities,
                          effect = adjEffect, limitation = limitation)
            _otherQualities.append(item)            
            addItem(item, v.get('translated_name',''))
            
    # import recipes
    productivityBonuses = {}
    for _,v in gameInfo['recipes'].items():
        if not (includeDisabled or v.get('enabled', False)):
            continue
        _otherQualities = [*repeat(None,len(qualityNames))]
        for i, q in enumerate(qualityNames):
            if q is None or q == 'normal':
                recipeName = v['name']
            else:
                recipeName = f"{q}-{v['name']}"
            def toRecipeComponent(d, isProduct):
                try:
                    num = d['amount']*d.get('probability',1)
                except KeyError:
                    num = d.get('probability',1) * (d['amount_max'] + d['amount_min']) / 2
                num += d.get('extra_count_fraction',0)
                if type(num) is float:
                    num = frac_from_float_round(num, precision = 9)
                if isProduct:
                    catalyst = d.get('catalyst_amount', None)
                    if catalyst is None:
                        catalyst = d.get('ignored_by_productivity', 0)
                else:
                    catalyst = 0
                return RecipeComponent(item=lookupItem(d['name'], q, i), num = num, catalyst = catalyst)
            inputs = tuple(toRecipeComponent(rc, False) for rc in v['ingredients'])
            products = []
            byproducts = []
            for product in v['products']:
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
                        if o.item.baseItem.name == d['main_product']['name']:
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
            time = frac(v.get('energy', 0.5), float_conv_method = 'round')
            allowedEffects = AllowedEffects(**v.get('allowed_effects', {}))
            maxProductivity = frac_from_float_round(v.get('maximum_productivity', 3), precision = 6)
            order = getOrderKey(v,i)
            recipe = Recipe(recipeName,q,i,_otherQualities,
                            categories.get(v['category'], None),inputs,products,byproducts,time,
                            allowedEffects,maxProductivity,order)
            _otherQualities[i] = recipe
            addRecipe(recipe, v.get('translated_name', ''))
            if not v.get('enabled', False):
                disabledRecipes.add(recipeName)

        if importBonuses is True:
            bonus = frac_from_float_round(v.get('productivity_bonus', 0), precision = 6)
            if bonus != 0:
                productivityBonuses[_otherQualities[0]] = bonus

    for cls, recipeName in fixedRecipes:
        try:
            cls.fixedRecipe = rcpByName[recipeName]
        except KeyError:
            pass

    rocketSiloDefaultProduct = {}

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
            try:
                recipe = getattr(rocketSilo, 'fixedRecipe')
            except AttributeError:
                pass
            num = rocketSilo.rocketPartsRequired
            rocket_parts_inputs = tuple(RecipeComponent(rc.num*num, 0, rc.item) for rc in recipe.inputs)
            rocket_parts_time = recipe.time*num
            if useHint == '' or useHint == 'default-for-machine':
                name = f'{item.name}--{rocketSilo.name}'
            elif useHint == 'default' or useHint == 'default-for-item':
                name = item.name
            else:
                raise ValueError(f"expected one of 'skip', 'default' or '' for rocketRecipeHints['{name}'] but got '{useHint}'")
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
                allowedEffects = AllowedEffects(),
                maxProductivity = 3,
                time = rocket_parts_time,
                cargo = RecipeComponent(num=1, catalyst=0, item=lookupItem(k)),
            )
            addRecipe(recipe)
            if useHint == 'default' or useHint == 'default-for-machine':
                if rocketSilo in rocketSiloDefaultProduct:
                    rocketSiloDefaultProduct[rocketSilo] = None
                else:
                    rocketSiloDefaultProduct[rocketSilo] = recipe

    for rocketSilo, product in list(rocketSiloDefaultProduct.items()):
        if product is None:
            del rocketSiloDefaultProduct[rocketSilo]

    steam = Recipe(
        name = 'steam',
        quality = None,
        qualityIdx = 0,
        _otherQualities = [None],
        category = Category('Boiler', [mchByName['boiler']]),
        inputs = (RecipeComponent(60, 0, lookupItem('water')),),
        products = (RecipeComponent(60, 0, lookupItem('steam')),),
        byproducts = (),
        time = 1,
        allowedEffects = AllowedEffects(),
        maxProductivity = 3,
        order = ('','',''))
    steam._otherQualities[0] = steam
    addRecipe(steam)

    res = data.GameInfo(
        gameVersion = gameVersion,
        emptyBarrel = itmByName['empty-barrel'] if gameVersion == '1.1' else itmByName['barrel'],
        rcpByName = rcpByName,
        itmByName = itmByName,
        mchByName = mchByName,
        translatedNames = translatedNames,
        disabledRecipes = disabledRecipes,
        rocketSiloDefaultProduct = rocketSiloDefaultProduct,
        qualityLevels = qualityNames,
        maxQualityIdx = len(qualityNames) - 1,
        recipeProductivityBonus = productivityBonuses
    )

    return res

def genMaxProd(maxLevel, *machines):
    from . import itm
    def maxProd(level = maxLevel, beacon = None, beacons = None):
        if level == 1:
            prodModule = itm.productivity_module
        else:
            prodModule = getattr(itm, f'productivity_module_{level}')
        return MachinePrefs(machine(modules = prodModule, beacon = beacon, beacons = beacons) for machine in machines)
    return maxProd

def vanillaPresets():
    from . import mch, itm
    return {
        'MP_EARLY_GAME': MachinePrefs(mch.AssemblingMachine1(), mch.StoneFurnace()),
        'MP_LATE_GAME': MachinePrefs(mch.AssemblingMachine3(), mch.ElectricFurnace()),
        'MP_MAX_PROD' : genMaxProd(
            3,
            mch.AssemblingMachine3,
            mch.ElectricFurnace,
            mch.ChemicalPlant,
            mch.OilRefinery,
            mch.RocketSilo,
            mch.Centrifuge
        ),
        'SPEED_BEACON': mch.Beacon(modules=[itm.speed_module_3, itm.speed_module_3]),
        'sciencePacks': {itm.automation_science_pack,
                         itm.logistic_science_pack,
                         itm.chemical_science_pack,
                         itm.production_science_pack,
                         itm.utility_science_pack,
                         itm.space_science_pack,
                         itm.military_science_pack}
    }

def saPresets():
    from . import mch, itm, rcp
    return {
        'MP_EARLY_GAME': MachinePrefs(mch.AssemblingMachine1(), mch.StoneFurnace(), mch.ChemicalPlant()),
        'MP_EARLY_MID_GAME': MachinePrefs(mch.AssemblingMachine3(), mch.ElectricFurnace(), mch.ChemicalPlant()),
        'MP_LATE_GAME': MachinePrefs(
            mch.Foundry(),
            mch.ElectromagneticPlant(),
            mch.AssemblingMachine3(rcp.rocket_fuel),
            mch.ChemicalPlant(rcp.light_oil_cracking),
            mch.ChemicalPlant(rcp.heavy_oil_cracking),
            mch.Biochamber(),
            mch.CryogenicPlant(),
            mch.AssemblingMachine3(),
            mch.ElectricFurnace()),
        'MP_LEGENDARY': MachinePrefs(
            mch.LegendaryFoundry(modules=itm.legendary_productivity_module_3),
            mch.LegendaryElectromagneticPlant(modules=itm.legendary_productivity_module_3),
            mch.LegendaryAssemblingMachine3(rcp.rocket_fuel, modules=itm.legendary_productivity_module_3),
            mch.LegendaryChemicalPlant(rcp.light_oil_cracking, modules=itm.legendary_productivity_module_3),
            mch.LegendaryChemicalPlant(rcp.heavy_oil_cracking, modules=itm.legendary_productivity_module_3),
            mch.LegendaryBiochamber(modules=itm.legendary_productivity_module_3),
            mch.LegendaryCryogenicPlant(modules=itm.legendary_productivity_module_3),
            mch.LegendaryAssemblingMachine3(modules=itm.legendary_productivity_module_3),
            mch.LegendaryElectricFurnace(modules=itm.legendary_productivity_module_3),
            mch.LegendaryChemicalPlant(modules=itm.legendary_productivity_module_3),
            mch.LegendaryOilRefinery(modules=itm.legendary_productivity_module_3),
            mch.LegendaryRocketSilo(modules=itm.legendary_productivity_module_3),
            mch.LegendaryCentrifuge(modules=itm.legendary_productivity_module_3),
            mch.LegendaryRecycler(rcp.scrap_recycling),
            mch.LegendaryRecycler(modules=itm.legendary_quality_module_3),
        ),
        'sciencePacks': {itm.automation_science_pack,
                         itm.logistic_science_pack,
                         itm.chemical_science_pack,
                         itm.production_science_pack,
                         itm.utility_science_pack,
                         itm.military_science_pack,
                         itm.space_science_pack,
                         itm.metallurgic_science_pack,
                         itm.electromagnetic_science_pack,
                         itm.agricultural_science_pack,
                         itm.cryogenic_science_pack,
                         itm.promethium_science_pack},
    }


def vanillaResearchHacks(gi):
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

    from .helper import FakeLab

    def addResearch(name, order, inputs):
        order = ('z', 'z', order)
        from . import helper
        item = addItem(Research, name, order)
        recipe = Recipe(name = name,
                        quality = None,
                        qualityIdx = 0,
                        _otherQualities = [None],
                        category = Category('FakeLab', [FakeLab]),
                        inputs = (RecipeComponent(1, 0, i) for i in sorted(inputs, key = lambda k: k.order)),
                        products = (RecipeComponent(1, 0, item),),
                        byproducts = (),
                        time = 1,
                        allowedEffects = AllowedEffects(),
                        maxProductivity = 3,
                        order = order)
        recipe._otherQualities[0] = recipe
        addRecipe(recipe)

    addResearch('_production_research', 'zz0', gi.presets['sciencePacks'] - {gi.itm.military_science_pack})
    addResearch('_military_research', 'zz1', gi.presets['sciencePacks'] - {gi.itm.production_science_pack})
    addResearch('_combined_research', 'zz2', gi.presets['sciencePacks'])

def vanillaCraftingHints():
    from . import rcpByName, itm, config
    craftingHints = {}

    emptyBarrel = config.gameInfo.get().emptyBarrel

    for r in rcpByName.values():
        if any(item == emptyBarrel for _, _, item in r.outputs) and len(r.outputs) > 1:
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


def _aliasPass(gi, nameTouchup = None):
    if nameTouchup is None:
        nameTouchup = lambda name: name

    conflicts = defaultdict(list)
    for name,obj in gi.itmByName.items():
        alias = nameTouchup(name)
        alias = toPythonName(alias)
        conflicts[f'itm.{alias}'].append(name)
        setattr(gi.itm, alias,  obj)
        gi.aliases[name] = alias
    conflicts = {k: v for k, v in conflicts.items() if len(v) > 1}
    if conflicts:
        raise AliasConflicts(conflicts)

    conflicts = defaultdict(list)
    for name,obj in gi.rcpByName.items():
        alias = nameTouchup(name)
        alias = toPythonName(alias)
        conflicts[f'rcp.{alias}'].append(name)
        setattr(gi.rcp, alias, obj)
        gi.aliases[name] = alias
    conflicts = {k: v for k, v in conflicts.items() if len(v) > 1}
    if conflicts:
        raise AliasConflicts(conflicts)

    conflicts = defaultdict(list)
    for name,cls in gi.mchByName.items():
        alias = nameTouchup(name)
        alias = toClassName(alias)
        conflicts[f'mch.{alias}'].append(name)
        cls.__name__ = alias
        cls.__qualname__ = alias
        setattr(gi.mch, alias, cls)
    conflicts = {k: v for k, v in conflicts.items() if len(v) > 1}
    if conflicts:
        raise AliasConflicts(conflicts)

class AliasConflicts(ValueError):
    def __init__(self, conflicts):
        super().__init__(conflicts)

def importGameInfo(gameInfo, *,
                   includeDisabled = True,
                   importBonuses = False,
                   preAliasPasses = (),
                   nameTouchups = None,
                   fuelPreferences = ('coal',),
                   presets = None,
                   extraPasses = (),
                   craftingHints = None,
                   byproducts = ('empty-barrel',),
                   rocketRecipeHints = None,
                   logger = None):
    """Import game info by populating the `config.gameInfo` context variable.

    *gameInfo*
        A JSON string or `pathlib.Path` to a file that contains the
        game info to import.  Created with the "Recipe Exporter" mod.

    *includeDisabled*
        If false, skip recipes marked as disabled.  Disabled recipes include
        those that are not yet researched.

    *importBonuses*
        Import recipe productivity bonuses if true.  If `None` than only
        import bonuses if a path is also specifed.

    *nameTouchups*
        A function to transform internal names before they are
        converted to aliases.

    *presets*
        A function to create useful presets that live in the `presets` module.
        The function takes no paramaters and is expected to return a `dict`.
        The `config.gameInfo` context variable is set so `mch`, `itm`,
        `rcp` are now populated.

    *extraPasses*
        Sequence of extra passes to run.  Each function takes in
        `config.gameInfo` as a paramater and is expected to modify it in
        place.

    *craftingHints*
        A function to create hints used to guide the selection of machines
        `produce` selects.  Like the *presets* function, it takes no
        paramaters and is expected to return a `dict`.  See the source code
        for `vanillaCraftingHints` for more details on how this function is
        used.

    *byproducts*
        A list used to help determine byproducts in recipes that have more
        than one output.  Each element of the list is one of: an internal name
        of an item, a tuple with multiple items, or a nested tuple of the form
        ``(<item>, (<item>, ...))```.

        If just an item name, than that item is considered a byproduct if a
        recipe has multiple outputs and at least one other output is not in
        the list.

        If a tuple, and more than one item within the tuple is in the output
        of a recipe, the earlier item will be considered a byproduct and the
        later item the normal output.  For example, the tuple
        ``('empty-barrel', 'water')`` will mark both the empty barrel and
        water as a byproduct, but if both are outputs of a recipe (for example
        when emptying a water barrel) than the empty barrel will be the
        byproduct.

        A tuple of the form ``(<item>, (<item1>, <item2>, ...))``. Is a
        shortcut for ``(<item>, <item1>)``, ``(<item>, <item2>)``,
        ``(<item>, ...)``.

        Within a tuple, the special string ``*fluid*`` can be used as shortcut
        for all possible fluids in the game.  Unlike specifying the fluids
        explicitly, the fluid itself is not marked as a byproduct, unless it is
        also mentioned elsewhere is the list.  For example, ``[('empty-barrel',
        'water')]`` is equivalent to ``[('empty-barrel', '*fluid*'), 'water']``.

    *rocketRecipeHints*
        A mapping used to guide the creation of special recipes for the
        results of a rocket launch.  The key is normaly a string of the form
        ``<rocket-silo>::<product>``, where ``<rocket-silo>`` is the internal
        name of the rocket silo used to launch the rocket, and ``<product>``
        is the result of launching the rocket.  The value of the mapping is
        one of ``''`` (an empty string), ``default``, ``default-for-machine``,
        ``default-for-item`` or ``skip``.  If an empty string or
        ``default-for-machine`` than a recipe is created but the name is
        mangled.  If ``default`` or ``default-for-item``, than a recipe is
        created and given the same name as the product.  In addition, if the
        value is ``default`` or ``default-for-machine`` than the recipe will
        be assumed to be the product of a launching a rocket in the specified
        rocket silo when importing blueprints.  If ``skip`` is used than no
        recipe is created.  As a special case, if ``skip`` is used and the key
        is a name of a rocket silo without any product, than no recipes are
        created involving that rocket silo.

        If *logger* is set then a warning will be created for any combinations
        not included in this mapping.

    *fuelPreferences*
        Sequence of items to use as fuel that will be tried in order.

    *logger*
        Function called to log additional info, it is called once per line to
        be logged.  A suitable function to use, for example, would be `print`.

    """
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

    res = _importGameInfo(d, includeDisabled, importBonuses, set(byproducts), rocketRecipeHints, logger)

    for p in preAliasPasses:
        p(res)

    _aliasPass(res, nameTouchups)

    res.fuelPreferences = tuple(res.itmByName[fuelName] for fuelName in fuelPreferences)

    token = config.gameInfo.set(res)

    if presets:
        res.presets = presets()
    else:
        res.presets = {}

    for p in extraPasses:
        p(res)

    res.finalize()

    if craftingHints:
        res.craftingHints = craftingHints()
    else:
        res.craftingHints = {}

    return token

__all__ = ('setGameConfig', 'userRecipesFile', 'importGameInfo',
           'genMaxProd',
           'vanillaResearchHacks', 'vanillaCraftingHints',
           'CraftingHint', 'GameInfo', 'toPythonName', 'toClassName')
