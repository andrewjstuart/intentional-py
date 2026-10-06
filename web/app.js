// Web front end glue: loads Pyodide, installs the intentional_py wheel, and
// calls into the unmodified core via src/intentional_py/web/actions.py.
// This file is the only piece of this experimental front end that's
// Pyodide-specific; the Python side (web/actions.py, web/reporter.py) is
// plain CPython and has its own pytest coverage.

const statusEl = document.getElementById("status");
const statusTextEl = document.getElementById("statusText");
const taskButtons = document.querySelectorAll(".task-button");
const taskBlurbEl = document.getElementById("taskBlurb");
const zipInput = document.getElementById("zipInput");
const folderInput = document.getElementById("folderInput");
const projectSourceTypeInputs = document.querySelectorAll('input[name="projectSourceType"]');
const excelInput = document.getElementById("excelInput");
const exportInput = document.getElementById("exportInput");
const configNameInput = document.getElementById("configName");
const modeInputs = document.querySelectorAll('input[name="mode"]');
const languageSelect = document.getElementById("language");
const sheetInput = document.getElementById("sheet");
const mergeChoiceSelect = document.getElementById("mergeChoice");
const exportZipLabel = document.querySelector('label[for="exportInput"]');
const verticalInput = document.getElementById("vertical");
const contextInput = document.getElementById("context");
const lowercaseInput = document.getElementById("lowercase");
const reuseInput = document.getElementById("reuse");
const cleanInput = document.getElementById("clean");
const runButton = document.getElementById("runButton");
const openProjectButton = document.getElementById("openProjectButton");
const newProjectButton = document.getElementById("newProjectButton");
const downloadProjectButton = document.getElementById("downloadProjectButton");
const downloadPackageButton = document.getElementById("downloadPackageButton");
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

const folderInputNameEl = document.getElementById("folderInputName");
folderInput.addEventListener("change", () => {
  const count = folderInput.files.length;
  const topFolder = folderInput.files[0]?.webkitRelativePath.split("/")[0];
  folderInputNameEl.textContent = count
    ? `${topFolder} (${count} file${count === 1 ? "" : "s"})`
    : "No folder chosen";
});

function currentProjectSourceType() {
  return document.querySelector('input[name="projectSourceType"]:checked').value;
}

function updateProjectSourceFields() {
  const useFolder = currentProjectSourceType() === "folder";
  document.getElementById("field-zipSource").style.display = useFolder ? "none" : "";
  document.getElementById("field-folderSource").style.display = useFolder ? "" : "none";
  // clear the hidden input's selection so switching back and forth can't mix sources
  if (useFolder) {
    zipInput.value = "";
    document.getElementById("zipInputName").textContent = "No file chosen";
  } else {
    folderInput.value = "";
    folderInputNameEl.textContent = "No folder chosen";
  }
}
for (const input of projectSourceTypeInputs) {
  input.addEventListener("change", updateProjectSourceFields);
}
updateProjectSourceFields();

// Each task's visible fields (beyond the always-open project) and which
// Python function it calls.
const TASKS = {
  buildDd: {
    label: "Build Intents",
    fields: ["configName", "clean", "mergeChoice", "exportZip"],
  },
  buildNl: {
    label: "Build Intents",
    fields: [
      "configName", "vertical", "context", "lowercase", "reuse", "clean",
      "mergeChoice", "exportZip",
    ],
  },
  validate: { label: "Validate", fields: ["configName"] },
  extract: { label: "Extract phrases", fields: ["excelFile", "mode", "language"] },
  design: { label: "Create Config", fields: ["excelFile", "sheet", "configName"] },
  compare: { label: "Compare", fields: ["configName", "mode", "exportZip"] },
  merge: { label: "Merge", fields: ["exportZip"] },
  package: { label: "Package", fields: ["exportZip"] },
};
const ALL_FIELDS = [
  "excelFile", "exportZip", "configName", "mode",
  "language", "sheet", "vertical", "context", "lowercase", "reuse", "clean", "mergeChoice",
];

// The one-line description shown under the task buttons.
const TASK_BLURBS = {
  buildDd: "Builds directed dialog intents from a config file using Training Phrases and writes them to the intents folder. Runs the same checks as Validate first.",
  buildNl: "Builds natural language intents from your Training Phrases NL folder and writes them to the intents folder. Runs the same checks as Validate first.",
  validate: "Checks the supplied config file and folder structure for possible issues, without writing anything. Also done automatically as part of both build tasks.",
  extract: "Pulls phrases out of an Excel workbook into text files Build NL/DD can read, replacing what's already there (the old phrases are backed up first).",
  design: "Creates a config file from an Excel design document, so you don't copy rows by hand. Review it, then run Build Intents (DD) directly.",
  compare: "Shows what a build would add or change in a Dialogflow agent export, without writing or downloading anything. Needs access to a current export of the agent.",
  merge: "Takes the intents already built and produces a complete copy of an agent export, for Dialogflow's Restore action. Build Intents first if the folder needs updating.",
  package: "Takes the intents already built and produces a partial copy of just the new/changed intents, for Dialogflow's Import action. Build Intents first if the folder needs updating.",
};

let currentTask = "buildDd";

// Extract and Compare share the same Mode control but default to different
// values, since Extract is almost always NL and Compare almost always DD.
const MODE_DEFAULTS = { extract: "NL", compare: "DD" };

function currentMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function setMode(value) {
  for (const input of modeInputs) input.checked = input.value === value;
}

function currentMergeChoice() {
  return mergeChoiceSelect.value;
}

function updateVisibleFields() {
  const visible = new Set(TASKS[currentTask].fields);
  // the export field only applies to a build when a merge/package choice is made
  const buildTask = currentTask === "buildDd" || currentTask === "buildNl";
  if (buildTask && currentMergeChoice() === "") {
    visible.delete("exportZip");
  }
  for (const field of ALL_FIELDS) {
    document.getElementById(`field-${field}`).style.display = visible.has(field) ? "" : "none";
  }
  // the same export field is required for compare/merge/package, but optional for a build
  exportZipLabel.textContent = buildTask ? "Agent export (zip, optional)" : "Agent export (zip)";
  runButton.textContent = TASKS[currentTask].label;
  taskBlurbEl.textContent = TASK_BLURBS[currentTask];
}

for (const button of taskButtons) {
  button.addEventListener("click", () => {
    currentTask = button.dataset.task;
    for (const other of taskButtons) other.classList.toggle("active", other === button);
    if (MODE_DEFAULTS[currentTask]) setMode(MODE_DEFAULTS[currentTask]);
    updateVisibleFields();
    downloadPackageButton.style.display = "none";
  });
}
mergeChoiceSelect.addEventListener("change", updateVisibleFields);
document.querySelector('.task-button[data-task="buildDd"]').classList.add("active");
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
  showHelpSection(currentTask); // opens on the section for the current task
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
    "open_project_files, project_files, download_project, validate_project, " +
    "build_dd_project, build_nl_project, extract_project, design_project, " +
    "compare_project, merge_project, package_project, download_package)"
  );
  pyFunctions = {
    newProject: pyodide.globals.get("new_project"),
    openProject: pyodide.globals.get("open_project"),
    openProjectFiles: pyodide.globals.get("open_project_files"),
    projectFiles: pyodide.globals.get("project_files"),
    downloadProject: pyodide.globals.get("download_project"),
    validate: pyodide.globals.get("validate_project"),
    buildDd: pyodide.globals.get("build_dd_project"),
    buildNl: pyodide.globals.get("build_nl_project"),
    extract: pyodide.globals.get("extract_project"),
    design: pyodide.globals.get("design_project"),
    compare: pyodide.globals.get("compare_project"),
    merge: pyodide.globals.get("merge_project"),
    package: pyodide.globals.get("package_project"),
    downloadPackage: pyodide.globals.get("download_package"),
  };
  // exposed for console/debugging use, e.g. window.intentional.validate()
  window.intentional = pyFunctions;

  setStatus("ready", "Ready.");
  openProjectButton.disabled = false;
  newProjectButton.disabled = false;
  zipInput.disabled = false;
  folderInput.disabled = false;
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

// For an optional export (building): no file chosen just means no merge, not an error.
async function optionalFileBytesPy(input) {
  const file = input.files[0];
  if (!file) {
    return { name: "", bytesPy: null };
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  return { name: file.name, bytesPy: pyodideInstance.toPy(bytes) };
}

function setProjectOpen(open) {
  projectOpen = open;
  projectStatusEl.dataset.open = String(open);
  downloadProjectButton.disabled = !open;
  excelInput.disabled = !open;
  exportInput.disabled = !open;
  runButton.disabled = !open;
  downloadPackageButton.style.display = "none";
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

async function openFromFolder() {
  const files = Array.from(folderInput.files);
  if (!files.length) return pyFunctions.newProject();
  const entries = [];
  for (const file of files) {
    // the picked folder's own name is the first segment; strip it so files land
    // at the project root, the same as a zip's contents
    const relPath = file.webkitRelativePath.split("/").slice(1).join("/");
    if (!relPath) continue;
    const bytes = new Uint8Array(await file.arrayBuffer());
    entries.push([relPath, bytes]);
  }
  const entriesPy = pyodideInstance.toPy(entries);
  try {
    return pyFunctions.openProjectFiles(entriesPy);
  } finally {
    entriesPy.destroy();
  }
}

openProjectButton.addEventListener("click", async () => {
  await ready;
  try {
    let filesJson;
    if (currentProjectSourceType() === "folder") {
      filesJson = await openFromFolder();
    } else {
      const file = zipInput.files[0];
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
  const resultPy = pyFunctions.downloadProject();
  const bytes = resultPy.toJs();
  resultPy.destroy(); // pyodide does not auto-convert bytes, so this proxy needs releasing
  const blob = new Blob([bytes], { type: "application/zip" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "project.zip";
  link.click();
  URL.revokeObjectURL(url);
});

downloadPackageButton.addEventListener("click", () => {
  const resultPy = pyFunctions.downloadPackage();
  const bytes = resultPy.toJs();
  resultPy.destroy(); // pyodide does not auto-convert bytes, so this proxy needs releasing
  const blob = new Blob([bytes], { type: "application/zip" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = downloadPackageButton.textContent.replace(/^Download /, "") || "package.zip";
  link.click();
  URL.revokeObjectURL(url);
});

async function runTask(task) {
  const configName = configNameInput.value.trim();
  if (task === "validate") return pyFunctions.validate(configName);
  if (task === "buildDd") {
    const mergeChoice = currentMergeChoice();
    const { name, bytesPy } = mergeChoice
      ? await optionalFileBytesPy(exportInput)
      : { name: "", bytesPy: null };
    try {
      return pyFunctions.buildDd(configName, cleanInput.checked, bytesPy, name, mergeChoice || "restore");
    } finally {
      bytesPy?.destroy();
    }
  }
  if (task === "buildNl") {
    const mergeChoice = currentMergeChoice();
    const { name, bytesPy } = mergeChoice
      ? await optionalFileBytesPy(exportInput)
      : { name: "", bytesPy: null };
    try {
      return pyFunctions.buildNl(
        configName, verticalInput.value.trim(), contextInput.value.trim(),
        lowercaseInput.checked, reuseInput.checked, cleanInput.checked,
        bytesPy, name, mergeChoice || "restore"
      );
    } finally {
      bytesPy?.destroy();
    }
  }
  if (task === "extract") {
    const { name, bytesPy } = await fileBytesPy(excelInput, "an Excel file");
    try {
      return pyFunctions.extract(bytesPy, name, currentMode(), languageSelect.value);
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
      return pyFunctions.compare(bytesPy, name, currentMode(), configName);
    } finally {
      bytesPy.destroy();
    }
  }
  if (task === "merge") {
    const { name, bytesPy } = await fileBytesPy(exportInput, "an agent export zip");
    try {
      return pyFunctions.merge(bytesPy, name);
    } finally {
      bytesPy.destroy();
    }
  }
  if (task === "package") {
    const { name, bytesPy } = await fileBytesPy(exportInput, "an agent export zip");
    try {
      return pyFunctions.package(bytesPy, name);
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
  downloadPackageButton.style.display = "none";
  try {
    const resultJson = await runTask(currentTask);
    const parsed = JSON.parse(resultJson);
    render(parsed);
    if (parsed.output_name) {
      downloadPackageButton.textContent = `Download ${parsed.output_name}`;
      downloadPackageButton.style.display = "";
    }
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

function renderPackage(result, lines) {
  lines.push(textLine(`Style: ${result.style}`));
  lines.push(textLine(`Merged with ${result.source}`));
  for (const name of result.added) lines.push(textLine(`+ ${name}`));
  for (const change of result.changed) {
    lines.push(textLine(`~ ${change.name}: ${change.details.join("; ")}`));
  }
  for (const name of result.removed) lines.push(checkLine(`Removed: ${name}`, true));
  for (const name of result.needs_manual_removal) {
    lines.push(checkLine(`Marked for removal, but 'import' can't delete: ${name} - remove by hand`, false));
  }
  for (const name of result.unmarked) lines.push(textLine(`- ${name} (only in the export)`));
  lines.push(textLine(`${result.unchanged} unchanged`));
  if (result.output_name) lines.push(textLine(`Ready: ${result.output_name}`));
}

const RENDERERS = {
  validate: renderValidate,
  buildDd: renderBuild,
  buildNl: renderBuild,
  extract: renderExtract,
  design: renderDesign,
  compare: renderCompare,
  merge: renderPackage,
  package: renderPackage,
};

function render(result) {
  resultEl.textContent = "";
  const lines = [];
  RENDERERS[currentTask](result, lines);
  for (const line of lines) {
    resultEl.appendChild(line);
    resultEl.appendChild(document.createElement("br"));
  }
}

