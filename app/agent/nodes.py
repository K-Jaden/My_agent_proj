import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.agent.state import AgentState
from app.agent.prompts import (
    STAR_PROMPT,
    JD_ANALYSIS_PROMPT,
    INTERVIEW_QUESTION_PROMPT,
    FINAL_DRAFT_PROMPT,
    REVIEW_PROMPT,
    RECOMMEND_JOBS_PROMPT
)

load_dotenv()

def get_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=0.7
    )

def handle_agent_error(e: Exception) -> str:
    err_str = str(e)
    if "leaked" in err_str or "API key was reported as leaked" in err_str:
        return "Gemini API 키가 유출되어 비활성화되었습니다. 프로젝트 루트의 .env 파일에서 새로운 GEMINI_API_KEY를 설정해 주세요."
    if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
        return "유효하지 않은 Gemini API 키입니다. .env 파일의 GEMINI_API_KEY를 확인해 주세요."
    return err_str

def parse_json_markdown(text: str) -> dict:
    """Helper to parse JSON from markdown code blocks or raw string."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        json_str = match.group(1).strip()
    else:
        json_str = text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n원본 텍스트: {text}")

def structure_experience_node(state: AgentState) -> dict:
    """Stage 1: Convert raw experience to STAR format."""
    logs = list(state.get("logs", []))
    logs.append("[Stage 1] 경험 구조화(STAR) 작업을 시작합니다.")
    
    raw_exp = state.get("raw_experience", "").strip()
    if not raw_exp:
        return {"error": "경험 데이터가 입력되지 않았습니다.", "logs": logs}
        
    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(STAR_PROMPT).format(raw_experience=raw_exp)
        response = llm.invoke(prompt)
        star_result = response.content
        logs.append("[Stage 1] 경험 STAR 구조화 작성이 완료되었습니다.")
        return {
            "star_experience": star_result,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[Stage 1 에러] {handle_agent_error(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def analyze_jd_node(state: AgentState) -> dict:
    """Stage 2: Analyze Job Description and Question."""
    logs = list(state.get("logs", []))
    logs.append("[Stage 2] 채용 공고(JD) 및 자소서 문항 분석을 시작합니다.")
    
    jd = state.get("job_description", "").strip()
    question = state.get("question_text", "").strip()
    
    if not jd or not question:
        return {"error": "채용 공고 또는 문항이 입력되지 않았습니다.", "logs": logs}
        
    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(JD_ANALYSIS_PROMPT).format(
            job_description=jd,
            question_text=question
        )
        response = llm.invoke(prompt)
        analysis_data = parse_json_markdown(response.content)
        logs.append("[Stage 2] 공고 및 문항 분석이 완료되었습니다.")
        return {
            "jd_analysis": analysis_data,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[Stage 2 에러] {handle_agent_error(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def generate_interview_question_node(state: AgentState) -> dict:
    """New Stage: Generate sequential guiding interview questions (1 to 3)."""
    logs = list(state.get("logs", []))
    current_turn = state.get("current_turn", 1)
    logs.append(f"[면접 가이드] {current_turn}/3번째 유도 질문을 생성합니다.")
    
    raw_experience = state.get("raw_experience", "")
    company_insights = state.get("company_insights", {})
    job_description = state.get("job_description", "")
    question_text = state.get("question_text", "")
    interview_turns = state.get("interview_turns", []) or []
    
    # Format previous history
    history_lines = []
    for turn in interview_turns:
        if turn.get("a"):
            history_lines.append(f"Q: {turn.get('q')}\nA: {turn.get('a')}")
    history_text = "\n\n".join(history_lines) if history_lines else "이전 대화 없음"
    
    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(INTERVIEW_QUESTION_PROMPT).format(
            raw_experience=raw_experience,
            company_insights=json.dumps(company_insights, ensure_ascii=False),
            job_description=job_description,
            question_text=question_text,
            current_turn=current_turn,
            history_text=history_text
        )
        response = llm.invoke(prompt)
        result_data = parse_json_markdown(response.content)
        
        q_text = result_data.get("question", "질문 생성 실패")
        hint_text = result_data.get("hint", "가이드라인이 없습니다.")
        intent_text = result_data.get("intent", "")
        
        # Build new turn data
        updated_turns = list(interview_turns)
        # Find if turn already exists to overwrite, otherwise append
        existing_index = next((i for i, t in enumerate(updated_turns) if t.get("turn") == current_turn), None)
        
        turn_data = {
            "turn": current_turn,
            "q": q_text,
            "hint": hint_text,
            "intent": intent_text,
            "a": ""
        }
        
        if existing_index is not None:
            updated_turns[existing_index] = turn_data
        else:
            updated_turns.append(turn_data)
            
        logs.append(f"[면접 가이드] {current_turn}/3번째 질문 생성 완료.")
        return {
            "interview_turns": updated_turns,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[질문 생성 에러] {handle_agent_error(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def generate_final_draft_node(state: AgentState) -> dict:
    """Stage 3: Generate first draft based on resume, company insights, and 3 interview QA logs."""
    logs = list(state.get("logs", []))
    logs.append("[Stage 3] 면접 답변을 종합하여 최종 자소서 작성을 시작합니다.")
    
    raw_experience = state.get("raw_experience", "")
    company_insights = state.get("company_insights", {})
    job_description = state.get("job_description", "")
    question_text = state.get("question_text", "")
    max_chars = state.get("max_chars", 500)
    interview_turns = state.get("interview_turns", []) or []
    
    # Format QA logs
    qa_lines = []
    for turn in sorted(interview_turns, key=lambda x: x.get("turn", 0)):
        q = turn.get("q", "")
        a = turn.get("a", "")
        qa_lines.append(f"[질문 {turn.get('turn')}]: {q}\n[답변]: {a}")
    interview_text = "\n\n".join(qa_lines)
    
    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(FINAL_DRAFT_PROMPT).format(
            raw_experience=raw_experience,
            company_insights=json.dumps(company_insights, ensure_ascii=False),
            job_description=job_description,
            question_text=question_text,
            interview_text=interview_text,
            max_chars=max_chars
        )
        response = llm.invoke(prompt)
        draft_text = response.content.strip()
        logs.append("[Stage 3] 최종 자소서 작성이 완료되었습니다.")
        return {
            "draft": draft_text,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[최종 자소서 작성 에러] {handle_agent_error(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def review_draft_node(state: AgentState) -> dict:
    """Stage 4: Evaluate the draft and generate refined version with comments."""
    logs = list(state.get("logs", []))
    logs.append("[Stage 4] 최종 완성본 교정 및 첨삭 리포트 생성을 시작합니다.")
    
    draft = state.get("draft")
    jd = state.get("job_description")
    question = state.get("question_text")
    max_chars = state.get("max_chars", 500)
    
    if not draft:
        return {"error": "작성된 자소서가 없습니다.", "logs": logs}
        
    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(REVIEW_PROMPT).format(
            draft=draft,
            job_description=jd,
            question_text=question,
            max_chars=max_chars
        )
        response = llm.invoke(prompt)
        review_data = parse_json_markdown(response.content)
        
        scores = review_data.get("scores", {"readability": 80, "logic": 80, "job_fit": 80})
        comments = review_data.get("comments", [])
        refined_draft = review_data.get("refined_draft", draft)
        
        feedback = {
            "scores": scores,
            "comments": comments
        }
        
        logs.append("[Stage 4] 수석 평가관 평가서 작성이 끝났습니다. 전체 과정이 완료되었습니다.")
        return {
            "refined_draft": refined_draft,
            "feedback": feedback,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[첨삭 평가 에러] {handle_agent_error(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def recommend_jobs_node(user_experience: str, job_listings: list) -> dict:
    """
    Compares the user's experience details against all cached recruitments
    and returns matching job ids and the top 3 recommendations.
    """
    if not user_experience.strip() or not job_listings:
        return {"matching_seqnos": [], "recommendations": []}

    # Format the listings into a compact string to fit in the context window
    listings_text = ""
    for job in job_listings:
        listings_text += f"- ID: {job['emp_seqno']} | Company: {job['company']} | Title: {job['title']} | Job Type: {job['job_type']}\n"

    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(RECOMMEND_JOBS_PROMPT).format(
            user_experience=user_experience,
            job_listings=listings_text
        )
        response = llm.invoke(prompt)
        result_data = parse_json_markdown(response.content)
        return {
            "matching_seqnos": result_data.get("matching_seqnos", []),
            "recommendations": result_data.get("recommendations", [])
        }
    except Exception as e:
        print(f"[recommend_jobs_node Exception] {e}")
        return {
            "error": handle_agent_error(e),
            "matching_seqnos": [],
            "recommendations": []
        }

