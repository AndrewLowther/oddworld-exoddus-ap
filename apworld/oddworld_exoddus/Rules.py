from typing import Dict, Callable, List, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    from worlds.oddworld_exoddus import OddworldExoddusWorld
from .Names import ItemName, RegionName
from BaseClasses import Region, CollectionState


def set_rules(world: "OddworldExoddusWorld"):
    # Completion condition.
    world.multiworld.completion_condition[world.player] = lambda state: goal_rule(state, world)

def region_connection_rule(state: CollectionState, world: "OddworldExoddusWorld", region_connection: Tuple[str, str]) -> bool:
    from .Regions import region_data_table

    src_region, dest_region = region_connection
    if dest_region not in region_data_table:
        return True

    access_key = region_data_table[dest_region].access_key
    if access_key and not state.has(access_key, world.player):
        return False

    if region_data_table[dest_region].needs_mudokons:
        return state.has(ItemName.mudokon, world.player, world.mudokons_required)
    
    return True

def connect_region(world: "OddworldExoddusWorld", region: Region, dest_regions: List[str]):
    rules: Dict[str, Callable[[CollectionState], bool]] = {}
    
    for dest_region in dest_regions:
        region_connection: Tuple[str, str] = (region.name, dest_region)
        rules[dest_region] = lambda state, region_connection=region_connection: region_connection_rule(state, world, region_connection)

    region.add_exits(dest_regions, rules)

def goal_rule(state: CollectionState, world: "OddworldExoddusWorld"):
    return state.can_reach_region(RegionName.soulstorm_brewery_ender, world.player)