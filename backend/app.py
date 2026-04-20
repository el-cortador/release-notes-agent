from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
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


def build_prompt(owner: str, repo: str, since: str, branch: str | None) -> str:
    branch_clause = f" в ветке {branch}" if branch else ""
    return (
        f"Используй GitHub MCP чтобы получить коммиты репозитория {owner}/{repo}"
        f"{branch_clause} начиная с {since}.\n\n"
        "Затем сгенерируй release notes на русском языке в формате markdown:\n"
        "- Сгруппируй по типам: Features, Bug Fixes, Other\n"
        "- Каждый пункт — одно предложение, человекочитаемое\n"
        "- Убери служебные коммиты (merge, bump version и т.п.)"
    )


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


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
            messages=[{"role": "user", "content": build_prompt(owner, repo, since, branch)}],
            mcp_servers=MCP_SERVERS,
            tools=[{"type": "mcp_toolset", "mcp_server_name": "github"}],
            betas=["mcp-client-2025-11-20"],
        )
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 502

    result = "".join(
        block.text for block in response.content if block.type == "text"
    )

    # Strip Claude's preamble before the actual markdown document
    md_start = result.find("#")
    if md_start > 0:
        result = result[md_start:]

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
