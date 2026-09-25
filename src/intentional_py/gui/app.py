"""CustomTkinter window for intentional-py.

Widgets only collect values and display events; the work is done by
``gui.actions`` on a background thread started by ``gui.worker.JobRunner``.
"""

import queue
import sys
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from intentional_py import __version__, constants
from intentional_py.gui import actions
from intentional_py.gui.worker import GuiReporter, JobRunner
from intentional_py.reporting import Level

POLL_MS = 100
PAD = {"padx": 10, "pady": 6}
LEVEL_COLORS = {"warning": "#d18b00", "error": "#d64545"}
EXCEL_TYPES = [("Excel files", "*.xlsb *.xlsm *.xlsx"), ("All files", "*.*")]
CONFIG_TYPES = [("Config files", "*.cfg"), ("All files", "*.*")]


class App(ctk.CTk):
    def __init__(self, project: Path | None = None) -> None:
        super().__init__()
        self.title(f"Intentional {__version__}")
        self.geometry("920x740")
        self.minsize(740, 580)

        self.runner = JobRunner()
        self.running = False
        self.run_buttons: list[ctk.CTkButton] = []
        self.progress_text = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_project_row(project or Path.cwd())
        self._build_tabs()
        self._build_status()
        self._build_log()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(POLL_MS, self._poll)

    # ----- layout -----

    def _build_project_row(self, project: Path) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text="Project folder").grid(row=0, column=0, sticky="w", **PAD)
        self.project_entry = ctk.CTkEntry(frame)
        self.project_entry.insert(0, str(project))
        self.project_entry.grid(row=0, column=1, sticky="ew", **PAD)
        ctk.CTkButton(
            frame, text="Browse…", width=90, command=self._browse_project
        ).grid(row=0, column=2, **PAD)
        ctk.CTkLabel(frame, text=f"v{__version__}", text_color="gray").grid(
            row=0, column=3, **PAD
        )

    def _build_tabs(self) -> None:
        tabs = ctk.CTkTabview(self, height=250)
        tabs.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 0))
        self._build_dd_tab(self._tab(tabs, "Build DD"))
        self._build_nl_tab(self._tab(tabs, "Build NL"))
        self._build_extract_tab(self._tab(tabs, "Extract"))
        self._build_validate_tab(self._tab(tabs, "Validate"))

    @staticmethod
    def _tab(tabs: ctk.CTkTabview, name: str) -> ctk.CTkFrame:
        tab = tabs.add(name)
        tab.grid_columnconfigure(1, weight=1)
        return tab

    def _build_dd_tab(self, tab: ctk.CTkFrame) -> None:
        self.dd_config = self._file_row(
            tab, 0, "Config file", constants.DEFAULT_DD_CONFIG, CONFIG_TYPES
        )
        self._hint(tab, 1, "Training phrases are read from, and intents written to, the config file's folder.")
        self._run_button(tab, 2, "Build DD intents", self._run_dd)

    def _build_nl_tab(self, tab: ctk.CTkFrame) -> None:
        self.nl_config = self._file_row(
            tab, 0, "Config file", constants.DEFAULT_NL_CONFIG, CONFIG_TYPES
        )
        self.nl_vertical = self._entry_row(tab, 1, "Vertical prefix", "e.g. RTL")
        self.nl_context = self._entry_row(tab, 2, "Context", "")
        self.nl_context.insert(0, constants.DEFAULT_NL_CONTEXT)

        options = ctk.CTkFrame(tab, fg_color="transparent")
        options.grid(row=3, column=1, sticky="w")
        self.nl_reuse = ctk.CTkCheckBox(options, text="Reuse existing config")
        self.nl_reuse.grid(row=0, column=0, **PAD)
        self.nl_lowercase = ctk.CTkCheckBox(options, text="Lowercase actions")
        self.nl_lowercase.grid(row=0, column=1, **PAD)
        self._run_button(tab, 4, "Build NL intents", self._run_nl)

    def _build_extract_tab(self, tab: ctk.CTkFrame) -> None:
        self.xl_file = self._file_row(tab, 0, "Excel file", "", EXCEL_TYPES)

        options = ctk.CTkFrame(tab, fg_color="transparent")
        options.grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(options, text="Mode").grid(row=0, column=0, **PAD)
        self.xl_mode = ctk.CTkOptionMenu(options, values=["NL", "DD"], width=90)
        self.xl_mode.grid(row=0, column=1, **PAD)
        ctk.CTkLabel(options, text="Language").grid(row=0, column=2, **PAD)
        self.xl_language = ctk.CTkOptionMenu(
            options, values=list(constants.LANGUAGE_NAMES), width=90
        )
        self.xl_language.grid(row=0, column=3, **PAD)

        self._hint(tab, 2, "Phrases are saved under the project's Training Phrases folder; phrases being replaced are zipped first.")
        self._run_button(tab, 3, "Extract phrases", self._run_extract)

    def _build_validate_tab(self, tab: ctk.CTkFrame) -> None:
        self.val_config = self._file_row(
            tab, 0, "Config file", "Leave blank to check the standard config files", CONFIG_TYPES
        )
        self._run_button(tab, 1, "Validate", self._run_validate)

    def _build_status(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(6, 0))
        frame.grid_columnconfigure(0, weight=1)
        self.summary_label = ctk.CTkLabel(frame, text="Ready", anchor="w")
        self.summary_label.grid(row=0, column=0, sticky="ew", **PAD)
        self.progress = ctk.CTkProgressBar(frame)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=10)
        self.progress_label = ctk.CTkLabel(frame, text="", anchor="w")
        self.progress_label.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))

    def _build_log(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(frame, text="Log").grid(row=0, column=0, sticky="w", **PAD)
        ctk.CTkButton(frame, text="Clear", width=70, command=self._clear_log).grid(
            row=0, column=1, **PAD
        )
        self.log = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.log.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        for level, color in LEVEL_COLORS.items():
            self.log.tag_config(level, foreground=color)
        self.log.configure(state="disabled")

    # ----- widget helpers -----

    def _entry_row(self, tab: ctk.CTkFrame, row: int, label: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(tab, text=label).grid(row=row, column=0, sticky="w", **PAD)
        entry = ctk.CTkEntry(tab, placeholder_text=placeholder)
        entry.grid(row=row, column=1, sticky="ew", **PAD)
        return entry

    def _file_row(
        self, tab: ctk.CTkFrame, row: int, label: str, placeholder: str, filetypes: list
    ) -> ctk.CTkEntry:
        entry = self._entry_row(tab, row, label, placeholder)
        ctk.CTkButton(
            tab,
            text="Browse…",
            width=90,
            command=lambda: self._browse_file(entry, label, filetypes),
        ).grid(row=row, column=2, **PAD)
        return entry

    @staticmethod
    def _hint(tab: ctk.CTkFrame, row: int, text: str) -> None:
        ctk.CTkLabel(tab, text=text, text_color="gray", anchor="w", wraplength=620).grid(
            row=row, column=1, columnspan=2, sticky="w", padx=10
        )

    def _run_button(self, tab: ctk.CTkFrame, row: int, text: str, command: Callable) -> None:
        button = ctk.CTkButton(tab, text=text, command=command)
        button.grid(row=row, column=1, sticky="w", padx=10, pady=(12, 6))
        self.run_buttons.append(button)

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _initial_dir(self) -> str:
        project = Path(self.project_entry.get().strip())
        return str(project) if project.is_dir() else str(Path.cwd())

    def _browse_project(self) -> None:
        path = filedialog.askdirectory(parent=self, initialdir=self._initial_dir(), title="Project folder")
        if path:
            self._set_entry(self.project_entry, path)

    def _browse_file(self, entry: ctk.CTkEntry, title: str, filetypes: list) -> None:
        path = filedialog.askopenfilename(
            parent=self, initialdir=self._initial_dir(), title=title, filetypes=filetypes
        )
        if path:
            self._set_entry(entry, path)

    # ----- jobs -----

    def _run_dd(self) -> None:
        project, config = self.project_entry.get(), self.dd_config.get()
        self._start("Build DD intents", lambda r: actions.build_dd(project, config, r))

    def _run_nl(self) -> None:
        values = (
            self.project_entry.get(),
            self.nl_config.get(),
            self.nl_vertical.get(),
            self.nl_context.get(),
            bool(self.nl_lowercase.get()),
            bool(self.nl_reuse.get()),
        )
        self._start("Build NL intents", lambda r: actions.build_nl(*values, r))

    def _run_extract(self) -> None:
        values = (
            self.project_entry.get(),
            self.xl_file.get(),
            self.xl_mode.get(),
            self.xl_language.get(),
        )
        self._start("Extract phrases", lambda r: actions.extract(*values, r))

    def _run_validate(self) -> None:
        project, config = self.project_entry.get(), self.val_config.get()
        self._start("Validate", lambda r: actions.validate(project, config, r))

    def _start(self, title: str, job: Callable[[GuiReporter], actions.Result]) -> None:
        if self.running:
            return
        self._set_running(True)
        self._log("info", f"── {title} ──")
        self.summary_label.configure(text=f"{title}…", text_color=("gray10", "gray90"))
        self.progress.set(0)
        self.progress_label.configure(text="")
        self.runner.start(job)

    def _set_running(self, running: bool) -> None:
        self.running = running
        for button in self.run_buttons:
            button.configure(state="disabled" if running else "normal")

    def _on_close(self) -> None:
        # the worker thread is a daemon, so closing stops it mid-write
        if self.running and not messagebox.askyesno(
            "Intentional",
            "A job is still running. Closing now may leave incomplete files.\n\nClose anyway?",
            parent=self,
        ):
            return
        self.destroy()

    # ----- events from the worker -----

    def _poll(self) -> None:
        try:
            while True:
                self._handle(self.runner.events.get_nowait())
        except queue.Empty:
            pass
        finally:
            self.after(POLL_MS, self._poll)

    def _handle(self, event: tuple) -> None:
        kind, *data = event
        if kind == "message":
            level, text = data
            self._log(level, text)
        elif kind == "table":
            columns, rows, level = data
            self._log(level, " | ".join(columns))
            for row in rows:
                self._log(level, "    " + " | ".join(row))
        elif kind == "progress_start":
            self.progress_text, total = data
            self.progress.set(0)
            self.progress_label.configure(text=f"{self.progress_text}  0/{total}")
        elif kind == "progress":
            done, total = data
            self.progress.set(done / total if total else 1)
            self.progress_label.configure(text=f"{self.progress_text}  {done}/{total}")
        elif kind == "confirm":
            question, answer, answered = data
            answer["value"] = messagebox.askyesno(
                "Intentional", f"{question}?\n\nDetails are shown in the log.", parent=self
            )
            answered.set()
        elif kind == "done":
            self._finish(data[0])
        elif kind == "failed":
            self._log("error", data[0])
            self.summary_label.configure(text="✖ Failed — see the log for details", text_color=LEVEL_COLORS["error"])
            self._set_running(False)

    def _finish(self, result: actions.Result) -> None:
        for level, text in actions.details(result):
            self._log(level, text)
        figures = "    ".join(f"{name}: {value}" for name, value in actions.summary(result))
        self.summary_label.configure(text=f"✔ Done    {figures}", text_color=("gray10", "gray90"))
        self._set_running(False)

    def _log(self, level: Level, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{text}\n", level if level in LEVEL_COLORS else None)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def show_cli_notice(self, args: list[str]) -> None:
        notice = (
            f"Command-line options are ignored by the GUI: {' '.join(args)}\n"
            "Use intentional-cli for command-line use, e.g. intentional-cli nl -v FIN"
        )
        self._log("warning", notice)
        messagebox.showinfo("Intentional", notice, parent=self)


def main(project: Path | None = None) -> None:
    ctk.set_appearance_mode("system")
    App(project).mainloop()


def launch() -> None:
    """Entry point for the ``intentional`` command and ``intentional.exe``."""
    ctk.set_appearance_mode("system")
    app = App()
    if len(sys.argv) > 1:
        app.after(200, lambda: app.show_cli_notice(sys.argv[1:]))
    app.mainloop()
