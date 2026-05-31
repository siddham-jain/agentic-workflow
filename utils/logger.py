"""Structured JSON trace logging for agent workflow tracking."""

import json
from datetime import datetime, timezone


class TraceLogger:
    """Logs agent steps, corrections, and final answers as structured JSON."""

    def __init__(self) -> None:
        self._trace: list[dict] = []

    def log_step(
        self,
        step_num: int,
        thought: str,
        action: str,
        action_input: str,
        observation: str,
    ) -> None:
        """Append a step entry to the trace."""
        self._trace.append({
            "type": "step",
            "step_number": step_num,
            "thought": thought,
            "action": action,
            "action_input": action_input,
            "observation": observation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def log_correction(
        self,
        original_step_num: int,
        corrected_step: dict,
        reason: str,
    ) -> None:
        """Append a correction entry to the trace."""
        self._trace.append({
            "type": "correction",
            "original_step": original_step_num,
            "corrected_step": corrected_step,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def log_final_answer(self, answer: str) -> None:
        """Append a final answer entry to the trace."""
        self._trace.append({
            "type": "final_answer",
            "answer": answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save_trace(self, filepath: str) -> None:
        """Write the trace to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self._trace, f, indent=2)

    def get_trace(self) -> list[dict]:
        """Return the trace list."""
        return self._trace

    def to_json(self) -> str:
        """Return the trace as a JSON string."""
        return json.dumps(self._trace, indent=2)