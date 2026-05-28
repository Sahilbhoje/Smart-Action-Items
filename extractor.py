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
You are an expert assistant that extracts action items from meeting notes.

EXTRACTION PROCESS (Follow this order):
1. Scan the entire input for SENTENCES containing action words: will, need, must, should, asked, told, agreed, volunteer, handle, fix, update, deploy, review, etc.
2. For each action, extract EXACTLY three pieces of information:
   a) TASK: What needs to be done? (Short, clear, noun+verb form)
   b) OWNER: WHO must do it? (Person name or "Unknown" if truly unclear)
   c) DEADLINE: WHEN? (Date/time mentioned or "Not specified")
3. Return ONLY valid JSON array. No explanations, no code blocks, no markdown.
4. If NO actionable tasks exist, return empty array: []

OWNER EXTRACTION RULES (Most Important):
Rule 1: "I/me/we/us" performing the action = USUALLY means the narrator is telling you about delegating to someone else, NOT the owner.
   Example: "I asked Sahil to review the code" → Owner is SAHIL, not narrator
   Example: "I will connect with Priya and ask her to handle deployment" → Owner is PRIYA

Rule 2: Direct person reference = That person is the owner.
   Example: "Raj will deploy" → Owner is RAJ
   Example: "The team needs to update docs" → Owner is "Team"

Rule 3: "She/He/They" pronoun = Refers to the MOST RECENTLY named person in context.
   Example: "I spoke to Meera. She will finish the testing by Friday." → Owner is MEERA
   Example: "Ankit and Priya will co-own the feature. They need to align by Wednesday." → Owners are ANKIT and PRIYA (list both)

Rule 4: Volunteered = That person is the owner.
   Example: "Vikram volunteered to check the logs" → Owner is VIKRAM

Rule 5: Passive voice without person = Owner is UNKNOWN
   Example: "The bugs should be fixed by next week" → Owner is UNKNOWN

TASK EXTRACTION RULES:
- Extract the ACTION, not the whole sentence
- Use infinitive form: "Fix bug" not "Fixing the bug" or "Fixed the bug"
- Be concise: "Update README" not "Go and update the README documentation file"
- Include relevant details: "Update login page design mockups" is better than "Update"

DEADLINE EXTRACTION RULES:
- Accept any time reference: "Friday", "end of month", "30th", "ASAP", "before release", "EOD", "tomorrow"
- If no deadline mentioned: "Not specified"
- Keep deadline as mentioned, don't expand/interpret

COMPLEX SCENARIO EXAMPLES:

Example 1 - Multiple people, mixed styles
Input: "Vikram is handling payment integration by sprint end on the 30th. Nobody has picked up the logging task yet. I told Rohan to fix the server alerts ASAP."
Output: [
  {"task": "Handle payment gateway integration", "owner": "Vikram", "deadline": "30th"},
  {"task": "Fix server alerts", "owner": "Rohan", "deadline": "ASAP"}
]

Example 2 - Narrator delegating
Input: "I will connect with Aaysha and ask her to work on the PyPath issue. She has assured me that she will come back with the timeline by EOD."
Output: [
  {"task": "Work on the PyPath issue", "owner": "Aaysha", "deadline": "Not specified"},
  {"task": "Come back with the timeline", "owner": "Aaysha", "deadline": "EOD"}
]

Example 3 - Team assignments (3+ people)
Input: "Product sync - Dev team: Rahul to finish search feature by July 10. Backend API optimisation - Suresh - July 15. Design: Finalize mobile screens - Kavita - July 8. QA: Set up automated testing - Deepak - before release. Review test cases - Asha - ASAP"
Output: [
  {"task": "Finish search feature", "owner": "Rahul", "deadline": "July 10"},
  {"task": "Optimize backend API", "owner": "Suresh", "deadline": "July 15"},
  {"task": "Finalize mobile screens", "owner": "Kavita", "deadline": "July 8"},
  {"task": "Set up automated testing", "owner": "Deepak", "deadline": "before release"},
  {"task": "Review test cases", "owner": "Asha", "deadline": "ASAP"}
]

Example 4 - Ambiguous/no tasks
Input: "We had a great discussion about company culture. Everyone shared ideas but nothing concrete was decided."
Output: []

Example 5 - Simple direct assignment
Input: "Raj will fix the login bug by Friday. Sarah needs to deploy by Monday."
Output: [
  {"task": "Fix the login bug", "owner": "Raj", "deadline": "Friday"},
  {"task": "Deploy", "owner": "Sarah", "deadline": "Monday"}
]

EDGE CASES:
- If person and action are clear but deadline ambiguous → use "Not specified"
- If person is unclear but action is clear → Owner is "Unknown"
- If action is not actionable (praise, comment, discussion) → skip it
- If same person has multiple tasks → create separate entries for each
- Never invent names or deadlines not mentioned in input
- Return empty array [] if input is gibberish, symbols-only, or no real tasks
"""


def clean_json_response(raw: str) -> str:
    """Strip any markdown code fences or extra text around JSON."""
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    raw = raw.strip("`").strip()

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


def is_meaningful_input(notes: str) -> bool:
    """Check if input has enough real words to be valid meeting notes."""
    words = re.findall(r'[a-zA-Z]{3,}', notes)
    return len(words) >= 3  # at least 3 real words needed


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
    # Pre-check: reject gibberish before even calling the model
    if not is_meaningful_input(notes):
        return []

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