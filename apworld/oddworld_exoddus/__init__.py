from BaseClasses import ItemClassification, Region, Tutorial
from typing import Dict, List, Tuple, ClassVar
from worlds.AutoWorld import WebWorld, World
from worlds.oddworld_exoddus.Locations import location_table

from . import components
from .Options import oddworld_exoddus_options_groups, OddworldExoddusOptions
from .settings_group import OddworldExoddusSettings
from .Regions import region_data_table
from .Items import OddworldExoddusItem, item_data_table, item_table, unlockable_item_data_table
from .Names import ItemName
from .Locations import main_path_mudokon_locations

class OddworldExoddusWebWorld(WebWorld):
    theme = "stone"

    setup_en = Tutorial(
        tutorial_name="Oddworld Abe's Exoddus",
        description="A guide for playing Abe's Exoddus in Archipelago",
        language="English",
        file_name="guide_en.md",
        link="guide/en",
        authors=["CapNSlaughta"]
    )

    tutorials = [setup_en]

    option_groups = oddworld_exoddus_options_groups

class OddworldExoddusWorld(World):
    """
    Experience the world of Oddworld Abe's Exoddus in Archipelago
    """

    # Class Data
    game = "Oddworld Abe's Exoddus"
    web = OddworldExoddusWebWorld()
    options_dataclass = OddworldExoddusOptions
    options = OddworldExoddusOptions
    item_name_to_id = item_table
    location_name_to_id = location_table

    settings_key = "oddworld_exoddus_options"
    settings: ClassVar[OddworldExoddusSettings]

    # Instance Data
    mudokons_required: int
    active_logic_mapping: Dict[str, List[List[str]]]
    active_region_logic_mapping: Dict[Tuple[str], List[List[str]]]

    def create_item(self, name: str) -> OddworldExoddusItem:
        # Only create the number of Mudokons for progression
        if getattr(self, "mudokons_required", 0) and name == ItemName.mudokon:
            classification: ItemClassification = ItemClassification.filler
            self.prog_mudokons = getattr(self, "prog_mudokons", 0)
            if self.prog_mudokons < self.mudokons_required:
                classification = ItemClassification.progression
                self.prog_mudokons += 1
            return OddworldExoddusItem(name, classification, item_data_table[name].code, self.player)
        else:
            return OddworldExoddusItem(name, item_data_table[name].type, item_data_table[name].code, self.player)

    def create_items(self) -> None:
        item_pool: List[OddworldExoddusItem] = []

        location_count: int = len(main_path_mudokon_locations)

        item_pool += [
            self.create_item(name)
            for name in unlockable_item_data_table.keys()
        ]

        real_total_mudokons: int = min(self.options.mudokons_to_save.value, location_count - len(item_pool))
        self.mudokons_required = int(real_total_mudokons * (self.options.mudokons_required_percentage.value / 100))

        item_pool += [self.create_item(ItemName.mudokon) for _ in range(real_total_mudokons)]

        filler_items_count: int = location_count - len(item_pool)
        item_pool += [self.create_item(self.get_filler_item_name()) for _ in range(filler_items_count)]

        self.multiworld.itempool += item_pool

    def create_regions(self) -> None:
        # Create regions
        for region_name in region_data_table.keys():
            region = Region(region_name, self.player, self.multiworld)
            self.multiworld.regions.append(region)

        for region_name, region_data in region_data_table.items():
            region = self.multiworld.get_region(region_name, self.player)
            region.add_locations({
                location_name: location_data.address for location_name, location_data in main_path_mudokon_locations.items()
                if location_data.region == region_name
            })

            from .Rules import connect_region
            connect_region(self, region, region_data_table[region_name].connecting_regions)

    def set_rules(self):
        from .Rules import set_rules
        set_rules(self)

    def get_filler_item_name(self) -> str:
        return ItemName.paramite_pie

    def fill_slot_data(self):
        return {
            "death_link": self.options.death_link.value,
            "death_link_amnesty": self.options.death_link_amnesty.value,
            "mudokons_required": self.mudokons_required
        }
