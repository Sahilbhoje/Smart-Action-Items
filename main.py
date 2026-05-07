"""
Smart Action Items - FastAPI service to extract structured action items from meeting notes.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from extractor import extract_actions

app = FastAPI(
    title="Smart Action Items",
    description="Convert messy meeting notes into structured action items using AI.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



class NotesInput(BaseModel):
    notes: str

    class Config:
        json_schema_extra = {
            "example": {
                "notes": "Raj will fix the login bug by Friday. Sarah needs to deploy by Monday."
            }
        }


class ActionItem(BaseModel):
    task: str
    owner: str
    deadline: str


class ActionsOutput(BaseModel):
    actions: list[ActionItem]


@app.get("/")
def root():
    return {"message": "Smart Action Items API is running. POST to /extract-actions"}


@app.post("/extract-actions", response_model=ActionsOutput)
def extract(input: NotesInput):
    """
    Extract structured action items from messy meeting notes.

    - **notes**: Raw meeting notes text (any format)

    Returns a list of action items with task, owner, and deadline.
    """
    if not input.notes.strip():
        raise HTTPException(status_code=400, detail="Notes cannot be empty.")

    try:
        actions = extract_actions(input.notes)
        return {"actions": actions}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Could not parse AI response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
