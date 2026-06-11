from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent.parent

env_file = ROOT_DIR / ".env"

print("Loading env from:", env_file)

load_dotenv(env_file)

GCP_API_KEY = os.getenv("GCP_API_KEY")

print("GCP_API_KEY loaded:", GCP_API_KEY)