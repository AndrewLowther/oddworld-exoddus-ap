import asyncio
import json
import os
import tempfile
import unittest
from unittest import mock

from ..Client import (
    OddworldExoddusContext,
    events_from_lines,
    goal_in_log,
    is_new_playthrough,
    load_state,
    locations_from_log,
    parse_line,
    read_complete_lines,
    save_state,
    start_playthrough,
)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name

    def path(self, name: str) -> str:
        return os.path.join(self.dir, name)

    def write(self, name: str, data: bytes) -> str:
        path = self.path(name)
        with open(path, "wb") as file:
            file.write(data)
        return path


class TestLoadAndSaveState(TempDirTestCase):
    def test_load_missing_file_returns_none(self):
        self.assertIsNone(load_state(self.path("missing.json")))

    def test_load_invalid_json_returns_none(self):
        path = self.write("state.json", b"{not json")
        self.assertIsNone(load_state(path))

    def test_load_valid_state(self):
        path = self.write("state.json", b'{"seed": "abc", "slot": "Abe"}')
        self.assertEqual(load_state(path), {"seed": "abc", "slot": "Abe"})

    def test_save_then_load_round_trips(self):
        path = self.path("state.json")
        state = {"seed": "abc", "slot": "Abe", "log_start": 12}
        save_state(path, state)
        self.assertEqual(load_state(path), state)

    def test_save_overwrites_and_leaves_no_temp_file(self):
        path = self.path("state.json")
        save_state(path, {"seed": "old"})
        save_state(path, {"seed": "new"})
        self.assertEqual(load_state(path), {"seed": "new"})
        self.assertFalse(os.path.exists(path + ".tmp"))


class TestIsNewPlaythrough(unittest.TestCase):
    def test_no_saved_state_is_new(self):
        self.assertTrue(is_new_playthrough(None, "seed", "slot"))

    def test_matching_seed_and_slot_is_not_new(self):
        self.assertFalse(is_new_playthrough({"seed": "seed", "slot": "slot"}, "seed", "slot"))

    def test_different_seed_is_new(self):
        self.assertTrue(is_new_playthrough({"seed": "other", "slot": "slot"}, "seed", "slot"))

    def test_different_slot_is_new(self):
        self.assertTrue(is_new_playthrough({"seed": "seed", "slot": "other"}, "seed", "slot"))

    def test_empty_saved_state_is_new(self):
        self.assertTrue(is_new_playthrough({}, "seed", "slot"))


class TestStartPlaythrough(TempDirTestCase):
    def test_without_existing_log_saves_fresh_state(self):
        log_path = self.path("events.jsonl")
        state_path = self.path("state.json")

        state = start_playthrough(log_path, state_path, "seed", "slot")

        self.assertEqual(state, {"seed": "seed", "slot": "slot", "log_start": 0})
        self.assertEqual(load_state(state_path), state)

    def test_existing_log_is_archived(self):
        log_path = self.write("events.jsonl", b"old data\n")
        state_path = self.path("state.json")

        state = start_playthrough(log_path, state_path, "seed", "slot")

        self.assertEqual(state["log_start"], 0)
        self.assertFalse(os.path.exists(log_path))
        archived = [name for name in os.listdir(self.dir) if name.startswith("events.jsonl.")]
        self.assertEqual(len(archived), 1)
        with open(self.path(archived[0]), "rb") as file:
            self.assertEqual(file.read(), b"old data\n")

    def test_log_start_is_file_size_when_archiving_fails(self):
        log_path = self.write("events.jsonl", b"12345678")
        state_path = self.path("state.json")
        real_replace = os.replace

        def replace(src, dst):
            if src == log_path:
                raise PermissionError("in use")
            real_replace(src, dst)

        with mock.patch("os.replace", side_effect=replace):
            state = start_playthrough(log_path, state_path, "seed", "slot")

        self.assertEqual(state["log_start"], 8)
        self.assertTrue(os.path.exists(log_path))
        self.assertEqual(load_state(state_path), state)


class TestReadCompleteLines(TempDirTestCase):
    def test_missing_file_returns_nothing_and_keeps_offset(self):
        self.assertEqual(read_complete_lines(self.path("missing"), 5), ([], 5))

    def test_empty_file(self):
        path = self.write("log", b"")
        self.assertEqual(read_complete_lines(path), ([], 0))

    def test_reads_all_complete_lines(self):
        path = self.write("log", b"one\ntwo\n")
        self.assertEqual(read_complete_lines(path), (["one", "two"], 8))

    def test_partial_trailing_line_is_left_for_later(self):
        path = self.write("log", b"one\ntwo\nthr")
        self.assertEqual(read_complete_lines(path), (["one", "two"], 8))

    def test_only_partial_line_returns_nothing(self):
        path = self.write("log", b"partial")
        self.assertEqual(read_complete_lines(path), ([], 0))

    def test_reads_from_start_offset(self):
        path = self.write("log", b"one\ntwo\n")
        self.assertEqual(read_complete_lines(path, 4), (["two"], 8))

    def test_resumes_after_file_grows(self):
        path = self.write("log", b"one\ntw")
        lines, offset = read_complete_lines(path)
        self.assertEqual((lines, offset), (["one"], 4))

        self.write("log", b"one\ntwo\nthree\n")
        self.assertEqual(read_complete_lines(path, offset), (["two", "three"], 14))

    def test_offset_at_end_returns_nothing(self):
        path = self.write("log", b"one\n")
        self.assertEqual(read_complete_lines(path, 4), ([], 4))

    def test_offset_beyond_file_size_restarts_from_beginning(self):
        path = self.write("log", b"one\n")
        self.assertEqual(read_complete_lines(path, 100), (["one"], 4))

    def test_crlf_line_endings(self):
        path = self.write("log", b"one\r\ntwo\r\n")
        self.assertEqual(read_complete_lines(path), (["one", "two"], 10))

    def test_invalid_utf8_is_replaced(self):
        path = self.write("log", b"bad\xff\n")
        lines, offset = read_complete_lines(path)
        self.assertEqual(lines, ["bad\ufffd"])
        self.assertEqual(offset, 5)

    def test_offset_counts_bytes_not_characters(self):
        path = self.write("log", "\u00e9\nx\n".encode("utf-8"))
        self.assertEqual(read_complete_lines(path), (["\u00e9", "x"], 5))


class TestLocationsFromLog(unittest.TestCase):
    @staticmethod
    def rescue(location_id) -> str:
        return json.dumps({"event": "rescue", "id": location_id})

    def test_no_lines(self):
        self.assertEqual(locations_from_log([], {1, 2}), set())

    def test_rescue_in_missing_locations_is_found(self):
        self.assertEqual(locations_from_log([self.rescue(1)], {1, 2}), {1})

    def test_rescue_not_in_missing_locations_is_ignored(self):
        self.assertEqual(locations_from_log([self.rescue(3)], {1, 2}), set())

    def test_duplicates_are_collapsed(self):
        self.assertEqual(locations_from_log([self.rescue(1), self.rescue(1)], {1}), {1})

    def test_multiple_locations(self):
        lines = [self.rescue(1), self.rescue(2), self.rescue(3)]
        self.assertEqual(locations_from_log(lines, {1, 3}), {1, 3})

    def test_other_events_are_ignored(self):
        line = json.dumps({"event": "death", "id": 1})
        self.assertEqual(locations_from_log([line], {1}), set())

    def test_line_without_event_is_ignored(self):
        self.assertEqual(locations_from_log([json.dumps({"id": 1})], {1}), set())

    def test_rescue_without_id_is_ignored(self):
        self.assertEqual(locations_from_log([json.dumps({"event": "rescue"})], {1}), set())

    def test_malformed_lines_are_skipped(self):
        lines = ["not json", "", "{", self.rescue(2)]
        self.assertEqual(locations_from_log(lines, {2}), {2})

    def test_accepts_dict_as_missing_locations_table(self):
        self.assertEqual(locations_from_log([self.rescue(5)], {5: "loc"}), {5})


class TestParseLine(unittest.TestCase):
    def test_json_object_is_returned(self):
        self.assertEqual(parse_line('{"event": "rescue", "id": 1}'), {"event": "rescue", "id": 1})

    def test_invalid_json_returns_none_and_warns(self):
        with self.assertLogs(level="WARNING") as logs:
            self.assertIsNone(parse_line("not json"))
        self.assertIn("not json", logs.output[0])

    def test_non_object_json_returns_none(self):
        for line in ("[1, 2]", "5", '"text"', "null"):
            with self.subTest(line=line):
                self.assertIsNone(parse_line(line))


class TestEventsFromLines(unittest.TestCase):
    def test_yields_only_json_objects(self):
        lines = ['{"event": "a"}', "garbage", "[1]", '{"event": "b"}']
        with self.assertLogs(level="WARNING"):
            events = list(events_from_lines(lines))
        self.assertEqual(events, [{"event": "a"}, {"event": "b"}])

    def test_no_lines(self):
        self.assertEqual(list(events_from_lines([])), [])


class TestGoalInLog(unittest.TestCase):
    def test_goal_completed_event(self):
        self.assertTrue(goal_in_log(['{"event": "rescue", "id": 1}', '{"event": "goal_completed"}']))

    def test_no_goal_event(self):
        self.assertFalse(goal_in_log(['{"event": "rescue", "id": 1}']))

    def test_empty_log(self):
        self.assertFalse(goal_in_log([]))

    def test_malformed_lines_do_not_hide_goal(self):
        with self.assertLogs(level="WARNING"):
            self.assertTrue(goal_in_log(["garbage", '{"event": "goal_completed"}']))


class ContextTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = OddworldExoddusContext(None, None)
        self.addAsyncCleanup(self.ctx.shutdown)
        self.ctx.server_locations = {1, 2}
        self.ctx.send_msgs = mock.AsyncMock()
        self.ctx.check_locations = mock.AsyncMock()


class TestReportGoal(ContextTestCase):
    async def test_sends_goal_status_once(self):
        await self.ctx.report_goal()
        await self.ctx.report_goal()

        self.ctx.send_msgs.assert_awaited_once()
        (messages,), _ = self.ctx.send_msgs.await_args
        self.assertEqual(messages[0]["cmd"], "StatusUpdate")
        self.assertTrue(self.ctx.finished_game)

    async def test_does_nothing_if_already_finished(self):
        self.ctx.finished_game = True
        await self.ctx.report_goal()
        self.ctx.send_msgs.assert_not_awaited()


class TestHandleRescue(ContextTestCase):
    async def test_known_location_is_checked(self):
        await self.ctx.handle_rescue({"event": "rescue", "id": 1})
        self.ctx.check_locations.assert_awaited_once_with([1])

    async def test_unknown_location_is_warned_and_ignored(self):
        with self.assertLogs(level="WARNING"):
            await self.ctx.handle_rescue({"event": "rescue", "id": 99})
        self.ctx.check_locations.assert_not_awaited()

    async def test_missing_id_is_ignored(self):
        with self.assertLogs(level="WARNING"):
            await self.ctx.handle_rescue({"event": "rescue"})
        self.ctx.check_locations.assert_not_awaited()


class TestHandleEvent(ContextTestCase):
    async def test_rescue_is_dispatched(self):
        await self.ctx.handle_event({"event": "rescue", "id": 2})
        self.ctx.check_locations.assert_awaited_once_with([2])

    async def test_goal_completed_reports_goal(self):
        await self.ctx.handle_event({"event": "goal_completed"})
        self.assertTrue(self.ctx.finished_game)
        self.ctx.send_msgs.assert_awaited_once()

    async def test_abe_died_checks_nothing(self):
        await self.ctx.handle_event({"event": "abe_died"})
        self.ctx.check_locations.assert_not_awaited()
        self.ctx.send_msgs.assert_not_awaited()

    async def test_unknown_event_is_ignored(self):
        await self.ctx.handle_event({"event": "level"})
        await self.ctx.handle_event({})
        self.ctx.check_locations.assert_not_awaited()
        self.ctx.send_msgs.assert_not_awaited()


class TestHandleLogLine(ContextTestCase):
    async def test_valid_line_is_handled(self):
        await self.ctx.handle_log_line('{"event": "rescue", "id": 1}')
        self.ctx.check_locations.assert_awaited_once_with([1])

    async def test_invalid_line_is_ignored(self):
        with self.assertLogs(level="WARNING"):
            await self.ctx.handle_log_line("garbage")
        self.ctx.check_locations.assert_not_awaited()


class TestSpawnTask(ContextTestCase):
    async def test_task_is_tracked_until_done(self):
        async def work():
            return "done"

        task = self.ctx.spawn_task(work(), name="work")
        self.assertIn(task, self.ctx.background)
        self.assertEqual(await task, "done")
        await asyncio.sleep(0)
        self.assertNotIn(task, self.ctx.background)


class TestTailLog(ContextTestCase):
    async def run_one_iteration(self):
        with mock.patch("worlds.oddworld_exoddus.Client.asyncio.sleep", side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                await self.ctx.tail_log()

    async def test_handles_lines_and_advances_offset(self):
        lines = ['{"event": "rescue", "id": 1}', '{"event": "rescue", "id": 2}']
        with mock.patch("worlds.oddworld_exoddus.Client.read_complete_lines", return_value=(lines, 60)) as read:
            await self.run_one_iteration()

        read.assert_called_once()
        self.assertEqual(self.ctx.log_offset, 60)
        self.assertEqual(self.ctx.check_locations.await_count, 2)

    async def test_failing_line_does_not_stop_remaining_lines(self):
        lines = ['{"event": "rescue", "id": 1}', '{"event": "rescue", "id": 2}']
        self.ctx.check_locations.side_effect = [RuntimeError("boom"), None]
        with mock.patch("worlds.oddworld_exoddus.Client.read_complete_lines", return_value=(lines, 60)):
            with self.assertLogs(level="ERROR"):
                await self.run_one_iteration()

        self.assertEqual(self.ctx.check_locations.await_count, 2)
        self.assertEqual(self.ctx.log_offset, 60)

    async def test_read_error_is_logged_and_loop_continues(self):
        with mock.patch("worlds.oddworld_exoddus.Client.read_complete_lines", side_effect=OSError("denied")):
            with self.assertLogs(level="ERROR"):
                await self.run_one_iteration()

        self.assertEqual(self.ctx.log_offset, 0)


class TestOnPackageConnected(ContextTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ctx.server_seed_name = "seed"
        self.ctx.auth = "slot"
        self.ctx.missing_locations = {1, 2}
        self.ctx.tail_log = mock.AsyncMock()
        self.ctx.report_goal = mock.AsyncMock()

    def connect(self, saved, log_lines=(), offset=0):
        patches = {
            "load_state": mock.Mock(return_value=saved),
            "start_playthrough": mock.Mock(return_value={"seed": "seed", "slot": "slot", "log_start": 0}),
            "read_complete_lines": mock.Mock(return_value=(list(log_lines), offset)),
        }
        with mock.patch.multiple("worlds.oddworld_exoddus.Client", **patches):
            self.ctx.on_package("Connected", {})
        return patches

    async def settle(self):
        for _ in range(3):
            await asyncio.sleep(0)

    async def test_missing_seed_name_does_nothing(self):
        self.ctx.server_seed_name = None
        with self.assertLogs(level="WARNING"):
            patches = self.connect(None)

        patches["load_state"].assert_not_called()
        self.assertIsNone(self.ctx.tail_task)

    async def test_new_playthrough_starts_fresh_and_tails_log(self):
        patches = self.connect(None)
        await self.settle()

        patches["start_playthrough"].assert_called_once()
        self.assertEqual(patches["start_playthrough"].call_args.args[2:], ("seed", "slot"))
        self.ctx.tail_log.assert_awaited_once()
        self.ctx.check_locations.assert_not_awaited()
        self.ctx.report_goal.assert_not_awaited()

    async def test_existing_playthrough_resumes_from_saved_offset(self):
        saved = {"seed": "seed", "slot": "slot", "log_start": 42}
        patches = self.connect(saved, offset=100)

        patches["start_playthrough"].assert_not_called()
        self.assertEqual(patches["read_complete_lines"].call_args.args[1], 42)
        self.assertEqual(self.ctx.log_offset, 100)

    async def test_found_locations_are_sent_as_one_batch(self):
        lines = ['{"event": "rescue", "id": 1}', '{"event": "rescue", "id": 2}', '{"event": "rescue", "id": 3}']
        self.connect({"seed": "seed", "slot": "slot"}, lines)
        await self.settle()

        self.ctx.check_locations.assert_awaited_once()
        self.assertEqual(sorted(self.ctx.check_locations.await_args.args[0]), [1, 2])

    async def test_goal_in_log_is_reported(self):
        self.connect({"seed": "seed", "slot": "slot"}, ['{"event": "goal_completed"}'])
        await self.settle()

        self.ctx.report_goal.assert_awaited_once()

    async def test_running_tail_task_is_not_replaced(self):
        running = asyncio.get_running_loop().create_future()
        self.ctx.tail_task = running
        self.connect({"seed": "seed", "slot": "slot"})
        await self.settle()

        self.assertIs(self.ctx.tail_task, running)
        self.ctx.tail_log.assert_not_awaited()

    async def test_other_commands_are_ignored(self):
        with mock.patch("worlds.oddworld_exoddus.Client.load_state") as load:
            self.ctx.on_package("ReceivedItems", {"items": []})
        load.assert_not_called()
