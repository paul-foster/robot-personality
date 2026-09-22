"""Typed runtime configuration for the robot personality module."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
RECOMMENDED_MAX_PROFILE_WORDS = 1000
RECOMMENDED_MAX_MECHANISM_WORDS = 500
RECOMMENDED_MAX_TEAM_WORDS = 500


class ConfigurationError(ValueError):
    """Raised when the runtime configuration cannot support the requested mode."""


@dataclass(frozen=True)
class RobotProfile:
    """Facts and speaking guidance supplied to the robot personality."""

    name: str = "Nova"
    team: str = "XXXX"
    year: int = 2027
    mechanism_details: str = "Not configured yet"
    team_details: str = "Not configured yet"
    tone: str = "concise, informative, enthusiastic, and conversational"


@dataclass(frozen=True)
class AppConfig:
    """All settings needed to start the first application milestones."""

    robot: RobotProfile = field(default_factory=RobotProfile)
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"
    vosk_model_path: Path = PROJECT_ROOT / "vosk-model-small-en-us-0.15"
    input_sample_rate: int | None = None
    input_device: int | None = None
    audio_input_timeout_seconds: float = 30.0
    tts_backend: str = "espeak"
    tts_voice: str = "en-us"
    tts_speed: int = 155
    log_level: str = "INFO"
    max_history_messages: int = 12
    max_profile_words: int = RECOMMENDED_MAX_PROFILE_WORDS
    max_mechanism_words: int = RECOMMENDED_MAX_MECHANISM_WORDS
    max_team_words: int = RECOMMENDED_MAX_TEAM_WORDS


def _environment_value(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or not value.strip() else value.strip()


def _load_dotenv() -> None:
    """Load simple KEY=VALUE entries without overriding the shell environment."""

    dotenv_path = PROJECT_ROOT / ".env"
    if not dotenv_path.is_file():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            os.environ.setdefault(name, value)


def _positive_integer(name: str, default: int) -> int:
    value = _environment_value(name, str(default))
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer, got {value!r}") from error
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return parsed


def _sample_rate() -> int | None:
    value = _environment_value("INPUT_SAMPLE_RATE", "auto").lower()
    if value == "auto":
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError(
            "INPUT_SAMPLE_RATE must be 'auto' or a positive integer"
        ) from error
    if parsed <= 0:
        raise ConfigurationError("INPUT_SAMPLE_RATE must be greater than zero")
    return parsed


def _optional_device() -> int | None:
    value = _environment_value("INPUT_DEVICE", "default").lower()
    if value == "default":
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError("INPUT_DEVICE must be 'default' or a device index") from error
    if parsed < 0:
        raise ConfigurationError("INPUT_DEVICE must be zero or greater")
    return parsed


def _positive_float(name: str, default: float) -> float:
    value = _environment_value(name, str(default))
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number, got {value!r}") from error
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return parsed


def load_config() -> AppConfig:
    """Load configuration from environment variables and project defaults."""

    _load_dotenv()
    mechanism_path = Path(_environment_value("ROBOT_MECHANISMS", "mechanisms.md")).expanduser()
    if not mechanism_path.is_absolute():
        mechanism_path = PROJECT_ROOT / mechanism_path
    mechanism_details = "Not configured yet"
    if mechanism_path.is_file():
        mechanism_details = mechanism_path.read_text(encoding="utf-8").strip() or "Not configured yet"
    team_path = Path(_environment_value("ROBOT_TEAM_PROFILE", "team.md")).expanduser()
    if not team_path.is_absolute():
        team_path = PROJECT_ROOT / team_path
    team_details = "Not configured yet"
    if team_path.is_file():
        team_details = team_path.read_text(encoding="utf-8").strip() or "Not configured yet"

    vosk_model_path = Path(
        _environment_value(
            "VOSK_MODEL_PATH", str(PROJECT_ROOT / "vosk-model-small-en-us-0.15")
        )
    ).expanduser()
    if not vosk_model_path.is_absolute():
        vosk_model_path = PROJECT_ROOT / vosk_model_path

    return AppConfig(
        robot=RobotProfile(
            name=_environment_value("ROBOT_NAME", "Nova"),
            team=_environment_value("ROBOT_TEAM", "XXXX"),
            year=_positive_integer("ROBOT_YEAR", 2027),
            mechanism_details=mechanism_details,
            team_details=team_details,
            tone=_environment_value(
                "ROBOT_TONE",
                "concise, informative, enthusiastic, and conversational",
            ),
        ),
        ollama_host=_environment_value("OLLAMA_HOST", "http://127.0.0.1:11434"),
        ollama_model=_environment_value("OLLAMA_MODEL", "qwen2.5:1.5b"),
        vosk_model_path=vosk_model_path,
        input_sample_rate=_sample_rate(),
        input_device=_optional_device(),
        audio_input_timeout_seconds=_positive_float("AUDIO_INPUT_TIMEOUT_SECONDS", 30.0),
        tts_backend=_environment_value("TTS_BACKEND", "espeak").lower(),
        tts_voice=_environment_value("TTS_VOICE", "en-us"),
        tts_speed=_positive_integer("TTS_SPEED", 155),
        log_level=_environment_value("LOG_LEVEL", "INFO").upper(),
        max_history_messages=_positive_integer("MAX_HISTORY_MESSAGES", 12),
        max_profile_words=_positive_integer(
            "MAX_PROFILE_WORDS", RECOMMENDED_MAX_PROFILE_WORDS
        ),
        max_mechanism_words=_positive_integer(
            "MAX_MECHANISM_WORDS", RECOMMENDED_MAX_MECHANISM_WORDS
        ),
        max_team_words=_positive_integer("MAX_TEAM_WORDS", RECOMMENDED_MAX_TEAM_WORDS),
    )


def validate_startup(
    config: AppConfig,
    *,
    voice_mode: bool = False,
    executable_lookup=shutil.which,
) -> tuple[str, ...]:
    """Return actionable startup problems for the selected application mode."""

    problems: list[str] = []
    model_path = config.vosk_model_path
    if not model_path.is_dir():
        problems.append(f"Vosk model directory does not exist: {model_path}")
    elif not (model_path / "am" / "final.mdl").is_file():
        problems.append(f"Vosk model appears incomplete: {model_path}")

    if config.robot.mechanism_details == "Not configured yet":
        mechanism_path = _environment_value("ROBOT_MECHANISMS", "mechanisms.md")
        problems.append(f"Mechanism profile is missing or empty: {mechanism_path}")
    elif len(config.robot.mechanism_details.split()) > config.max_mechanism_words:
        problems.append(
            "Mechanism profile exceeds the recommended limit of "
            f"{config.max_mechanism_words} words"
        )

    if config.robot.team_details == "Not configured yet":
        team_path = _environment_value("ROBOT_TEAM_PROFILE", "team.md")
        problems.append(f"Team profile is missing or empty: {team_path}")
    elif len(config.robot.team_details.split()) > config.max_team_words:
        problems.append(
            "Team profile exceeds the recommended limit of "
            f"{config.max_team_words} words"
        )

    profile_words = len(config.robot.mechanism_details.split()) + len(
        config.robot.team_details.split()
    )
    if profile_words > config.max_profile_words:
        problems.append(
            "Combined mechanism and team profiles exceed the maximum of "
            f"{config.max_profile_words} words"
        )

    if executable_lookup("ollama") is None:
        problems.append("Ollama executable was not found on PATH")

    if voice_mode:
        if executable_lookup("espeak-ng") is None and config.tts_backend == "espeak":
            problems.append("espeak-ng executable was not found on PATH")
        if config.tts_backend not in {"espeak", "piper"}:
            problems.append(f"Unsupported TTS backend: {config.tts_backend!r}")

    return tuple(problems)


def require_valid_startup(config: AppConfig, *, voice_mode: bool = False) -> None:
    """Raise one readable error when startup validation finds a problem."""

    problems = validate_startup(config, voice_mode=voice_mode)
    if problems:
        details = "\n".join(f"- {problem}" for problem in problems)
        raise ConfigurationError(f"Startup validation failed:\n{details}")


def profile_summary(profile: RobotProfile) -> str:
    """Return a compact, non-sensitive summary for startup logs."""

    status = "configured" if profile.mechanism_details != "Not configured yet" else "not configured"
    return f"{profile.name} | Team {profile.team} | {profile.year} | Mechanisms: {status}"


__all__: Iterable[str] = (
    "AppConfig",
    "ConfigurationError",
    "PROJECT_ROOT",
    "RECOMMENDED_MAX_PROFILE_WORDS",
    "RECOMMENDED_MAX_MECHANISM_WORDS",
    "RECOMMENDED_MAX_TEAM_WORDS",
    "RobotProfile",
    "load_config",
    "profile_summary",
    "require_valid_startup",
    "validate_startup",
)
