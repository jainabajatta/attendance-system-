"""
Attendance management module
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path

class AttendanceManager:
    """Manages attendance operations"""
    
    def __init__(self, db_manager, face_system):
        self.db_manager = db_manager
        self.face_system = face_system
        self.attendance_cache = {}
    
    def mark_attendance(self, user_id: int, name: str, confidence: float) -> bool:
        """Mark attendance for a user"""
        today = date.today().isoformat()
        
        # Check if already marked today
        if self.is_already_marked(user_id, today):
            return False
        
        # Mark attendance
        return self.db_manager.mark_attendance(
            user_id=user_id,
            name=name,
            confidence=confidence
        )
    
    def is_already_marked(self, user_id: int, date_str: str) -> bool:
        """Check if user already marked attendance for given date"""
        records = self.db_manager.get_attendance_by_date(date_str)
        return any(record[0] == user_id for record in records)
    
    def export_attendance(self, date_from: str, date_to: str, format: str = "excel") -> Optional[str]:
        """Export attendance records to file"""
        records = self.db_manager.get_attendance_range(date_from, date_to)
        
        if not records:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(records, columns=[
            'user_id', 'name', 'employee_id', 'department', 
            'date', 'time', 'confidence', 'status'
        ])
        
        # Export
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "excel":
            file_path = export_dir / f"attendance_{timestamp}.xlsx"
            df.to_excel(file_path, index=False)
        elif format == "csv":
            file_path = export_dir / f"attendance_{timestamp}.csv"
            df.to_csv(file_path, index=False)
        else:
            file_path = export_dir / f"attendance_{timestamp}.json"
            df.to_json(file_path, orient='records')
        
        return str(file_path)