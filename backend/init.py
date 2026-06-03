"""
Backend package for Attendance System
"""

from .app import app
from .face_recognition import FaceRecognitionSystem
from .attendance_manager import AttendanceManager
from .database import DatabaseManager
from .config import settings
from .models import UserCreate, UserResponse, AttendanceRecord

__all__ = [
    'app',
    'FaceRecognitionSystem',
    'AttendanceManager', 
    'DatabaseManager',
    'settings',
    'UserCreate',
    'UserResponse',
    'AttendanceRecord'
]