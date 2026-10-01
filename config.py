"""Application configuration loaded from environment variables.

No secret is ever hard-coded. Defaults are intentionally safe for local
development so the app runs with zero configuration.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_dotenv():
    """Minimal .env loader so the project works without extra dependencies."""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "5")) * 1024 * 1024

    # Uploads are written here with a random name and never served publicly.
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))

    # Allowed resume types
    ALLOWED_EXTENSIONS = {"pdf"}

    # Minimum characters expected in a resume / job description
    MIN_RESUME_CHARS = int(os.environ.get("MIN_RESUME_CHARS", "80"))
    MIN_JD_CHARS = int(os.environ.get("MIN_JD_CHARS", "60"))

    # AI provider: "bedrock" or "mock"
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "mock").strip().lower()

    # Amazon Bedrock
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID = os.environ.get(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"
    )
    BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "2000"))
    BEDROCK_TEMPERATURE = float(os.environ.get("BEDROCK_TEMPERATURE", "0.2"))
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN", "")