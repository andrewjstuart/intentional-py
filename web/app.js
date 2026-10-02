// Web prototype glue: loads Pyodide, installs the intentional_py wheel, and
// calls into the unmodified core via src/intentional_py/web/actions.py.
// This file is the only piece of this prototype that's Pyodide-specific; the
// Python side (web/actions.py, web/reporter.py) is plain CPython and has its
// own pytest coverage.

const statusEl = document.getElementById("status");
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
const downloadLink = document.getElementById("downloadLink");
const resultEl = document.getElementById("result");
const themeToggle = document.getElementById("themeToggle");

const WHEEL_FILE = "./intentional_py-1.3.0-py3-none-any.whl";
const THEME_KEY = "intentional-web-theme";

// Each task's visible fields and which Python function it calls.
const TASKS = {
  validate: { label: "Validate", fields: ["projectZip", "configName"] },
  buildDd: { label: "Build DD intents", fields: ["projectZip", "configName", "clean"] },
  buildNl: {
    label: "Build NL intents",
    fields: ["projectZip", "configName", "vertical", "context", "lowercase", "reuse", "clean"],
  },
  extract: { label: "Extract phrases", fields: ["excelFile", "mode", "language"] },
  design: { label: "Create config from design doc", fields: ["excelFile", "sheet", "configName"] },
  compare: { label: "Compare with export", fields: ["projectZip", "configName", "mode", "exportZip"] },
};
const ALL_FIELDS = [
  "projectZip", "excelFile", "exportZip", "configName", "mode",
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
  await pyodide.runPythonAsync(
    "from intentional_py.web.actions import (validate_project, build_dd_project, " +
    "build_nl_project, extract_project, design_project, compare_project)"
  );
  pyFunctions = {
    validate: pyodide.globals.get("validate_project"),
    buildDd: pyodide.globals.get("build_dd_project"),
    buildNl: pyodide.globals.get("build_nl_project"),
    extract: pyodide.globals.get("extract_project"),
    design: pyodide.globals.get("design_project"),
    compare: pyodide.globals.get("compare_project"),
  };
  // exposed for console/debugging use, e.g. window.intentional.validate(bytes, "")
  window.intentional = pyFunctions;

  statusEl.textContent = "Ready.";
  for (const input of [zipInput, excelInput, exportInput, runButton]) {
    input.disabled = false;
  }
}

const ready = setup().catch((error) => {
  statusEl.textContent = `Failed to load: ${error}`;
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

async function runTask(task) {
  const configName = configNameInput.value.trim();
  if (task === "validate") {
    const { bytesPy } = await fileBytesPy(zipInput, "a project zip");
    try {
      return pyFunctions.validate(bytesPy, configName);
    } finally {
      bytesPy.destroy();
    }
  }
  if (task === "buildDd") {
    const { bytesPy } = await fileBytesPy(zipInput, "a project zip");
    try {
      return pyFunctions.buildDd(bytesPy, configName, cleanInput.checked);
    } finally {
      bytesPy.destroy();
    }
  }
  if (task === "buildNl") {
    const { bytesPy } = await fileBytesPy(zipInput, "a project zip");
    try {
      return pyFunctions.buildNl(
        bytesPy, configName, verticalInput.value.trim(), contextInput.value.trim(),
        lowercaseInput.checked, reuseInput.checked, cleanInput.checked
      );
    } finally {
      bytesPy.destroy();
    }
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
    const project = await fileBytesPy(zipInput, "a project zip");
    const exportFile = await fileBytesPy(exportInput, "an agent export zip");
    try {
      return pyFunctions.compare(
        project.bytesPy, exportFile.bytesPy, exportFile.name, modeSelect.value, configName
      );
    } finally {
      project.bytesPy.destroy();
      exportFile.bytesPy.destroy();
    }
  }
  throw new Error(`Unknown task: ${task}`);
}

runButton.addEventListener("click", async () => {
  await ready;
  runButton.disabled = true;
  downloadLink.style.display = "none";
  resultEl.textContent = "Running…";
  try {
    const resultJson = await runTask(taskSelect.value);
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
  if (result.output_zip_base64) {
    const bytes = Uint8Array.from(atob(result.output_zip_base64), (c) => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: "application/zip" });
    downloadLink.href = URL.createObjectURL(blob);
    downloadLink.style.display = "inline";
  }
}

