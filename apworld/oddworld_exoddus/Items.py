from BaseClasses import Item, ItemClassification
from typing import Dict, NamedTuple, Optional
from .Names import ItemName

oddworld_exoddus_base_id = 50000

class OddworldExoddusItem(Item):
    game = "Oddworld Abe's Exoddus"

class OddworldExoddusItemData(NamedTuple):
    code: Optional[int] = None
    type: ItemClassification = ItemClassification.filler

collectible_item_data_table: Dict[str, OddworldExoddusItemData] = {
    ItemName.mudokon: OddworldExoddusItemData(oddworld_exoddus_base_id + 1, ItemClassification.progression_skip_balancing),
    ItemName.paramite_pie: OddworldExoddusItemData(oddworld_exoddus_base_id + 2, ItemClassification.filler)
}

# TBD
unlockable_item_data_table: Dict[str, OddworldExoddusItemData] = {
    ItemName.mudanchee_key: OddworldExoddusItemData(oddworld_exoddus_base_id + 3, ItemClassification.progression)
}

item_data_table: Dict[str, OddworldExoddusItemData] = {
    **collectible_item_data_table,
    **unlockable_item_data_table,
}

item_table = {
    name: data.code for name, data in item_data_table.items() if data.code is not None
}