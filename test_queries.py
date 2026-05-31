#!/usr/bin/env python3
"""Test runner for the 3 financial test queries.

Usage:
    export OPENROUTER_API_KEY=your_key
    export EXA_API_KEY=your_key
    python3 test_queries.py
"""
import os
import sys

# Check for API keys
if not os.getenv("OPENROUTER_API_KEY"):
    print("Error: OPENROUTER_API_KEY not set.", file=sys.stderr)
    print("Set it with: export OPENROUTER_API_KEY=your_key", file=sys.stderr)
    sys.exit(1)

from main import run_agent

QUERIES = [
    ("simple", "What is 15% of $45,000?"),
    ("medium", "What is the current yield of a bond with a 5% coupon trading at $980?"),
    ("complex", "Compare the P/E ratios of Apple and Microsoft based on their latest earnings and current stock prices"),
]

def main():
    for name, query in QUERIES:
        print(f"\n{'='*60}")
        print(f"Running {name} query: {query}")
        print(f"{'='*60}")
        
        try:
            answer, trace = run_agent(query)
            print(f"\nAnswer: {answer}\n")
            
            # Save trace
            import json
            trace_file = f"traces/{name}.log"
            with open(trace_file, "w") as f:
                json.dump(trace, f, indent=2)
            print(f"Trace saved to: {trace_file}")
            
            # Verify trace structure
            assert isinstance(trace, list), "Trace should be a list"
            assert len(trace) > 0, "Trace should not be empty"
            
            # Check for steps
            steps = [e for e in trace if e.get("type") == "step"]
            assert len(steps) > 0, "Trace should contain at least one step"
            
            # Verify step fields
            for step in steps:
                assert "thought" in step, "Step missing thought"
                assert "action" in step, "Step missing action"
                assert "action_input" in step, "Step missing action_input"
                assert "observation" in step, "Step missing observation"
            
            print(f"✓ Trace validation passed")
            
        except Exception as e:
            print(f"✗ Error running {name} query: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
