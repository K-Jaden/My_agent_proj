import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent_database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create cached_recruitments table for Work24 API caching (New)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_recruitments (
            emp_seqno TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            salary TEXT,
            close_date TEXT,
            job_type TEXT,
            job_cont TEXT,
            pref_cond TEXT,
            last_cached TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            emp_seqno TEXT,
            company_insights TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Safely alter table to add company_insights column if it does not exist
    try:
        cursor.execute("ALTER TABLE sessions ADD COLUMN company_insights TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Safely alter table to add emp_seqno column if it does not exist
    try:
        cursor.execute("ALTER TABLE sessions ADD COLUMN emp_seqno TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Create experiences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            star_content TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    # Create interview_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_num INTEGER NOT NULL,
            ai_question TEXT NOT NULL,
            ai_hint TEXT,
            user_answer TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    # Create questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            max_chars INTEGER NOT NULL,
            draft_content TEXT,
            refined_content TEXT,
            feedback_report TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

# Cached Recruitments CRUD
def save_cached_recruitments(items):
    """Saves or updates GoYong24 job listings, preserving already cached job details (job_cont, pref_cond)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for item in items:
            cursor.execute("""
                INSERT INTO cached_recruitments (emp_seqno, company, title, salary, close_date, job_type, last_cached)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(emp_seqno) DO UPDATE SET
                    company = excluded.company,
                    title = excluded.title,
                    salary = excluded.salary,
                    close_date = excluded.close_date,
                    job_type = excluded.job_type,
                    last_cached = excluded.last_cached
            """, (
                item["emp_seqno"],
                item["company"],
                item["title"],
                item["salary"],
                item["close_date"],
                item["job_type"]
            ))
        conn.commit()
    finally:
        conn.close()

def get_cached_recruitments():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM cached_recruitments ORDER BY last_cached DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_cached_recruitment(emp_seqno):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM cached_recruitments WHERE emp_seqno = ?", (emp_seqno,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_recruitment_detail(emp_seqno, job_cont, pref_cond):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE cached_recruitments 
            SET job_cont = ?, pref_cond = ?, last_cached = CURRENT_TIMESTAMP
            WHERE emp_seqno = ?
        """, (job_cont, pref_cond, emp_seqno))
        conn.commit()
    finally:
        conn.close()

def get_cache_last_updated():
    """Returns the timestamp of the latest cached recruitment item to assess 1-hour expiration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(last_cached) FROM cached_recruitments")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()

# Sessions CRUD
def create_session(session_id, company, job_title, emp_seqno=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO sessions (id, company, job_title, emp_seqno) VALUES (?, ?, ?, ?)",
            (session_id, company, job_title, emp_seqno)
        )
        conn.commit()
    finally:
        conn.close()

def update_session_emp_seqno(session_id, emp_seqno):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE sessions SET emp_seqno = ? WHERE id = ?",
            (emp_seqno, session_id)
        )
        conn.commit()
    finally:
        conn.close()

def update_session_info(session_id, company, job_title):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE sessions SET company = ?, job_title = ? WHERE id = ?",
            (company, job_title, session_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_session_insights(session_id, company_insights):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE sessions SET company_insights = ? WHERE id = ?",
            (json.dumps(company_insights) if isinstance(company_insights, (dict, list)) else company_insights, session_id)
        )
        conn.commit()
    finally:
        conn.close()

def delete_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

# Experiences CRUD
def save_experience(session_id, raw_content, star_content=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM experiences WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE experiences SET raw_content = ?, star_content = ? WHERE session_id = ?",
                (raw_content, star_content, session_id)
            )
        else:
            cursor.execute(
                "INSERT INTO experiences (session_id, raw_content, star_content) VALUES (?, ?, ?)",
                (session_id, raw_content, star_content)
            )
        conn.commit()
    finally:
        conn.close()

def get_experience(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM experiences WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# Interview Logs CRUD
def save_interview_turn(session_id, turn_num, ai_question, ai_hint, user_answer=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM interview_logs WHERE session_id = ? AND turn_num = ?", 
            (session_id, turn_num)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE interview_logs SET ai_question = ?, ai_hint = ?, user_answer = ? WHERE id = ?",
                (ai_question, ai_hint, user_answer, row["id"])
            )
        else:
            cursor.execute(
                "INSERT INTO interview_logs (session_id, turn_num, ai_question, ai_hint, user_answer) VALUES (?, ?, ?, ?, ?)",
                (session_id, turn_num, ai_question, ai_hint, user_answer)
            )
        conn.commit()
    finally:
        conn.close()

def update_interview_answer(session_id, turn_num, user_answer):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE interview_logs SET user_answer = ? WHERE session_id = ? AND turn_num = ?",
            (user_answer, session_id, turn_num)
        )
        conn.commit()
    finally:
        conn.close()

def get_interview_logs(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM interview_logs WHERE session_id = ? ORDER BY turn_num ASC", (session_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def clear_interview_logs(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM interview_logs WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

# Questions CRUD
def add_question(session_id, question_text, max_chars):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO questions (session_id, question_text, max_chars) VALUES (?, ?, ?)",
            (session_id, question_text, max_chars)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_question_draft(question_id, draft_content):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE questions SET draft_content = ? WHERE id = ?",
            (draft_content, question_id)
        )
        conn.commit()
    finally:
        conn.close()

def update_question_refinement(question_id, refined_content, feedback_report):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE questions SET refined_content = ?, feedback_report = ? WHERE id = ?",
            (refined_content, json.dumps(feedback_report) if isinstance(feedback_report, (dict, list)) else feedback_report, question_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_questions(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM questions WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def clear_questions(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM questions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()
