"""
Pydantic models for API
"""

import re
from typing import Optional
from pydantic import BaseModel, field_validator


# ==========================
# STUDENTS
# ==========================

class StudentCreate(BaseModel):
    student_id: str
    full_name: str
    department: str

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, value: str) -> str:
        pattern = r"^[A-Z]{3}[0-9]{7}$"
        if not re.match(pattern, value):
            raise ValueError(
                "Student ID must start with 3 uppercase letters followed by 7 digits (e.g., BCS0000227)"
            )
        return value


class StudentResponse(BaseModel):
    id: int
    student_id: str
    full_name: str
    department: str
    registration_date: str


# ==========================
# COURSES
# ==========================

class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    lecturer: str
    semester: str


class CourseResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    lecturer: str
    semester: str


# ==========================
# ENROLLMENTS
# ==========================

class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int


# ==========================
# SESSIONS
# ==========================

class SessionCreate(BaseModel):
    course_id: int


class SessionResponse(BaseModel):
    id: int
    course_id: int
    session_date: str
    start_time: str
    status: str


# ==========================
# ATTENDANCE
# ==========================

class AttendanceRecord(BaseModel):
    session_id: int
    student_id: int
    confidence: float
    status: str


# ==========================
# TRAINING STATUS
# ==========================

class TrainingStatus(BaseModel):
    is_trained: bool
    last_training: Optional[str] = None
    samples_count: int