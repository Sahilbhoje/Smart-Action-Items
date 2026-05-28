"""
tests/test_extractor_unit.py

Unit tests for extractor.py helper functions.
These tests do NOT require Ollama or a running server.
"""

import pytest
import sys
import os

# Allow importing from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from extractor import clean_json_response, validate_actions, is_meaningful_input



# is_meaningful_input


class TestIsMeaningfulInput:

    def test_valid_sentence_passes(self):
        assert is_meaningful_input("Raj will fix the bug") is True

    def test_empty_string_fails(self):
        assert is_meaningful_input("") is False

    def test_only_short_words_fails(self):
        # Words shorter than 3 chars are ignored by the regex [a-zA-Z]{3,}
        assert is_meaningful_input("a bb cc") is False

    def test_symbols_only_fails(self):
        assert is_meaningful_input("@@### !!! $$$") is False

    def test_numbers_only_fails(self):
        assert is_meaningful_input("1234567890") is False

    def test_emojis_only_fails(self):
        assert is_meaningful_input("🔥🚀💀") is False

    def test_three_real_words_passes(self):
        assert is_meaningful_input("Fix the bug") is True

    def test_exactly_two_real_words_fails(self):
        assert is_meaningful_input("Fix bug") is False

    def test_mixed_noise_with_real_words_passes(self):
        assert is_meaningful_input("@@@  Fix the bug @@@") is True

    def test_repeated_single_char_fails(self):
        assert is_meaningful_input("x" * 5000) is False


# clean_json_response

class TestCleanJsonResponse:

    def test_plain_json_array(self):
        raw = '[{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}]'
        result = clean_json_response(raw)
        assert result.startswith("[")

    def test_strips_markdown_json_fence(self):
        raw = '```json\n[{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}]\n```'
        result = clean_json_response(raw)
        assert "```" not in result
        assert result.startswith("[")

    def test_strips_plain_code_fence(self):
        raw = '```\n[{"task": "Deploy", "owner": "Sarah", "deadline": "Monday"}]\n```'
        result = clean_json_response(raw)
        assert "```" not in result

    def test_raises_if_no_array(self):
        with pytest.raises(ValueError, match="No JSON array found"):
            clean_json_response("Here is your answer: nothing here.")

    def test_fixes_missing_closing_bracket(self):
        # Truncated response — missing the closing ]
        raw = '[{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}'
        result = clean_json_response(raw)
        assert result.endswith("]")

    def test_fixes_trailing_comma_before_close(self):
        raw = '[{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"},'
        result = clean_json_response(raw)
        assert result.endswith("]")
        assert not result.rstrip().endswith(",]")

    def test_empty_array_passes_through(self):
        result = clean_json_response("[]")
        assert result == "[]"

    def test_leading_text_before_array_stripped(self):
        raw = 'Here are the action items:\n[{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}]'
        result = clean_json_response(raw)
        assert result.startswith("[")


# validate_actions

class TestValidateActions:

    def test_complete_item_passes_through(self):
        items = [{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}]
        result = validate_actions(items)
        assert result == [{"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}]

    def test_missing_owner_defaults_to_unknown(self):
        items = [{"task": "Fix bug", "deadline": "Friday"}]
        result = validate_actions(items)
        assert result[0]["owner"] == "Unknown"

    def test_missing_deadline_defaults_to_not_specified(self):
        items = [{"task": "Fix bug", "owner": "Raj"}]
        result = validate_actions(items)
        assert result[0]["deadline"] == "Not specified"

    def test_missing_task_defaults_to_unknown_task(self):
        items = [{"owner": "Raj", "deadline": "Friday"}]
        result = validate_actions(items)
        assert result[0]["task"] == "Unknown task"

    def test_empty_owner_string_becomes_unknown(self):
        items = [{"task": "Fix bug", "owner": "", "deadline": "Friday"}]
        result = validate_actions(items)
        assert result[0]["owner"] == "Unknown"

    def test_empty_deadline_string_becomes_not_specified(self):
        items = [{"task": "Fix bug", "owner": "Raj", "deadline": ""}]
        result = validate_actions(items)
        assert result[0]["deadline"] == "Not specified"

    def test_whitespace_stripped_from_values(self):
        items = [{"task": "  Fix bug  ", "owner": "  Raj  ", "deadline": "  Friday  "}]
        result = validate_actions(items)
        assert result[0] == {"task": "Fix bug", "owner": "Raj", "deadline": "Friday"}

    def test_multiple_items_all_validated(self):
        items = [
            {"task": "Task A", "owner": "Alice", "deadline": "Monday"},
            {"task": "Task B"},
        ]
        result = validate_actions(items)
        assert len(result) == 2
        assert result[1]["owner"] == "Unknown"
        assert result[1]["deadline"] == "Not specified"

    def test_empty_list_returns_empty_list(self):
        assert validate_actions([]) == []
