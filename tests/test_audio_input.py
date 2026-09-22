from pathlib import Path

import pytest

import config
from audio_input import AudioInputError, InputDevice, VoskInput, _result_text, format_input_devices, list_input_devices


def test_list_input_devices_filters_output_only_devices():
    devices = list_input_devices(
        lambda: [
            {"name": "Speaker", "max_input_channels": 0, "default_samplerate": 48000},
            {"name": "Mic", "max_input_channels": 1, "default_samplerate": 16000},
        ]
    )

    assert devices == [InputDevice(1, "Mic", 1, 16000)]
    assert "1: Mic (16000 Hz" in format_input_devices(devices)


def test_empty_device_list_is_clear():
    assert format_input_devices([]) == "No input devices were found."


def test_load_config_uses_longer_default_audio_timeout(monkeypatch):
    monkeypatch.delenv("AUDIO_INPUT_TIMEOUT_SECONDS", raising=False)
    app_config = config.load_config()
    assert app_config.audio_input_timeout_seconds == 30.0


def test_result_text_accepts_vosk_json():
    assert _result_text('{"text": "  hello robot  "}') == "hello robot"
    assert _result_text('{"text": ""}') == ""


def test_missing_model_is_rejected(tmp_path):
    with pytest.raises(AudioInputError, match="does not exist"):
        VoskInput(tmp_path / "missing")


def test_non_positive_frame_timeout_is_rejected(tmp_path):
    model_path = tmp_path / "model"
    model_path.mkdir()
    with pytest.raises(AudioInputError, match="timeout"):
        VoskInput(
            model_path,
            frame_timeout_seconds=0,
            vosk_model_factory=lambda path: object(),
        )


def test_vosk_input_uses_device_rate_and_returns_completed_text(tmp_path):
    model_path = tmp_path / "model"
    model_path.mkdir()
    created = {}

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            created["sample_rate"] = sample_rate
            self.calls = 0

        def AcceptWaveform(self, data):
            self.calls += 1
            return self.calls == 1

        def Result(self):
            return '{"text": "hello robot"}'

    class FakeStream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]

        def __enter__(self):
            self.callback(b"audio", 1, None, None)
            return self

        def __exit__(self, *args):
            return False

    audio = VoskInput(
        model_path,
        frame_timeout_seconds=0.01,
        vosk_model_factory=lambda path: object(),
        recognizer_factory=FakeRecognizer,
        stream_factory=FakeStream,
    )

    # Patch only the device query used after model initialization.
    import audio_input
    original_query = audio_input.sd.query_devices
    audio_input.sd.query_devices = lambda device, kind: {"default_samplerate": 22050}
    try:
        assert audio.listen_once() == "hello robot"
    finally:
        audio_input.sd.query_devices = original_query

    assert created["sample_rate"] == 22050


def test_vosk_input_fails_when_stream_produces_no_frames(tmp_path):
    model_path = tmp_path / "model"
    model_path.mkdir()

    class SilentStream:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            pass

    audio = VoskInput(
        model_path,
        frame_timeout_seconds=0.01,
        vosk_model_factory=lambda path: object(),
        recognizer_factory=FakeRecognizer,
        stream_factory=SilentStream,
    )

    import audio_input
    original_query = audio_input.sd.query_devices
    audio_input.sd.query_devices = lambda device, kind: {"default_samplerate": 16000}
    try:
        with pytest.raises(AudioInputError, match="No microphone audio frames received"):
            audio.listen_once()
    finally:
        audio_input.sd.query_devices = original_query


def test_vosk_input_fails_when_stream_only_produces_unrecognized_audio(tmp_path):
    model_path = tmp_path / "model"
    model_path.mkdir()

    class SilentStream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]

        def __enter__(self):
            self.callback(b"silence", 1, None, None)
            return self

        def __exit__(self, *args):
            return False

    class NeverCompleteRecognizer:
        def __init__(self, model, sample_rate):
            pass

        def AcceptWaveform(self, data):
            return False

    audio = VoskInput(
        model_path,
        frame_timeout_seconds=0.01,
        vosk_model_factory=lambda path: object(),
        recognizer_factory=NeverCompleteRecognizer,
        stream_factory=SilentStream,
    )

    import audio_input
    original_query = audio_input.sd.query_devices
    audio_input.sd.query_devices = lambda device, kind: {"default_samplerate": 16000}
    try:
        with pytest.raises(AudioInputError, match="No speech detected"):
            audio.listen_once()
    finally:
        audio_input.sd.query_devices = original_query