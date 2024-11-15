# app/routers/incident.py
from fastapi import APIRouter, Depends, HTTPException, Header, Form, UploadFile, File
import httpx
from sqlalchemy import text
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
from ..models.model import EmailIncidentRequest, Incident, IncidentHistory
from ..session import get_db
from typing import List, Optional
import uuid
import os
import jwt
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


router = APIRouter(prefix="/incident-command", tags=["Incident"])

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8002/user")
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'secret_key')
ALGORITHM = "HS256"

def get_current_user(authorization: str = Header(None)):
    if authorization is None:
        return None
    try:
        token = authorization.replace('Bearer ', '') if authorization.startswith('Bearer ') else authorization
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

@router.post("/", response_model=CreateIncidentResponse)
def create_incident(
    incident: CreateIncidentRequest, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
       raise HTTPException(status_code=401, detail="Authentication required")
   
    new_incident = Incident(
        id=uuid.uuid4(),
        description=incident.description,
        state=incident.state,
        channel=incident.channel,
        priority=incident.priority,
        user_id=incident.user_id,
        company_id=incident.company_id
    )

    if current_user['user_type'] == 'manager':
        new_incident.manager_id = current_user['sub']

    history_log = IncidentHistory(
        incident_id=new_incident.id,
        description="Incidente creado por asesor."
    )

    db.add(new_incident)
    db.add(history_log)
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
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
       raise HTTPException(status_code=401, detail="Authentication required")
   
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
    
    history_log = IncidentHistory(
        incident_id=new_incident.id,
        description="Incidente creado por usuario."
    )
        
    db.add(new_incident)
    db.add(history_log)
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
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
       raise HTTPException(status_code=401, detail="Authentication required")

    if current_user['user_type'] != 'manager' and current_user['sub'] != str(data.user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this data")

    incidents = db.query(Incident).filter(
        Incident.user_id == data.user_id,
        Incident.company_id == data.company_id
    ).order_by(Incident.creation_date.desc()).limit(20).all()
    return incidents


@router.post("/email", response_model=CreateIncidentResponse)
async def create_email_incident(
    incident: EmailIncidentRequest,
    db: Session = Depends(get_db)
):
    """
    Special endpoint for creating incidents from email processor.
    No JWT required, but requires validation of email and company.
    """
    try:
        async with httpx.AsyncClient() as client:
            # First, find company by name
            try:
                company_response = await client.get(
                    f"{USER_SERVICE_URL}/email/company",
                    params={"name": incident.company_name}
                )
                if company_response.status_code == 404:
                    # Try to get list of companies for this email to provide better error message
                    companies_response = await client.get(
                        f"{USER_SERVICE_URL}/email/companies",
                        params={"email": incident.email}
                    )
                    if companies_response.status_code == 200:
                        companies = companies_response.json()['companies']
                        raise HTTPException(
                            status_code=404,
                            detail=f"Company '{incident.company_name}' not found. Available companies for your email: {', '.join(c['name'] for c in companies)}"
                        )
                    raise HTTPException(
                        status_code=404,
                        detail=f"Company '{incident.company_name}' not found"
                    )
                company_data = company_response.json()
                
                # Validate user belongs to company
                validation_response = await client.get(
                    f"{USER_SERVICE_URL}/email/validate",
                    params={
                        "email": incident.email,
                        "company_id": company_data['id']
                    }
                )
                if validation_response.status_code != 200:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Email {incident.email} not authorized for company {incident.company_name}"
                    )
                user_data = validation_response.json()
                
            except httpx.RequestError as e:
                logger.error(f"Error contacting user service: {str(e)}")
                raise HTTPException(status_code=503, detail="User service unavailable")
            
            # Create the incident
            new_incident = Incident(
                id=uuid.uuid4(),
                description=incident.description,
                state="open",
                channel="email",
                priority="medium",
                user_id=user_data['id'],
                company_id=company_data['id']
            )
            
            history_log = IncidentHistory(
                incident_id=new_incident.id,
                description="Incident created via email."
            )
            
            db.add(new_incident)
            db.add(history_log)
            db.commit()
            db.refresh(new_incident)
            
            logger.info(f"Created email incident with ID: {new_incident.id}")
            return CreateIncidentResponse.model_validate(new_incident)
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating email incident: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error creating incident"
        )