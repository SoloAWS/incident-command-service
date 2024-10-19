# model.py
from sqlalchemy import Column, String, Enum, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(String, nullable=False)
    state = Column(Enum("open", "in_progress", "closed", "escalated", name="incident_state"), nullable=False)
    channel = Column(Enum("phone", "email", "chat", "mobile", name="incident_channel"), nullable=False)
    priority = Column(Enum("low", "medium", "high", name="incident_priority"), nullable=False)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(UUID(as_uuid=True), nullable=False)
    company_id = Column(UUID(as_uuid=True), nullable=False)
    manager_id = Column(UUID(as_uuid=True))
    file_data = Column(LargeBinary, nullable=True)
    file_name = Column(String, nullable=True)