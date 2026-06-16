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
    
    # Create sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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

def create_session(session_id, company, job_title):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO sessions (id, company, job_title) VALUES (?, ?, ?)",
            (session_id, company, job_title)
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

def delete_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

def save_experience(session_id, raw_content, star_content=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if experience already exists for this session
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
