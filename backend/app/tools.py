"""The five LangGraph tools.

Every tool returns a uniform dict:
    { "form_patch": {...}, "assistant_text": "...", "db_effect": {...} }

form_patch uses the canonical frontend field keys (camelCase) and includes a
key ONLY when the tool is setting it (absent key = leave form field untouched).

The 'current interaction' being edited is tracked per session in
_SESSION_STATE so edit_interaction never needs an id from the user. This is
the robustness fix: the edit target does not depend on the LLM remembering an
id from chat history.
"""
from datetime import date, datetime, time as time_cls

from langchain_core.tools import tool
from sqlalchemy import func

from .database import SessionLocal
from . import models
from .llm import extract_interaction, extract_edit, suggest_followups_llm


# session_id -> current interaction id (the record subsequent edits apply to)
_SESSION_STATE: dict[str, int] = {}


def set_active_session(session_id: str):
    """Called by the agent runner so tools know which session is active."""
    _CURRENT["session_id"] = session_id


# module-level 'which session am I serving right now' (set per request)
_CURRENT = {"session_id": "default"}


def _sid() -> str:
    return _CURRENT["session_id"]


# ---- field mapping: snake_case (DB/LLM) -> camelCase (frontend/patch) ----

def _to_patch(extracted) -> dict:
    """Convert a populated Extracted* model into a camelCase form_patch,
    omitting any field that is None."""
    mapping = {
        "hcp_name": "hcpName",
        "interaction_type": "interactionType",
        "date": "date",
        "topics_discussed": "topicsDiscussed",
        "sentiment": "sentiment",
        "materials_shared": "materialsShared",
        "samples_distributed": "samplesDistributed",
        "outcomes": "outcomes",
    }
    patch = {}
    data = extracted.model_dump()
    for snake, camel in mapping.items():
        val = data.get(snake)
        if val is not None:
            patch[camel] = val
    return patch


def _match_hcp(db, name: str):
    """Case-insensitive fuzzy match of an HCP by name; None if no match."""
    if not name:
        return None
    return (
        db.query(models.HCP)
        .filter(func.lower(models.HCP.name).like(f"%{name.lower()}%"))
        .first()
    )


# =====================  TOOL 1: LOG (mandatory)  =====================

@tool
def log_interaction(raw_notes: str) -> dict:
    """Log a NEW HCP interaction from the rep's freeform description.
    Use this whenever the rep describes a meeting, call, or visit with an HCP
    that has not been saved yet (e.g. 'Met Dr. Smith, discussed Product X,
    positive sentiment, shared brochure'). Extracts the fields, saves the
    record, and populates the form."""
    db = SessionLocal()
    try:
        extracted = extract_interaction(raw_notes)

        # resolve date
        interaction_date = None
        if extracted.date:
            try:
                interaction_date = datetime.strptime(extracted.date, "%Y-%m-%d").date()
            except ValueError:
                interaction_date = date.today()
        else:
            interaction_date = date.today()

        hcp = _match_hcp(db, extracted.hcp_name) if extracted.hcp_name else None

        interaction = models.Interaction(
            hcp_id=hcp.id if hcp else None,
            hcp_name_raw=extracted.hcp_name,
            interaction_type=extracted.interaction_type or "Meeting",
            interaction_date=interaction_date,
            topics_discussed=extracted.topics_discussed,
            sentiment=extracted.sentiment,
            outcomes=extracted.outcomes,
            summary=extracted.summary,
            attendees=[],
            suggested_followups=[],
            status="committed",
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        # link materials that match seeded records
        linked_materials = []
        for mname in (extracted.materials_shared or []):
            mat = (
                db.query(models.Material)
                .filter(func.lower(models.Material.name).like(f"%{mname.lower()}%"))
                .first()
            )
            if mat:
                db.add(models.InteractionMaterial(
                    interaction_id=interaction.id, material_id=mat.id, role="shared"))
                linked_materials.append(mat.name)
        if linked_materials:
            db.commit()

        # remember this as the active interaction for future edits
        _SESSION_STATE[_sid()] = interaction.id

        # build patch + ensure date is always shown
        patch = _to_patch(extracted)
        patch["date"] = interaction_date.isoformat()

        filled = ", ".join(
            k for k in ["hcpName", "date", "sentiment", "topicsDiscussed",
                        "materialsShared", "outcomes"] if k in patch
        )
        assistant_text = (
            f"Interaction logged successfully. The details ({filled}) have been "
            "automatically populated based on your summary. Would you like me to "
            "suggest a specific follow-up action, such as scheduling a meeting?"
        )
        return {
            "form_patch": patch,
            "assistant_text": assistant_text,
            "db_effect": {"created_interaction_id": interaction.id},
        }
    finally:
        db.close()


# =====================  TOOL 2: EDIT (mandatory)  =====================

@tool
def edit_interaction(changes_description: str) -> dict:
    """Modify fields on the CURRENT interaction. Use this when the rep corrects
    or changes already-populated details (e.g. 'Sorry, the name was actually
    Dr. John and the sentiment was negative'). ONLY the mentioned fields
    change; everything else stays the same."""
    db = SessionLocal()
    try:
        interaction_id = _SESSION_STATE.get(_sid())
        if not interaction_id:
            return {
                "form_patch": {},
                "assistant_text": ("I don't have an interaction to edit yet. "
                                   "Please log an interaction first."),
                "db_effect": {},
            }

        interaction = db.get(models.Interaction, interaction_id)
        if not interaction:
            return {
                "form_patch": {},
                "assistant_text": "I couldn't find the interaction to edit.",
                "db_effect": {},
            }

        current_form = {
            "hcpName": interaction.hcp_name_raw,
            "interactionType": interaction.interaction_type,
            "sentiment": interaction.sentiment,
            "topicsDiscussed": interaction.topics_discussed,
            "outcomes": interaction.outcomes,
        }
        edit = extract_edit(changes_description, current_form)
        patch = _to_patch(edit)

        # apply only changed fields to the DB row
        if edit.hcp_name is not None:
            interaction.hcp_name_raw = edit.hcp_name
            matched = _match_hcp(db, edit.hcp_name)
            interaction.hcp_id = matched.id if matched else None
        if edit.interaction_type is not None:
            interaction.interaction_type = edit.interaction_type
        if edit.topics_discussed is not None:
            interaction.topics_discussed = edit.topics_discussed
        if edit.sentiment is not None:
            interaction.sentiment = edit.sentiment
        if edit.outcomes is not None:
            interaction.outcomes = edit.outcomes
        if edit.date is not None:
            try:
                interaction.interaction_date = datetime.strptime(edit.date, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.commit()

        if not patch:
            assistant_text = "I didn't catch a specific change to make. Could you clarify what to update?"
        else:
            changed = ", ".join(patch.keys())
            assistant_text = f"Updated {changed}. Everything else stays the same."

        return {
            "form_patch": patch,
            "assistant_text": assistant_text,
            "db_effect": {"updated_interaction_id": interaction.id},
        }
    finally:
        db.close()


# =====================  TOOL 3: SEARCH HCP  =====================

@tool
def search_hcp(name_query: str) -> dict:
    """Find an HCP by name and return their profile and recent interactions.
    Use for questions like 'who is Dr. Lee' or 'what did I discuss with Dr.
    Smith last time'."""
    db = SessionLocal()
    try:
        hcp = _match_hcp(db, name_query)
        if not hcp:
            return {
                "form_patch": {},
                "assistant_text": f"I couldn't find an HCP matching '{name_query}'.",
                "db_effect": {},
            }
        recent = (
            db.query(models.Interaction)
            .filter(models.Interaction.hcp_id == hcp.id)
            .order_by(models.Interaction.created_at.desc())
            .limit(3)
            .all()
        )
        if recent:
            hist = "; ".join(
                f"{i.interaction_date or 'unknown date'}: {i.topics_discussed or 'no topic'}"
                for i in recent
            )
            hist_text = f" Recent interactions: {hist}."
        else:
            hist_text = " No prior interactions logged."
        assistant_text = (
            f"{hcp.name} — {hcp.specialty} at {hcp.institution}.{hist_text}"
        )
        return {
            "form_patch": {},
            "assistant_text": assistant_text,
            "db_effect": {"found_hcp_id": hcp.id},
        }
    finally:
        db.close()


# =====================  TOOL 4: SUGGEST FOLLOW-UPS  =====================

@tool
def suggest_followups() -> dict:
    """Suggest concrete follow-up actions for the current interaction. Use when
    the rep asks for suggestions or accepts the offer to suggest follow-ups."""
    db = SessionLocal()
    try:
        interaction_id = _SESSION_STATE.get(_sid())
        if not interaction_id:
            return {
                "form_patch": {},
                "assistant_text": "Log an interaction first, then I can suggest follow-ups.",
                "db_effect": {},
            }
        interaction = db.get(models.Interaction, interaction_id)
        basis = interaction.summary or interaction.topics_discussed or "an HCP interaction"
        actions = suggest_followups_llm(basis)

        interaction.suggested_followups = actions
        db.commit()

        return {
            "form_patch": {"followUpActions": actions},
            "assistant_text": "Here are some suggested follow-ups: " + "; ".join(actions),
            "db_effect": {"interaction_id": interaction.id, "followups": actions},
        }
    finally:
        db.close()


# =====================  TOOL 5: SEARCH MATERIALS  =====================

@tool
def search_materials(query: str) -> dict:
    """Search approved marketing materials or samples by name or product, and
    attach a match to the current interaction. Use to attach the right
    brochure or sample (e.g. 'attach the Product X brochure')."""
    db = SessionLocal()
    try:
        matches = (
            db.query(models.Material)
            .filter(
                func.lower(models.Material.name).like(f"%{query.lower()}%")
                | func.lower(models.Material.product).like(f"%{query.lower()}%")
            )
            .limit(5)
            .all()
        )
        if not matches:
            return {
                "form_patch": {},
                "assistant_text": f"No approved materials matched '{query}'.",
                "db_effect": {},
            }

        names = [m.name for m in matches]
        interaction_id = _SESSION_STATE.get(_sid())
        role_field = "materialsShared"
        if interaction_id:
            interaction = db.get(models.Interaction, interaction_id)
            for m in matches:
                exists = (
                    db.query(models.InteractionMaterial)
                    .filter_by(interaction_id=interaction.id, material_id=m.id)
                    .first()
                )
                if not exists:
                    db.add(models.InteractionMaterial(
                        interaction_id=interaction.id, material_id=m.id, role="shared"))
            db.commit()

        return {
            "form_patch": {role_field: names},
            "assistant_text": "Found and attached: " + ", ".join(names) + ".",
            "db_effect": {"materials": names},
        }
    finally:
        db.close()


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    search_hcp,
    suggest_followups,
    search_materials,
]