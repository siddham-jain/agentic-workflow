"""ReAct parser for extracting thought/action/action_input from LLM output."""
import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReActStep:
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[str] = None
    final_answer: Optional[str] = None
    is_malformed: bool = False
    is_valid_action: bool = False


class ReActParser:
    def __init__(self, valid_tools: list[str] = None):
        self.valid_tools = valid_tools or ["calculator", "knowledge_lookup", "web_search"]

    def parse(self, llm_output: str) -> ReActStep:
        step = ReActStep()

        if not llm_output or not llm_output.strip():
            step.is_malformed = True
            return step

        # Check for Final Answer first
        final_match = re.search(r"Final Answer:\s*(.+?)(?:\n|$)", llm_output, re.IGNORECASE | re.DOTALL)
        if final_match:
            step.final_answer = final_match.group(1).strip()
            return step

        # Extract thought
        thought_match = re.search(r"Thought:\s*(.+?)(?:\n(?:Action|Action Input|Final)|$)", llm_output, re.IGNORECASE | re.DOTALL)
        if thought_match:
            step.thought = thought_match.group(1).strip()

        # Extract action
        action_match = re.search(r"Action:\s*(.+?)(?:\n|$)", llm_output, re.IGNORECASE)
        if action_match:
            step.action = action_match.group(1).strip()
            step.is_valid_action = step.action in self.valid_tools

        # Extract action input
        action_input_match = re.search(r"Action Input:\s*(.+?)(?:\n(?:Action|Final)|$)", llm_output, re.IGNORECASE | re.DOTALL)
        if action_input_match:
            step.action_input = action_input_match.group(1).strip()

        # Mark as malformed if no valid components found
        if not step.thought and not step.action and not step.final_answer:
            step.is_malformed = True

        return step

    def parse_tool_call(self, tool_call: dict) -> ReActStep:
        step = ReActStep()

        if not isinstance(tool_call, dict):
            step.is_malformed = True
            return step

        name = tool_call.get("name")
        args = tool_call.get("arguments", {})

        if name:
            step.action = name
            step.is_valid_action = name in self.valid_tools

        if isinstance(args, dict):
            step.action_input = json.dumps(args)
        else:
            step.action_input = str(args)

        return step