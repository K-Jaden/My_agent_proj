from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.nodes import (
    structure_experience_node,
    analyze_jd_node,
    generate_draft_node,
    review_draft_node
)

def create_agent_graph():
    # 1. Initialize the StateGraph with the AgentState TypedDict
    workflow = StateGraph(AgentState)
    
    # 2. Add all nodes
    workflow.add_node("structure_experience", structure_experience_node)
    workflow.add_node("analyze_jd", analyze_jd_node)
    workflow.add_node("generate_draft", generate_draft_node)
    workflow.add_node("review_draft", review_draft_node)
    
    # 3. Add edges (Linear workflow)
    workflow.add_edge(START, "structure_experience")
    workflow.add_edge("structure_experience", "analyze_jd")
    workflow.add_edge("analyze_jd", "generate_draft")
    workflow.add_edge("generate_draft", "review_draft")
    workflow.add_edge("review_draft", END)
    
    # 4. Compile the graph
    app = workflow.compile()
    return app

# Compile a default instance of the graph
agent_graph = create_agent_graph()
