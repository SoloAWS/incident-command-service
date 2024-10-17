import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
import jwt
from datetime import datetime

from app.models.model import Incident
from app.schemas.incident import IncidentState, IncidentChannel, IncidentPriority
from app.main import app

client = TestClient(app)

SECRET_KEY = "secret_key"
ALGORITHM = "HS256"

def create_test_token(user_id: UUID, user_type: str):
    token_data = {
        "sub": str(user_id),
        "user_type": user_type
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

def test_create_incident_as_user(db_session: Session):
    user_id = uuid4()
    company_id = uuid4()
    
    incident_data = {
        "user_id": str(user_id),
        "company_id": str(company_id),
        "description": "Test incident",
        "state": IncidentState.OPEN.value,
        "channel": IncidentChannel.EMAIL.value,
        "priority": IncidentPriority.MEDIUM.value
    }
    
    token = create_test_token(user_id, "user")
    response = client.post("/incident-command-main/", json=incident_data, headers={"token": token})
    print(response)
    assert response.status_code == 200
    data = response.json()
    assert "manager_id" not in data

def test_get_user_company_incidents(db_session: Session):
    user_id = uuid4()
    company_id = uuid4()
    
    # Create some test incidents
    for _ in range(5):
        incident_data = {
            "user_id": str(user_id),
            "company_id": str(company_id),
            "description": "Test incident",
            "state": IncidentState.OPEN.value,
            "channel": IncidentChannel.EMAIL.value,
            "priority": IncidentPriority.MEDIUM.value
        }
        token = create_test_token(user_id, "user")
        client.post("/incident-command-main/", json=incident_data, headers={"token": token})
    
    request_data = {
        "user_id": str(user_id),
        "company_id": str(company_id)
    }
    
    token = create_test_token(user_id, "user")
    response = client.post("/incident-command-main/user-company", json=request_data, headers={"token": token})
    print(response)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

def test_get_user_company_incidents_no_incidents(db_session: Session):
    user_id = uuid4()
    company_id = uuid4()
    
    request_data = {
        "user_id": str(user_id),
        "company_id": str(company_id)
    }
    
    token = create_test_token(user_id, "user")
    response = client.post("/incident-command-main/user-company", json=request_data, headers={"token": token})
    print(response)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_get_user_company_incidents_unauthorized(db_session: Session):
    user_id = uuid4()
    company_id = uuid4()
    
    request_data = {
        "user_id": str(user_id),
        "company_id": str(company_id)
    }
    
    response = client.post("/incident-command-main/user-company", json=request_data)
    print(response)
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"

def test_get_user_company_incidents_wrong_user(db_session: Session):
    user_id = uuid4()
    company_id = uuid4()
    other_user_id = uuid4()
    
    request_data = {
        "user_id": str(user_id),
        "company_id": str(company_id)
    }
    
    token = create_test_token(other_user_id, "user")
    response = client.post("/incident-command-main/user-company", json=request_data, headers={"token": token})
    print(response)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this data"