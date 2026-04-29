from __future__ import annotations

_RELEASE_NOTES_INSTRUCTIONS = """\
Сгенерируй release notes на русском языке в формате markdown:
- Сгруппируй по типам: Features, Bug Fixes, Other
- Каждый пункт — одно предложение, человекочитаемое
- Убери служебные коммиты (merge, bump version и т.п.)"""


def github_prompt(owner: str, repo: str, since: str, branch: str | None) -> str:
    branch_clause = f" в ветке {branch}" if branch else ""
    return (
        f"Используй GitHub MCP чтобы получить коммиты репозитория {owner}/{repo}"
        f"{branch_clause} начиная с {since}.\n\n"
        f"Затем {_RELEASE_NOTES_INSTRUCTIONS}"
    )


def jira_prompt(issues: list[dict]) -> str:
    lines = "\n".join(
        f"- [{i['key']}] ({i['type']}) {i['summary']}"
        for i in issues
    )
    return (
        f"На основе следующих Jira-задач {_RELEASE_NOTES_INSTRUCTIONS}\n\n"
        f"Задачи:\n{lines}"
    )
