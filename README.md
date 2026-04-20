# Release Notes Agent

Веб-приложение, которое автоматически генерирует release notes по коммитам GitHub-репозитория. Использует Claude Sonnet с подключённым GitHub MCP-сервером для получения истории коммитов и формирует читаемый markdown-отчёт на русском языке.

## Как это работает

1. Пользователь вводит owner/repo и дату начала периода
2. Flask-бэкенд отправляет запрос в Claude Sonnet API с подключённым GitHub MCP
3. Claude получает коммиты через MCP и формирует release notes, сгруппированные по типам: Features, Bug Fixes, Other
4. Результат рендерится как markdown прямо в браузере

## Структура проекта

```
├── backend/
│   └── app.py          # Flask API
├── frontend/
│   └── index.html      # Одностраничный UI
├── .env.example
└── requirements.txt
```

## Требования

- Python 3.10+
- Ключ Anthropic API с доступом к remote MCP
- GitHub token (для MCP-сервера GitHub Copilot)

## Запуск

**1. Создайте `.env` на основе `.env.example` и заполните ключи:**

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
```

**2. Запустите:**

```bash
bash run.sh
```

Скрипт создаёт виртуальное окружение, устанавливает зависимости и стартует сервер. Откройте `http://127.0.0.1:5000`.

## API

### `POST /generate`

Генерирует release notes для указанного репозитория.

**Тело запроса:**

```json
{
  "owner": "microsoft",
  "repo": "vscode",
  "since": "2024-01-01"
}
```

**Ответ:**

```json
{
  "result": "## Features\n- ...\n\n## Bug Fixes\n- ..."
}
```