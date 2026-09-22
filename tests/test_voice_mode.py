from config import RobotProfile
from conversation import ConversationManager
from robot_personality import run_voice_mode


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