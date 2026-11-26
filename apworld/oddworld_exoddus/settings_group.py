import settings

class OddworldExoddusSettings(settings.Group):
    class GameFolder(settings.OptionalUserFolderPath):
        """The folder the modified game runs in. The client reads the event log from it and writes the unlocks file to it."""
        description = "Abe's Exoddus (modified RELIVE) game folder"

    game_folder: GameFolder = GameFolder("C:/Program Files (x86)/Steam/steamapps/common/Oddworld Abes Exoddus/")