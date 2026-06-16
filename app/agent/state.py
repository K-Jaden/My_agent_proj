from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    # Inputs
    raw_experience: str
    job_description: str
    question_text: str
    max_chars: int
    
    # Outputs/Intermediates
    star_experience: Optional[str]
    jd_analysis: Optional[Dict[str, Any]]
    draft: Optional[str]
    refined_draft: Optional[str]
    feedback: Optional[Dict[str, Any]]
    
    # Process management
    logs: List[str]
    error: Optional[str]
