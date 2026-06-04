"""
Attendance management module
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


class AttendanceManager:
    """Manages attendance operations"""

    def __init__(self, db_manager, face_system):
        self.db_manager = db_manager
        self.face_system = face_system

    def mark_attendance(self, session_id: int, student_id: int, confidence: float) -> bool:
        """
        Mark attendance for a student in a specific class session.
        Returns False if the student is already marked or if insertion fails.
        """
        # The database manager already runs 'attendance_exists' internally before inserting.
        # Removing the duplicate call here protects against unnecessary database overhead.
        return self.db_manager.mark_attendance(
            session_id=session_id,
            student_id=student_id,
            confidence=confidence
        )

    def export_attendance(self, date_from: str, date_to: str, format: str = "excel") -> Optional[str]:
        """
        Fetch attendance records across a date range and export them to a file.
        Supported formats: 'excel', 'csv', 'json'.
        """
        records = self.db_manager.get_attendance_range(date_from, date_to)
        if not records:
            return None

        columns = ["attendance_id", "session_id", "student_id", "time_marked", "confidence", "status"]
        df = pd.DataFrame(records, columns=columns)

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
            df.to_json(file_path, orient="records")

        return str(file_path)