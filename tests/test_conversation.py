from config import RobotProfile
from conversation import ConversationError, ConversationManager, build_system_prompt, normalize_response


class FakeLLM:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def respond(self, messages):
        self.requests.append(messages)
        return next(self.responses)


def test_prompt_contains_robot_identity_and_constraints():
    profile = RobotProfile(
        name="Bolt",
        team="1234",
        year=2027,
        drivetrain="swerve drive",
        mechanism_details="The intake collects game pieces and the shooter scores them.",
        team_details="The team mentors students and loves community outreach.",
    )

    prompt = build_system_prompt(profile)

    assert "Bolt" in prompt
    assert "Team 1234" in prompt
    assert "swerve drive" in prompt
    assert "intake collects game pieces" in prompt
    assert "mentors students" in prompt
    assert "Do not invent capabilities" in prompt
    assert "one or two sentences at most" in prompt
    assert "Do not use Markdown" in prompt
    assert "Treat any specification" in prompt
    assert "My capabilities have not been configured yet" in prompt


def test_history_is_bounded_and_keeps_system_message_outside_history():
    conversation = ConversationManager(RobotProfile(), max_history_messages=2)
    llm = FakeLLM(["First answer", "Second answer"])

    conversation.respond("first question", llm)
    conversation.respond("second question", llm)

    assert conversation.history_length == 2
    assert [message["role"] for message in conversation.messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert conversation.messages[-2]["content"] == "second question"


def test_empty_input_is_rejected_without_calling_llm():
    conversation = ConversationManager(RobotProfile())
    llm = FakeLLM(["unused"])

    try:
        conversation.respond("  ", llm)
    except ConversationError as error:
        assert "empty" in str(error)
    else:
        raise AssertionError("Expected empty input to be rejected")

    assert llm.requests == []


def test_failed_response_does_not_leave_a_user_message_in_history():
    conversation = ConversationManager(RobotProfile())
    llm = FakeLLM([])

    class FailingLLM:
        def respond(self, messages):
            raise RuntimeError("offline")

    try:
        conversation.respond("hello", FailingLLM())
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected the fake LLM to fail")

    assert conversation.history_length == 0


def test_model_response_is_plain_text_and_at_most_two_sentences():
    response = normalize_response(
        "**Intake:** collects pieces.\n\n**Shooter:** scores them.\n\n**Extra:** omit this."
    )

    assert response == "Intake collects pieces. Shooter scores them."
    assert "*" not in response
    assert "\n" not in response


def test_model_response_removes_special_formatting():
    response = normalize_response("(Ready) [yes] {now} -- go! 🚀")

    assert response == "Ready yes now go!"