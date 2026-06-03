"""
Pydantic models for API
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    employee_id: str
    department: str

class UserResponse(BaseModel):
    id: int
    name: str
    employee_id: str
    department: str
    registration_date: str

class AttendanceRecord(BaseModel):
    user_id: int
    name: str
    date: str
    time: str
    confidence: float
    status: str

class TrainingStatus(BaseModel):
    is_trained: bool
    last_training: Optional[str]
    samples_count: int