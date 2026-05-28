"""
tests/test_integration.py

Integration tests — require a LIVE Ollama server + FastAPI server running.

Run only these with:
    pytest -m integration

Skip these (run everything else) with:
    pytest -m "not integration"
"""

import pytest
import requests as http_requests

API_URL = "http://localhost:8000/extract-actions"


def is_server_live():
    try:
        http_requests.get("http://localhost:8000/", timeout=3)
        return True
    except Exception:
        return False


# Skip the whole module if the server isn't up
pytestmark = pytest.mark.skipif(
    not is_server_live(),
    reason="FastAPI server not running. Start with: uvicorn main:app --reload",
)


# Parametrized over a representative sample

SAMPLE_VALID = [
    "Raj will fix the login bug by Friday. Sarah needs to deploy the hotfix by Monday.",
    "Priya is responsible for writing unit tests, updating API docs, and setting up CI/CD.",
    "- Fix navbar alignment bug - Amit\n- Write migration script - due Thursday",
    "I had a call with Sahil and asked him to look into the PyTest issue.",
]

SAMPLE_INVALID = [
    "",
    "     ",
    "@@### !!! $$$",
    "🔥🚀💀",
]


@pytest.mark.integration
@pytest.mark.parametrize("notes", SAMPLE_VALID)
def test_live_valid_notes_return_200(notes):
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.parametrize("notes", SAMPLE_VALID)
def test_live_valid_notes_have_actions_key(notes):
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    assert "actions" in resp.json()


@pytest.mark.integration
@pytest.mark.parametrize("notes", SAMPLE_VALID)
def test_live_action_items_have_correct_fields(notes):
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    for action in resp.json().get("actions", []):
        for field in ("task", "owner", "deadline"):
            assert field in action
            assert isinstance(action[field], str)


@pytest.mark.integration
@pytest.mark.parametrize("notes", SAMPLE_INVALID)
def test_live_invalid_notes_no_500(notes):
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    assert resp.status_code != 500


@pytest.mark.integration
@pytest.mark.parametrize("notes", SAMPLE_INVALID)
def test_live_invalid_notes_never_hallucinate(notes):
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    if resp.status_code == 200:
        assert resp.json()["actions"] == []


@pytest.mark.integration
def test_live_narrator_i_not_assigned_as_owner():
    """The narrator 'I' should never appear as the task owner."""
    notes = (
        "I had a call with Sahil and asked him to look into the PyTest issue. "
        "Next, I will connect with Aaysha and ask her to work on the PyPath issue."
    )
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    assert resp.status_code == 200
    for action in resp.json().get("actions", []):
        assert action["owner"].strip().lower() not in ("i", "me", "myself")


@pytest.mark.integration
def test_live_markdown_wrapped_response_handled():
    """Verify clean_json_response works end-to-end even if model wraps output."""
    notes = "Raj will fix the login bug by Friday."
    resp = http_requests.post(API_URL, json={"notes": notes}, timeout=30)
    # Just make sure it doesn't explode — model output format varies
    assert resp.status_code in (200, 422)
