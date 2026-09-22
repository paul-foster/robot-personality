"""Entry point for the FRC robot personality module."""

from __future__ import annotations

import argparse
import sys

from audio_input import AudioInputError, VoskInput, format_input_devices, list_input_devices
from audio_output import AudioOutputError, SpeechOutput, create_speech_output
from config import ConfigurationError, load_config, profile_summary, require_valid_startup
from conversation import ConversationError, ConversationManager
from llm_client import LLMError, OllamaLLM


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline FRC robot personality module")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--text", action="store_true", help="start interactive text mode")
    mode.add_argument("--voice", action="store_true", help="start local microphone mode")
    mode.add_argument("--list-devices", action="store_true", help="list available input devices")
    return parser


def run_text_mode(
    conversation: ConversationManager,
    llm: OllamaLLM,
    *,
    input_fn=input,
    output_fn=print,
) -> int:
    """Run the development-friendly text conversation loop."""

    output_fn("Robot personality text mode. Type 'quit' to exit.")
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
    voice_mode = options.voice

    try:
        require_valid_startup(config, voice_mode=voice_mode)
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

    conversation = ConversationManager(
        profile=config.robot,
        max_history_messages=config.max_history_messages,
    )
    return run_text_mode(conversation, OllamaLLM(config.ollama_model, config.ollama_host))


def run_voice_mode(
    conversation: ConversationManager,
    llm: OllamaLLM,
    audio_input: VoskInput,
    speech_output: SpeechOutput,
    *,
    output_fn=print,
) -> int:
    """Transcribe local utterances and print responses until interrupted."""

    output_fn("Robot personality voice mode. Press Ctrl+C to exit.")
    try:
        while True:
            output_fn("Listening...")
            try:
                user_text = audio_input.listen_once()
            except AudioInputError as error:
                output_fn(f"Audio error: {error}")
                return 2
            output_fn(f"You: {user_text}")
            try:
                response = conversation.respond(user_text, llm)
            except (ConversationError, LLMError) as error:
                output_fn(f"Robot error: {error}")
                continue
            output_fn(f"Robot: {response}")
            try:
                speech_output.speak(response)
            except AudioOutputError as error:
                output_fn(f"Robot audio error: {error}")
    except KeyboardInterrupt:
        output_fn("Goodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
