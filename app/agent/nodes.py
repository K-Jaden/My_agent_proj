import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.agent.state import AgentState
from app.agent.prompts import STAR_PROMPT, JD_ANALYSIS_PROMPT, DRAFT_PROMPT, REVIEW_PROMPT

load_dotenv()

# Initialize Gemini Model
def get_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
    
    # Use gemini-1.5-flash for speed and reliability.
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.7
    )

def parse_json_markdown(text: str) -> dict:
    """Helper to parse JSON from markdown code blocks or raw string."""
    text = text.strip()
    # Remove markdown code blocks if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        json_str = match.group(1).strip()
    else:
        json_str = text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Fallback regex search or simple key-value extraction if parsing fails
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
        error_msg = f"[Stage 1 에러] {str(e)}"
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
        error_msg = f"[Stage 2 에러] {str(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def generate_draft_node(state: AgentState) -> dict:
    """Stage 3: Generate first draft based on STAR experience and JD analysis."""
    logs = list(state.get("logs", []))
    logs.append("[Stage 3] 자소서 초안 생성을 시작합니다.")
    
    star_exp = state.get("star_experience")
    jd = state.get("job_description")
    question = state.get("question_text")
    max_chars = state.get("max_chars", 500)
    
    if not star_exp:
        return {"error": "구조화된 경험 데이터가 없습니다. Stage 1을 먼저 완료해야 합니다.", "logs": logs}
        
    try:
        llm = get_llm()
        prompt = PromptTemplate.from_template(DRAFT_PROMPT).format(
            star_experience=star_exp,
            job_description=jd,
            question_text=question,
            max_chars=max_chars
        )
        response = llm.invoke(prompt)
        draft_text = response.content.strip()
        logs.append("[Stage 3] 초안 생성이 완료되었습니다.")
        return {
            "draft": draft_text,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[Stage 3 에러] {str(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}

def review_draft_node(state: AgentState) -> dict:
    """Stage 4: Evaluate the draft and generate refined version with comments."""
    logs = list(state.get("logs", []))
    logs.append("[Stage 4] 초안 첨삭 및 평가 작업을 시작합니다.")
    
    draft = state.get("draft")
    jd = state.get("job_description")
    question = state.get("question_text")
    max_chars = state.get("max_chars", 500)
    
    if not draft:
        return {"error": "작성된 초안이 없습니다. Stage 3를 먼저 완료해야 합니다.", "logs": logs}
        
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
        
        logs.append("[Stage 4] 첨삭 및 평가 보고서 생성이 완료되었습니다. 최종 결과 준비 완료.")
        return {
            "refined_draft": refined_draft,
            "feedback": feedback,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"[Stage 4 에러] {str(e)}"
        logs.append(error_msg)
        return {"error": error_msg, "logs": logs}
