# app/routers/incident.py
from fastapi import APIRouter, Depends, HTTPException, Header, Form, UploadFile, File
from sqlalchemy.orm import Session
from ..schemas.incident import (
    CreateIncidentRequest, 
    CreateIncidentResponse, 
    IncidentResponse,
    UserCompanyRequest,
    IncidentState, 
    IncidentChannel,
    IncidentPriority
)
from ..models.model import Incident
from ..session import get_db
from typing import List, Optional
import uuid
import os
import jwt

SERVICE_TYPE = os.environ.get('SERVICE_TYPE', 'main')
router = APIRouter(prefix="/incident-command-{SERVICE_TYPE}", tags=["Incident"])

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'secret_key')
ALGORITHM = "HS256"

def get_current_user(token: str = Header(None)):
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

@router.post("/", response_model=CreateIncidentResponse)
def create_incident(
    incident: CreateIncidentRequest, 
    db: Session = Depends(get_db),
    #current_user: dict = Depends(get_current_user)
):
    # if not current_user:
    #    raise HTTPException(status_code=401, detail="Authentication required")
   
    new_incident = Incident(
        id=uuid.uuid4(),
        description=incident.description,
        state=incident.state,
        channel=incident.channel,
        priority=incident.priority,
        user_id=incident.user_id,
        company_id=incident.company_id
    )

    # if current_user['user_type'] == 'manager':
    #     new_incident.manager_id = current_user['sub']

    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    return CreateIncidentResponse.model_validate(new_incident)

@router.post("/user-incident", response_model=CreateIncidentResponse, status_code=201)
async def create_incident(
    user_id: uuid.UUID = Form(...),
    company_id: uuid.UUID = Form(...),
    description: str = Form(...),
    state: str = Form(IncidentState.OPEN.value),
    channel: str = Form(IncidentChannel.MOBILE.value),
    priority: str = Form(IncidentPriority.MEDIUM.value),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    #current_user: dict = Depends(get_current_user)
):
    state_enum = parse_enum_string(state, IncidentState)
    channel_enum = parse_enum_string(channel, IncidentChannel)
    priority_enum = parse_enum_string(priority, IncidentPriority)
    
    new_incident = Incident(
        id=uuid.uuid4(),
        description=description,
        state=state_enum.value,
        channel=channel_enum.value,
        priority=priority_enum.value,
        user_id=user_id,
        company_id=company_id
    )
    
    if file:
        file_content = await file.read()
        new_incident.file_data = file_content
        new_incident.file_name = file.filename
        
    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    return CreateIncidentResponse.model_validate(new_incident)

def parse_enum_string(value: str, enum_class):
    try:
        enum_value = value.split('.')[-1].lower()
        return enum_class[enum_value.upper()]
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid value for {enum_class.__name__}: {value}")


@router.post("/user-company", response_model=List[IncidentResponse])
def get_user_company_incidents(
    data: UserCompanyRequest,
    db: Session = Depends(get_db),
    #current_user: dict = Depends(get_current_user)
):
    # if not current_user:
    #    raise HTTPException(status_code=401, detail="Authentication required")

    # if current_user['user_type'] != 'manager' and current_user['sub'] != str(data.user_id):
    #     raise HTTPException(status_code=403, detail="Not authorized to access this data")

    incidents = db.query(Incident).filter(
        Incident.user_id == data.user_id,
        Incident.company_id == data.company_id
    ).order_by(Incident.creation_date.desc()).limit(20).all()
    return incidents