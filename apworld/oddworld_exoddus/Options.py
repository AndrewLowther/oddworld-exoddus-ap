from Options import DeathLink, OptionGroup, PerGameCommonOptions, Range
from dataclasses import dataclass

class DeathLinkAmnesty(Range):
    """
    How many deaths before a deathlink is sent
    """
    display_name = "Death Link Amnesty"
    range_start = 0
    range_end = 30
    default = 5

class TotalMudokons(Range):
    """
    How many Mudokons exist
    """
    display_name = "Total Mudokons"
    range_start = 1
    range_end = 300
    default = 60

class MudokonsRequiredPercentage(Range):
    """
    What percentage of Mudokons need to be saved
    """
    display_name = "Mudokons Required Percentage"
    range_start = 0
    range_end = 100
    default = 80

oddworld_exoddus_options_groups = [
    OptionGroup("Goal Options", [
        TotalMudokons,
        MudokonsRequiredPercentage
    ]),
]

@dataclass
class OddworldExoddusOptions(PerGameCommonOptions):
    death_link: DeathLink
    death_link_amnesty: DeathLinkAmnesty
  
    mudokons_to_save: TotalMudokons
    mudokons_required_percentage: MudokonsRequiredPercentage
