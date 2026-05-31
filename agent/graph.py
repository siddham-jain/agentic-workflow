"""LangGraph StateGraph for the ReAct agent."""
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import think_node, execute_tool_node, should_continue_edge, format_final_answer_node


def create_agent_graph():
    """Create and return the ReAct agent StateGraph."""
    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("think", think_node)
    workflow.add_node("execute_tool", execute_tool_node)
    workflow.add_node("format_final_answer", format_final_answer_node)
    
    # Add edges
    workflow.set_entry_point("think")
    workflow.add_conditional_edges(
        "think",
        should_continue_edge,
        {
            "continue": "execute_tool",
            "end": "format_final_answer",
        },
    )
    workflow.add_edge("execute_tool", "think")
    workflow.add_edge("format_final_answer", END)
    
    return workflow.compile()
