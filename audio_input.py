"""Local microphone input and Vosk speech-to-text integration."""

from __future__ import annotations

import json
import multiprocessing as mp
import queue
import sys
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sounddevice as sd
import vosk


class AudioInputError(RuntimeError):
    """Raised when microphone input cannot be initialized or read."""


@dataclass(frozen=True)
class InputDevice:
    """Human-readable information about an available input device."""

    index: int
    name: str
    max_input_channels: int
    default_sample_rate: int


def list_input_devices(query_devices: Callable[[], Iterable[Any]] = sd.query_devices) -> list[InputDevice]:
    """Return devices that expose at least one input channel."""

    devices: list[InputDevice] = []
    try:
        queried_devices = query_devices()
        for index, device in enumerate(queried_devices):
            input_channels = int(device.get("max_input_channels", 0))
            if input_channels <= 0:
                continue
            devices.append(
                InputDevice(
                    index=index,
                    name=str(device.get("name", f"Input device {index}")),
                    max_input_channels=input_channels,
                    default_sample_rate=int(float(device.get("default_samplerate", 16000))),
                )
            )
    except Exception as error:
        raise AudioInputError(f"Could not enumerate audio devices: {error}") from error
    return devices


def format_input_devices(devices: Iterable[InputDevice]) -> str:
    """Format input devices for the setup command and diagnostics."""

    device_list = list(devices)
    if not device_list:
        return "No input devices were found."
    return "\n".join(
        f"{device.index}: {device.name} ({device.default_sample_rate} Hz, "
        f"{device.max_input_channels} input channel(s))"
        for device in device_list
    )


class VoskInput:
    """Capture one completed utterance from a local microphone."""

    def __init__(
        self,
        model_path: Path,
        sample_rate: int | None = None,
        device: int | None = None,
        frame_timeout_seconds: float = 5.0,
        *,
        vosk_model_factory=vosk.Model,
        recognizer_factory=vosk.KaldiRecognizer,
        stream_factory=sd.RawInputStream,
    ) -> None:
        if not model_path.is_dir():
            raise AudioInputError(f"Vosk model directory does not exist: {model_path}")
        try:
            self._model = vosk_model_factory(str(model_path))
        except Exception as error:
            raise AudioInputError(f"Could not load Vosk model from {model_path}: {error}") from error

        self._sample_rate = sample_rate
        self._device = device
        if frame_timeout_seconds <= 0:
            raise AudioInputError("Audio frame timeout must be greater than zero")
        self._frame_timeout_seconds = frame_timeout_seconds
        self._recognizer_factory = recognizer_factory
        self._stream_factory = stream_factory

    def listen_once(self) -> str:
        """Block until Vosk returns an utterance or the input deadline expires."""

        # PortAudio is not safe to re-initialize from a forked child process; a
        # daemon thread preserves the timeout-based watchdog without tripping the
        # "PortAudio not initialized" startup failure seen with real devices.
        return self._listen_in_thread()

    def _listen_in_process(self) -> str:
        """Isolate the native audio backend so a wedged stream can be terminated."""

        context = mp.get_context("fork")
        result_queue = context.Queue(maxsize=1)
        worker = context.Process(
            target=self._capture_worker,
            args=(result_queue,),
            name="vosk-capture",
            daemon=True,
        )
        worker.start()
        try:
            result = result_queue.get(timeout=self._frame_timeout_seconds)
        except KeyboardInterrupt:
            worker.terminate()
            worker.join(timeout=1)
            raise
        except queue.Empty as error:
            worker.terminate()
            worker.join(timeout=1)
            selected_device = self._device if self._device is not None else "the default input"
            raise AudioInputError(
                f"Audio input did not become ready from {selected_device} "
                f"within {self._frame_timeout_seconds:g} seconds. "
                "Reconnect the microphone or set INPUT_DEVICE to a working input device."
            ) from error
        finally:
            if worker.is_alive():
                worker.terminate()
            worker.join(timeout=1)

        if isinstance(result, Exception):
            raise result
        return result

    def _listen_in_thread(self) -> str:
        """Run injected test backends without requiring process-safe objects."""

        result_queue: queue.Queue[str | Exception] = queue.Queue(maxsize=1)

        worker = threading.Thread(
            target=self._capture_worker,
            args=(result_queue,),
            name="vosk-capture",
            daemon=True,
        )
        worker.start()
        try:
            result = result_queue.get(timeout=self._frame_timeout_seconds)
        except KeyboardInterrupt:
            raise
        except queue.Empty as error:
            selected_device = self._device if self._device is not None else "the default input"
            raise AudioInputError(
                f"Audio input did not become ready from {selected_device} "
                f"within {self._frame_timeout_seconds:g} seconds. "
                "Reconnect the microphone or set INPUT_DEVICE to a working input device."
            ) from error

        if isinstance(result, Exception):
            raise result
        return result

    def _capture_worker(self, result_queue: queue.Queue[str | Exception]) -> None:
        """Run the backend call outside the interruptible application thread."""

        audio_queue: queue.Queue[bytes] = queue.Queue()
        try:
            input_info = sd.query_devices(self._device, "input")
            sample_rate = self._sample_rate or int(float(input_info["default_samplerate"]))
            recognizer = self._recognizer_factory(self._model, sample_rate)
            deadline = time.monotonic() + self._frame_timeout_seconds
            received_frame = False

            def callback(indata, frames, callback_time, status) -> None:
                if status:
                    print(status, file=sys.stderr)
                audio_queue.put(bytes(indata))

            with self._stream_factory(
                samplerate=sample_rate,
                blocksize=8000,
                device=self._device,
                dtype="int16",
                channels=1,
                callback=callback,
            ):
                while True:
                    remaining_seconds = deadline - time.monotonic()
                    if remaining_seconds <= 0:
                        selected_device = self._device if self._device is not None else "the default input"
                        message = (
                            f"No speech detected from {selected_device} "
                            if received_frame
                            else f"No microphone audio frames received from {selected_device} "
                        )
                        result_queue.put(
                            AudioInputError(
                                message
                                + f"within {self._frame_timeout_seconds:g} seconds. "
                                "Reconnect the microphone, speak closer to it, or set "
                                "INPUT_DEVICE to a working input device."
                            )
                        )
                        return
                    try:
                        data = audio_queue.get(timeout=remaining_seconds)
                    except queue.Empty as error:
                        selected_device = self._device if self._device is not None else "the default input"
                        message = (
                            f"No speech detected from {selected_device} "
                            if received_frame
                            else f"No microphone audio frames received from {selected_device} "
                        )
                        result_queue.put(
                            AudioInputError(
                                message
                                + f"within {self._frame_timeout_seconds:g} seconds. "
                                "Reconnect the microphone, speak closer to it, or set "
                                "INPUT_DEVICE to a working input device."
                            )
                        )
                        return
                    received_frame = True
                    if recognizer.AcceptWaveform(data):
                        text = _result_text(recognizer.Result())
                        if text:
                            result_queue.put(text)
                            return
        except KeyboardInterrupt:
            return
        except Exception as error:
            result_queue.put(AudioInputError(f"Microphone input failed: {error}"))


def _result_text(result: str | dict[str, Any]) -> str:
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return ""
    text = result.get("text", "") if isinstance(result, dict) else ""
    return text.strip() if isinstance(text, str) else ""


__all__ = [
    "AudioInputError",
    "InputDevice",
    "VoskInput",
    "format_input_devices",
    "list_input_devices",
]