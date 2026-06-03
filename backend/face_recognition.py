"""
Face recognition module for web application
"""

import cv2
import numpy as np
import pickle
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
import json

class FaceRecognitionSystem:
    """Handles all face recognition operations"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=2, neighbors=16, grid_x=8, grid_y=8, threshold=80.0
        )
        self.known_faces = {}
        self.model_path = "data/recognizer_model.yml"
        self.faces_path = "data/known_faces.pkl"
        self.training_status = {
            "is_trained": False,
            "last_training": None,
            "samples_count": 0
        }
        self.load_data()
    
    def load_data(self):
        """Load existing face data"""
        if os.path.exists(self.faces_path):
            with open(self.faces_path, 'rb') as f:
                self.known_faces = pickle.load(f)
        
        if os.path.exists(self.model_path):
            try:
                self.recognizer.read(self.model_path)
                self.training_status["is_trained"] = True
                self.training_status["last_training"] = datetime.fromtimestamp(
                    os.path.getmtime(self.model_path)
                ).isoformat()
            except:
                pass
    
    def save_data(self):
        """Save face data"""
        with open(self.faces_path, 'wb') as f:
            pickle.dump(self.known_faces, f)
        
        if self.training_status["is_trained"]:
            self.recognizer.write(self.model_path)
    
    def register_face(self, user_id: int, name: str, face_samples: List[np.ndarray]) -> bool:
        """Register a new face with multiple samples"""
        try:
            # Store face samples
            user_dir = Path(f"uploads/faces/user_{user_id}")
            user_dir.mkdir(parents=True, exist_ok=True)
            
            for idx, sample in enumerate(face_samples):
                sample_path = user_dir / f"sample_{idx}.jpg"
                cv2.imwrite(str(sample_path), sample)
            
            # Store metadata
            self.known_faces[user_id] = {
                "name": name,
                "samples": len(face_samples),
                "registration_date": datetime.now().isoformat()
            }
            
            self.save_data()
            return True
            
        except Exception as e:
            print(f"Registration error: {e}")
            return False
    
    def train_model(self) -> bool:
        """Train the face recognition model"""
        try:
            faces = []
            labels = []
            
            # Collect all training samples
            for user_id in self.known_faces:
                user_dir = Path(f"uploads/faces/user_{user_id}")
                if user_dir.exists():
                    for sample_path in user_dir.glob("sample_*.jpg"):
                        img = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            faces.append(img)
                            labels.append(user_id)
            
            if len(faces) > 0:
                self.recognizer.train(faces, np.array(labels))
                self.training_status["is_trained"] = True
                self.training_status["last_training"] = datetime.now().isoformat()
                self.training_status["samples_count"] = len(faces)
                self.save_data()
                return True
            
            return False
            
        except Exception as e:
            print(f"Training error: {e}")
            return False
    
    def recognize_faces(self, frame: np.ndarray) -> List[Dict]:
        """Recognize faces in a frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        
        results = []
        
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (100, 100))
            
            if self.training_status["is_trained"]:
                try:
                    label, confidence = self.recognizer.predict(face_roi)
                    confidence_percent = max(0, min(100, 100 - (confidence / 2)))
                    
                    if confidence_percent > 50 and label in self.known_faces:
                        results.append({
                            "user_id": label,
                            "name": self.known_faces[label]["name"],
                            "confidence": confidence_percent,
                            "bbox": [int(x), int(y), int(w), int(h)]
                        })
                    else:
                        results.append({
                            "user_id": -1,
                            "name": "Unknown",
                            "confidence": confidence_percent,
                            "bbox": [int(x), int(y), int(w), int(h)]
                        })
                except:
                    results.append({
                        "user_id": -1,
                        "name": "Unknown",
                        "confidence": 0,
                        "bbox": [int(x), int(y), int(w), int(h)]
                    })
            else:
                results.append({
                    "user_id": -1,
                    "name": "Not Trained",
                    "confidence": 0,
                    "bbox": [int(x), int(y), int(w), int(h)]
                })
        
        return results
    
    def get_last_training_date(self) -> Optional[str]:
        """Get last training date"""
        return self.training_status["last_training"]
    
    def get_training_status(self) -> Dict:
        """Get training status"""
        return self.training_status