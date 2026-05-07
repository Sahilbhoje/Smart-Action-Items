"""
extractor.py - Handles communication with Ollama and parses action items from meeting notes.
"""

import json
import re
from openai import OpenAI

OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL = "llama3.2:1b"

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

system_prompt = """
You are an assistant that extracts action items from meeting notes.

STRICT RULES:
1. Return ONLY a valid JSON array. No explanation. No markdown. No code blocks.
2. Each item must have exactly these fields:
   - "task": extracted directly from the notes
   - "owner": person mentioned in the notes, or "Unknown" if not mentioned
   - "deadline": deadline mentioned in the notes, or "Not specified" if not mentioned
3. If the input has NO actionable tasks, return an empty array: []
4. NEVER invent, assume, or hallucinate tasks, owners, or deadlines not present in the input.
5. If input is gibberish, symbols, numbers, or small talk with no tasks → return []
6. Only extract tasks that are EXPLICITLY stated in the notes.
7. Do not add example tasks like "Follow up on invoices" or "Update website" unless they are in the notes.

Output format:
[
  {"task": "...", "owner": "...", "deadline": "..."}
]

If nothing actionable: []
"""

def clean_json_response(raw: str) -> str:
    """Strip any markdown code fences or extra text around JSON."""
    # Remove ```json ... ``` or ``` ... ```
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    raw = raw.strip("`").strip()

    # Find the start of the JSON array
    start = raw.find("[")
    if start == -1:
        raise ValueError(f"No JSON array found in response: {raw}")
    
    raw = raw[start:]
    stripped = raw.rstrip()

    # Fix truncated response - if closing ] is missing, add it
    if not stripped.endswith("]"):
        if stripped.endswith(","):
            stripped = stripped[:-1]          # remove trailing comma
        if not stripped.endswith("}"):
            stripped += "}"                   # close open object
        stripped += "\n]"                     # close the array

    return stripped

def validate_actions(actions: list) -> list:
    """Ensure each action item has the required fields."""
    validated = []
    for item in actions:
        validated.append({
            "task": str(item.get("task", "Unknown task")).strip(),
            "owner": str(item.get("owner", "Unknown")).strip() or "Unknown",
            "deadline": str(item.get("deadline", "Not specified")).strip() or "Not specified",
        })
    return validated


def extract_actions(notes: str) -> list:
    """
    Send meeting notes to Ollama and return structured action items.

    Args:
        notes: Raw meeting notes string

    Returns:
        List of dicts with keys: task, owner, deadline

    Raises:
        ValueError: If the AI response cannot be parsed as JSON
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract action items from these meeting notes:\n\n{notes}"}
        ],
        temperature=0.1,  # low temperature = more consistent/predictable output
    )

    raw = response.choices[0].message.content.strip()

    try:
        cleaned = clean_json_response(raw)
        actions = json.loads(cleaned)
        if not isinstance(actions, list):
            raise ValueError("Response is not a list")
        return validate_actions(actions)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from model: {raw}. Error: {e}")
def is_meaningful_input(notes: str) -> bool:
    """Check if input has enough real words to be valid meeting notes."""
    # Remove symbols and numbers, check if real words remain
    words = re.findall(r'[a-zA-Z]{3,}', notes)
    return len(words) >= 3  # at least 3 real words needed


def extract_actions(notes: str) -> list:
    # Pre-check: reject gibberish before even calling the model
    if not is_meaningful_input(notes):
        return []

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract action items from these meeting notes:\n\n{notes}"}
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()

    try:
        cleaned = clean_json_response(raw)
        actions = json.loads(cleaned)
        if not isinstance(actions, list):
            raise ValueError("Response is not a list")
        return validate_actions(actions)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from model: {raw}. Error: {e}")
 