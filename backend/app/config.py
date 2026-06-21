import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ENV = Path(__file__).resolve().parents[1] / ".env"

load_dotenv(BACKEND_ENV)

DEFAULT_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

GROQ_ENDPOINT = os.getenv("GROQ_ENDPOINT", DEFAULT_GROQ_ENDPOINT).strip().strip('"').strip("'")
if not GROQ_ENDPOINT.startswith(("http://", "https://")):
    GROQ_ENDPOINT = DEFAULT_GROQ_ENDPOINT

DEFAULT_MODEL = os.getenv("GROQ_MODEL") or os.getenv("DEFAULT_MODEL") or "llama-3.3-70b-versatile"
DEFAULT_MODEL = DEFAULT_MODEL.strip().strip('"').strip("'")
if DEFAULT_MODEL.startswith("os.getenv("):
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
if GROQ_API_KEY.startswith("os.getenv("):
    GROQ_API_KEY = ""

GROQ_API_KEY_2 = (
    os.getenv("GROQ_API_KEY_2")
    or os.getenv("GROQ_API2")
    or os.getenv("GROQ_API_KEY_SECONDARY")
    or ""
)
GROQ_API_KEY_2 = GROQ_API_KEY_2.strip().strip('"').strip("'")
if GROQ_API_KEY_2.startswith("os.getenv("):
    GROQ_API_KEY_2 = ""
