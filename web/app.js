// Web prototype glue: loads Pyodide, installs the intentional_py wheel, and
// calls into the unmodified core via src/intentional_py/web/actions.py.
// This file is the only piece of this prototype that's Pyodide-specific; the
// Python side (web/actions.py, web/reporter.py) is plain CPython and has its
// own pytest coverage.

const statusEl = document.getElementById("status");
const zipInput = document.getElementById("zipInput");
const configNameInput = document.getElementById("configName");
const runButton = document.getElementById("runButton");
const resultEl = document.getElementById("result");
const themeToggle = document.getElementById("themeToggle");

const WHEEL_FILE = "./intentional_py-1.3.0-py3-none-any.whl";
const THEME_KEY = "intentional-web-theme";

// Applied before Pyodide starts loading, so there's no flash of the wrong theme.
function systemPrefersDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function currentTheme() {
  return document.documentElement.dataset.theme || (systemPrefersDark() ? "dark" : "light");
}

function applyTheme(theme) {
  if (theme) {
    document.documentElement.dataset.theme = theme;
  } else {
    delete document.documentElement.dataset.theme;
  }
  // label shows the mode a click switches *to*
  themeToggle.textContent = currentTheme() === "dark" ? "☀️ Light" : "🌙 Dark";
}

applyTheme(localStorage.getItem(THEME_KEY));
themeToggle.addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
});

let pyodideInstance = null;
let validateProject = null;

async function setup() {
  statusEl.textContent = "Loading Pyodide…";
  const pyodide = await loadPyodide();
  pyodideInstance = pyodide;
  window.pyodide = pyodide;

  statusEl.textContent = "Installing intentional_py (this only happens once per page load)…";
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  await micropip.install(WHEEL_FILE);

  statusEl.textContent = "Starting intentional_py…";
  await pyodide.runPythonAsync("from intentional_py.web.actions import validate_project");
  validateProject = pyodide.globals.get("validate_project");
  // exposed for console/debugging use, e.g. window.validateProject(bytes, "")
  window.validateProject = validateProject;

  statusEl.textContent = "Ready.";
  zipInput.disabled = false;
  runButton.disabled = false;
}

const ready = setup().catch((error) => {
  statusEl.textContent = `Failed to load: ${error}`;
  throw error;
});

runButton.addEventListener("click", async () => {
  await ready;
  const file = zipInput.files[0];
  if (!file) {
    resultEl.textContent = "Choose a project zip first.";
    return;
  }
  runButton.disabled = true;
  resultEl.textContent = "Running…";
  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    // pyodide does not auto-convert a typed array to Python bytes; this does
    const bytesPy = pyodideInstance.toPy(bytes);
    const configName = configNameInput.value.trim();
    const resultJson = validateProject(bytesPy, configName);
    bytesPy.destroy();
    render(JSON.parse(resultJson));
  } catch (error) {
    resultEl.textContent = `Error: ${error}`;
  } finally {
    runButton.disabled = false;
  }
});

function checkLine(label, ok) {
  const span = document.createElement("span");
  span.className = ok ? "ok" : "fail";
  span.textContent = `${ok ? "✔" : "✖"} ${label}`;
  return span;
}

function render(result) {
  resultEl.textContent = "";
  const lines = [];
  for (const [label, ok] of result.directories) lines.push(checkLine(label, ok));
  if (result.used_standard_configs) {
    const note = document.createElement("span");
    note.textContent = "Using STANDARD config files";
    lines.push(note);
  }
  for (const [label, ok] of result.config_files) lines.push(checkLine(label, ok));
  for (const config of result.configs) {
    lines.push(checkLine(config.label, config.ok));
    for (const detail of config.details) {
      const d = document.createElement("span");
      d.textContent = `    ${detail}`;
      lines.push(d);
    }
  }
  for (const line of lines) {
    resultEl.appendChild(line);
    resultEl.appendChild(document.createElement("br"));
  }
}
