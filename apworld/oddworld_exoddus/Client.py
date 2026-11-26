import asyncio
import json
import logging
import os
import time

from . import OddworldExoddusWorld
from CommonClient import CommonContext, get_base_parser, gui_enabled, server_loop
from NetUtils import ClientStatus

GAME_PATH = OddworldExoddusWorld.settings.game_folder
LOG_FILE = "archipelago_events.jsonl"
STATE_FILE = "oddworld_exoddus_state.json"
EVENTS_FILE = "archipelago_events.txt"
UNLOCKS_FILE = "archipelago_unlocks.txt"

def load_state(path: str) -> dict | None:
    """
    Load the current game state, have we started a new seed, is this an existing one
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return None

def save_state(path: str, state: dict) -> None:
    """
    Save the current game state
    """
    with open(path + ".tmp", "w", encoding="utf-8") as file:
        json.dump(state, file)
    os.replace(path + ".tmp", path)

def is_new_playthrough(saved: dict | None, seed: str, slot: str) -> bool:
    """
    Have we started a new playthrough (seed)
    """
    if saved is None:
        return True
    if saved.get("seed") != seed:
        return True
    if saved.get("slot") != slot:
        return True
    return False

def start_playthrough(log_path: str,state_path: str, events_path: str, unlocks_path: str, seed: str, slot: str) -> dict:
    """
    Start a new playthrough by initializing the state and log
    Move an old state if needs be
    """
    log_start = 0
    try:
        if os.path.exists(log_path):
            os.replace(log_path, log_path + "." + time.strftime("%Y%m%d-%H%M%S"))
        if os.path.exists(events_path):
            os.replace(events_path, events_path + "." + time.strftime("%Y%m%d-%H%M%S"))
        if os.path.exists(unlocks_path):
            os.replace(unlocks_path, unlocks_path + "." + time.strftime("%Y%m%d-%H%M%S"))
    except OSError:
        log_start = os.path.getsize(log_path)

    state = {
        "seed": seed,
        "slot": slot,
        "log_start": log_start
    }
    save_state(state_path, state)
    return state

def read_complete_lines(path: str, start: int = 0) -> tuple[list[str], int]:
    """
    Complete lines from `start`, and the offset just after the last one.
    """
    try:
        with open(path, "rb") as file:
            if os.fstat(file.fileno()).st_size < start:
                start = 0
            file.seek(start)
            contents = file.read()
    except FileNotFoundError:
        return [], start

    last_newline = contents.rfind(b"\n")
    if last_newline == -1:
        return [], start
    complete = contents[: last_newline + 1]
    lines = complete.decode("utf-8", errors="replace").splitlines()
    return lines, start + len(complete)

def locations_from_log(lines, missing_locations_table) -> set[int]:
    """
    Check every location in the log against our table of items
    return a list to add to the set of items
    """
    return {e.get("id") for e in events_from_lines(lines) if e.get("event") == "rescue" and e.get("id") in missing_locations_table}

def write_unlocks(path: str, names: list[str]) -> None:
    """Replace the unlocks file with one line per received item, duplicates kept."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as file:
        file.write("".join(name + "\n" for name in names))
    os.replace(tmp, path)

def goal_in_log(lines):
    return any(e.get("event") == "goal_completed" for e in events_from_lines(lines))

# Yield every line that is a json object, ignore the rest
def events_from_lines(lines):
    for line in lines:
        event = parse_line(line)
        if event is not None:
            yield event

def parse_line(line: str):
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        logging.warning("bad line: %s", line)
        return None
    if not isinstance(event, dict):
        return None
    return event

class OddworldExoddusContext(CommonContext):
    game = "Oddworld Abe's Exoddus"
    items_handling = 0b111
    want_slot_data = True

    def __init__(self, address, password):
        super().__init__(address, password)
        self.tail_task = None
        self.log_offset = 0
        self.background: set[asyncio.Task] = set()
        self.deathlink: bool = False
        self.deathlink_amnesty: int = 0
        self.death_count: int = 0
        self.ignore_deaths_until: float = 0
        self.mudokons_required: int = 60

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
            if self.server_seed_name is None:
                logging.warning("Server seed name is not set")
                return

            logging.info("Received the args: %s", args)
            logging.info("Connected to server as slot: %s", self.slot)

            # Check the state files first
            saved = load_state(GAME_PATH + STATE_FILE)
            state = saved
            if is_new_playthrough(saved, self.server_seed_name, self.auth):
                state = start_playthrough(
                    GAME_PATH + LOG_FILE, 
                    GAME_PATH + STATE_FILE, 
                    GAME_PATH + EVENTS_FILE, 
                    GAME_PATH + UNLOCKS_FILE, 
                    self.server_seed_name, 
                    self.auth
                )

            # Read the item log from the start, compare against missing_locations
            self.log_offset = state.get("log_start", 0)
            read_log_lines, self.log_offset = read_complete_lines(GAME_PATH + LOG_FILE, self.log_offset)
            found_locations = locations_from_log(read_log_lines, self.missing_locations)

            slot_data = args.get("slot_data", {})
            self.mudokons_required = slot_data.get("mudokons_required", 60)
            self.deathlink = bool(slot_data.get("death_link", False))
            self.deathlink_amnesty = slot_data.get("death_link_amnesty", 1)
            self.spawn_task(self.update_death_link(self.deathlink))

            # Any found locations get sent as one batch of checks
            if len(found_locations):
                self.spawn_task(self.check_locations(list(found_locations)))

            if self.tail_task is None or self.tail_task.done():
                self.tail_task = self.spawn_task(self.tail_log(), name="tail log")

            if goal_in_log(read_log_lines):
                self.spawn_task(self.report_goal())
        elif cmd == "ReceivedItems":
            # Add a mudokons required value into the file at the beginning
            names = [self.item_names.lookup_in_slot(item.item) for item in self.items_received]
            names.insert(0, f"mudokons_required={self.mudokons_required}")
            write_unlocks(GAME_PATH + UNLOCKS_FILE, names)

    def on_deathlink(self, data):
        # Write to the events file
        self.ignore_deaths_until = time.time() + 10
        with open(GAME_PATH + EVENTS_FILE, "a") as f:
            f.write("kill %d\n" % round(time.time() * 1000))

    async def report_goal(self):
        if self.finished_game:
            return
        await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
        self.finished_game = True

    async def handle_event(self, event):
        kind = event.get("event")
        if kind == "goal_completed":
            await self.report_goal()
        elif kind == "rescue":
            await self.handle_rescue(event)
        elif kind == "abe_died":
            if time.time() < self.ignore_deaths_until:
                return
            await self.handle_death()

    async def handle_rescue(self, event):
        location_id = event.get("id")
        if location_id not in self.server_locations:
            logging.warning("rescue id %s is not a location in this slot", location_id)
            return
        await self.check_locations([location_id])

    async def handle_death(self):
        if not self.deathlink:
            return
        if self.death_count < self.deathlink_amnesty:
            self.death_count += 1
            return
        self.death_count = 0
        await self.send_death("Abe got turned into a Paramite Pie")

    async def handle_log_line(self, line: str):
        event = parse_line(line)
        if event is None:
            return
        await self.handle_event(event)

    async def tail_log(self):
        logging.info("Starting to tail log file: %s", GAME_PATH + LOG_FILE)
        while True:
            try:
                lines, offset = read_complete_lines(GAME_PATH + LOG_FILE, self.log_offset)
                for line in lines:
                    logging.info("event: %s, offset: %s", line.rstrip("\n"), offset)
                    try:
                        await self.handle_log_line(line)
                    except Exception as e:
                        logging.exception("could not handle line: %s", line)
                self.log_offset = offset
            except Exception as e:
                logging.exception("Error while tailing log file: %s", e)
            await asyncio.sleep(0.5)

    def spawn_task(self, coro, name: str = None):
        task = asyncio.create_task(coro, name=name)
        self.background.add(task)
        task.add_done_callback(self.background.discard)
        return task

def main():
    parser = get_base_parser(description="Oddworld Abe's Exoddus client")
    parser.add_argument("--name", default=None, help="Slot name to connect as.")
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.INFO)

    async def run():
        ctx = OddworldExoddusContext(args.connect, args.password)
        ctx.auth = args.name
        ctx.server_task = ctx.spawn_task(server_loop(ctx), name="server loop")
        if gui_enabled and not getattr(args, "nogui", False):
            ctx.run_gui()
        ctx.run_cli()
        await ctx.exit_event.wait()
        await ctx.shutdown()

    asyncio.run(run())


if __name__ == "__main__":
    main()