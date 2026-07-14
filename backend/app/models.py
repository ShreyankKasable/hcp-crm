"""SQLAlchemy models: hcps, materials, interactions, interaction_materials."""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, Date, Time, DateTime,
    ForeignKey, Enum, JSON,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    specialty = Column(String(255))
    institution = Column(String(255))
    created_at = Column(DateTime, default=_utcnow)

    interactions = relationship("Interaction", back_populates="hcp")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    # brochure | sample | pdf
    type = Column(String(50), nullable=False)
    product = Column(String(255))
    created_at = Column(DateTime, default=_utcnow)


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=True)
    hcp_name_raw = Column(String(255))
    interaction_type = Column(String(100), default="Meeting")
    interaction_date = Column(Date)
    interaction_time = Column(Time)
    attendees = Column(JSON, default=list)
    topics_discussed = Column(Text)
    # positive | neutral | negative
    sentiment = Column(String(50))
    outcomes = Column(Text)
    summary = Column(Text)                 # LLM-generated
    suggested_followups = Column(JSON, default=list)
    # draft | committed
    status = Column(String(50), default="committed")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    hcp = relationship("HCP", back_populates="interactions")
    materials = relationship(
        "InteractionMaterial", back_populates="interaction",
        cascade="all, delete-orphan",
    )


class InteractionMaterial(Base):
    __tablename__ = "interaction_materials"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"))
    material_id = Column(Integer, ForeignKey("materials.id"))
    # shared | sample_distributed
    role = Column(String(50))

    interaction = relationship("Interaction", back_populates="materials")
    material = relationship("Material")