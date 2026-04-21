from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
import anthropic
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic()

MCP_SERVERS = [
    {
        "type": "url",
        "url": "https://api.githubcopilot.com/mcp/",
        "name": "github",
        "authorization_token": os.getenv("GITHUB_TOKEN"),
    }
]

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


# ── GitHub ────────────────────────────────────────────────────────────────────

def build_github_prompt(owner: str, repo: str, since: str, branch: str | None) -> str:
    branch_clause = f" в ветке {branch}" if branch else ""
    return (
        f"Используй GitHub MCP чтобы получить коммиты репозитория {owner}/{repo}"
        f"{branch_clause} начиная с {since}.\n\n"
        "Затем сгенерируй release notes на русском языке в формате markdown:\n"
        "- Сгруппируй по типам: Features, Bug Fixes, Other\n"
        "- Каждый пункт — одно предложение, человекочитаемое\n"
        "- Убери служебные коммиты (merge, bump version и т.п.)"
    )


# ── Jira ──────────────────────────────────────────────────────────────────────

def parse_jira_urls(urls: list[str]) -> dict[str, list[str]]:
    """Returns {base_url: [issue_key, ...]}"""
    result: dict[str, list[str]] = {}
    for url in urls:
        parsed = urlparse(url.strip())
        base = f"{parsed.scheme}://{parsed.netloc}"
        parts = parsed.path.strip("/").split("/")
        # handles both /browse/KEY-123 and /KEY-123
        key = next((p for p in reversed(parts) if p and "-" in p), None)
        if key:
            result.setdefault(base, []).append(key)
    return result


def fetch_jira_issues(base_url: str, keys: list[str]) -> list[dict]:
    auth = HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
    issues = []
    for key in keys:
        resp = requests.get(
            f"{base_url}/rest/api/3/issue/{key}",
            auth=auth,
            params={"fields": "summary,issuetype,status"},
            timeout=10,
        )
        resp.raise_for_status()
        fields = resp.json()["fields"]
        issues.append({
            "key": key,
            "summary": fields.get("summary", ""),
            "type": fields.get("issuetype", {}).get("name", ""),
            "status": fields.get("status", {}).get("name", ""),
        })
    return issues


def build_jira_prompt(issues: list[dict]) -> str:
    lines = "\n".join(
        f"- [{i['key']}] ({i['type']}) {i['summary']}"
        for i in issues
    )
    return (
        "На основе следующих Jira-задач сгенерируй release notes на русском языке в формате markdown:\n"
        "- Сгруппируй по типам: Features, Bug Fixes, Other\n"
        "- Каждый пункт — одно предложение, человекочитаемое\n\n"
        f"Задачи:\n{lines}"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_markdown(text: str) -> str:
    md_start = text.find("#")
    return text[md_start:] if md_start > 0 else text


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    owner = data.get("owner", "").strip()
    repo = data.get("repo", "").strip()
    since = data.get("since", "").strip()
    branch = data.get("branch", "").strip() or None

    if not all([owner, repo, since]):
        return jsonify({"error": "Поля owner, repo и since обязательны"}), 400

    try:
        response = client.beta.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            messages=[{"role": "user", "content": build_github_prompt(owner, repo, since, branch)}],
            mcp_servers=MCP_SERVERS,
            tools=[{"type": "mcp_toolset", "mcp_server_name": "github"}],
            betas=["mcp-client-2025-11-20"],
        )
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 502

    result = "".join(block.text for block in response.content if block.type == "text")
    return jsonify({"result": extract_markdown(result)})


@app.route("/generate-jira", methods=["POST"])
def generate_jira():
    data = request.get_json(silent=True) or {}
    urls = [u for u in data.get("urls", []) if u.strip()]

    if not urls:
        return jsonify({"error": "Укажите хотя бы один URL задачи"}), 400

    if not os.getenv("JIRA_EMAIL") or not os.getenv("JIRA_API_TOKEN"):
        return jsonify({"error": "JIRA_EMAIL и JIRA_API_TOKEN не заданы в .env"}), 500

    try:
        parsed = parse_jira_urls(urls)
        if not parsed:
            return jsonify({"error": "Не удалось распознать Jira URL"}), 400
        issues = [issue for base, keys in parsed.items() for issue in fetch_jira_issues(base, keys)]
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status in (401, 403, 404):
            return jsonify({"error": f"Jira API вернул {status}. Проверьте JIRA_EMAIL и JIRA_API_TOKEN в .env, а также доступ к задачам."}), 502
        return jsonify({"error": f"Ошибка Jira API ({status}): {e}"}), 502
    except requests.RequestException as e:
        return jsonify({"error": f"Не удалось подключиться к Jira: {e}"}), 502

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            messages=[{"role": "user", "content": build_jira_prompt(issues)}],
        )
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 502

    result = "".join(block.text for block in response.content if block.type == "text")
    return jsonify({"result": extract_markdown(result)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
