# incident.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List
from enum import Enum

class IncidentState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    ESCALATED = "escalated"
    
class IncidentChannel(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    CHAT = "chat"
    MOBILE = "mobile"
    
class IncidentPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    
class IncidentResponse(BaseModel):
    id: UUID
    description: str
    state: IncidentState
    creation_date: datetime
    
class UserCompanyRequest(BaseModel):
    user_id: UUID
    company_id: UUID
    
class IncidentsResponse(BaseModel):
    incidents: List[IncidentResponse]
    
class CreateIncidentRequest(BaseModel):
    user_id: UUID
    company_id: UUID
    description: str
    state: IncidentState = Field(default=IncidentState.OPEN)
    channel: IncidentChannel
    priority: IncidentPriority
    
class CreateIncidentResponse(BaseModel):
    id: UUID
    user_id: UUID
    company_id: UUID
    description: str
    state: IncidentState = Field(default=IncidentState.OPEN)
    channel: IncidentChannel
    priority: IncidentPriority
    creation_date: datetime
    
    model_config = {
        "from_attributes": True
    }







