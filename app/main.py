import os
import uuid
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import (
    init_db,
    create_session,
    get_sessions,
    get_session,
    delete_session,
    save_experience,
    get_experience,
    add_question,
    update_question_draft,
    update_question_refinement,
    get_questions,
    clear_questions
)
from app.agent.nodes import (
    structure_experience_node,
    analyze_jd_node,
    generate_draft_node,
    review_draft_node
)
import pypdf

app = FastAPI(title="나만의 자소서 에이전트")

# Ensure DB and Uploads directories exist
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static and templates
templates_dir = os.path.join(BASE_DIR, "app", "templates")
static_dir = os.path.join(BASE_DIR, "app", "static")
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

# We will create these directories if they don't exist
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

@app.on_event("startup")
def startup_event():
    init_db()

# Models
class SessionCreate(BaseModel):
    company: str
    job_title: str

# Helper to extract PDF text
def extract_text_from_pdf(file_path: str) -> str:
    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 텍스트 추출 중 오류가 발생했습니다: {str(e)}")

# Page Routes
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Session API
@app.post("/api/sessions")
def api_create_session(data: SessionCreate):
    session_id = str(uuid.uuid4())[:8] # short unique id
    create_session(session_id, data.company, data.job_title)
    return {"id": session_id, "company": data.company, "job_title": data.job_title}

@app.get("/api/sessions")
def api_get_sessions():
    return get_sessions()

@app.get("/api/sessions/{session_id}")
def api_get_session_detail(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    experience = get_experience(session_id)
    questions = get_questions(session_id)
    
    return {
        "session": session,
        "experience": experience,
        "questions": questions
    }

@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str):
    delete_session(session_id)
    return {"status": "success"}

# Experience API
@app.post("/api/sessions/{session_id}/experience")
async def api_save_experience(
    session_id: str,
    raw_content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    combined_content = raw_content or ""
    
    if file:
        file_ext = os.path.splitext(file.filename)[1].lower()
        temp_file_path = os.path.join(UPLOAD_DIR, f"{session_id}_{file.filename}")
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            if file_ext == ".pdf":
                extracted = extract_text_from_pdf(temp_file_path)
                combined_content = (combined_content + "\n\n" + extracted).strip()
            elif file_ext in [".txt", ".md"]:
                with open(temp_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    extracted = f.read()
                    combined_content = (combined_content + "\n\n" + extracted).strip()
            else:
                raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. (.pdf, .txt, .md만 가능)")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    if not combined_content.strip():
        raise HTTPException(status_code=400, detail="입력된 텍스트나 업로드된 파일의 내용이 비어있습니다.")
        
    # Save raw experience to DB
    save_experience(session_id, combined_content, star_content=None)
    return {"status": "success", "raw_content": combined_content}

# Agent Workflow Steps
@app.post("/api/sessions/{session_id}/step1_star")
def api_step1_star(session_id: str):
    experience = get_experience(session_id)
    if not experience or not experience.get("raw_content"):
        raise HTTPException(status_code=400, detail="경험 데이터가 없습니다. 먼저 등록해주세요.")
        
    # Run Agent Stage 1 Node
    state = {
        "raw_experience": experience["raw_content"],
        "logs": []
    }
    result = structure_experience_node(state)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # Save the structured STAR back to DB
    save_experience(session_id, experience["raw_content"], result["star_experience"])
    return {
        "status": "success",
        "star_experience": result["star_experience"],
        "logs": result["logs"]
    }

@app.post("/api/sessions/{session_id}/step2_analyze")
def api_step2_analyze(
    session_id: str,
    question_text: str = Form(...),
    max_chars: int = Form(500)
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    # Run Agent Stage 2 Node
    state = {
        "job_description": f"회사: {session['company']}\n직무: {session['job_title']}",
        "question_text": question_text,
        "logs": []
    }
    result = analyze_jd_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # We clear old questions for this session and add the new one
    clear_questions(session_id)
    question_id = add_question(session_id, question_text, max_chars)
    
    return {
        "status": "success",
        "question_id": question_id,
        "jd_analysis": result["jd_analysis"],
        "logs": result["logs"]
    }

@app.post("/api/questions/{question_id}/step3_draft")
def api_step3_draft(question_id: int):
    # Fetch question and session details
    conn = app.state.db_connection() if hasattr(app.state, "db_connection") else None # SQLite fallback
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*, s.company, s.job_title, e.star_content 
        FROM questions q
        JOIN sessions s ON q.session_id = s.id
        LEFT JOIN experiences e ON s.id = e.session_id
        WHERE q.id = ?
    """, (question_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="질문 정보를 찾을 수 없습니다.")
        
    question_data = dict(row)
    if not question_data.get("star_content"):
        raise HTTPException(status_code=400, detail="구조화된 STAR 경험 데이터가 존재하지 않습니다. 1단계를 완료해 주세요.")
        
    # Run Agent Stage 3 Node
    state = {
        "star_experience": question_data["star_content"],
        "job_description": f"회사: {question_data['company']}\n직무: {question_data['job_title']}",
        "question_text": question_data["question_text"],
        "max_chars": question_data["max_chars"],
        "logs": []
    }
    result = generate_draft_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # Save draft
    update_question_draft(question_id, result["draft"])
    return {
        "status": "success",
        "draft": result["draft"],
        "logs": result["logs"]
    }

@app.post("/api/questions/{question_id}/step4_review")
def api_step4_review(question_id: int):
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*, s.company, s.job_title 
        FROM questions q
        JOIN sessions s ON q.session_id = s.id
        WHERE q.id = ?
    """, (question_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="질문 정보를 찾을 수 없습니다.")
        
    question_data = dict(row)
    if not question_data.get("draft_content"):
        raise HTTPException(status_code=400, detail="초안이 없습니다. 3단계를 먼저 실행해 주세요.")
        
    # Run Agent Stage 4 Node
    state = {
        "draft": question_data["draft_content"],
        "job_description": f"회사: {question_data['company']}\n직무: {question_data['job_title']}",
        "question_text": question_data["question_text"],
        "max_chars": question_data["max_chars"],
        "logs": []
    }
    result = review_draft_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # Save refinement and feedback
    update_question_refinement(question_id, result["refined_draft"], result["feedback"])
    return {
        "status": "success",
        "refined_draft": result["refined_draft"],
        "feedback": result["feedback"],
        "logs": result["logs"]
    }

@app.post("/api/questions/{question_id}/apply_refined")
def api_apply_refined(question_id: int):
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT refined_draft FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        if not row or not row["refined_draft"]:
            raise HTTPException(status_code=400, detail="적용할 첨삭 개선안이 존재하지 않습니다.")
            
        refined = row["refined_draft"]
        # Update draft_content with refined_draft
        cursor.execute("UPDATE questions SET draft_content = ? WHERE id = ?", (refined, question_id))
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "success", "draft_content": refined}
