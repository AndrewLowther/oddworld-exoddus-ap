from . import OddworldExoddusTestBase

class TestBeatableAtDefault(OddworldExoddusTestBase):
    def test_unbeatable_with_nothing(self):
        self.assertBeatable(False)

    def test_beatable_with_required_items(self):
        self.collect_all_but([])
        self.assertBeatable(True)

class TestBeatableAtExtremes(OddworldExoddusTestBase):
    def test_min_and_max(self):
        for mudokons_required in (1, 2):
            with self.subTest(mudokons_required=mudokons_required):
                self.options = {"mudokons_required": mudokons_required}
                self.world_setup()
                self.collect_all_but([])
                self.assertBeatable(True)