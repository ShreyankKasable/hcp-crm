"""Pydantic schemas: structured LLM extraction + API request/response shapes."""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


Sentiment = Literal["positive", "neutral", "negative"]


class ExtractedInteraction(BaseModel):
    """Fields the LLM extracts from a rep's freeform description.

    Every field is optional: the model only fills what the text supports.
    """
    hcp_name: Optional[str] = Field(
        None, description="Name of the healthcare professional, e.g. 'Dr. Smith'."
    )
    interaction_type: Optional[str] = Field(
        None, description="One of: Meeting, Call, Email, Conference. Default Meeting."
    )
    date: Optional[str] = Field(
        None, description="Interaction date as YYYY-MM-DD. Resolve 'today' to the real date."
    )
    topics_discussed: Optional[str] = Field(
        None, description="Short summary of what was discussed."
    )
    sentiment: Optional[Sentiment] = Field(
        None, description="HCP's sentiment: positive, neutral, or negative."
    )
    materials_shared: Optional[List[str]] = Field(
        None, description="Names of brochures/materials shared, e.g. ['Brochures']."
    )
    samples_distributed: Optional[List[str]] = Field(
        None, description="Names of samples distributed."
    )
    outcomes: Optional[str] = Field(
        None, description="Key outcomes or agreements from the interaction."
    )
    summary: Optional[str] = Field(
        None, description="A one-sentence professional CRM summary of the interaction."
    )


class ExtractedEdit(BaseModel):
    """Partial changes for an edit. Only the fields the rep is changing are set."""
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    topics_discussed: Optional[str] = None
    sentiment: Optional[Sentiment] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    outcomes: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Per-session UUID minted by the frontend.")
    message: str


class ChatResponse(BaseModel):
    assistant_text: str
    form_patch: dict
    interaction_id: Optional[int] = None