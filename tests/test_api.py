"""
tests/test_api.py

Tests for the FastAPI /extract-actions endpoint.
The LLM (Ollama) is mocked — no server needed.
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import VALID_NOTES, INVALID_NOTES


# ─────────────────────────────────────────────────────────────────────────────
# Response-shape helper
# ─────────────────────────────────────────────────────────────────────────────

def assert_valid_action_schema(action: dict):
    """Every action item must have exactly the three required string fields."""
    assert isinstance(action, dict), "Action item should be a dict"
    for field in ("task", "owner", "deadline"):
        assert field in action, f"Missing field: {field}"
        assert isinstance(action[field], str), f"Field '{field}' should be a string"
        assert action[field].strip() != "", f"Field '{field}' should not be blank"


# ─────────────────────────────────────────────────────────────────────────────
# Root endpoint sanity check
# ─────────────────────────────────────────────────────────────────────────────

class TestRootEndpoint:

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_message(self, client):
        data = response = client.get("/")
        assert "message" in response.json()



# Empty / blank input → 400 (no LLM call needed)


class TestEmptyInput:

    def test_empty_string_returns_400(self, client):
        resp = client.post("/extract-actions", json={"notes": ""})
        assert resp.status_code == 400

    def test_whitespace_only_returns_400(self, client):
        resp = client.post("/extract-actions", json={"notes": "   "})
        assert resp.status_code == 400

    def test_400_detail_message_present(self, client):
        resp = client.post("/extract-actions", json={"notes": ""})
        assert "detail" in resp.json()

    def test_missing_notes_key_returns_422(self, client):
        # Pydantic validation error — notes field required
        resp = client.post("/extract-actions", json={})
        assert resp.status_code == 422

# Valid notes → 200 + list of actions  (LLM mocked)


class TestValidNotes:

    @pytest.mark.parametrize("notes", VALID_NOTES)
    def test_valid_notes_return_200(self, client, mock_llm, notes):
        # Give the mock a plausible single-action response
        mock_llm('[{"task": "Fix the bug", "owner": "Raj", "deadline": "Friday"}]')
        resp = client.post("/extract-actions", json={"notes": notes})
        assert resp.status_code == 200

    @pytest.mark.parametrize("notes", VALID_NOTES)
    def test_valid_notes_response_has_actions_key(self, client, mock_llm, notes):
        mock_llm('[{"task": "Fix the bug", "owner": "Raj", "deadline": "Friday"}]')
        resp = client.post("/extract-actions", json={"notes": notes})
        assert "actions" in resp.json()

    @pytest.mark.parametrize("notes", VALID_NOTES)
    def test_valid_notes_actions_is_list(self, client, mock_llm, notes):
        mock_llm('[{"task": "Fix the bug", "owner": "Raj", "deadline": "Friday"}]')
        resp = client.post("/extract-actions", json={"notes": notes})
        assert isinstance(resp.json()["actions"], list)

    def test_multiple_actions_all_have_correct_schema(self, client, mock_llm):
        mock_llm(json.dumps([
            {"task": "Fix the bug", "owner": "Raj", "deadline": "Friday"},
            {"task": "Deploy hotfix", "owner": "Sarah", "deadline": "Monday"},
        ]))
        resp = client.post(
            "/extract-actions",
            json={"notes": "Raj will fix the bug by Friday. Sarah deploys Monday."},
        )
        assert resp.status_code == 200
        for action in resp.json()["actions"]:
            assert_valid_action_schema(action)

    def test_no_action_items_returns_empty_list(self, client, mock_llm):
        """General discussion notes → model returns [] → API returns []."""
        mock_llm("[]")
        resp = client.post(
            "/extract-actions",
            json={"notes": "We had a general discussion about company culture."},
        )
        assert resp.status_code == 200
        assert resp.json()["actions"] == []

    def test_unknown_owner_is_preserved(self, client, mock_llm):
        mock_llm('[{"task": "Update README", "owner": "Unknown", "deadline": "Not specified"}]')
        resp = client.post(
            "/extract-actions",
            json={"notes": "Someone needs to update the README before the sprint."},
        )
        assert resp.status_code == 200
        assert resp.json()["actions"][0]["owner"] == "Unknown"


# Invalid / gibberish notes → 400 or empty list  (LLM mocked)

class TestInvalidNotes:

    @pytest.mark.parametrize("notes", INVALID_NOTES)
    def test_invalid_notes_do_not_return_500(self, client, mock_llm, notes):
        """API should never crash with an unhandled 500 on bad input."""
        mock_llm("[]")
        resp = client.post("/extract-actions", json={"notes": notes})
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.parametrize("notes", INVALID_NOTES)
    def test_invalid_notes_never_hallucinate_actions(self, client, mock_llm, notes):
        """
        If the model returns [] for junk input, the API must echo that.
        Tests that the pipeline never invents tasks from garbage input.
        """
        mock_llm("[]")
        resp = client.post("/extract-actions", json={"notes": notes})
        if resp.status_code == 200:
            assert resp.json()["actions"] == [], (
                f"Hallucinated actions for invalid input: {notes[:80]!r}"
            )

    def test_xss_payload_is_safely_handled(self, client, mock_llm):
        mock_llm("[]")
        resp = client.post(
            "/extract-actions",
            json={"notes": "<script>alert('xss')</script>"},
        )
        assert resp.status_code in (200, 400)

    def test_very_long_repeated_char_handled(self, client, mock_llm):
        mock_llm("[]")
        resp = client.post("/extract-actions", json={"notes": "x" * 5000})
        assert resp.status_code in (200, 400)


# 
# LLM error handling — bad JSON from model
# 

class TestLLMErrorHandling:

    def test_invalid_json_from_model_returns_422(self, client, mock_llm):
        """If Ollama returns unparseable text, API should return 422."""
        mock_llm("Sorry, I cannot do that today.")
        resp = client.post(
            "/extract-actions",
            json={"notes": "Raj will fix the login bug by Friday."},
        )
        assert resp.status_code == 422

    def test_422_has_detail_field(self, client, mock_llm):
        mock_llm("not json at all {{{}}")
        resp = client.post(
            "/extract-actions",
            json={"notes": "Raj will fix the login bug by Friday."},
        )
        assert "detail" in resp.json()

    def test_model_returns_object_instead_of_array(self, client, mock_llm):
        """Model returns {} instead of [] → should raise 422."""
        mock_llm('{"task": "Fix bug"}')   # dict, not list
        resp = client.post(
            "/extract-actions",
            json={"notes": "Raj will fix the login bug by Friday."},
        )
        assert resp.status_code == 422

    def test_markdown_wrapped_json_is_handled(self, client, mock_llm):
        """clean_json_response should strip markdown fences cleanly."""
        mock_llm('```json\n[{"task":"Fix bug","owner":"Raj","deadline":"Friday"}]\n```')
        resp = client.post(
            "/extract-actions",
            json={"notes": "Raj will fix the login bug by Friday."},
        )
        assert resp.status_code == 200
        assert len(resp.json()["actions"]) == 1
