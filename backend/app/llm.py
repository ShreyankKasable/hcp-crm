"""LLM initialization and structured extraction helpers.

Uses `.with_structured_output(...)` so extraction returns a validated Pydantic
object instead of a hand-parsed JSON string. This is the reliable, idiomatic
approach — no 'return ONLY JSON' prompting, no try/except string parsing.
"""
import os
from datetime import date

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from .schemas import ExtractedInteraction, ExtractedEdit

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "gemma2-9b-it")

# Base chat model (also used by the agent node, bound to tools there).
llm = ChatGroq(
    model=GROQ_MODEL,
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_retries=3,
)


def _today_str() -> str:
    return date.today().isoformat()


def extract_interaction(raw_notes: str) -> ExtractedInteraction:
    """Extract structured interaction fields from freeform notes."""
    structured = llm.with_structured_output(ExtractedInteraction)
    prompt = (
        "You extract structured CRM data from a pharmaceutical sales rep's notes.\n"
        f"Today's date is {_today_str()}. Resolve relative dates like 'today' "
        "or 'yesterday' to an absolute YYYY-MM-DD.\n"
        "Only fill a field if the notes clearly support it; otherwise leave it null.\n"
        "Also write a one-sentence professional 'summary'.\n\n"
        f'Rep notes: "{raw_notes}"'
    )
    return structured.invoke(prompt)


def extract_edit(changes_description: str, current_form: dict) -> ExtractedEdit:
    """Extract ONLY the fields the rep wants to change on the current record."""
    structured = llm.with_structured_output(ExtractedEdit)
    prompt = (
        "A pharmaceutical sales rep is correcting an already-logged interaction.\n"
        "Return ONLY the fields they are explicitly changing; leave everything "
        "else null so the rest of the record stays untouched.\n\n"
        f"Current record: {current_form}\n\n"
        f'Requested change: "{changes_description}"'
    )
    return structured.invoke(prompt)


def suggest_followups_llm(interaction_summary: str) -> list[str]:
    """Generate 2-3 concrete follow-up actions as a list of short strings."""
    from pydantic import BaseModel, Field

    class Followups(BaseModel):
        actions: list[str] = Field(
            ..., description="2-3 concrete, specific follow-up actions."
        )

    structured = llm.with_structured_output(Followups)
    prompt = (
        "Based on this HCP interaction, suggest 2-3 concrete follow-up actions "
        "a pharma rep should take, following sales best practices. Keep each "
        "action short and specific.\n\n"
        f"Interaction: {interaction_summary}"
    )
    result = structured.invoke(prompt)
    return result.actions