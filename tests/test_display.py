from robot_personality import VoiceState
from display import DisplayAdapter


def test_display_adapter_renders_state_face():
    display = DisplayAdapter()

    idle = display.render_state(VoiceState.IDLE)
    thinking = display.render_state(VoiceState.THINKING)

    assert "idle" in idle.lower()
    assert "thinking" in thinking.lower()
    assert "▀" in idle or "◉" in idle or "o" in idle


def test_display_adapter_builds_touch_targets_for_choices():
    display = DisplayAdapter()

    targets = display.touch_targets(["Yes", "No", "Maybe"])

    assert [target["label"] for target in targets] == ["Yes", "No", "Maybe"]
    assert all(target["size"] in {"large", "medium"} for target in targets)
    assert all("x" in target and "y" in target for target in targets)
