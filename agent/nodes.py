"""Node functions for the ReAct agent graph."""
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from agent.state import AgentState
from agent.prompts import REACT_SYSTEM_PROMPT
from utils.config import MAX_ITERATIONS, OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL
from utils.parser import ReActParser, ReActStep
from utils.logger import TraceLogger

# Initialize parser
parser = ReActParser()


_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            temperature=0.1,
        )
    return _llm


def think_node(state: AgentState) -> dict[str, Any]:
    """LLM thinks about next step."""
    messages = [SystemMessage(content=REACT_SYSTEM_PROMPT)]
    
    # Build conversation history from state
    query = state["query"]
    messages.append(HumanMessage(content=f"Question: {query}"))
    
    # Add previous steps as context
    for i in range(len(state["thoughts"])):
        thought = state["thoughts"][i]
        action = state["actions"][i] if i < len(state["actions"]) else ""
        action_input = state["action_inputs"][i] if i < len(state["action_inputs"]) else ""
        observation = state["observations"][i] if i < len(state["observations"]) else ""
        
        messages.append(AIMessage(content=f"Thought: {thought}\nAction: {action}\nAction Input: {action_input}"))
        messages.append(HumanMessage(content=f"Observation: {observation}"))
    
    # Call LLM
    response = _get_llm().invoke(messages)
    content = response.content
    
    # Parse the response
    step = parser.parse(content)
    
    # Handle malformed output
    if step.is_malformed:
        return {
            "thoughts": state["thoughts"] + ["Error: Malformed output from LLM."],
            "actions": state["actions"] + [""],
            "action_inputs": state["action_inputs"] + [""],
            "current_step": state["current_step"] + 1,
        }
    
    # If final answer detected, capture it
    if step.final_answer is not None:
        return {
            "thoughts": state["thoughts"] + [step.thought or "Final answer provided."],
            "actions": state["actions"],
            "action_inputs": state["action_inputs"],
            "current_step": state["current_step"] + 1,
            "final_answer": step.final_answer,
        }
    
    return {
        "thoughts": state["thoughts"] + [step.thought],
        "actions": state["actions"] + ([step.action] if step.action else []),
        "action_inputs": state["action_inputs"] + ([step.action_input] if step.action_input else []),
        "current_step": state["current_step"] + 1,
    }


def execute_tool_node(state: AgentState) -> dict[str, Any]:
    """Execute the tool called by the LLM."""
    if not state["actions"]:
        return {"observations": state["observations"] + ["Error: No action specified"]}
    
    current_idx = len(state["observations"])
    if current_idx >= len(state["actions"]):
        return {"observations": state["observations"] + ["Error: Action index out of range"]}
    
    action = state["actions"][current_idx]
    action_input = state["action_inputs"][current_idx] if current_idx < len(state["action_inputs"]) else ""
    
    # Check for duplicate tool calls
    cache_key = f"{action}|{action_input}"
    if cache_key in state["tool_call_cache"]:
        cached_obs = state["tool_call_cache"][cache_key]
        return {
            "observations": state["observations"] + [f"{cached_obs}\n[Note: This is a cached result from a previous identical tool call.]"],
        }
    
    # Import tools dynamically
    if action == "calculator":
        from tools.calculator import run as calc_run
        observation = calc_run(action_input)
    elif action == "knowledge_lookup":
        from tools.knowledge_lookup import run as kb_run
        observation = kb_run(action_input)
    elif action == "web_search":
        from tools.web_search import run as web_run
        observation = web_run(action_input)
    else:
        observation = f"Error: Unknown tool '{action}'. Available tools: calculator, knowledge_lookup, web_search."
    
    # Cache the result
    new_cache = dict(state["tool_call_cache"])
    new_cache[cache_key] = observation
    
    return {
        "observations": state["observations"] + [observation],
        "tool_call_cache": new_cache,
    }


def should_continue_edge(state: AgentState) -> str:
    """Decide whether to continue the loop or end."""
    # Check iteration limit
    if state["current_step"] >= MAX_ITERATIONS:
        return "end"
    
    # Check if we have a final answer
    if state["final_answer"] is not None:
        return "end"
    
    # Check if the last action was empty (final answer detected in think_node)
    # Actually, we need to check if the last thought contained a Final Answer
    # This is handled by checking if there's no action for the last thought
    if len(state["thoughts"]) > len(state["actions"]):
        # Last thought was a final answer (no action generated)
        return "end"
    
    return "continue"


def format_final_answer_node(state: AgentState) -> dict[str, Any]:
    """Format the final answer from the state."""
    if state["final_answer"]:
        return {"final_answer": state["final_answer"]}
    
    # Extract final answer from the last thought if not explicitly set
    if state["thoughts"]:
        last_thought = state["thoughts"][-1]
        # Try to extract Final Answer from the thought
        if "Final Answer:" in last_thought:
            answer = last_thought.split("Final Answer:")[-1].strip()
            return {"final_answer": answer}
        return {"final_answer": last_thought}
    
    return {"final_answer": "No answer could be generated."}
