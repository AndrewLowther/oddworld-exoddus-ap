from typing import NamedTuple, Tuple, Dict

from .Names import RegionName

class OddworldExoddusRegionsData(NamedTuple):
    connecting_regions: Tuple[str] = ()
    game_id: int = 0
    access_key: str = ""
    needs_mudokons: bool = False

region_data_table: Dict[str, OddworldExoddusRegionsData] = {
    RegionName.main_menu: OddworldExoddusRegionsData((RegionName.necrum_mines,)),

    RegionName.necrum_mines: OddworldExoddusRegionsData((RegionName.necrum,), 1),
    RegionName.necrum: OddworldExoddusRegionsData((RegionName.mudanchee_vault, RegionName.mudomo_vault, RegionName.feeco_depot), 2),
    RegionName.mudanchee_vault: OddworldExoddusRegionsData((RegionName.mudanchee_vault_ender,), 4),
    RegionName.mudanchee_vault_ender: OddworldExoddusRegionsData((RegionName.necrum,), 7),
    RegionName.mudomo_vault: OddworldExoddusRegionsData((RegionName.mudomo_vault_ender,), 3),
    RegionName.mudomo_vault_ender: OddworldExoddusRegionsData((RegionName.necrum,), 11),
    RegionName.feeco_depot: OddworldExoddusRegionsData((RegionName.slig_barracks, RegionName.bonewerkz, RegionName.soulstorm_brewery, RegionName.feeco_depot_ender), 5),
    RegionName.feeco_depot_ender: OddworldExoddusRegionsData((RegionName.feeco_depot,), 12),
    RegionName.slig_barracks: OddworldExoddusRegionsData((RegionName.slig_barracks_ender,), 6),
    RegionName.slig_barracks_ender: OddworldExoddusRegionsData((RegionName.feeco_depot,), 13),
    RegionName.bonewerkz: OddworldExoddusRegionsData((RegionName.bonewerkz_ender,), 8),
    RegionName.bonewerkz_ender: OddworldExoddusRegionsData((RegionName.feeco_depot,), 14),
    RegionName.soulstorm_brewery: OddworldExoddusRegionsData((RegionName.soulstorm_brewery_ender,), 9),
    RegionName.soulstorm_brewery_ender: OddworldExoddusRegionsData((), 10, needs_mudokons=True),
}