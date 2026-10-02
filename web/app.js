// Web front end glue: loads Pyodide, installs the intentional_py wheel, and
// calls into the unmodified core via src/intentional_py/web/actions.py.
// This file is the only piece of this experimental front end that's
// Pyodide-specific; the Python side (web/actions.py, web/reporter.py) is
// plain CPython and has its own pytest coverage.

const statusEl = document.getElementById("status");
const statusTextEl = document.getElementById("statusText");
const taskSelect = document.getElementById("task");
const zipInput = document.getElementById("zipInput");
const excelInput = document.getElementById("excelInput");
const exportInput = document.getElementById("exportInput");
const configNameInput = document.getElementById("configName");
const modeSelect = document.getElementById("mode");
const languageSelect = document.getElementById("language");
const sheetInput = document.getElementById("sheet");
const verticalInput = document.getElementById("vertical");
const contextInput = document.getElementById("context");
const lowercaseInput = document.getElementById("lowercase");
const reuseInput = document.getElementById("reuse");
const cleanInput = document.getElementById("clean");
const runButton = document.getElementById("runButton");
const openProjectButton = document.getElementById("openProjectButton");
const newProjectButton = document.getElementById("newProjectButton");
const downloadProjectButton = document.getElementById("downloadProjectButton");
const projectStatusEl = document.getElementById("projectStatus");
const projectStatusTextEl = document.getElementById("projectStatusText");
const projectFilesDetails = document.getElementById("projectFilesDetails");
const projectFilesList = document.getElementById("projectFilesList");
const resultEl = document.getElementById("result");
const themeToggle = document.getElementById("themeToggle");

const THEME_KEY = "intentional-web-theme";

// state: "loading" | "ready" | "error"; drives the badge's colour/dot via CSS.
function setStatus(state, text) {
  statusEl.dataset.state = state;
  statusTextEl.textContent = `Status: ${text}`;
}

// Shows the chosen file's name next to its "Choose file…" button.
function wireFileName(input, nameId) {
  const nameEl = document.getElementById(nameId);
  input.addEventListener("change", () => {
    nameEl.textContent = input.files[0]?.name || "No file chosen";
  });
}
wireFileName(zipInput, "zipInputName");
wireFileName(excelInput, "excelInputName");
wireFileName(exportInput, "exportInputName");

// Each task's visible fields (beyond the always-open project) and which
// Python function it calls.
const TASKS = {
  validate: { label: "Validate", fields: ["configName"] },
  buildDd: { label: "Build DD intents", fields: ["configName", "clean"] },
  buildNl: {
    label: "Build NL intents",
    fields: ["configName", "vertical", "context", "lowercase", "reuse", "clean"],
  },
  extract: { label: "Extract phrases", fields: ["excelFile", "mode", "language"] },
  design: { label: "Create config from design doc", fields: ["excelFile", "sheet", "configName"] },
  compare: { label: "Compare with export", fields: ["configName", "mode", "exportZip"] },
};
const ALL_FIELDS = [
  "excelFile", "exportZip", "configName", "mode",
  "language", "sheet", "vertical", "context", "lowercase", "reuse", "clean",
];

function updateVisibleFields() {
  const visible = new Set(TASKS[taskSelect.value].fields);
  for (const field of ALL_FIELDS) {
    document.getElementById(`field-${field}`).style.display = visible.has(field) ? "" : "none";
  }
  runButton.textContent = TASKS[taskSelect.value].label;
}

taskSelect.addEventListener("change", updateVisibleFields);
updateVisibleFields();

// Help dialog: a native <dialog> (backdrop, ESC to close, focus trapping for free).
const helpDialog = document.getElementById("helpDialog");
const helpButton = document.getElementById("helpButton");
const closeHelp = document.getElementById("closeHelp");

function showHelpSection(name) {
  for (const button of document.querySelectorAll(".help-nav button")) {
    button.classList.toggle("active", button.dataset.section === name);
  }
  for (const section of document.querySelectorAll(".help-section")) {
    section.classList.toggle("active", section.id === `help-${name}`);
  }
}

helpButton.addEventListener("click", () => {
  helpDialog.showModal();
  showHelpSection(taskSelect.value); // opens on the section for the current task
});
closeHelp.addEventListener("click", () => helpDialog.close());
helpDialog.addEventListener("click", (event) => {
  if (event.target === helpDialog) helpDialog.close(); // click on the backdrop
});
for (const button of document.querySelectorAll(".help-nav button")) {
  button.addEventListener("click", () => showHelpSection(button.dataset.section));
}

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
let pyFunctions = {};
let projectOpen = false;

async function setup() {
  setStatus("loading", "Loading Pyodide…");
  const pyodide = await loadPyodide();
  pyodideInstance = pyodide;
  window.pyodide = pyodide;

  setStatus("loading", "Installing intentional_py (this only happens once per page load)…");
  // written by web/serve.py, so this file never hardcodes a version
  const wheelFile = (await (await fetch("wheel-filename.txt")).text()).trim();
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  await micropip.install(`./${wheelFile}`);

  setStatus("loading", "Starting intentional_py…");
  await pyodide.runPythonAsync(
    "from intentional_py.web.actions import (new_project, open_project, " +
    "project_files, download_project, validate_project, build_dd_project, " +
    "build_nl_project, extract_project, design_project, compare_project)"
  );
  pyFunctions = {
    newProject: pyodide.globals.get("new_project"),
    openProject: pyodide.globals.get("open_project"),
    projectFiles: pyodide.globals.get("project_files"),
    downloadProject: pyodide.globals.get("download_project"),
    validate: pyodide.globals.get("validate_project"),
    buildDd: pyodide.globals.get("build_dd_project"),
    buildNl: pyodide.globals.get("build_nl_project"),
    extract: pyodide.globals.get("extract_project"),
    design: pyodide.globals.get("design_project"),
    compare: pyodide.globals.get("compare_project"),
  };
  // exposed for console/debugging use, e.g. window.intentional.validate()
  window.intentional = pyFunctions;

  setStatus("ready", "Ready.");
  openProjectButton.disabled = false;
  newProjectButton.disabled = false;
  zipInput.disabled = false;
}

const ready = setup().catch((error) => {
  setStatus("error", `Failed to load: ${error}`);
  throw error;
});

async function fileBytesPy(input, label) {
  const file = input.files[0];
  if (!file) {
    throw new Error(`Choose ${label} first.`);
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  // pyodide does not auto-convert a typed array to Python bytes; this does
  return { name: file.name, bytesPy: pyodideInstance.toPy(bytes) };
}

function setProjectOpen(open) {
  projectOpen = open;
  projectStatusEl.dataset.open = String(open);
  downloadProjectButton.disabled = !open;
  excelInput.disabled = !open;
  exportInput.disabled = !open;
  runButton.disabled = !open;
}

function showProjectFiles(filesJson) {
  const { files } = JSON.parse(filesJson);
  projectStatusTextEl.textContent = `Project open — ${files.length} file${files.length === 1 ? "" : "s"}`;
  projectFilesList.textContent = files.length ? files.join("\n") : "(empty)";
  projectFilesDetails.style.display = files.length ? "" : "none";
}

async function refreshProjectFiles() {
  showProjectFiles(pyFunctions.projectFiles());
}

openProjectButton.addEventListener("click", async () => {
  await ready;
  try {
    const file = zipInput.files[0];
    let filesJson;
    if (file) {
      const bytes = new Uint8Array(await file.arrayBuffer());
      const bytesPy = pyodideInstance.toPy(bytes);
      try {
        filesJson = pyFunctions.openProject(bytesPy);
      } finally {
        bytesPy.destroy();
      }
    } else {
      filesJson = pyFunctions.newProject();
    }
    showProjectFiles(filesJson);
    setProjectOpen(true);
    resultEl.textContent = "";
  } catch (error) {
    resultEl.textContent = `Error: ${error}`;
  }
});

newProjectButton.addEventListener("click", async () => {
  await ready;
  showProjectFiles(pyFunctions.newProject());
  setProjectOpen(true);
  resultEl.textContent = "";
});

downloadProjectButton.addEventListener("click", () => {
  const bytes = pyFunctions.downloadProject().toJs();
  const blob = new Blob([bytes], { type: "application/zip" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "project.zip";
  link.click();
  URL.revokeObjectURL(url);
});

async function runTask(task) {
  const configName = configNameInput.value.trim();
  if (task === "validate") return pyFunctions.validate(configName);
  if (task === "buildDd") return pyFunctions.buildDd(configName, cleanInput.checked);
  if (task === "buildNl") {
    return pyFunctions.buildNl(
      configName, verticalInput.value.trim(), contextInput.value.trim(),
      lowercaseInput.checked, reuseInput.checked, cleanInput.checked
    );
  }
  if (task === "extract") {
    const { name, bytesPy } = await fileBytesPy(excelInput, "an Excel file");
    try {
      return pyFunctions.extract(bytesPy, name, modeSelect.value, languageSelect.value);
    } finally {
      bytesPy.destroy();
    }
  }
  if (task === "design") {
    const { name, bytesPy } = await fileBytesPy(excelInput, "an Excel file");
    try {
      return pyFunctions.design(bytesPy, name, sheetInput.value.trim(), configName);
    } finally {
      bytesPy.destroy();
    }
  }
  if (task === "compare") {
    const { name, bytesPy } = await fileBytesPy(exportInput, "an agent export zip");
    try {
      return pyFunctions.compare(bytesPy, name, modeSelect.value, configName);
    } finally {
      bytesPy.destroy();
    }
  }
  throw new Error(`Unknown task: ${task}`);
}

runButton.addEventListener("click", async () => {
  await ready;
  if (!projectOpen) {
    resultEl.textContent = "Open or start a project first.";
    return;
  }
  runButton.disabled = true;
  resultEl.textContent = "Running…";
  try {
    const resultJson = await runTask(taskSelect.value);
    render(JSON.parse(resultJson));
    await refreshProjectFiles();
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

function textLine(text) {
  const span = document.createElement("span");
  span.textContent = text;
  return span;
}

function renderValidate(result, lines) {
  for (const [label, ok] of result.directories) lines.push(checkLine(label, ok));
  if (result.used_standard_configs) lines.push(textLine("Using STANDARD config files"));
  for (const [label, ok] of result.config_files) lines.push(checkLine(label, ok));
  for (const config of result.configs) {
    lines.push(checkLine(config.label, config.ok));
    for (const detail of config.details) lines.push(textLine(`    ${detail}`));
  }
}

function renderBuild(result, lines) {
  for (const [label, value] of result.summary) lines.push(textLine(`${label}: ${value}`));
  for (const [level, row, message] of result.issues) {
    lines.push(checkLine(row ? `Row ${row}: ${message}` : message, level !== "error"));
  }
}

function renderExtract(result, lines) {
  lines.push(textLine(`Files: ${result.files}`));
  lines.push(textLine(`Phrases: ${result.phrases}`));
  for (const sheet of result.empty_sheets) {
    lines.push(checkLine(`Sheet ${sheet} has no phrases`, false));
  }
}

function renderDesign(result, lines) {
  lines.push(textLine(`Rows written: ${result.rows}`));
  for (const error of result.errors) lines.push(checkLine(error, false));
  for (const warning of result.warnings) lines.push(checkLine(warning, true));
}

function renderCompare(result, lines) {
  lines.push(textLine(`Compared with ${result.source}`));
  for (const name of result.added) lines.push(textLine(`+ ${name}`));
  for (const change of result.changed) {
    lines.push(textLine(`~ ${change.name}: ${change.details.join("; ")}`));
  }
  for (const name of result.removed) lines.push(textLine(`- ${name} (only in the export)`));
  lines.push(textLine(`${result.unchanged} unchanged`));
}

const RENDERERS = {
  validate: renderValidate,
  buildDd: renderBuild,
  buildNl: renderBuild,
  extract: renderExtract,
  design: renderDesign,
  compare: renderCompare,
};

function render(result) {
  resultEl.textContent = "";
  const lines = [];
  RENDERERS[taskSelect.value](result, lines);
  for (const line of lines) {
    resultEl.appendChild(line);
    resultEl.appendChild(document.createElement("br"));
  }
}

