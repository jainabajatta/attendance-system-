"""
Face recognition module for web application
"""

import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import cv2
import numpy as np
from fastapi import HTTPException


class FaceRecognitionSystem:
    """Handles all face recognition operations using Haar Cascades and LBPH"""
    
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
        
        # Ensure workspace directories exist
        os.makedirs("data", exist_ok=True)
        os.makedirs("uploads/faces", exist_ok=True)
        
        self.training_status = {
            "is_trained": False,
            "last_training": None,
            "samples_count": 0
        }
        self.load_data()
    
    def load_data(self) -> None:
        """Load existing face data and metadata profiles"""
        if os.path.exists(self.faces_path):
            try:
                with open(self.faces_path, 'rb') as f:
                    loaded_faces = pickle.load(f)
                    # Force integer mapping for keys to maintain alignment with LBPH labels
                    self.known_faces = {int(k): v for k, v in loaded_faces.items()}
            except Exception as e:
                print(f"Warning: Metadata file corrupted, re-initializing profiles. Info: {e}")
                self.known_faces = {}
        
        if os.path.exists(self.model_path):
            try:
                self.recognizer.read(self.model_path)
                self.training_status["is_trained"] = True
                self.training_status["last_training"] = datetime.fromtimestamp(
                    os.path.getmtime(self.model_path)
                ).isoformat()
            except Exception as e:
                print(f"Warning: Weight model file unreadable, training needed. Info: {e}")
                self.training_status["is_trained"] = False
    
    def save_data(self) -> None:
        """Save local weight matrices and profile records to disk"""
        with open(self.faces_path, 'wb') as f:
            pickle.dump(self.known_faces, f)
        
        if self.training_status["is_trained"]:
            self.recognizer.write(self.model_path)
    
    def register_face(self, user_id: int, name: str, face_samples: List[np.ndarray]) -> bool:
        """Register a new face profile with multiple training frame samples"""
        try:
            user_dir = Path(f"uploads/faces/user_{user_id}")
            user_dir.mkdir(parents=True, exist_ok=True)
            
            for idx, sample in enumerate(face_samples):
                sample_path = user_dir / f"sample_{idx}.jpg"
                cv2.imwrite(str(sample_path), sample)
            
            # Store structured user metadata profile
            self.known_faces[int(user_id)] = {
                "name": name,
                "samples": len(face_samples),
                "registration_date": datetime.now().isoformat()
            }
            
            self.save_data()
            return True
            
        except Exception as e:
            print(f"Registration processing failed: {e}")
            return False
    
    def train_model(self) -> bool:
        """Train the local LBPH face recognition model from scratch"""
        try:
            faces = []
            labels = []
            
            # Collect all registered image sequences
            for user_id in self.known_faces:
                user_dir = Path(f"uploads/faces/user_{user_id}")
                if user_dir.exists():
                    for sample_path in user_dir.glob("sample_*.jpg"):
                        img = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            faces.append(img)
                            labels.append(int(user_id))
            
            if len(faces) > 0:
                self.recognizer.train(faces, np.array(labels, dtype=np.int32))
                self.training_status["is_trained"] = True
                self.training_status["last_training"] = datetime.now().isoformat()
                self.training_status["samples_count"] = len(faces)
                self.save_data()
                return True
            
            raise ValueError("No valid face samples found. Please register students before initializing training.")
            
        except Exception as e:
            print(f"Training operation halted: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def recognize_faces(self, frame: np.ndarray) -> List[Dict]:
        """Detect and classify faces within a live image frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        
        results = []
        
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (100, 100))
            bbox = [int(x), int(y), int(w), int(h)]
            
            if self.training_status["is_trained"]:
                try:
                    label, confidence = self.recognizer.predict(face_roi)
                    # Map LBPH distance values roughly into a 0-100% metric scale
                    confidence_percent = max(0, min(100, 100 - (confidence / 2)))
                    
                    if confidence_percent > 50 and int(label) in self.known_faces:
                        results.append({
                            "user_id": int(label),
                            "name": self.known_faces[int(label)]["name"],
                            "confidence": round(confidence_percent, 2),
                            "bbox": bbox
                        })
                    else:
                        results.append({
                            "user_id": -1,
                            "name": "Unknown",
                            "confidence": round(confidence_percent, 2),
                            "bbox": bbox
                        })
                except Exception as e:
                    print(f"Error executing prediction frame step: {e}")
                    results.append({
                        "user_id": -1,
                        "name": "Unknown",
                        "confidence": 0.0,
                        "bbox": bbox
                    })
            else:
                results.append({
                    "user_id": -1,
                    "name": "Not Trained",
                    "confidence": 0.0,
                    "bbox": bbox
                })
        
        return results
    
    def get_last_training_date(self) -> Optional[str]:
        """Get last recorded successful training timestamp"""
        return self.training_status["last_training"]
    
    def get_training_status(self) -> Dict:
        """Fetch current validation status details"""
        return self.training_status