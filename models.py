"""
Database models and helper functions for ProctorGuard
Handles all database operations including initialization and queries
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from config import DATABASE_PATH


def get_db_connection():
    """
    Get a connection to the SQLite database
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute('PRAGMA foreign_keys = ON')
        print(f"[DB] Connected to database: {DATABASE_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"[DB ERROR] Connection failed: {e}")
        raise


def execute_query(query: str, params: tuple = ()) -> None:
    """
    Execute a database query (INSERT, UPDATE, DELETE)
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters for safe execution
    
    Raises:
        sqlite3.Error: If database operation fails
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        print(f"[DB] Query executed successfully")
    except sqlite3.Error as e:
        print(f"[DB ERROR] Query execution failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def fetch_one(query: str, params: tuple = ()) -> Optional[Dict]:
    """
    Fetch a single row from the database
    
    Args:
        query (str): SQL SELECT query
        params (tuple): Query parameters
    
    Returns:
        Optional[Dict]: Single row as dictionary or None if no results
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        print(f"[DB] Fetched one row")
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[DB ERROR] Fetch one failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def fetch_all(query: str, params: tuple = ()) -> List[Dict]:
    """
    Fetch all rows from the database
    
    Args:
        query (str): SQL SELECT query
        params (tuple): Query parameters
    
    Returns:
        List[Dict]: List of rows as dictionaries
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        print(f"[DB] Fetched {len(rows)} rows")
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[DB ERROR] Fetch all failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def init_database() -> None:
    """
    Initialize the database with required tables and schema
    Creates tables only if they don't already exist
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                exam_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("[DB] Students table created/verified")
        
        # Create exams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT,
                duration INTEGER,
                total_questions INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("[DB] Exams table created/verified")

        # Add missing columns for existing databases
        cursor.execute("PRAGMA table_info(exams)")
        exam_columns = {row[1] for row in cursor.fetchall()}
        if 'code' not in exam_columns:
            cursor.execute('ALTER TABLE exams ADD COLUMN code TEXT')
            print("[DB] Exams table updated with code column")
        
        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                severity TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (exam_id) REFERENCES exams(id)
            )
        ''')
        print("[DB] Alerts table created/verified")
        
        # Create submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                answers TEXT,
                score INTEGER,
                flagged INTEGER DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (exam_id) REFERENCES exams(id)
            )
        ''')
        print("[DB] Submissions table created/verified")

        # Add missing columns for existing databases
        cursor.execute("PRAGMA table_info(submissions)")
        submission_columns = {row[1] for row in cursor.fetchall()}
        if 'flagged' not in submission_columns:
            cursor.execute('ALTER TABLE submissions ADD COLUMN flagged INTEGER DEFAULT 0')
            print("[DB] Submissions table updated with flagged column")

        # Create violation_screenshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violation_screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                image_data TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES alerts(id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (exam_id) REFERENCES exams(id)
            )
        ''')
        print("[DB] Violation screenshots table created/verified")
        
        conn.commit()
        print("[DB] Database initialization completed successfully")
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Database initialization failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def add_student(name: str, email: str, exam_id: Optional[str] = None) -> int:
    """
    Add a new student to the database
    
    Args:
        name (str): Student name
        email (str): Student email
        exam_id (Optional[str]): Associated exam ID
    
    Returns:
        int: ID of the newly created student
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO students (name, email, exam_id) VALUES (?, ?, ?)',
            (name, email, exam_id)
        )
        conn.commit()
        student_id = cursor.lastrowid
        print(f"[DB] Student added with ID: {student_id}")
        return student_id
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to add student: {e}")
        raise
    finally:
        if conn:
            conn.close()


def add_exam(name: str, duration: int, total_questions: int, code: Optional[str] = None) -> int:
    """
    Add a new exam to the database
    
    Args:
        name (str): Exam name
        duration (int): Duration in minutes
        total_questions (int): Total number of questions
    
    Returns:
        int: ID of the newly created exam
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO exams (name, code, duration, total_questions) VALUES (?, ?, ?, ?)',
            (name, code, duration, total_questions)
        )
        conn.commit()
        exam_id = cursor.lastrowid
        print(f"[DB] Exam added with ID: {exam_id}")
        return exam_id
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to add exam: {e}")
        raise
    finally:
        if conn:
            conn.close()


def add_alert(student_id: int, exam_id: int, reason: str, severity: str = 'warning') -> int:
    """
    Add a new alert to the database
    
    Args:
        student_id (int): Student ID
        exam_id (int): Exam ID
        reason (str): Reason for alert
        severity (str): Alert severity ('warning' or 'critical')
    
    Returns:
        int: ID of the newly created alert
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO alerts (student_id, exam_id, reason, severity) VALUES (?, ?, ?, ?)',
            (student_id, exam_id, reason, severity)
        )
        conn.commit()
        alert_id = cursor.lastrowid
        print(f"[DB] Alert added with ID: {alert_id}")
        return alert_id
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to add alert: {e}")
        raise
    finally:
        if conn:
            conn.close()


def add_submission(student_id: int, exam_id: int, answers: Dict, score: int, flagged: bool = False) -> int:
    """
    Add a new submission to the database
    
    Args:
        student_id (int): Student ID
        exam_id (int): Exam ID
        answers (Dict): Student's answers as dictionary
        score (int): Score obtained
    
    Returns:
        int: ID of the newly created submission
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        answers_json = json.dumps(answers)
        cursor.execute(
            'INSERT INTO submissions (student_id, exam_id, answers, score, flagged) VALUES (?, ?, ?, ?, ?)',
            (student_id, exam_id, answers_json, score, 1 if flagged else 0)
        )
        conn.commit()
        submission_id = cursor.lastrowid
        print(f"[DB] Submission added with ID: {submission_id}")
        return submission_id
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to add submission: {e}")
        raise
    finally:
        if conn:
            conn.close()


def add_violation_screenshot(
    alert_id: int,
    student_id: int,
    exam_id: int,
    image_data: str,
    violation_type: str
) -> int:
    """
    Add a violation screenshot to the database
    
    Args:
        alert_id (int): Linked alert ID
        student_id (int): Student ID
        exam_id (int): Exam ID
        image_data (str): Base64 image data
        violation_type (str): Type of violation
    
    Returns:
        int: ID of the newly created screenshot record
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO violation_screenshots
            (alert_id, student_id, exam_id, image_data, violation_type)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (alert_id, student_id, exam_id, image_data, violation_type)
        )
        conn.commit()
        screenshot_id = cursor.lastrowid
        print(f"[DB] Violation screenshot added with ID: {screenshot_id}")
        return screenshot_id
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to add violation screenshot: {e}")
        raise
    finally:
        if conn:
            conn.close()


print("[MODELS] Models module loaded successfully")
