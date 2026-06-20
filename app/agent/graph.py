from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.nodes import (
    structure_experience_node,
    analyze_jd_node,
    generate_interview_question_node,
    generate_final_draft_node,
    review_draft_node
)

def create_agent_graph():
    # 1. Initialize StateGraph
    workflow = StateGraph(AgentState)
    
    # 2. Add nodes
    workflow.add_node("structure_experience", structure_experience_node)
    workflow.add_node("analyze_jd", analyze_jd_node)
    workflow.add_node("generate_interview_question", generate_interview_question_node)
    workflow.add_node("generate_final_draft", generate_final_draft_node)
    workflow.add_node("review_draft", review_draft_node)
    
    # 3. Add edges (Linear workflow representation)
    workflow.add_edge(START, "structure_experience")
    workflow.add_edge("structure_experience", "analyze_jd")
    workflow.add_edge("analyze_jd", "generate_interview_question")
    workflow.add_edge("generate_interview_question", "generate_final_draft")
    workflow.add_edge("generate_final_draft", "review_draft")
    workflow.add_edge("review_draft", END)
    
    # 4. Compile
    app = workflow.compile()
    return app

agent_graph = create_agent_graph()
