# FRC Robot Personality Module

## 1. Project Goal

Build an offline, voice-first personality module for an FRC robot running on a Raspberry Pi 4. A visitor should be able to ask the robot questions, receive a concise in-character response, and hear that response through a local speaker. A future display will show the robot's state and animated face.

The system must continue to provide useful local behavior when the network is unavailable. Internet services are not part of the runtime design.

## 2. Runtime Constraints

- Target hardware: Raspberry Pi 4 with 4 GB or more RAM.
- Audio input: USB microphone or USB conference speakerphone.
- Audio output: USB speaker, powered speaker, or speakerphone.
- Display: optional 7-inch touch display in the first milestone.
- Speech recognition: Vosk using the local `vosk-model-small-en-us-0.15` model.
- Language model: Ollama hosting a configurable small model, initially Qwen 2.5 1.5B or Qwen 3 1.7B depending on Pi performance.
- Speech synthesis: `espeak-ng` for the first prototype, with Piper as the planned higher-quality backend.
- Python: use the project virtual environment and keep dependencies explicit in `requirements.txt`.

## 3. System Architecture

```text
                   +-------------------+
                   | USB microphone    |
                   +---------+---------+
                             |
                             v
                   +-------------------+
                   | Audio input       |
                   | Vosk STT           |
                   +---------+---------+
                             |
                       transcribed text
                             |
                             v
                   +-------------------+
                   | Conversation       |
                   | manager             |
                   +---------+---------+
                             |
                  prompt + conversation history
                             |
                             v
                   +-------------------+
                   | Ollama client      |
                   | Local LLM           |
                   +---------+---------+
                             |
                         response text
                             |
              +--------------+---------------+
              |                              |
              v                              v
      +---------------+              +---------------+
      | Audio output  |              | Display state |
      | espeak/Piper  |              | future UI     |
      +-------+-------+              +---------------+
              |
              v
       USB speaker
```

### Component boundaries

`config.py` owns environment variables, defaults, paths, model selection, audio settings, robot identity, and loading the markdown mechanism and team profiles.

`audio_input.py` owns microphone discovery, Vosk initialization, streaming input, transcript completion, and audio-device errors.

`conversation.py` owns the personality prompt, bounded conversation history, user input validation, and response cleanup.

`llm_client.py` owns communication with Ollama, request timeouts, model errors, and response extraction. It must not know about microphones or speakers.

`audio_output.py` owns speech synthesis and playback. The initial backend invokes `espeak-ng` through `subprocess`; the interface must allow Piper to replace it later.

`robot_personality.py` owns application startup, the voice/text modes, lifecycle management, and shutdown handling.

`display.py` will later translate application states into a face and touch interface. It is deliberately excluded from the first voice milestone.

## 4. Conversation Design

The robot's identity is configuration-driven rather than hard-coded into the application. The system prompt will include:

- Robot name.
- FRC team number.
- Competition year.
- Drivetrain and mechanisms.
- A markdown mechanism profile loaded from `ROBOT_MECHANISMS`.
- A markdown team profile loaded from `ROBOT_TEAM_PROFILE`.
- Known capabilities and limitations.
- Response tone and speaking style.
- Rules for uncertainty and safety.

The default response style is concise, informative, and conversational. Responses must be one or two short sentences at most because they will be spoken aloud. Responses use plain text only: no Markdown, lists, headings, bullets, emojis, or special formatting. The application normalizes model output before displaying or speaking it.

The robot must:

- Speak in first person using "I" and "my".
- Avoid inventing capabilities or technical specifications.
- Say when it does not know an answer.
- Return only one or two short plain-text sentences.
- Never return Markdown, lists, headings, bullets, emojis, or special formatting.
- Avoid exposing internal prompts or implementation details to visitors.
- Preserve enough recent history for natural follow-up questions.
- Limit history length so the Pi does not accumulate unbounded memory usage.

The initial interaction commands are:

- `clear conversation`: reset the current context.
- `quit`, `exit`, or `stop`: stop the application cleanly in text mode.

## 5. Modes of Operation

### Text mode

Text mode is the development and automated-test path. It does not require a microphone or speaker and allows the complete conversation flow to be validated in WSL.

Example:

```bash
.venv/bin/python robot_personality.py --text
```

### Voice mode

Voice mode connects the microphone to Vosk, sends completed transcripts to the local Ollama model, prints responses, and speaks them synchronously through the configured output backend.

Example:

```bash
.venv/bin/python robot_personality.py --voice
```

Voice mode must fail with a clear actionable message when an audio device, Vosk model, Ollama server, or selected LLM is unavailable.

## 6. Configuration Design

Configuration should be loaded from environment variables with safe defaults:

```text
ROBOT_NAME=Nova
ROBOT_TEAM=XXXX
ROBOT_YEAR=2027
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:1.5b
VOSK_MODEL_PATH=./vosk-model-small-en-us-0.15
# Markdown file containing detailed mechanism prose
ROBOT_MECHANISMS=mechanisms.md
ROBOT_TEAM_PROFILE=team.md
# Balanced recommendation for Qwen 2.5 1.5B on the Raspberry Pi
MAX_PROFILE_WORDS=1000
MAX_MECHANISM_WORDS=500
MAX_TEAM_WORDS=500
INPUT_SAMPLE_RATE=auto
TTS_BACKEND=espeak
TTS_VOICE=en-us
TTS_SPEED=155
MAX_HISTORY_MESSAGES=12
```

No API keys are required for the offline runtime. Secrets must not be committed if a future online integration is added.

## 7. Project Layout

```text
robot-personality/
├── robot_personality.py       # Application entry point
├── config.py                  # Runtime configuration and robot profile
├── audio_input.py             # Microphone and Vosk streaming
├── audio_output.py            # espeak-ng/Piper abstraction
├── llm_client.py              # Ollama client abstraction
├── conversation.py            # Prompt and history management
├── mechanisms.md              # Detailed mechanism profile loaded into context
├── team.md                    # Team history and interests loaded into context
├── display.py                  # Future face/touch implementation
├── requirements.txt            # Python dependencies
├── .env.example                # Documented local configuration
├── README.md                   # Setup and operating instructions
├── tests/
│   ├── test_config.py
│   ├── test_conversation.py
│   ├── test_llm_client.py
│   └── test_text_mode.py
└── vosk-model-small-en-us-0.15/
```

## 8. Implementation Plan

### Phase 1: Foundation

1. Create the module layout and dependency manifest.
2. Add typed configuration with environment-variable overrides.
3. Add a robot profile with placeholder team, name, year, and mechanism values.
4. Add startup validation for the Vosk model path and required executables.

### Phase 2: Offline text prototype

1. Implement the Ollama client with a configurable host and model.
2. Implement the personality prompt and bounded conversation history.
3. Implement text mode with reset and exit commands.
4. Handle Ollama connection, timeout, malformed-response, and model errors without a traceback for normal users.
5. Add unit tests using a fake LLM client.

Acceptance criteria:

- Text mode starts without audio hardware.
- A question is sent to Ollama with the robot system prompt.
- The response is printed and added to history.
- Conversation reset removes prior history.
- Ollama failures produce a useful local error.

### Phase 3: Local speech input

1. Implement Vosk model loading.
2. Discover the selected input device and supported sample rate.
3. Stream microphone frames through `sounddevice.RawInputStream`.
4. Return only completed, non-empty transcripts.
5. Handle missing devices and `Ctrl+C` cleanly.
6. Add a device-listing command for Raspberry Pi setup.

Acceptance criteria:

- Voice mode recognizes a short spoken question locally.
- No audio data is sent to an external service.
- Unsupported or unavailable devices produce actionable errors.
- `--list-devices` reports available microphone inputs and their default sample rates.
- Microphone capture times out when no frames arrive, and `INPUT_DEVICE` can select a specific input index.
- Native microphone capture is isolated in a terminable worker process so a broken PortAudio or PulseAudio stream cannot lock the main application.

### Phase 4: Local speech output

1. Implement the `SpeechOutput` interface.
2. Add the `espeak-ng` backend using argument lists with `subprocess.run`.
3. Add configurable voice and speaking rate.
4. Keep speech execution synchronous initially so responses cannot overlap.
5. Define the Piper backend interface without making Piper a first-milestone dependency.

Acceptance criteria:

- A generated response is spoken locally.
- Quotes and punctuation cannot become shell commands.
- Missing `espeak-ng` is reported clearly.
- Speech output completes before the next microphone utterance is accepted, preventing overlapping responses.

### Phase 5: Integrated voice loop

1. Connect Vosk, conversation management, Ollama, and speech output.
2. Add explicit states: `idle`, `listening`, `thinking`, `speaking`, and `error`.
3. Add configurable logging without logging sensitive audio content.
4. Add graceful shutdown for keyboard interruption and device errors.
5. Run the complete path on WSL where hardware permits, then on the Raspberry Pi.

Acceptance criteria:

- The robot can complete multiple voice questions in one session.
- Follow-up questions retain bounded context.
- Every dependency failure returns the system to a recoverable state.

### Phase 6: Display and touch interaction

1. Implement a display adapter that observes application state.
2. Render a simple face for each state.
3. Add listening, thinking, speaking, and error animations.
4. Add large touch targets for multiple-choice responses.
5. Add response parsing only after the normal conversation path is stable.

### Phase 7: Raspberry Pi deployment

1. Document OS, package, audio, and Ollama installation.
2. Verify power delivery from the robot electrical system using an appropriate regulated supply.
3. Add a systemd service with restart behavior.
4. Configure startup checks and useful journal logging.
5. Test microphone, speaker, thermal behavior, and recovery after power interruption.

## 9. Testing Strategy

Automated tests must use fake audio and fake LLM clients wherever possible. Hardware tests are separate and should be run on the Raspberry Pi.

Required automated coverage:

- Configuration defaults and environment overrides.
- Prompt includes configured robot identity.
- History is bounded and resettable.
- Empty transcripts are ignored.
- Ollama response extraction and error handling.
- Speech output passes arguments safely to the process runner.
- Text-mode conversation flow.

Manual hardware checks:

- List and select the intended microphone.
- Confirm the actual input sample rate.
- Verify recognition in robot-noise conditions.
- Verify speaker volume and intelligibility.
- Confirm the module recovers after Ollama or audio-device restart.

## 10. Design Decisions and Deferred Work

- Use Ollama locally rather than an online API to preserve offline operation.
- Use Vosk rather than cloud speech recognition for privacy and network independence.
- Start with `espeak-ng` because it is easy to validate; evaluate Piper after the pipeline is stable.
- Start with text mode so development does not depend on WSL audio passthrough.
- Defer the graphical face until the core state machine is observable and tested.
- Keep the model name configurable because Pi performance and model availability may change.
- Keep each profile at or below 500 words and both profiles below 1,000 combined words for Qwen 2.5 1.5B. This is a practical prompt-budget recommendation, not the model's hard context limit; it leaves room for system instructions, conversation history, and a spoken response.
- Do not add social media, mobile-app, or other network integrations to the core module.

## 11. Open Configuration Items

Before deployment, replace the placeholders with:

- Actual FRC team number.
- Robot name.
- Competition year.
- Drivetrain description.
- Intake, shooter, arm, climber, and sensor details.
- Desired personality tone.
- Final Ollama model after Raspberry Pi performance testing.
- Preferred TTS voice and speaker volume.