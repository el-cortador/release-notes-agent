# Release Notes Agent

Веб-приложение для автоматической генерации release notes. Поддерживает два источника данных: коммиты GitHub-репозитория (через Claude Sonnet + GitHub MCP) и задачи Jira (через REST API).

## Как это работает

**GitHub:** пользователь указывает ссылку на репозиторий и дату начала периода → бэкенд запрашивает Claude Sonnet с подключённым GitHub MCP → Claude получает историю коммитов и формирует release notes.

**Jira:** пользователь вставляет URL задач → бэкенд вызывает Jira REST API, собирает summary и тип каждой задачи → Claude генерирует release notes на их основе.

Результат рендерится как markdown в браузере и доступен для скачивания в `.md`.

## Структура проекта

```
├── app/
│   ├── config.py       # переменные окружения
│   ├── schemas.py      # Pydantic-модели запросов и ответов
│   ├── prompts.py      # промпты для Claude
│   ├── jira.py         # Jira API клиент
│   └── main.py         # FastAPI приложение
├── web/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── .env.example
├── requirements.txt
└── run.sh
```

## Требования

- Python 3.10+
- Anthropic API key с доступом к remote MCP
- GitHub token (для MCP-сервера GitHub Copilot)
- Jira email + API token (только для режима Jira)

## Запуск

**1. Создайте `.env` на основе `.env.example` и заполните ключи:**

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...

# Только для режима Jira
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=your-jira-api-token
```

**2. Запустите:**

```bash
bash run.sh
```

Скрипт устанавливает зависимости и стартует сервер. Откройте `http://127.0.0.1:5001`.

## API

### `POST /generate`

Генерирует release notes по коммитам GitHub.

**Тело запроса:**

```json
{
  "owner": "microsoft",
  "repo": "vscode",
  "since": "2024-01-01",
  "branch": "main"
}
```

### `POST /generate-jira`

Генерирует release notes по задачам Jira.

**Тело запроса:**

```json
{
  "urls": [
    "https://company.atlassian.net/browse/PROJ-123",
    "https://company.atlassian.net/browse/PROJ-456"
  ]
}
```

### Ответ (оба эндпоинта)

```json
{
  "result": "## Features\n- ...\n\n## Bug Fixes\n- ..."
}
```

| Код | Причина |
|-----|---------|
| 400 | Не заполнены обязательные поля или невалидный URL |
| 500 | Не заданы учётные данные в `.env` |
| 502 | Ошибка при обращении к Anthropic API или Jira |
