"""Display adapter for robot state feedback and touch interaction."""

from __future__ import annotations

from typing import Any, Callable, Iterable


class DisplayAdapter:
    """Render simple robot states and touch targets for a future display."""

    _FACE_BY_STATE = {
        "idle": "  ◉ ◉\n   |\n  / \\\n  ╰╯",
        "listening": "  ◉ ◉\n   |\n  /|\\\n  ╰╯",
        "thinking": "  ◉ ◉\n   ?\n  / \\\n  ╲╱",
        "speaking": "  ◉ ◉\n   |\n  / \\\n  --",
        "error": "  ◉ ◉\n  ! !\n   |\n  ╰╯",
    }

    def __init__(self, *, on_state_change: Callable[[str], None] | None = None):
        self.on_state_change = on_state_change

    def update_state(self, state: Any) -> str:
        """Observe a new state and return the ASCII/Unicode face for it."""
        key = getattr(state, "value", str(state)).lower()
        if self.on_state_change is not None:
            self.on_state_change(key)
        return self.render_state(key)

    def render_state(self, state: Any) -> str:
        """Return a human-readable face and label for a given state."""
        key = getattr(state, "value", str(state)).lower().replace(" ", "_")
        label = key.replace("_", " ")
        face = self._FACE_BY_STATE.get(key, self._FACE_BY_STATE["idle"])
        return f"{label}\n{face}"

    def touch_targets(self, labels: Iterable[str]) -> list[dict[str, Any]]:
        """Create large touch targets for a set of user-choice responses."""
        entries = list(labels)
        positions = [
            (10, 10),
            (42, 10),
            (10, 36),
            (42, 36),
            (10, 62),
            (42, 62),
        ]
        targets = []
        for index, label in enumerate(entries):
            x, y = positions[index % len(positions)]
            size = "large" if len(entries) <= 3 else "medium"
            targets.append(
                {
                    "label": str(label),
                    "x": x,
                    "y": y,
                    "size": size,
                    "width": 28 if size == "large" else 22,
                    "height": 18,
                }
            )
        return targets


__all__ = ["DisplayAdapter"]
