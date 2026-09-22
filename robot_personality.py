"""Entry point for the FRC robot personality module."""

from __future__ import annotations

import argparse
import logging
import sys
from enum import Enum
from typing import Callable

from audio_input import AudioInputError, VoskInput, format_input_devices, list_input_devices
from audio_output import AudioOutputError, SpeechOutput, create_speech_output
from config import ConfigurationError, load_config, profile_summary, require_valid_startup
from conversation import ConversationError, ConversationManager
from llm_client import LLMError, OllamaLLM

logger = logging.getLogger(__name__)


class VoiceState(str, Enum):
    """Observable states for the voice interaction loop."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline FRC robot personality module")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--text", action="store_true", help="start interactive text mode")
    mode.add_argument(
        "--text-speech",
        action="store_true",
        help="start text input mode with spoken responses",
    )
    mode.add_argument("--voice", action="store_true", help="start local microphone mode")
    mode.add_argument("--list-devices", action="store_true", help="list available input devices")
    return parser


def run_text_mode(
    conversation: ConversationManager,
    llm: OllamaLLM,
    *,
    input_fn=input,
    output_fn=print,
    speech_output: SpeechOutput | None = None,
) -> int:
    """Run the development-friendly text conversation loop."""

    if speech_output is None:
        output_fn("Robot personality text mode. Type 'quit' to exit.")
    else:
        output_fn("Robot personality text-to-speech mode. Type 'quit' to exit.")
    while True:
        try:
            user_text = input_fn("You: ")
        except EOFError:
            output_fn("Goodbye.")
            return 0

        command = user_text.strip().lower()
        if command in {"quit", "exit", "stop"}:
            output_fn("Goodbye.")
            return 0
        if command == "clear conversation":
            conversation.clear()
            output_fn("Conversation cleared.")
            continue
        if not user_text.strip():
            continue

        try:
            response = conversation.respond(user_text, llm)
        except (ConversationError, LLMError) as error:
            output_fn(f"Robot error: {error}")
            continue
        output_fn(f"Robot: {response}")
        if speech_output is not None:
            try:
                speech_output.speak(response)
            except AudioOutputError as error:
                logger.error("Speech output failed: %s", error)
                output_fn(f"Robot audio error: {error}")


def main(arguments: list[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    if options.list_devices:
        try:
            print(format_input_devices(list_input_devices()))
        except AudioInputError as error:
            print(error, file=sys.stderr)
            return 2
        return 0

    config = load_config()
    logging.basicConfig(level=getattr(logging, config.log_level, logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    voice_mode = options.voice
    text_speech_mode = options.text_speech

    try:
        require_valid_startup(config, voice_mode=voice_mode or text_speech_mode)
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 2

    print(f"Configuration is valid: {profile_summary(config.robot)}")
    if voice_mode:
        try:
            return run_voice_mode(
                ConversationManager(
                    profile=config.robot,
                    max_history_messages=config.max_history_messages,
                ),
                OllamaLLM(config.ollama_model, config.ollama_host),
                VoskInput(
                    config.vosk_model_path,
                    sample_rate=config.input_sample_rate,
                    device=config.input_device,
                    frame_timeout_seconds=config.audio_input_timeout_seconds,
                ),
                create_speech_output(
                    config.tts_backend,
                    config.tts_voice,
                    config.tts_speed,
                ),
            )
        except (AudioInputError, AudioOutputError) as error:
            print(f"Audio error: {error}", file=sys.stderr)
            return 2

    speech_output = None
    if text_speech_mode:
        try:
            speech_output = create_speech_output(
                config.tts_backend,
                config.tts_voice,
                config.tts_speed,
            )
        except AudioOutputError as error:
            print(f"Audio error: {error}", file=sys.stderr)
            return 2

    conversation = ConversationManager(
        profile=config.robot,
        max_history_messages=config.max_history_messages,
    )
    return run_text_mode(
        conversation,
        OllamaLLM(config.ollama_model, config.ollama_host),
        speech_output=speech_output,
    )


def run_voice_mode(
    conversation: ConversationManager,
    llm: OllamaLLM,
    audio_input: VoskInput,
    speech_output: SpeechOutput,
    *,
    output_fn=print,
    state_fn: Callable[[VoiceState], None] | None = None,
) -> int:
    """Transcribe local utterances and print responses until interrupted."""

    def set_state(state: VoiceState) -> None:
        logger.debug("Voice state: %s", state.value)
        if state_fn is not None:
            state_fn(state)

    output_fn("Robot personality voice mode. Press Ctrl+C to exit.")
    set_state(VoiceState.IDLE)
    try:
        while True:
            set_state(VoiceState.LISTENING)
            output_fn("Listening...")
            try:
                user_text = audio_input.listen_once()
            except AudioInputError as error:
                set_state(VoiceState.ERROR)
                logger.error("Audio input failed: %s", error)
                output_fn(f"Audio error: {error}")
                return 2
            if not user_text.strip():
                set_state(VoiceState.IDLE)
                continue
            output_fn(f"You: {user_text}")
            set_state(VoiceState.THINKING)
            try:
                response = conversation.respond(user_text, llm)
            except (ConversationError, LLMError) as error:
                set_state(VoiceState.ERROR)
                logger.error("Conversation failed: %s", error)
                output_fn(f"Robot error: {error}")
                continue
            output_fn(f"Robot: {response}")
            set_state(VoiceState.SPEAKING)
            try:
                speech_output.speak(response)
            except AudioOutputError as error:
                set_state(VoiceState.ERROR)
                logger.error("Speech output failed: %s", error)
                output_fn(f"Robot audio error: {error}")
            finally:
                set_state(VoiceState.IDLE)
    except KeyboardInterrupt:
        set_state(VoiceState.IDLE)
        logger.info("Voice mode stopped by keyboard interruption")
        output_fn("Goodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
