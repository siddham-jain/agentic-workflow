"""Self-correction module that verifies agent traces and re-runs steps if issues are found."""
import json
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from agent.state import AgentState
from agent.prompts import SELF_CORRECTION_PROMPT
from utils.config import MAX_CORRECTION_CYCLES, OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL
from utils.logger import TraceLogger


class SelfCorrection:
    """Verifies agent execution traces and re-runs steps when issues are found."""
    
    def __init__(self):
        try:
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL,
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                temperature=0.0,
            )
        except Exception:
            self.llm = None
    
    def run_correction(self, state: AgentState, trace: list[dict]) -> AgentState:
        """Run self-correction on the agent trace.
        
        Args:
            state: Current agent state
            trace: Full execution trace from TraceLogger
            
        Returns:
            Updated state with corrections applied (or original if no issues)
        """
        if not trace or self.llm is None:
            return state
        
        # Check if we've already done max corrections
        if len(state.get("correction_history", [])) >= MAX_CORRECTION_CYCLES:
            return state
        
        # Build verification prompt
        trace_text = json.dumps(trace, indent=2)
        messages = [
            SystemMessage(content=SELF_CORRECTION_PROMPT),
            HumanMessage(content=f"Please review this agent execution trace:\n\n{trace_text}"),
        ]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            
            # Try to parse JSON response
            try:
                # Extract JSON from response (might be wrapped in markdown)
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                result = json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                # If JSON parsing fails, assume no issues
                return state
            
            issues_found = result.get("issues_found", False)
            issues = result.get("issues", [])
            
            if not issues_found or not issues:
                # No issues found
                new_history = list(state.get("correction_history", []))
                new_history.append({
                    "assessment": result.get("overall_assessment", "No issues found."),
                    "issues": [],
                    "corrected": False,
                })
                return {**state, "correction_history": new_history}
            
            # Apply corrections
            new_state = dict(state)
            new_history = list(state.get("correction_history", []))
            corrections_made = []
            
            for issue in issues:
                step_num = issue.get("step_number")
                description = issue.get("description", "")
                corrected_input = issue.get("corrected_input", "")
                
                if step_num is None or not corrected_input:
                    continue
                
                # Find the step to correct
                step_idx = step_num - 1  # Convert to 0-based index
                if step_idx < 0 or step_idx >= len(state.get("actions", [])):
                    continue
                
                action = state["actions"][step_idx]
                
                # Re-run the tool with corrected input
                if action == "calculator":
                    from tools.calculator import run as calc_run
                    new_observation = calc_run(corrected_input)
                elif action == "knowledge_lookup":
                    from tools.knowledge_lookup import run as kb_run
                    new_observation = kb_run(corrected_input)
                elif action == "web_search":
                    from tools.web_search import run as web_run
                    new_observation = web_run(corrected_input)
                else:
                    continue
                
                # Update observations
                new_observations = list(state["observations"])
                if step_idx < len(new_observations):
                    old_observation = new_observations[step_idx]
                    new_observations[step_idx] = new_observation
                    
                    corrections_made.append({
                        "step_number": step_num,
                        "description": description,
                        "corrected_input": corrected_input,
                        "old_observation": old_observation,
                        "new_observation": new_observation,
                    })
            
            new_history.append({
                "assessment": result.get("overall_assessment", ""),
                "issues": issues,
                "corrected": len(corrections_made) > 0,
                "corrections": corrections_made,
            })
            
            if corrections_made:
                new_state["observations"] = new_observations
                new_state["correction_history"] = new_history
                
                # Update final answer if needed
                if new_state.get("final_answer"):
                    # Re-run the final answer formatting with corrected observations
                    # For now, just mark that corrections were applied
                    pass
            
            return new_state
            
        except Exception as e:
            # If correction fails, return original state with warning
            new_history = list(state.get("correction_history", []))
            new_history.append({
                "assessment": f"Correction failed: {type(e).__name__}: {e}",
                "issues": [],
                "corrected": False,
                "error": str(e),
            })
            return {**state, "correction_history": new_history}
