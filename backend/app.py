"""
Main FastAPI application for Attendance System
"""

import re
import json
import base64
import asyncio
from datetime import datetime
from typing import List

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from face_recognition import FaceRecognitionSystem
from attendance_manager import AttendanceManager
from database import DatabaseManager
from models import CourseCreate, EnrollmentCreate, SessionCreate

# Initialize FastAPI app
app = FastAPI(title="Vision Attendance System", version="2.0.0")

# Global state tracker for active session
current_session_id = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

# Initialize components
db_manager = DatabaseManager()
face_system = FaceRecognitionSystem()
attendance_manager = AttendanceManager(db_manager, face_system)


# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_frame_result(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)


manager = ConnectionManager()


# Helper function to decode images safely
def decode_base64_image(base64_str: str, color_mode: int = cv2.IMREAD_COLOR) -> np.ndarray:
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        return cv2.imdecode(nparr, color_mode)
    except Exception as e:
        raise ValueError(f"Failed to decode image: {str(e)}")


# --- UI Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard"""
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard page"""
    with open("templates/dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Registration page"""
    with open("templates/register.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/reports", response_class=HTMLResponse)
async def reports_page():
    """Reports page"""
    with open("templates/reports.html", "r") as f:
        return HTMLResponse(content=f.read())


# --- API Endpoints ---

@app.get("/api/statistics")
async def get_statistics():
    return JSONResponse({
        "total_students": db_manager.get_student_count(),
        "system_status": "online",
        "last_training": face_system.get_last_training_date()
    })


@app.post("/api/students/register")
async def register_student(
    full_name: str = Form(...),
    student_id: str = Form(...),
    department: str = Form(...),
    face_images: str = Form(...)
):
    try:
        images_data = json.loads(face_images)
        face_samples = []

        for img_data in images_data:
            img = decode_base64_image(img_data, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                face_samples.append(img)

        if len(face_samples) < 10:
            raise HTTPException(
                status_code=400,
                detail="Need at least 10 valid face samples"
            )

        if not re.match(r"^[A-Z]{3}[0-9]{7}$", student_id):
            raise HTTPException(
                status_code=400,
                detail="Student ID must be in format BCS0000227"
            )

        db_student_id = db_manager.create_student(
            student_id,
            full_name,
            department
        )

        # Offload intensive registration to a separate thread
        success = await asyncio.to_thread(
            face_system.register_face, db_student_id, full_name, face_samples
        )

        if success:
            return {
                "success": True,
                "student_id": db_student_id,
                "message": f"{full_name} registered successfully"
            }

        raise HTTPException(
            status_code=500,
            detail="Face registration failed"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/train")
async def train_system():
    try:
        success = await asyncio.to_thread(face_system.train_model)
        if success:
            return {
                "success": True,
                "message": "System trained successfully"
            }
        raise HTTPException(status_code=500, detail="Training failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students")
async def get_students():
    students = db_manager.get_all_students()
    return JSONResponse([
        {
            "id": s[0],
            "student_id": s[1],
            "full_name": s[2],
            "department": s[3],
            "registration_date": s[4]
        }
        for s in students
    ])


@app.post("/api/courses")
async def create_course(course: CourseCreate):
    course_id = db_manager.create_course(
        course.course_code,
        course.course_name,
        course.lecturer,
        course.semester
    )
    return {
        "success": True,
        "course_id": course_id
    }


@app.get("/api/courses")
async def get_courses():
    courses = db_manager.get_courses()
    return [
        {
            "id": c[0],
            "course_code": c[1],
            "course_name": c[2],
            "lecturer": c[3],
            "semester": c[4]
        }
        for c in courses
    ]


@app.post("/api/enrollments")
async def enroll_student(enrollment: EnrollmentCreate):
    db_manager.enroll_student(
        enrollment.student_id,
        enrollment.course_id
    )
    return {
        "success": True,
        "message": "Student enrolled successfully"
    }


@app.post("/api/sessions/start")
async def start_session(session: SessionCreate):
    global current_session_id

    if current_session_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Another attendance session is already active"
        )

    session_id = db_manager.create_session(session.course_id)
    current_session_id = session_id

    return {
        "success": True,
        "session_id": session_id,
        "message": "Attendance session started"
    }


@app.post("/api/sessions/stop")
async def stop_session():
    global current_session_id

    if current_session_id is None:
        raise HTTPException(
            status_code=400,
            detail="No active session"
        )

    db_manager.close_session(current_session_id)
    current_session_id = None

    return {
        "success": True,
        "message": "Session stopped"
    }


@app.get("/api/attendance")
async def get_attendance(
    date_from: str = Query(..., description="Start date format YYYY-MM-DD"),
    date_to: str = Query(..., description="End date format YYYY-MM-DD")
):
    records = db_manager.get_attendance_range(date_from, date_to)
    return [
        {
            "attendance_id": r[0],
            "session_id": r[1],
            "student_id": r[2],
            "time_marked": r[3],
            "confidence": r[4],
            "status": r[5]
        }
        for r in records
    ]


@app.post("/api/attendance/export")
async def export_attendance(
    date_from: str, 
    date_to: str, 
    format: str = "excel"
):
    """Export attendance records"""
    file_path = attendance_manager.export_attendance(date_from, date_to, format)
    if file_path:
        return FileResponse(file_path, filename=f"attendance_{date_from}_to_{date_to}.{format}")
    raise HTTPException(status_code=404, detail="No data found")


# --- WebSocket Implementation ---

@app.websocket("/ws/recognize")
async def websocket_endpoint(websocket: WebSocket):
    global current_session_id
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            if data.startswith("data:image"):
                # Run OpenCV decoding and classification in an async-safe worker thread
                frame = await asyncio.to_thread(decode_base64_image, data, cv2.IMREAD_COLOR)
                results = await asyncio.to_thread(face_system.recognize_faces, frame)

                for result in results:
                    if (
                        current_session_id is not None
                        and result.get("user_id") != -1
                        and result.get("confidence", 0) >= 65
                    ):
                        # Safely process standard IO write Operations 
                        await asyncio.to_thread(
                            attendance_manager.mark_attendance,
                            session_id=current_session_id,
                            student_id=result["user_id"],
                            confidence=result["confidence"]
                        )

                await manager.send_frame_result(
                    websocket,
                    {
                        "type": "recognition",
                        "faces": results,
                        "timestamp": datetime.now().isoformat()
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/api/training/status")
async def get_training_status():
    """Get training status"""
    status = face_system.get_training_status()
    return JSONResponse(status)