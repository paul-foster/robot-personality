# FRC Robot Personality Module

Offline voice personality module for an FRC robot. Phase 1 established typed configuration and startup validation. Phase 2 added the local Ollama conversation client, robot personality prompt, bounded conversation history, and text mode. Phase 3 added local Vosk microphone transcription. Phase 4 adds synchronous local speech output through `espeak-ng`.

## Current setup

The project expects a Python virtual environment at `.venv/` and a Vosk model directory at `vosk-model-small-en-us-0.15/`.

Run text mode with:

```bash
.venv/bin/python robot_personality.py --text
```

Ask a question, then use `clear conversation` to reset context or `quit` to exit. Ollama must be installed, running locally, and have the configured model available.

List available microphone and audio input devices with:

```bash
.venv/bin/python robot_personality.py --list-devices
```

Start local voice transcription with:

```bash
.venv/bin/python robot_personality.py --voice
```

Voice mode listens for a completed utterance, sends the transcript through the same conversation path as text mode, prints the robot response, and speaks it synchronously. Responses are limited to two short plain-text sentences; Markdown, lists, and special formatting are removed before display and speech. Press `Ctrl+C` to exit. Configure `TTS_BACKEND`, `TTS_VOICE`, and `TTS_SPEED` in `.env`. Piper remains a future backend.

If no microphone is connected, voice mode stops after `AUDIO_INPUT_TIMEOUT_SECONDS` instead of waiting forever. Native audio capture runs in a terminable worker process, so a broken PortAudio or PulseAudio stream cannot lock the terminal. Use `--list-devices` to find a working input index, then set `INPUT_DEVICE` in `.env`; use `default` to let the audio system choose.

## Configuration

Copy `.env.example` to `.env` for a documented starting point. The application loads `.env` automatically without overriding values already exported by the shell.

Important settings include `ROBOT_NAME`, `ROBOT_TEAM`, `ROBOT_MECHANISMS`, `OLLAMA_MODEL`, and `VOSK_MODEL_PATH`.

`ROBOT_MECHANISMS` points to a Markdown file rather than a comma-separated list. `ROBOT_TEAM_PROFILE` points to a second Markdown file describing team history, interests, traditions, and passions. Both complete files are included in the robot's system prompt at startup.

For the selected Qwen 2.5 1.5B model, use the balanced defaults of 500 words per file and 1,000 words combined. This is a practical prompt-budget limit that leaves room for instructions, conversation history, and a spoken response. The application rejects missing, oversized, or over-budget profiles at startup.

Example:

```text
ROBOT_MECHANISMS=mechanisms.md
ROBOT_TEAM_PROFILE=team.md
MAX_PROFILE_WORDS=1000
MAX_MECHANISM_WORDS=500
MAX_TEAM_WORDS=500
```

Relative paths are resolved from the project root. Missing or oversized mechanism files fail startup validation with an actionable message.

## Tests

```bash
.venv/bin/python -m pytest
```

The test suite uses fake LLM clients for deterministic tests. The local integration path can be checked with:

```bash
printf 'Tell me about yourself\nquit\n' | .venv/bin/python robot_personality.py --text
```
