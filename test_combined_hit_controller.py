import unittest
import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("combined_hit_controller_v1.36.py")
SPEC = importlib.util.spec_from_file_location("combined_hit_controller_v1_36", MODULE_PATH)
combined_hit_controller = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = combined_hit_controller
SPEC.loader.exec_module(combined_hit_controller)

HitMvController = combined_hit_controller.HitMvController
Shrc203Controller = combined_hit_controller.Shrc203Controller
validate_integer_text = combined_hit_controller.validate_integer_text
controller_position_display = combined_hit_controller.controller_position_display
formatted_position_display = combined_hit_controller.formatted_position_display


class FakeConnection:
    def __init__(self, replies=None):
        self.replies = replies or {}
        self.commands = []
        self.is_open = True

    def send_command(self, command, read_reply=True):
        self.commands.append(command)
        if command == "?:FMT" and command not in self.replies:
            return "HIT"
        reply = self.replies.get(command, "")
        if isinstance(reply, list):
            return reply.pop(0)
        return reply


class CommandBuilderTests(unittest.TestCase):
    def test_hitmv_relative_move_uses_eight_field_vector_and_accepts_negative(self):
        controller = HitMvController(FakeConnection())
        self.assertEqual(
            controller.build_relative_move([1, 3, 8], "-100"),
            "M:-100,,-100,,,,,-100",
        )

    def test_hitmv_absolute_move_uses_eight_field_vector(self):
        controller = HitMvController(FakeConnection())
        self.assertEqual(
            controller.build_absolute_move([2, 4], "250"),
            "A:,250,,250,,,,",
        )

    def test_hitmv_home_jog_stop_vectors(self):
        controller = HitMvController(FakeConnection())
        self.assertEqual(controller.build_home([1, 8]), "H:1,,,,,,,1")
        self.assertEqual(controller.build_jog([2, 3], "+"), "J:,+,+,,,,,")
        self.assertEqual(controller.build_stop([4]), "L:,,,1,,,,")

    def test_hitmv_speed_uses_zero_based_axis_number(self):
        controller = HitMvController(FakeConnection())
        self.assertEqual(controller.build_speed(1, "100", "1000", "50"), "D:0,100,1000,50")
        self.assertEqual(controller.build_speed(8, "100", "1000", "50"), "D:7,100,1000,50")

    def test_hitmv_unit_conversion_accepts_kind_specific_units(self):
        controller = HitMvController(FakeConnection())
        self.assertEqual(controller.build_relative_move([1], "10", "um", {1: "linear"}), "M:1000,,,,,,,")
        self.assertEqual(controller.build_relative_move([1], "10", "degree", {1: "rotation"}), "M:100000,,,,,,,")

    def test_shrc_relative_move_uses_three_field_vector_and_accepts_negative(self):
        controller = Shrc203Controller(FakeConnection())
        self.assertEqual(controller.build_relative_move([1, 3], "-200"), "M:-200,,-200")

    def test_shrc_absolute_home_jog_stop_vectors(self):
        controller = Shrc203Controller(FakeConnection())
        self.assertEqual(controller.build_absolute_move([2], "300"), "A:,300,")
        self.assertEqual(controller.build_home([1, 2]), "H:1,1,")
        self.assertEqual(controller.build_jog([3], "-"), "J:,,-")
        self.assertEqual(controller.build_stop([1, 3]), "L:1,,1")

    def test_shrc_speed_uses_one_based_axis_number(self):
        controller = Shrc203Controller(FakeConnection())
        self.assertEqual(controller.build_speed(1, "100", "1000", "50"), "D:1,100,1000,50")
        self.assertEqual(controller.build_speed(3, "100", "1000", "50"), "D:3,100,1000,50")

    def test_shrc_clear_emergency_reenables_excitation(self):
        controller = Shrc203Controller(FakeConnection())
        self.assertEqual(controller.clear_emergency_commands([2]), ["BEC:,1,", "C:,1,"])

    def test_shrc_axis_map_matches_manual(self):
        expected = {
            "0": {1},
            "1": {2},
            "2": {3},
            "3": {1, 2},
            "4": {1, 3},
            "5": {2, 3},
            "6": {1, 2, 3},
        }
        for reply, axes in expected.items():
            controller = Shrc203Controller(FakeConnection({"?:AXIS": reply}))
            self.assertEqual(controller.detect_active_axes(), axes)

    def test_signed_integer_validation(self):
        self.assertEqual(validate_integer_text("-10", signed=True), "-10")
        self.assertEqual(validate_integer_text("+10", signed=True), "+10")
        with self.assertRaises(ValueError):
            validate_integer_text("-10", signed=False)
        with self.assertRaises(ValueError):
            validate_integer_text("10.5", signed=True)


class ParserTests(unittest.TestCase):
    def test_hitmv_refresh_status_splits_axis_eight_safely(self):
        replies = {
            "Q:": "10,20,30,40,50,60,70,80",
            "!:": "0,0,1,0,0,0,0,0",
            "Q:S": "00,00,00,00,00,00,00,00,01",
        }
        controller = HitMvController(FakeConnection(replies))
        status = controller.refresh_status()
        self.assertEqual(status[8]["position"], "80")
        self.assertEqual(status[8]["ready"], "Ready")
        self.assertEqual(status[8]["detail_status"], "01")

    def test_hitmv_detect_active_axes_uses_non_empty_busy_fields(self):
        controller = HitMvController(FakeConnection({"!:": "0,0,,,,,,1"}))
        self.assertEqual(controller.detect_active_axes(), {1, 2, 8})

    def test_shrc_refresh_status_uses_three_fields(self):
        replies = {
            "Q:": "100,,300",
            "Q:U": "U100,,U300",
            "Q:D": "D0.100,,D0.300",
            "!:": "0,,1",
            "Q:S": "1,,1",
        }
        controller = Shrc203Controller(FakeConnection(replies))
        controller.active_axes = {1, 3}
        status = controller.refresh_status()
        self.assertTrue(status[1]["active"])
        self.assertFalse(status[2]["active"])
        self.assertEqual(status[3]["ready"], "Busy")

    def test_position_display_keeps_raw_and_converted_units(self):
        self.assertEqual(controller_position_display("123456", "linear"), "123456 pls / 1234.56 um")
        self.assertEqual(controller_position_display("25000", "rotation"), "25000 pls / 2.5 degree")
        self.assertEqual(
            formatted_position_display("2315", "rotation", {"rotation": "2.315 degree"}),
            "2315 pls / 2.315 degree",
        )


if __name__ == "__main__":
    unittest.main()
