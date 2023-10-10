local json = require("json")

local function keys(obj)
  if obj == nil then
    return nil
  end
  local keys = {}
  for key, _ in pairs(obj) do
    table.insert(keys, key)
  end
  if next(keys) == nil then
    return nil
  else
    return keys
  end
end

local data = nil
local need_translation = nil

commands.add_command("dump_recipes", nil, function(command)

  if data ~= nil then
    game.player.print('previous dump_recipes command still running')
  end

  data = {}
  need_translation = {}

  script.on_event(defines.events.on_string_translated, function(event)
    if need_translation[event.id] == nil then
      return
    end
    if event.translated then
      need_translation[event.id].translated_name = event.result
    end
    need_translation[event.id] = nil
    if next(need_translation) == nil then
      --game.write_file('recipes.data', serpent.block(data))
      game.write_file('recipes.json', json.stringify(data))
      game.print('output written to script-output/recipes.json')
      script.on_event(defines.events.on_string_translated, nil)
      data = nil
      need_translation = nil
    end
  end)

  data['groups'] = {}
  local add_group = function(group)
    if not data['groups'][group.name] then
      data['groups'][group.name] = {
        name = group.name,
	type = group.type,
	order = group.order,
      }
      if group.type == 'item-group' then
        data['groups'][group.name]['order_in_recipe'] = group.order_in_recipe
      end
    end
    return group.name
  end
  data['recipes'] = {}
  for _, v in pairs(game.player.force.recipes) do
    data['recipes'][v.name] = {
      name = v.name,
      category = v.category,
      ingredients = v.ingredients,
      products = v.products,
      main_product = v.prototype.main_product,
      energy = v.energy,
      order = v.order,
      group = add_group(v.group),
      subgroup = add_group(v.subgroup),
      enabled = v.enabled,
    }
    local id = game.player.request_translation(v.localised_name)
    need_translation[id] = data['recipes'][v.name]
  end
  data['items'] = {}
  for _, v in pairs(game.item_prototypes) do
    data['items'][v.name] = {
      name = v.name,
      type = v.type,
      order = v.order,
      group = add_group(v.group),
      subgroup = add_group(v.subgroup),
      stack_size = v.stack_size,
      fuel_category = v.fuel_category,
      fuel_value = v.fuel_value,
      module_effects = v.module_effects,
      limitations = v.limitations,
      rocket_launch_products = v.rocket_launch_products,
      flags = keys(v.flags),
    }
    local id = game.player.request_translation(v.localised_name)
    need_translation[id] = data['items'][v.name]
  end
  data['fluids'] = {}
  for _, v in pairs(game.fluid_prototypes) do
    data['fluids'][v.name] = {
      name = v.name,
      order = v.order,
      group = add_group(v.group),
      subgroup = add_group(v.subgroup),
      fuel_value = v.fuel_value,
    }
    local id = game.player.request_translation(v.localised_name)
    need_translation[id] = data['fluids'][v.name]
  end
  data['entities'] = {}
  for _, v in pairs(game.entity_prototypes) do
    local name = v.name
    local type = v.type
    if (type == "beacon"
         or type == "furnace"
         or type == "assembling-machine"
         or type == "crafting-machine"
         or type == "boiler"
         or type == "rocket-silo"
         --or type == "rocket-silo-rocket"
         or type == "beacon")
    then
      local energy_consumption = nil
      local drain = nil
      local pollution = nil
      local energy_source = nil
      if v.electric_energy_source_prototype and v.energy_usage ~= nil then
        energy_consumption = v.energy_usage * 60
	drain = v.electric_energy_source_prototype.drain * 60
        pollution = v.electric_energy_source_prototype.emissions * energy_consumption * 60
        energy_source = 'electric'
      elseif v.burner_prototype and v.energy_usage ~= nil then
  	energy_consumption = v.energy_usage * 60
	drain = 0
        pollution = v.burner_prototype.emissions * energy_consumption * 60
        energy_source = 'burner'
      end
      data['entities'][v.name] = {
	name = name,
	type = type,
	order = v.order,
	group = v.group.name,
	subgroup = v.subgroup.name,
	crafting_speed = v.crafting_speed,
	crafting_categories = keys(v.crafting_categories),
	allowed_effects = keys(v.allowed_effects),
	module_inventory_size = v.module_inventory_size,
        fixed_recipe = v.fixed_recipe,
        
	rocket_parts_required = v.rocket_parts_required,
	--rocket_rising_delay = v.rocket_rising_delay,
	--launch_wait_time = v.launch_wait_time,
        --light_blinking_speed = v.light_blinking_speed,
        --door_opening_speed = v.door_opening_speed,
        --rising_speed = v.rising_speed,
        --engine_starting_speed = v.engine_starting_speed,
        --flying_speed = v.flying_speed,
        
	distribution_effectivity = v.distribution_effectivity,
	supply_area_distance = v.supply_area_distance,
	energy_consumption = energy_consumption,
	drain = drain,
        energy_source = energy_source,
	pollution = pollution,
        width = v.tile_width,
        height = v.tile_height,
        flags = keys(v.flags),
      }
      local id = game.player.request_translation(v.localised_name)
      need_translation[id] = data['entities'][v.name]
    end
  end
end)

