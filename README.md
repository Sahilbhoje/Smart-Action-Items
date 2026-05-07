# Smart Action Items

A FastAPI service that converts messy meeting notes into structured action items using a local LLM (Ollama + Llama 3.2).

---

## Setup

### 1. Install Ollama
Download from [ollama.com](https://ollama.com) and then pull the model:
```bash
ollama pull llama3.2:1b
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the API
```bash
uvicorn main:app --reload
```

API will be live at: `http://localhost:8000`

Interactive docs at: `http://localhost:8000/docs`

---

## Usage

### Endpoint
```
POST /extract-actions
```

### Request
```json
{
  "notes": "Raj will fix the login bug by Friday. Sarah needs to deploy by Monday."
}
```

### Response
```json
{
  "actions": [
    {
      "task": "Fix the login bug",
      "owner": "Raj",
      "deadline": "Friday"
    },
    {
      "task": "Deploy",
      "owner": "Sarah",
      "deadline": "Monday"
    }
  ]
}
```

---

## Example curl requests

**Example 1 - Clear notes:**
```bash
curl -X POST http://localhost:8000/extract-actions \
  -H "Content-Type: application/json" \
  -d '{"notes": "Raj will fix the login bug by Friday. Sarah needs to deploy by Monday."}'
```

**Example 2 - Bullet points:**
```bash
curl -X POST http://localhost:8000/extract-actions \
  -H "Content-Type: application/json" \
  -d '{"notes": "- Fix navbar bug - Priya\n- Write unit tests - due Thursday\n- Update API docs"}'
```

**Example 3 - Messy/vague:**
```bash
curl -X POST http://localhost:8000/extract-actions \
  -H "Content-Type: application/json" \
  -d '{"notes": "todo: deploy hotfix (urgent!!), ravi - check logs tmrw, standup 10am fri"}'
```

---

## Running Tests

```bash
python test_notes.py
```

Runs 20 diverse test cases and prints results.

---

## Project Structure

```
smart-action-items/
├── main.py          # FastAPI app and endpoints
├── extractor.py     # Ollama prompt logic and JSON parsing
├── test_notes.py    # 20 sample test cases with test runner
├── requirements.txt
└── README.md
```

---

## Design Decisions

### Prompt Design
- Explicitly told the model to return **only a JSON array**, no markdown, no explanation
- Used `temperature=0.1` for consistent, deterministic output
- Defined strict field names (`task`, `owner`, `deadline`) with fallback values

### Handling Edge Cases
- `clean_json_response()` strips markdown code fences in case the model wraps output
- `validate_actions()` fills missing fields with `"Unknown"` or `"Not specified"`
- Empty notes return a 400 error immediately without calling the model

### What Can Break It
- Extremely vague notes with zero actionable items → returns `[]`
- Very long notes may hit model context limits
- Non-English notes may reduce accuracy

### Improvements for Next Version
- Add confidence scores per action item
- Support multiple output formats (CSV, Markdown)
- Add a retry mechanism if JSON parsing fails
- Fine-tune with domain-specific meeting data
