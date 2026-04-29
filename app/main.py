from __future__ import annotations

from pathlib import Path

import anthropic
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import GITHUB_TOKEN, MAX_TOKENS, MODEL, PORT
from app.jira import JiraAuthError, JiraClient, JiraError, JiraRequestError
from app.prompts import github_prompt, jira_prompt
from app.schemas import GenerateResponse, GitHubRequest, JiraRequest

app = FastAPI(title="Release Notes Agent", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

MCP_SERVERS = [
    {
        "type": "url",
        "url": "https://api.githubcopilot.com/mcp/",
        "name": "github",
        "authorization_token": GITHUB_TOKEN,
    }
]

_anthropic = anthropic.Anthropic()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_markdown(text: str) -> str:
    md_start = text.find("#")
    return text[md_start:] if md_start > 0 else text


# ── Dependencies ──────────────────────────────────────────────────────────────

def get_jira_client() -> JiraClient:
    try:
        return JiraClient()
    except JiraError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.post("/generate", response_model=GenerateResponse)
def generate_github(payload: GitHubRequest) -> GenerateResponse:
    try:
        response = _anthropic.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": github_prompt(
                payload.owner, payload.repo, payload.since, payload.branch or None,
            )}],
            mcp_servers=MCP_SERVERS,
            tools=[{"type": "mcp_toolset", "mcp_server_name": "github"}],
            betas=["mcp-client-2025-11-20"],
        )
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    result = "".join(b.text for b in response.content if b.type == "text")
    return GenerateResponse(result=_extract_markdown(result))


@app.post("/generate-jira", response_model=GenerateResponse)
def generate_jira(
    payload: JiraRequest,
    jira: JiraClient = Depends(get_jira_client),
) -> GenerateResponse:
    urls = [u for u in payload.urls if u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="Укажите хотя бы один URL задачи")

    try:
        issues = jira.get_issues(urls)
    except JiraAuthError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except JiraRequestError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    if not issues:
        raise HTTPException(status_code=400, detail="Не удалось распознать Jira URL")

    try:
        response = _anthropic.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": jira_prompt(issues)}],
        )
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    result = "".join(b.text for b in response.content if b.type == "text")
    return GenerateResponse(result=_extract_markdown(result))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
