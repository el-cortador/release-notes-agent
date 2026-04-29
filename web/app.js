const repoUrlInput   = document.getElementById("repo-url");
const branchInput    = document.getElementById("branch");
const sinceInput     = document.getElementById("since");
const jiraUrlsInput  = document.getElementById("jira-urls");
const generateBtn    = document.getElementById("generate-btn");
const downloadBtn    = document.getElementById("download-btn");
const resultBox      = document.getElementById("result-box");
const resultSection  = document.getElementById("result-section");
const tabGithub      = document.getElementById("tab-github");
const tabJira        = document.getElementById("tab-jira");
const sectionGithub  = document.getElementById("section-github");
const sectionJira    = document.getElementById("section-jira");

let currentMode  = "github";
let lastMarkdown = null;

// ── Tabs ──────────────────────────────────────────────────────────────────────

tabGithub.addEventListener("click", () => switchTab("github"));
tabJira.addEventListener("click",   () => switchTab("jira"));

function switchTab(mode) {
  currentMode = mode;
  tabGithub.classList.toggle("tab--active", mode === "github");
  tabGithub.setAttribute("aria-selected", String(mode === "github"));
  tabJira.classList.toggle("tab--active", mode === "jira");
  tabJira.setAttribute("aria-selected", String(mode === "jira"));
  sectionGithub.hidden = mode !== "github";
  sectionJira.hidden   = mode !== "jira";
}

// ── Result rendering ──────────────────────────────────────────────────────────

function showResult() {
  resultSection.hidden = false;
}

function renderError(message) {
  showResult();
  resultBox.classList.add("result__box--error");
  resultBox.textContent = message;
  lastMarkdown = null;
}

function renderMarkdown(markdown) {
  showResult();
  resultBox.classList.remove("result__box--error");
  resultBox.innerHTML = marked.parse(markdown);
  lastMarkdown = markdown;
}

// ── GitHub URL parser ─────────────────────────────────────────────────────────

function parseGitHubUrl(url) {
  try {
    const match = new URL(url).pathname.match(/^\/([^/]+)\/([^/]+?)(?:\.git)?$/);
    return match ? { owner: match[1], repo: match[2] } : null;
  } catch {
    return null;
  }
}

// ── Generate ──────────────────────────────────────────────────────────────────

generateBtn.addEventListener("click", async () => {
  generateBtn.disabled = true;
  resultBox.classList.remove("result__box--error");
  resultBox.textContent = "Генерирую...";
  showResult();

  try {
    if (currentMode === "github") {
      await generateGithub();
    } else {
      await generateJira();
    }
  } finally {
    generateBtn.disabled = false;
  }
});

async function generateGithub() {
  const parsed = parseGitHubUrl(repoUrlInput.value.trim());
  if (!parsed) {
    renderError("Укажите корректную ссылку на GitHub-репозиторий.");
    return;
  }
  if (!sinceInput.value) {
    renderError("Укажите дату начала периода.");
    return;
  }

  await callApi("/generate", {
    owner:  parsed.owner,
    repo:   parsed.repo,
    since:  sinceInput.value,
    branch: branchInput.value.trim(),
  });
}

async function generateJira() {
  const urls = jiraUrlsInput.value.split("\n").map(u => u.trim()).filter(Boolean);
  if (!urls.length) {
    renderError("Вставьте хотя бы один URL задачи.");
    return;
  }
  await callApi("/generate-jira", { urls });
}

async function callApi(endpoint, body) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      renderError(data.detail || "Неизвестная ошибка.");
    } else {
      renderMarkdown(data.result);
    }
  } catch {
    renderError("Не удалось подключиться к серверу.");
  }
}

// ── Download ──────────────────────────────────────────────────────────────────

downloadBtn.addEventListener("click", () => {
  if (!lastMarkdown) {
    renderError("Сначала сгенерируйте результат.");
    return;
  }
  const blob = new Blob([lastMarkdown], { type: "text/markdown" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "release-notes.md";
  link.click();
  URL.revokeObjectURL(link.href);
});
