"""Calculator tool that executes Python math expressions in a sandboxed subprocess."""
import subprocess
import sys
from utils.config import MAX_TOOL_TIMEOUT, MAX_CODE_OUTPUT_CHARS, BLOCKED_MODULES

__all__ = ["run"]


def run(action_input: str) -> str:
    """Execute a Python math expression in a sandboxed subprocess.
    
    Args:
        action_input: Python code string to execute (should be a math expression)
        
    Returns:
        Structured result string: "Result: <value>" on success, "Error: <description>" on failure
    """
    # Build sandboxed code that blocks dangerous imports
    blocked_code = "\n".join([
        f"import {mod}\n" for mod in BLOCKED_MODULES
    ])
    
    # Create restricted execution environment
    sandboxed_code = f"""
import sys
# Block dangerous modules
for mod in {BLOCKED_MODULES!r}:
    sys.modules[mod] = None

# Execute user code
try:
    result = eval({action_input!r})
    print(f"Result: {{result}}")
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{e}}")
"""
    
    try:
        proc = subprocess.run(
            [sys.executable, "-c", sandboxed_code],
            capture_output=True,
            text=True,
            timeout=MAX_TOOL_TIMEOUT,
        )
        
        output = proc.stdout.strip()
        if not output:
            output = proc.stderr.strip()
        
        # Truncate if too long
        if len(output) > MAX_CODE_OUTPUT_CHARS:
            output = output[:MAX_CODE_OUTPUT_CHARS] + "\n[truncated]"
        
        if proc.returncode != 0 and not output.startswith("Error:"):
            return f"Error: Execution failed with return code {proc.returncode}. {output}"
        
        return output if output else "Error: No output produced"
        
    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {MAX_TOOL_TIMEOUT} seconds"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
