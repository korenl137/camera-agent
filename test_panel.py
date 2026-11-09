import pytest

import panel

KNOWN = {"Gain": {"id": 1, "min": 0, "max": 10}, "Gamma": {"id": 2, "min": 0, "max": 200}}


def test_preset_skips_controls_the_device_lacks():
    writes, skipped = panel.plan({"Gain": 1, "Backlight Compensation": 0}, KNOWN, skip_unknown=True)
    assert writes == {"Gain": 1}
    assert skipped == ["Backlight Compensation"]


def test_set_rejects_unknown_control():
    with pytest.raises(ValueError, match="invalid control"):
        panel.plan({"Backlight Compensation": 0}, KNOWN)


def test_preset_skips_values_outside_the_device_range():
    writes, skipped = panel.plan({"Gain": 99, "Gamma": 100}, KNOWN, skip_unknown=True)
    assert writes == {"Gamma": 100}
    assert skipped == ["Gain"]


def test_set_rejects_out_of_range_value():
    with pytest.raises(ValueError, match="invalid control"):
        panel.plan({"Gain": 99}, KNOWN)
