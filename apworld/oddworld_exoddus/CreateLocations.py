"""
Convert a complete log of events into location-based information.
Load from the archipelago_events.jsonl and convert it into location-based information.
"""

import pathlib

from typing import Dict, NamedTuple

from .Regions import region_data_table

def get_region_name(levelData):
    for region_name, region in region_data_table.items():
        if region.game_id == levelData.get("level"):
            return region_name
    return None

import json

FILE_PATH = pathlib.Path(__file__).parent / "archipelago_events.jsonl"

def get_level_friendly_name(levelData, mudokonId):
    # Get the applicable region for the Mudokon
    for region_name, region in region_data_table.items():
        if region.game_id == levelData.get("level"):
            return f"{region_name} - Path {levelData.get('path')} - Mudokon {mudokonId}"

    # A reasonable default if we can't find the region
    return f"{levelData.get('level')} - Path {levelData.get('path')} - Mudokon {mudokonId}"

def load_events():
    events = {}
    secret_cues = []
    with open(FILE_PATH, "r") as f:
        for line in f:
            event = json.loads(line)
            if event.get("event") != "rescue":
                continue
            levelData = event.get("tlv")
            # Pack the bits to get the ID
            if levelData:
                mudokonId = (levelData.get("offset") | (levelData.get("level") << 16 | levelData.get("path") << 24))
                events[mudokonId] = {
                    "friendly_name": get_level_friendly_name(levelData, mudokonId),
                    "region_name": get_region_name(levelData),
                    "tlv_data": levelData
                }
    return events

def get_secret_cues(events):
    secret_cues = []
    for mudokonId, event in events.items():
        event = event.get("event")
        if event == "secret_cue":
            secret_cues.append(event)
    return secret_cues

class LocationData(NamedTuple):
    id: int
    region: str

def create_locations_dictionary(events):
    locations: Dict[str, LocationData] = {}
    for mudokonId, event in events.items():
        friendly_name = event.get("friendly_name")
        region_name = event.get("region_name")
        if friendly_name and region_name:
            locations[friendly_name] = LocationData(
                id=mudokonId,
                region=region_name
            )
    return locations

if __name__ == "__main__":
    events = load_events()
    locations = create_locations_dictionary(events)
    secret_cues = get_secret_cues(events)
    print("Secret cues:", secret_cues)