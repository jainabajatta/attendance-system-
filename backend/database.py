"""
SQLite database manager
"""

import sqlite3
from datetime import datetime, date
from typing import List, Tuple, Optional
from pathlib import Path

class DatabaseManager:
    """Manages database operations"""
    
    def __init__(self, db_path: str = "data/attendance.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        Path("data").mkdir(exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_id TEXT UNIQUE NOT NULL,
                department TEXT,
                registration_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                employee_id TEXT,
                department TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                confidence REAL,
                status TEXT DEFAULT 'present',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Activity log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                user_id INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_user(self, name: str, employee_id: str, department: str) -> int:
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (name, employee_id, department, registration_date)
            VALUES (?, ?, ?, ?)
        """, (name, employee_id, department, datetime.now().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.log_activity("user_created", f"User {name} created", user_id)
        return user_id
    
    def get_all_users(self) -> List[Tuple]:
        """Get all active users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, employee_id, department, registration_date
            FROM users WHERE is_active = 1
            ORDER BY name
        """)
        
        users = cursor.fetchall()
        conn.close()
        return users
    
    def get_user_count(self) -> int:
        """Get total user count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def mark_attendance(self, user_id: int, name: str, confidence: float) -> bool:
        """Mark attendance for a user"""
        today = date.today().isoformat()
        now = datetime.now().strftime("%H:%M:%S")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user details
        cursor.execute("SELECT employee_id, department FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            employee_id, department = user
            
            cursor.execute("""
                INSERT INTO attendance (user_id, name, employee_id, department, date, time, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, name, employee_id, department, today, now, confidence))
            
            conn.commit()
            conn.close()
            
            self.log_activity("attendance_marked", f"{name} marked present", user_id)
            return True
        
        conn.close()
        return False
    
    def get_attendance_by_date(self, date_str: str) -> List[Tuple]:
        """Get attendance records for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, name, employee_id, department, time, confidence
            FROM attendance
            WHERE date = ?
            ORDER BY time
        """, (date_str,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_attendance_range(self, date_from: str, date_to: str) -> List[Tuple]:
        """Get attendance records for a date range"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, name, employee_id, department, date, time, confidence, status
            FROM attendance
            WHERE date BETWEEN ? AND ?
            ORDER BY date, time
        """, (date_from, date_to))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_today_attendance_count(self) -> int:
        """Get today's attendance count"""
        today = date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_recent_activity(self, limit: int = 10) -> List[Tuple]:
        """Get recent activity log"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, action, details
            FROM activity_log
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        activities = cursor.fetchall()
        conn.close()
        return activities
    
    def log_activity(self, action: str, details: str, user_id: int = None):
        """Log system activity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO activity_log (timestamp, action, details, user_id)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), action, details, user_id))
        
        conn.commit()
        conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Soft delete a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        self.log_activity("user_deleted", f"User ID {user_id} deleted")
        return True