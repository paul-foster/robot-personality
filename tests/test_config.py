from pathlib import Path

import pytest

from config import ConfigurationError, load_config, validate_startup


def test_defaults_point_to_the_local_model(monkeypatch):
    monkeypatch.delenv("VOSK_MODEL_PATH", raising=False)
    monkeypatch.setenv("ROBOT_NAME", "Nova")

    config = load_config()

    assert config.vosk_model_path == Path(__file__).parents[1] / "vosk-model-small-en-us-0.15"
    assert config.robot.name == "Nova"
    assert config.input_sample_rate is None


def test_environment_overrides_are_typed(monkeypatch, tmp_path):
    monkeypatch.setenv("ROBOT_YEAR", "2028")
    mechanism_file = tmp_path / "mechanisms.md"
    mechanism_file.write_text("# Intake\nA floor intake collects game pieces.", encoding="utf-8")
    team_file = tmp_path / "team.md"
    team_file.write_text("The team enjoys mentoring and outreach.", encoding="utf-8")
    monkeypatch.setenv("ROBOT_MECHANISMS", str(mechanism_file))
    monkeypatch.setenv("ROBOT_TEAM_PROFILE", str(team_file))
    monkeypatch.setenv("INPUT_SAMPLE_RATE", "16000")
    monkeypatch.setenv("VOSK_MODEL_PATH", str(tmp_path))

    config = load_config()

    assert config.robot.year == 2028
    assert "floor intake collects game pieces" in config.robot.mechanism_details
    assert "mentoring and outreach" in config.robot.team_details
    assert config.input_sample_rate == 16000


def test_invalid_integer_is_rejected(monkeypatch):
    monkeypatch.setenv("ROBOT_YEAR", "not-a-year")

    with pytest.raises(ConfigurationError, match="ROBOT_YEAR"):
        load_config()


def test_startup_validation_reports_missing_model_and_tools(tmp_path):
    config = load_config()
    config = config.__class__(**{**config.__dict__, "vosk_model_path": tmp_path / "missing"})

    problems = validate_startup(config, voice_mode=True, executable_lookup=lambda _: None)

    assert any("Vosk model directory" in problem for problem in problems)
    assert "Ollama executable was not found on PATH" in problems
    assert "espeak-ng executable was not found on PATH" in problems


def test_startup_validation_reports_missing_mechanism_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("ROBOT_MECHANISMS", str(tmp_path / "missing.md"))
    config = load_config()

    problems = validate_startup(config, executable_lookup=lambda _: "/usr/bin/tool")

    assert any("Mechanism profile is missing" in problem for problem in problems)


def test_startup_validation_reports_oversized_mechanism_profile(monkeypatch, tmp_path):
    mechanism_file = tmp_path / "mechanisms.md"
    mechanism_file.write_text("word " * 4, encoding="utf-8")
    monkeypatch.setenv("ROBOT_MECHANISMS", str(mechanism_file))
    monkeypatch.setenv("MAX_MECHANISM_WORDS", "3")
    config = load_config()

    problems = validate_startup(config, executable_lookup=lambda _: "/usr/bin/tool")

    assert any("exceeds the recommended limit" in problem for problem in problems)


def test_startup_validation_reports_oversized_team_profile(monkeypatch, tmp_path):
    team_file = tmp_path / "team.md"
    team_file.write_text("word " * 4, encoding="utf-8")
    monkeypatch.setenv("ROBOT_TEAM_PROFILE", str(team_file))
    monkeypatch.setenv("MAX_TEAM_WORDS", "3")
    config = load_config()

    problems = validate_startup(config, executable_lookup=lambda _: "/usr/bin/tool")

    assert any("Team profile exceeds" in problem for problem in problems)


def test_startup_validation_reports_combined_profile_overflow(monkeypatch, tmp_path):
    mechanism_file = tmp_path / "mechanisms.md"
    mechanism_file.write_text("mechanism " * 3, encoding="utf-8")
    team_file = tmp_path / "team.md"
    team_file.write_text("team " * 3, encoding="utf-8")
    monkeypatch.setenv("ROBOT_MECHANISMS", str(mechanism_file))
    monkeypatch.setenv("ROBOT_TEAM_PROFILE", str(team_file))
    monkeypatch.setenv("MAX_PROFILE_WORDS", "5")
    config = load_config()

    problems = validate_startup(config, executable_lookup=lambda _: "/usr/bin/tool")

    assert any("Combined mechanism and team profiles" in problem for problem in problems)
