from typing import TypedDict, Optional


class AgentState(TypedDict):
    query: str
    thoughts: list[str]
    actions: list[str]
    action_inputs: list[str]
    observations: list[str]
    current_step: int
    final_answer: Optional[str]
    trace: list[dict]
    correction_history: list[dict]
    tool_call_cache: dict[str, str]  # key: "action|action_input", value: observation