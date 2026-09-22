from config import RobotProfile
from conversation import ConversationManager
from robot_personality import run_text_mode


class FakeLLM:
    def respond(self, messages):
        return "I am ready to help."


def test_text_mode_handles_clear_and_exit_commands():
    conversation = ConversationManager(RobotProfile())
    inputs = iter(["hello", "clear conversation", "quit"])
    output = []

    result = run_text_mode(conversation, FakeLLM(), input_fn=lambda _: next(inputs), output_fn=output.append)

    assert result == 0
    assert "Robot: I am ready to help." in output
    assert "Conversation cleared." in output
    assert output[-1] == "Goodbye."
    assert conversation.history_length == 0