from config import RobotProfile
from conversation import ConversationManager
from robot_personality import VoiceState, run_voice_mode


class FakeAudioInput:
    def __init__(self):
        self.calls = 0

    def listen_once(self):
        self.calls += 1
        if self.calls == 1:
            return "hello robot"
        raise KeyboardInterrupt


class FakeLLM:
    def respond(self, messages):
        return "Hello from the robot."


class FakeSpeechOutput:
    def __init__(self):
        self.responses = []

    def speak(self, text):
        self.responses.append(text)


class OrderedAudioInput(FakeAudioInput):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def listen_once(self):
        self.events.append("listen")
        return super().listen_once()


class OrderedSpeechOutput(FakeSpeechOutput):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def speak(self, text):
        self.events.append("speak-start")
        super().speak(text)
        self.events.append("speak-complete")


def test_voice_mode_speaks_each_response_and_stops_cleanly():
    speech = FakeSpeechOutput()
    output = []

    result = run_voice_mode(
        ConversationManager(RobotProfile()),
        FakeLLM(),
        FakeAudioInput(),
        speech,
        output_fn=output.append,
    )

    assert result == 0
    assert speech.responses == ["Hello from the robot."]
    assert "Robot: Hello from the robot." in output
    assert output[-1] == "Goodbye."


def test_voice_mode_waits_for_speech_before_listening_again():
    events = []

    result = run_voice_mode(
        ConversationManager(RobotProfile()),
        FakeLLM(),
        OrderedAudioInput(events),
        OrderedSpeechOutput(events),
        output_fn=lambda _: None,
    )

    assert result == 0
    assert events == ["listen", "speak-start", "speak-complete", "listen"]


def test_voice_mode_reports_state_transitions():
    states = []

    result = run_voice_mode(
        ConversationManager(RobotProfile()),
        FakeLLM(),
        FakeAudioInput(),
        FakeSpeechOutput(),
        output_fn=lambda _: None,
        state_fn=states.append,
    )

    assert result == 0
    assert states == [
        VoiceState.IDLE,
        VoiceState.LISTENING,
        VoiceState.THINKING,
        VoiceState.SPEAKING,
        VoiceState.IDLE,
        VoiceState.LISTENING,
        VoiceState.IDLE,
    ]