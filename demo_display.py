"""Animated terminal demo showing robot face states and touch targets."""

from __future__ import annotations

import os
import time

from display import DisplayAdapter
from robot_personality import VoiceState


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def main() -> None:
    display = DisplayAdapter()
    states = [
        VoiceState.IDLE,
        VoiceState.LISTENING,
        VoiceState.THINKING,
        VoiceState.SPEAKING,
        VoiceState.ERROR,
    ]

    for frame in range(10):
        state = states[frame % len(states)]
        _clear()
        print(f"=== {state.value.upper()} ===")
        print(display.render_state(state))
        print("\n=== TOUCH TARGETS ===")
        for target in display.touch_targets(["Yes", "No", "Maybe"]):
            print(target)
        time.sleep(0.7)


if __name__ == "__main__":
    main()
