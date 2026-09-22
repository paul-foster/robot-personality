"""Local speech synthesis backends."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence


class AudioOutputError(RuntimeError):
    """Raised when a response cannot be spoken locally."""


class SpeechOutput:
    """Interface implemented by local speech synthesis backends."""

    def speak(self, text: str) -> None:
        raise NotImplementedError


class EspeakOutput(SpeechOutput):
    """Synchronous espeak-ng speech output using a safe argument list."""

    def __init__(
        self,
        voice: str = "en-us",
        speed: int = 155,
        *,
        executable_lookup=shutil.which,
        runner=subprocess.run,
        executable: str | None = None,
    ) -> None:
        if speed <= 0:
            raise AudioOutputError("TTS speed must be greater than zero")
        resolved_executable = executable or executable_lookup("espeak-ng")
        if resolved_executable is None:
            raise AudioOutputError("espeak-ng executable was not found on PATH")
        self.voice = voice
        self.speed = speed
        self._executable = resolved_executable
        self._runner = runner

    def speak(self, text: str) -> None:
        cleaned_text = text.strip()
        if not cleaned_text:
            return
        command = [
            self._executable,
            "-v",
            self.voice,
            "-s",
            str(self.speed),
            cleaned_text,
        ]
        try:
            self._runner(command, check=True)
        except subprocess.CalledProcessError as error:
            raise AudioOutputError(f"espeak-ng failed with exit code {error.returncode}") from error
        except OSError as error:
            raise AudioOutputError(f"Could not start espeak-ng: {error}") from error


class PiperOutput(SpeechOutput):
    """Placeholder for the higher-quality Piper backend planned for later."""

    def speak(self, text: str) -> None:
        raise AudioOutputError("Piper speech output is not implemented yet")


def create_speech_output(backend: str, voice: str, speed: int) -> SpeechOutput:
    """Create the configured speech backend."""

    if backend == "espeak":
        return EspeakOutput(voice=voice, speed=speed)
    if backend == "piper":
        return PiperOutput()
    raise AudioOutputError(f"Unsupported TTS backend: {backend!r}")


__all__: Sequence[str] = (
    "AudioOutputError",
    "EspeakOutput",
    "PiperOutput",
    "SpeechOutput",
    "create_speech_output",
)