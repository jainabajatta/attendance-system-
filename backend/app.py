"""
Main FastAPI application for Attendance System
"""

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, List
import cv2
import numpy as np
import base64
from datetime import datetime, date
import asyncio
from pathlib import Path
import json

from face_recognition import FaceRecognitionSystem
from attendance_manager import AttendanceManager
from database import DatabaseManager
from models import UserCreate, UserResponse, AttendanceRecord, TrainingStatus
from config import settings

# Initialize FastAPI app
app = FastAPI(title="Vision Attendance System", version="2.0.0")

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
        self.face_processing_tasks = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_frame_result(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)

manager = ConnectionManager()

# Routes
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

# API Endpoints
@app.get("/api/statistics")
async def get_statistics():
    """Get system statistics"""
    stats = {
        "total_users": db_manager.get_user_count(),
        "today_attendance": db_manager.get_today_attendance_count(),
        "total_attendance_today": len(db_manager.get_attendance_by_date(date.today().isoformat())),
        "recent_activity": db_manager.get_recent_activity(10),
        "system_status": "online",
        "last_training": face_system.get_last_training_date()
    }
    return JSONResponse(stats)

@app.post("/api/register")
async def register_user(
    name: str = Form(...),
    employee_id: str = Form(...),
    department: str = Form(...),
    face_images: str = Form(...)  # JSON string of base64 images
):
    """Register a new user with face images"""
    try:
        # Parse face images
        images_data = json.loads(face_images)
        face_samples = []
        
        for img_data in images_data:
            # Decode base64 image
            img_bytes = base64.b64decode(img_data.split(',')[1])
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.COLOR_BGR2GRAY)
            face_samples.append(img)
        
        if len(face_samples) < 10:
            raise HTTPException(status_code=400, detail="Need at least 10 face samples")
        
        # Register user
        user_id = db_manager.create_user(name, employee_id, department)
        success = face_system.register_face(user_id, name, face_samples)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": f"User {name} registered successfully",
                "user_id": user_id
            })
        else:
            raise HTTPException(status_code=500, detail="Face registration failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/train")
async def train_system():
    """Train the face recognition system"""
    try:
        success = face_system.train_model()
        if success:
            return JSONResponse({
                "success": True,
                "message": "System trained successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Training failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def get_users():
    """Get all registered users"""
    users = db_manager.get_all_users()
    return JSONResponse([{
        "id": u[0],
        "name": u[1],
        "employee_id": u[2],
        "department": u[3],
        "registration_date": u[4]
    } for u in users])

@app.get("/api/attendance/today")
async def get_today_attendance():
    """Get today's attendance records"""
    records = db_manager.get_attendance_by_date(date.today().isoformat())
    return JSONResponse([{
        "name": r[1],
        "employee_id": r[2],
        "department": r[3],
        "time": r[4],
        "confidence": r[5]
    } for r in records])

@app.get("/api/attendance/date/{date_str}")
async def get_attendance_by_date(date_str: str):
    """Get attendance for specific date"""
    records = db_manager.get_attendance_by_date(date_str)
    return JSONResponse([{
        "name": r[1],
        "employee_id": r[2],
        "department": r[3],
        "time": r[4],
        "confidence": r[5]
    } for r in records])

@app.post("/api/attendance/export")
async def export_attendance(date_from: str, date_to: str, format: str = "excel"):
    """Export attendance records"""
    file_path = attendance_manager.export_attendance(date_from, date_to, format)
    if file_path:
        return FileResponse(file_path, filename=f"attendance_{date_from}_to_{date_to}.{format}")
    raise HTTPException(status_code=404, detail="No data found")

@app.delete("/api/user/{user_id}")
async def delete_user(user_id: int):
    """Delete a user"""
    success = db_manager.delete_user(user_id)
    if success:
        return JSONResponse({"success": True, "message": "User deleted"})
    raise HTTPException(status_code=404, detail="User not found")

# WebSocket for real-time face recognition
@app.websocket("/ws/recognize")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive frame from client
            data = await websocket.receive_text()
            
            # Parse frame
            if data.startswith('data:image'):
                # Decode base64 image
                img_data = data.split(',')[1]
                img_bytes = base64.b64decode(img_data)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Process frame for face recognition
                results = face_system.recognize_faces(frame)
                
                # Mark attendance for recognized faces
                for result in results:
                    if result['confidence'] > 65:  # Threshold
                        attendance_manager.mark_attendance(
                            user_id=result['user_id'],
                            name=result['name'],
                            confidence=result['confidence']
                        )
                
                # Send results back
                await manager.send_frame_result(websocket, {
                    "type": "recognition",
                    "faces": results,
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.post("/api/training/status")
async def get_training_status():
    """Get training status"""
    status = face_system.get_training_status()
    return JSONResponse(status)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)