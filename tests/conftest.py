"""
conftest.py — Shared pytest fixtures for Smart Action Items test suite.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient



# App client fixture (no real Ollama needed — extractor is imported lazily)


@pytest.fixture(scope="session")
def client():
    """
    FastAPI TestClient. Imported here so that extractor.py's module-level
    OpenAI() call doesn't fail when Ollama is not running.
    """
    from main import app
    return TestClient(app)


# Helper: build a mock OpenAI-style completion response


def _mock_completion(json_text: str):
    """Return a mock object that looks like openai.ChatCompletion."""
    msg = MagicMock()
    msg.content = json_text

    choice = MagicMock()
    choice.message = msg

    completion = MagicMock()
    completion.choices = [choice]
    return completion


@pytest.fixture()
def mock_llm(monkeypatch):
    """
    Fixture that patches extractor.client.chat.completions.create so tests
    never call Ollama. Call it with the JSON string you want the model to
    return:

        def test_something(mock_llm):
            mock_llm('[{"task":"Fix bug","owner":"Raj","deadline":"Friday"}]')
            ...
    """
    calls = {}

    def _setup(json_response: str):
        completion = _mock_completion(json_response)
        mock = MagicMock(return_value=completion)
        monkeypatch.setattr("extractor.client.chat.completions.create", mock)
        calls["mock"] = mock
        return mock

    _setup.__dict__["calls"] = calls
    return _setup



# Shared test-data sets (used by both unit and integration tests)


VALID_NOTES = [
    pytest.param(
        "Raj will fix the login bug by Friday. Sarah needs to deploy the hotfix by Monday.",
        id="simple_two_assignees",
    ),
    pytest.param(
        "Someone needs to update the README documentation before the next sprint.",
        id="no_named_owner",
    ),
    pytest.param(
        "John will review the open pull requests soon.",
        id="vague_deadline",
    ),
    pytest.param(
        "Priya is responsible for writing unit tests, updating the API docs, and setting up CI/CD.",
        id="multiple_tasks_one_owner",
    ),
    pytest.param(
        "- Fix navbar alignment bug - Amit\n- Write migration script - due Thursday\n"
        "- Update environment variables\n- Schedule client demo - Neha - next Tuesday",
        id="bullet_points",
    ),
    pytest.param(
        "In today's standup Vikram is going to handle the payment gateway integration "
        "before sprint ends on the 30th. Nobody has picked up the logging task yet.",
        id="standup_mixed",
    ),
    pytest.param(
        "todo: deploy hotfix (urgent!!), ravi - check server logs tmrw, standup 10am fri",
        id="todo_style_messy",
    ),
    pytest.param(
        "We had a general discussion about company culture and team morale. "
        "Nothing specific was decided.",
        id="no_action_items",
    ),
    pytest.param(
        "Raj and Priya will co-own the dashboard redesign. Deadline is end of month.",
        id="co_owners",
    ),
    pytest.param(
        "Meeting notes 14th June:\n- Ankit: database backup script by Wednesday\n"
        "- Sneha will handle client onboarding emails\n\n"
        "Karan volunteered to look into search page performance but no deadline set.",
        id="meeting_notes_with_date",
    ),
    pytest.param(
        "The production server is down. DevOps team needs to fix it ASAP. Rohan is on it.",
        id="urgent_production",
    ),
    pytest.param(
        "Submit the quarterly report by 30/06. Meena owns this.",
        id="explicit_date",
    ),
    pytest.param(
        "Need to migrate the old database to PostgreSQL. Should be done by end of Q3.",
        id="no_owner_with_deadline",
    ),
    pytest.param(
        "jhon shuld reveiw the desgn mockups by next wendsday. sara wil update the stying",
        id="typos_misspellings",
    ),
    pytest.param(
        "Product sync - 3rd July\nDev team:\n- Rahul to finish search feature by July 10\n"
        "- Backend API optimisation - Suresh - July 15\nDesign:\n"
        "- Finalize mobile screens - Kavita - July 8\nQA:\n"
        "- Set up automated testing - Deepak - before release\n"
        "- Review test cases - Asha - ASAP",
        id="multi_team_structured",
    ),
    pytest.param(
        "Arjun: database indexing. Meera: frontend performance. Siddharth: API rate limiting.",
        id="colon_assignment_style",
    ),
    pytest.param(
        "I was thinking maybe someone should look into the memory leak issue? "
        "And the auth token expiry bug should also be fixed at some point.",
        id="vague_suggestions",
    ),
    pytest.param(
        "Deploy by 5pm today. Raj.",
        id="ultra_short",
    ),
    pytest.param(
        "Great meeting everyone! By the way, Nisha will prepare the investor deck by Thursday.",
        id="casual_with_action",
    ),
    pytest.param(
        "Bhai, Rohit ko Monday tak login page fix karni hai. Aur staging deploy karo jaldi.",
        id="hindi_mixed",
    ),
    pytest.param(
        "I had a call with Sahil and asked him to look into the PyTest issue. "
        "Next, I will connect with Aaysha and ask her to work on the PyPath issue. "
        "She has assured me that she will come back with the timeline by EOD.",
        id="narrator_i_style",
    ),
]

INVALID_NOTES = [
    pytest.param("", id="empty_string"),
    pytest.param("     ", id="whitespace_only"),
    pytest.param("@@### !!! $$$ ???", id="symbols_only"),
    pytest.param("1234567890", id="numbers_only"),
    pytest.param("Raj.", id="single_word_with_dot"),
    pytest.param("blah blah blah blah blah blah blah blah", id="filler_words"),
    pytest.param("x" * 5000, id="single_char_repeated_5000"),
    pytest.param("By Friday.", id="deadline_without_task"),
    pytest.param("<script>alert('xss')</script>", id="xss_payload"),
    pytest.param("🔥🚀💀❌✅🎯", id="emojis_only"),
]
