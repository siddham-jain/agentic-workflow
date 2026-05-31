#!/usr/bin/env python3
"""CLI entry point for the ReAct analytical agent."""
import argparse
import os
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent.graph import create_agent_graph
from agent.correction import SelfCorrection
from agent.state import AgentState
from utils.config import MAX_WALL_CLOCK_SECONDS
from utils.logger import TraceLogger


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nInterrupted by user. Exiting...", file=sys.stderr)
    sys.exit(130)


# Register signal handler
signal.signal(signal.SIGINT, signal_handler)


def run_agent(query: str) -> tuple[str, list[dict]]:
    """Run the agent on a query and return the answer and trace.

    Args:
        query: The user's question

    Returns:
        Tuple of (final_answer, trace)
    """
    # Initialize logger
    logger = TraceLogger()

    # Create initial state
    initial_state: AgentState = {
        "query": query,
        "thoughts": [],
        "actions": [],
        "action_inputs": [],
        "observations": [],
        "current_step": 0,
        "final_answer": None,
        "trace": [],
        "correction_history": [],
        "tool_call_cache": {},
    }

    def _print_step(step_num: int, thought: str, action: str, action_input: str, observation: str) -> None:
        """Print a single ReAct step to the terminal."""
        print(f"  Step {step_num}")
        print(f"    Thought: {thought.strip()}")
        if action:
            print(f"    Action: {action}")
            print(f"    Action Input: {action_input}")
        print(f"    Observation: {observation.strip()}")
        print()

    # Create and run graph synchronously (no streaming)
    graph = create_agent_graph()
    final_state = graph.invoke(initial_state)

    # Reconstruct trace from final state
    thoughts = final_state.get("thoughts", [])
    actions = final_state.get("actions", [])
    action_inputs = final_state.get("action_inputs", [])
    observations = final_state.get("observations", [])

    print("Trace:")
    print("-" * 60)

    for i in range(len(thoughts)):
        step_num = i + 1
        thought = thoughts[i]
        action = actions[i] if i < len(actions) else ""
        action_input = action_inputs[i] if i < len(action_inputs) else ""
        observation = observations[i] if i < len(observations) else ""
        if action:
            logger.log_step(step_num, thought, action, action_input, observation)
            _print_step(step_num, thought, action, action_input, observation)
        else:
            # Final answer step (no action)
            print(f"  Step {step_num}")
            print(f"    Thought: {thought.strip()}")
            print(f"    Final Answer: {thought.strip()}")
            print()

    # Log final answer
    final_answer = final_state.get("final_answer", "")
    if final_answer:
        logger.log_final_answer(final_answer)
    else:
        final_answer = "No answer generated."

    # Run self-correction
    try:
        corrector = SelfCorrection()
        trace = logger.get_trace()
        if final_state:
            corrected_state = corrector.run_correction(final_state, trace)
            # Log corrections if any were made
            if corrected_state.get("correction_history"):
                last_correction = corrected_state["correction_history"][-1]
                if last_correction.get("corrected"):
                    corrections = last_correction.get("corrections", [])
                    for corr in corrections:
                        logger.log_correction(
                            corr["step_number"],
                            {
                                "step_number": corr["step_number"],
                                "observation": corr["new_observation"],
                                "corrected_input": corr["corrected_input"],
                            },
                            corr["description"],
                        )
                    # Update final answer if corrections changed it
                    if corrected_state.get("final_answer"):
                        final_answer = corrected_state["final_answer"]
    except Exception as e:
        print(f"Warning: Self-correction failed: {e}", file=sys.stderr)

    return final_answer, logger.get_trace()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="ReAct Analytical Agent")
    parser.add_argument("query", nargs="?", help="The question to answer")
    args = parser.parse_args()

    # Get query from argument or stdin
    if args.query:
        query = args.query
    else:
        query = sys.stdin.read().strip()

    if not query:
        print("Error: No query provided. Use --help for usage.", file=sys.stderr)
        sys.exit(1)

    # Check for required API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set. Please set it in your .env file or environment.", file=sys.stderr)
        sys.exit(1)

    print(f"Query: {query}\n")
    print("Thinking...\n")

    # Run agent with timeout
    import threading
    result = [None, None]

    def target():
        result[0], result[1] = run_agent(query)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=MAX_WALL_CLOCK_SECONDS)

    if thread.is_alive():
        print(f"\nError: Agent timed out after {MAX_WALL_CLOCK_SECONDS} seconds.", file=sys.stderr)
        sys.exit(1)

    final_answer, trace = result

    # Print answer
    print(f"Answer: {final_answer}\n")

    # Save trace
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_filename = f"traces/trace_{timestamp}.json"
    os.makedirs("traces", exist_ok=True)

    logger = TraceLogger()
    for entry in trace:
        if entry.get("type") == "step":
            logger.log_step(
                entry.get("step_number", 0),
                entry.get("thought", ""),
                entry.get("action", ""),
                entry.get("action_input", ""),
                entry.get("observation", ""),
            )
        elif entry.get("type") == "correction":
            logger.log_correction(
                entry.get("original_step", 0),
                entry.get("corrected_step", {}),
                entry.get("reason", ""),
            )
        elif entry.get("type") == "final_answer":
            logger.log_final_answer(entry.get("answer", ""))

    logger.save_trace(trace_filename)
    print(f"Trace saved to: {trace_filename}")


if __name__ == "__main__":
    main()