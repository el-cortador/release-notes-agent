from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

MODEL = os.getenv("MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8096"))
PORT = int(os.getenv("PORT", "5001"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
