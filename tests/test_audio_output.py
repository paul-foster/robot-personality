import subprocess

import pytest

from audio_output import AudioOutputError, EspeakOutput, PiperOutput, create_speech_output


def test_espeak_uses_safe_argument_list_and_configured_voice_and_speed():
    calls = []
    speaker = EspeakOutput(
        voice="en-us",
        speed=170,
        executable_lookup=lambda _: "/usr/bin/espeak-ng",
        runner=lambda command, check: calls.append((command, check)),
    )

    speaker.speak("Hello; do not interpret this as a shell command.")

    assert calls == [
        (
            [
                "/usr/bin/espeak-ng",
                "-v",
                "en-us",
                "-s",
                "170",
                "Hello; do not interpret this as a shell command.",
            ],
            True,
        )
    ]


def test_empty_text_is_not_sent_to_espeak():
    calls = []
    speaker = EspeakOutput(
        executable_lookup=lambda _: "/usr/bin/espeak-ng",
        runner=lambda command, check: calls.append(command),
    )

    speaker.speak("  ")

    assert calls == []


def test_missing_espeak_is_reported():
    with pytest.raises(AudioOutputError, match="not found"):
        EspeakOutput(executable_lookup=lambda _: None)


def test_espeak_process_failure_is_translated():
    def failing_runner(command, check):
        raise subprocess.CalledProcessError(1, command)

    speaker = EspeakOutput(
        executable_lookup=lambda _: "/usr/bin/espeak-ng",
        runner=failing_runner,
    )

    with pytest.raises(AudioOutputError, match="exit code 1"):
        speaker.speak("hello")


def test_piper_boundary_is_explicit():
    with pytest.raises(AudioOutputError, match="not implemented"):
        PiperOutput().speak("hello")


def test_unknown_backend_is_rejected():
    with pytest.raises(AudioOutputError, match="Unsupported"):
        create_speech_output("unknown", "en-us", 155)