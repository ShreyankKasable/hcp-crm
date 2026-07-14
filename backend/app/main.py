"""FastAPI application: /api/chat (the agent) + supporting REST endpoints."""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import get_db, engine, Base
from . import models
from .schemas import ChatRequest, ChatResponse
from .agent import run_agent

# create tables if they don't exist (seed script also does this)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM — HCP Log Interaction")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Main entry: run the LangGraph agent for one turn."""
    try:
        result = run_agent(req.session_id, req.message)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")


@app.get("/api/hcps")
def list_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.HCP)
    if q:
        query = query.filter(models.HCP.name.ilike(f"%{q}%"))
    return [
        {"id": h.id, "name": h.name, "specialty": h.specialty,
         "institution": h.institution}
        for h in query.limit(20).all()
    ]


@app.get("/api/materials")
def list_materials(q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.Material)
    if q:
        query = query.filter(models.Material.name.ilike(f"%{q}%"))
    return [
        {"id": m.id, "name": m.name, "type": m.type, "product": m.product}
        for m in query.limit(20).all()
    ]


@app.get("/api/interactions/{interaction_id}")
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    i = db.get(models.Interaction, interaction_id)
    if not i:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {
        "id": i.id,
        "hcp_name": i.hcp_name_raw,
        "interaction_type": i.interaction_type,
        "date": i.interaction_date.isoformat() if i.interaction_date else None,
        "topics_discussed": i.topics_discussed,
        "sentiment": i.sentiment,
        "outcomes": i.outcomes,
        "summary": i.summary,
        "suggested_followups": i.suggested_followups,
        "materials": [
            {"name": m.material.name, "role": m.role} for m in i.materials
        ],
    }