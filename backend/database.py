"""
SQLite database manager
"""

import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple, Optional


class DatabaseManager:
    """Manages database operations"""

    def __init__(self, db_path: str = "data/attendance.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize database tables"""
        Path("data").mkdir(exist_ok=True)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Students
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                department TEXT,
                registration_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
            """)

            # Courses
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE NOT NULL,
                course_name TEXT NOT NULL,
                lecturer TEXT,
                semester TEXT
            )
            """)

            # Enrollments
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrollment_date TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
            """)

            # Class Sessions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
            """)

            # Attendance
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                time_marked TEXT NOT NULL,
                confidence REAL,
                status TEXT DEFAULT 'Present',
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
            """)

            # Activity Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                user_id INTEGER
            )
            """)

    # ==========================
    # STUDENTS
    # ==========================

    def create_student(self, student_id: str, full_name: str, department: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO students (student_id, full_name, department, registration_date)
            VALUES (?, ?, ?, ?)
            """, (
                student_id,
                full_name,
                department,
                datetime.now().isoformat()
            ))
            new_id = cursor.lastrowid

        self.log_activity("student_created", f"{full_name} registered", new_id)
        return new_id

    def get_all_students(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, student_id, full_name, department, registration_date
            FROM students
            WHERE is_active = 1
            ORDER BY full_name
            """)
            return cursor.fetchall()

    def get_student_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT COUNT(*) FROM students WHERE is_active = 1
            """)
            return cursor.fetchone()[0]

    # ==========================
    # COURSES
    # ==========================

    def create_course(self, course_code: str, course_name: str, lecturer: str, semester: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO courses (course_code, course_name, lecturer, semester)
            VALUES (?, ?, ?, ?)
            """, (course_code, course_name, lecturer, semester))
            return cursor.lastrowid

    def get_courses(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, course_code, course_name, lecturer, semester 
            FROM courses 
            ORDER BY course_code
            """)
            return cursor.fetchall()

    # ==========================
    # ENROLLMENTS
    # ==========================

    def enroll_student(self, student_id: int, course_id: int) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO enrollments (student_id, course_id, enrollment_date)
            VALUES (?, ?, ?)
            """, (student_id, course_id, datetime.now().isoformat()))

    # ==========================
    # SESSIONS
    # ==========================

    def create_session(self, course_id: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO sessions (course_id, session_date, start_time)
            VALUES (?, ?, ?)
            """, (course_id, date.today().isoformat(), datetime.now().isoformat()))
            return cursor.lastrowid

    def close_session(self, session_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE sessions
            SET status = 'closed',
                end_time = ?
            WHERE id = ?
            """, (datetime.now().isoformat(), session_id))
            return True

    # ==========================
    # ATTENDANCE
    # ==========================

    def attendance_exists(self, session_id: int, student_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id FROM attendance WHERE session_id = ? AND student_id = ?
            """, (session_id, student_id))
            return cursor.fetchone() is not None

    def mark_attendance(self, session_id: int, student_id: int, confidence: float) -> bool:
        if self.attendance_exists(session_id, student_id):
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO attendance (session_id, student_id, time_marked, confidence)
            VALUES (?, ?, ?, ?)
            """, (session_id, student_id, datetime.now().isoformat(), confidence))
            return True

    def get_attendance_range(self, date_from: str, date_to: str) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT a.id, a.session_id, a.student_id, a.time_marked, a.confidence, a.status
            FROM attendance a
            JOIN sessions s ON a.session_id = s.id
            WHERE s.session_date BETWEEN ? AND ?
            ORDER BY s.session_date
            """, (date_from, date_to))
            return cursor.fetchall()

    # ==========================
    # ACTIVITY LOG
    # ==========================

    def log_activity(self, action: str, details: str, user_id: Optional[int] = None) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO activity_log (timestamp, action, details, user_id)
            VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), action, details, user_id))