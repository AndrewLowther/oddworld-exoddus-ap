# Oddworld Abe's Exoddus Setup Guide

## Required Software
- A relive build of Abe's Exoddus from: [Oddworld Abe's Exoddus Relive Archipelago](https://github.com/AndrewLowther/alive_reversing_archipelago/releases/)

## Optional Software
- Poptracker in the works

## Installation (Windows)
1. Download the relive release
2. Extract and install relive.exe and SDL3.dll into the game directory
3. Edit host.yaml to ensure oddworld_exoddus_options game_folder is looking in the right place

## Joining a MultiWorld Game
1. Open the `Oddworld Abe's Exoddus Client` from the Archipelago launcher
2. Run the game via the `relive.exe` file in the game's directory
3. Connect to the Archipelago server via the client, e.g. `archipelago.gg:65431`
4. For the `SlotName` field, enter your "name" field from the yaml config.
5. For the `Password` field, enter the server password if one exists; otherwise leave this field blank.
6. Play through the game