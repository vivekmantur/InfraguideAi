from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent.parent

env_file = ROOT_DIR / ".env"

print("Loading env from:", env_file)

load_dotenv(env_file)

GCP_API_KEY = os.getenv("GCP_API_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip().strip('"').strip("'")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip().strip('"').strip("'")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "").strip().strip('"').strip("'")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1").strip().strip('"').strip("'")
AWS_PROFILE = os.getenv("AWS_PROFILE", "").strip().strip('"').strip("'")

print("GCP_API_KEY loaded:", bool(GCP_API_KEY))
print("AWS credentials loaded:", bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY))
