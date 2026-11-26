from worlds.LauncherComponents import Component, Type, components, launch

def run_client(*args: str) -> None:
    from .Client import main
    launch(main, name="Oddworld Abe's Exoddus Client", args=args)

components.append(Component(
    display_name="Oddworld Abe's Exoddus Client",
    game_name="Oddworld Abe's Exoddus",
    func=run_client,
    component_type=Type.CLIENT
))