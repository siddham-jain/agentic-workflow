import os
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = 10
MAX_CORRECTION_CYCLES = 2
MAX_WALL_CLOCK_SECONDS = 120
MAX_TOOL_TIMEOUT = 30
MAX_CODE_OUTPUT_CHARS = 10000
BLOCKED_MODULES = [
    "os", "sys", "subprocess", "socket", "requests",
    "urllib", "shutil", "pathlib", "importlib", "ctypes", "signal"
]
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"