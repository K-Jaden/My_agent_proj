import os
import uuid
import shutil
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import (
    init_db,
    create_session,
    get_sessions,
    get_session,
    update_session_insights,
    delete_session,
    save_experience,
    get_experience,
    add_question,
    update_question_draft,
    update_question_refinement,
    get_questions,
    clear_questions,
    save_interview_turn,
    update_interview_answer,
    get_interview_logs,
    clear_interview_logs
)
from app.agent.nodes import (
    structure_experience_node,
    analyze_jd_node,
    generate_interview_question_node,
    generate_final_draft_node,
    review_draft_node
)
from app.goyong_api import fetch_recruitment_list, fetch_recruitment_detail
from app.naver_api import fetch_company_insights
import pypdf

app = FastAPI(title="나만의 자소서 에이전트")

# Ensure directories exist
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

templates_dir = os.path.join(BASE_DIR, "app", "templates")
static_dir = os.path.join(BASE_DIR, "app", "static")
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)
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

def get_augmented_job_description(session) -> str:
    from app.database import get_cached_recruitment
    jd_desc = f"회사: {session['company']}\n직무: {session['job_title']}"
    if session.get("emp_seqno"):
        rec_detail = get_cached_recruitment(session["emp_seqno"])
        if rec_detail:
            if rec_detail.get("job_cont"):
                jd_desc += f"\n\n[상세 직무내용]\n{rec_detail['job_cont']}"
            if rec_detail.get("pref_cond"):
                jd_desc += f"\n\n[우대/자격요건]\n{rec_detail['pref_cond']}"
    return jd_desc

# Public recruitment list
@app.get("/api/goyong/recruitments")
def api_get_recruitments():
    from datetime import datetime, timedelta
    from app.database import get_cache_last_updated, get_cached_recruitments
    
    last_updated_str = get_cache_last_updated()
    should_refresh = True
    if last_updated_str:
        try:
            last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_updated < timedelta(hours=1):
                should_refresh = False
        except Exception as e:
            print(f"[Main Cache Check Exception] {e}")
            
    if should_refresh:
        print("[Main Cache] Cache expired or missing. Fetching online from GoYong24...")
        fetch_recruitment_list()
    else:
        print("[Main Cache] Cache is valid (less than 1 hour old). Serving from SQLite.")
        
    return get_cached_recruitments()

# Session API
@app.post("/api/sessions")
def api_create_session(data: SessionCreate):
    session_id = str(uuid.uuid4())[:8]
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
    interview_logs = get_interview_logs(session_id)
    
    # Parse company insights if available
    insights = None
    if session.get("company_insights"):
        try:
            insights = json.loads(session["company_insights"])
        except Exception:
            insights = session["company_insights"]

    # Fetch cached recruitment detail if emp_seqno is present
    recruitment_detail = None
    if session.get("emp_seqno"):
        from app.database import get_cached_recruitment
        recruitment_detail = get_cached_recruitment(session["emp_seqno"])

    return {
        "session": session,
        "company_insights": insights,
        "recruitment_detail": recruitment_detail,
        "experience": experience,
        "questions": questions,
        "interview_logs": interview_logs
    }

@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str):
    delete_session(session_id)
    return {"status": "success"}

# Save Experience API
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
        raise HTTPException(status_code=400, detail="입력된 내용이 비어있습니다.")
        
    save_experience(session_id, combined_content, star_content=None)
    return {"status": "success", "raw_content": combined_content}

# Company Naver Search Analysis API
@app.post("/api/sessions/{session_id}/analyze-company")
def api_analyze_company(
    session_id: str,
    company_name: str = Form(...),
    emp_seqno: Optional[str] = Form(None)
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    # If emp_seqno is provided, associate it with the session and load detail to cache
    if emp_seqno:
        from app.database import update_session_emp_seqno
        update_session_emp_seqno(session_id, emp_seqno)
        # Fetch detailed content online if not cached (Lazy Loading Cache)
        fetch_recruitment_detail(emp_seqno)
        
    # Run Naver & LLM analysis
    insights = fetch_company_insights(company_name)
    update_session_insights(session_id, insights)
    
    # Update session company info in DB
    from app.database import update_session_info
    update_session_info(session_id, company_name, session["job_title"])
    
    return {"status": "success", "company_insights": insights}

# Match and Recommend Job listings based on experience
@app.post("/api/sessions/{session_id}/recommend-jobs")
def api_recommend_jobs(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    experience = get_experience(session_id)
    if not experience or not experience.get("raw_content"):
        return {"status": "success", "total_matching_count": 0, "recommendations": []}
        
    from app.database import get_cached_recruitments
    from app.agent.nodes import recommend_jobs_node
    
    # Get all cached listings from DB
    listings = get_cached_recruitments()
    if not listings:
        return {"status": "success", "total_matching_count": 0, "recommendations": []}
        
    user_exp = experience["raw_content"]
    
    # Run LLM analysis node to get matching_seqnos and recommendations
    result = recommend_jobs_node(user_exp, listings)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    matching_seqnos = result.get("matching_seqnos", [])
    recommendations_raw = result.get("recommendations", [])
    
    # Compile the detailed objects for recommendations
    recommendations = []
    for rec in recommendations_raw:
        seqno = rec.get("emp_seqno")
        reason = rec.get("reason", "적합한 직무로 판단됩니다.")
        
        # Find matching cached listing details
        job_info = next((job for job in listings if job["emp_seqno"] == seqno), None)
        if job_info:
            recommendations.append({
                "emp_seqno": seqno,
                "company": job_info["company"],
                "title": job_info["title"],
                "job_type": job_info["job_type"],
                "reason": reason
            })
            
    # Calculate matching count
    valid_matching_seqnos = [seq for seq in matching_seqnos if any(job["emp_seqno"] == seq for job in listings)]
    total_matching_count = len(valid_matching_seqnos)
    
    # If LLM matching count is 0 but there are recommendations, fallback
    if total_matching_count == 0 and recommendations:
        total_matching_count = len(recommendations)
        
    return {
        "status": "success",
        "total_matching_count": total_matching_count,
        "recommendations": recommendations
    }

# Step 2: JD & Question analysis
@app.post("/api/sessions/{session_id}/step2_analyze")
def api_step2_analyze(
    session_id: str,
    question_text: str = Form(...),
    max_chars: int = Form(500),
    company: str = Form("미정"),
    job_title: str = Form("미정")
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    from app.database import update_session_info
    update_session_info(session_id, company, job_title)
        
    # Analyze JD & question core intent (augmented with GoYong24 job description details)
    state = {
        "job_description": get_augmented_job_description(session),
        "question_text": question_text,
        "logs": []
    }
    result = analyze_jd_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    clear_questions(session_id)
    # Also reset interview logs since questions changed
    clear_interview_logs(session_id)
    
    question_id = add_question(session_id, question_text, max_chars)
    
    return {
        "status": "success",
        "question_id": question_id,
        "jd_analysis": result["jd_analysis"],
        "logs": result["logs"]
    }

# Step 3: Interactive Interview APIs
@app.post("/api/sessions/{session_id}/interview/next")
def api_interview_next(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    experience = get_experience(session_id)
    raw_exp = experience["raw_content"] if experience else ""
    
    # Get active question
    questions = get_questions(session_id)
    if not questions:
        raise HTTPException(status_code=400, detail="문항 정보가 등록되지 않았습니다. 2단계를 완료해 주세요.")
    active_question = questions[0]
    
    # Get insights
    insights = {}
    if session.get("company_insights"):
        try:
            insights = json.loads(session["company_insights"])
        except Exception:
            insights = session["company_insights"]
            
    # Calculate turn
    logs = get_interview_logs(session_id)
    current_turn = len(logs) + 1
    
    if current_turn > 1:
        # Check if the first turn is answered
        if len(logs) == 1 and logs[0].get("user_answer"):
            return {"status": "completed", "message": "모든 면접 질문에 답했습니다. 초안을 생성해 주세요."}
        elif len(logs) == 1:
            # We are waiting for the first answer
            return {
                "status": "waiting",
                "turn": 1,
                "question": logs[0]["ai_question"],
                "hint": logs[0]["ai_hint"]
            }
        raise HTTPException(status_code=400, detail="이미 1회 대화가 끝났습니다. 다음 단계로 넘어가 주세요.")
        
    # Format logs for agent
    formatted_turns = []
    for log in logs:
        formatted_turns.append({
            "turn": log["turn_num"],
            "q": log["ai_question"],
            "hint": log.get("ai_hint"),
            "intent": log.get("ai_intent"),
            "a": log.get("user_answer") or ""
        })

    # Compile state for interviewer agent (augmented with GoYong24 job description details)
    state = {
        "raw_experience": raw_exp,
        "company_insights": insights,
        "job_description": get_augmented_job_description(session),
        "question_text": active_question["question_text"],
        "interview_turns": formatted_turns,
        "current_turn": current_turn,
        "logs": []
    }
    
    result = generate_interview_question_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # Find the newly generated question
    new_turn = next(t for t in result["interview_turns"] if t["turn"] == current_turn)
    
    # Save to SQLite (with new intent parameter)
    save_interview_turn(session_id, current_turn, new_turn["q"], new_turn["hint"], ai_intent=new_turn.get("intent", ""))
    
    return {
        "status": "success",
        "turn": current_turn,
        "question": new_turn["q"],
        "hint": new_turn["hint"],
        "intent": new_turn.get("intent", "")
    }

@app.post("/api/sessions/{session_id}/interview/submit-answer")
def api_interview_submit_answer(
    session_id: str,
    turn_num: int = Form(...),
    answer: str = Form(...)
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
    update_interview_answer(session_id, turn_num, answer.strip())
    return {"status": "success"}

# Step 4: Final Draft Compilation
@app.post("/api/questions/{question_id}/step3_draft")
def api_step3_draft(question_id: int):
    # Fetch details
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*, s.company, s.job_title, s.emp_seqno, s.company_insights, e.raw_content
        FROM questions q
        JOIN sessions s ON q.session_id = s.id
        LEFT JOIN experiences e ON s.id = e.session_id
        WHERE q.id = ?
    """, (question_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="질문 정보를 찾을 수 없습니다.")
        
    q_data = dict(row)
    session_id = q_data["session_id"]
    
    # Fetch all interview turns
    logs = get_interview_logs(session_id)
    if len(logs) < 1 or not all(turn.get("user_answer") for turn in logs):
        raise HTTPException(status_code=400, detail="1회 면접 질문에 모두 답변해야 초안 작성이 가능합니다.")
        
    # Parse insights
    insights = {}
    if q_data.get("company_insights"):
        try:
            insights = json.loads(q_data["company_insights"])
        except Exception:
            insights = q_data["company_insights"]
            
    # Format logs for agent
    formatted_turns = []
    for log in logs:
        formatted_turns.append({
            "turn": log["turn_num"],
            "q": log["ai_question"],
            "hint": log.get("ai_hint"),
            "intent": log.get("ai_intent"),
            "a": log.get("user_answer") or ""
        })

    # Run Agent node to compile final draft (augmented with GoYong24 job description details)
    session_dict = {
        "company": q_data["company"],
        "job_title": q_data["job_title"],
        "emp_seqno": q_data["emp_seqno"]
    }
    state = {
        "raw_experience": q_data["raw_content"] or "",
        "company_insights": insights,
        "job_description": get_augmented_job_description(session_dict),
        "question_text": q_data["question_text"],
        "max_chars": q_data["max_chars"],
        "interview_turns": formatted_turns,
        "logs": []
    }
    
    result = generate_final_draft_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    update_question_draft(question_id, result["draft"])
    return {
        "status": "success",
        "draft": result["draft"],
        "logs": result["logs"]
    }

# Step 5: Review & Feedback
@app.post("/api/questions/{question_id}/step4_review")
def api_step4_review(question_id: int):
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*, s.company, s.job_title, s.emp_seqno
        FROM questions q
        JOIN sessions s ON q.session_id = s.id
        WHERE q.id = ?
    """, (question_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="질문 정보를 찾을 수 없습니다.")
        
    q_data = dict(row)
    if not q_data.get("draft_content"):
        raise HTTPException(status_code=400, detail="초안이 작성되어 있지 않습니다. 이전 단계를 완료해 주세요.")
        
    session_dict = {
        "company": q_data["company"],
        "job_title": q_data["job_title"],
        "emp_seqno": q_data["emp_seqno"]
    }
    state = {
        "draft": q_data["draft_content"],
        "job_description": get_augmented_job_description(session_dict),
        "question_text": q_data["question_text"],
        "max_chars": q_data["max_chars"],
        "logs": []
    }
    
    result = review_draft_node(state)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
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
        cursor.execute("SELECT refined_content FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        if not row or not row["refined_content"]:
            raise HTTPException(status_code=400, detail="적용할 첨삭 개선안이 존재하지 않습니다.")
            
        refined = row["refined_content"]
        cursor.execute("UPDATE questions SET draft_content = ? WHERE id = ?", (refined, question_id))
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "success", "draft_content": refined}
