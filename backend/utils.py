"""
Utility functions for the backend
"""
import numpy as np
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import shutil

def create_directory(path: str) -> None:
    """Create directory if it doesn't exist"""
    Path(path).mkdir(parents=True, exist_ok=True)

def clean_temp_files(directory: str, age_minutes: int = 60) -> int:
    """Clean temporary files older than specified minutes"""
    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(minutes=age_minutes)
    
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
    
    return deleted_count

def get_file_size(file_path: str) -> str:
    """Get human-readable file size"""
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def backup_database(db_path: str, backup_dir: str) -> Optional[str]:
    """Create backup of database"""
    try:
        create_directory(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"attendance_backup_{timestamp}.db")
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def calculate_face_quality(face_img) -> float:
    """Calculate face image quality score"""
    import cv2
    import numpy as np
    
    # Laplacian variance for sharpness
    laplacian_var = cv2.Laplacian(face_img, cv2.CV_64F).var()
    
    # Normalize to 0-100
    quality = min(100, max(0, laplacian_var / 10))
    
    # Check brightness
    mean_brightness = np.mean(face_img)
    if mean_brightness < 50 or mean_brightness > 200:
        quality *= 0.7  # Penalize too dark or too bright
    
    return quality

def generate_employee_id(prefix: str = "EMP") -> str:
    """Generate unique employee ID"""
    import random
    import string
    
    random_digits = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{random_digits}"

def validate_face_samples(samples: list, min_samples: int = 10) -> Dict:
    """Validate face samples for quality"""
    import cv2
    import numpy as np
    from io import BytesIO
    import base64
    
    valid_samples = []
    quality_scores = []
    
    for sample in samples:
        # Decode base64 image
        img_data = base64.b64decode(sample.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        if img is not None:
            quality = calculate_face_quality(img)
            if quality > 30:
                valid_samples.append(img)
                quality_scores.append(quality)
    
    return {
        "valid_count": len(valid_samples),
        "samples": valid_samples,
        "average_quality": np.mean(quality_scores) if quality_scores else 0,
        "is_sufficient": len(valid_samples) >= min_samples
    }

def log_system_event(event_type: str, message: str, data: Any = None):
    """Log system events to file"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "message": message,
        "data": data
    }
    
    log_file = "logs/system_events.json"
    create_directory("logs")
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def get_system_metrics() -> Dict:
    """Get system performance metrics"""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "uptime": datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    }

def hash_face_features(features: np.ndarray) -> str:
    """Create hash of face features for duplicate detection"""
    import hashlib
    feature_bytes = features.tobytes()
    return hashlib.sha256(feature_bytes).hexdigest()[:16]

class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, client_id: str) -> bool:
        now = datetime.now()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if (now - req_time).seconds < self.time_window
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(now)
        return True