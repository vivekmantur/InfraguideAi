import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(BACKEND_ENV)

DEFAULT_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://62.72.30.227:5174",
]

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

GROQ_API_KEY_FALLBACK = (
    os.getenv("GROQ_API_KEY_FALLBACK")
    or os.getenv("GROQ_API2")
    or os.getenv("GROQ_API_KEY_SECONDARY")
    or ""
)
GROQ_API_KEY_FALLBACK = GROQ_API_KEY_FALLBACK.strip().strip('"').strip("'")
if GROQ_API_KEY_FALLBACK.startswith("os.getenv("):
    GROQ_API_KEY_FALLBACK = ""

def get_cors_origins() -> list[str]:
    """Return allowed CORS origins from environment configuration.

    Args:
        None.

    Returns:
        Configured CORS origins, or default local development origins.
    """
    configured_origins = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    return origins or DEFAULT_CORS_ORIGINS
