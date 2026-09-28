"""CustomTkinter window for intentional-py.

Widgets only collect values and display events; the work is done by
``gui.actions`` on a background thread started by ``gui.worker.JobRunner``.
"""

import queue
import sys
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from intentional_py import __version__, constants
from intentional_py.gui import actions, help_text
from intentional_py.gui.worker import GuiReporter, JobRunner
from intentional_py.reporting import Level

POLL_MS = 100
PAD = {"padx": 10, "pady": 6}
LEVEL_COLORS = {"warning": "#d18b00", "error": "#d64545"}
LEVEL_NAMES = {"warning": "⚠ Warning", "error": "✖ Error"}
EXCEL_TYPES = [("Excel files", "*.xlsb *.xlsm *.xlsx"), ("All files", "*.*")]
CONFIG_TYPES = [("Config files", "*.cfg"), ("All files", "*.*")]
TABLE_STYLE = "Results.Treeview"


def select_tab(tabs: ctk.CTkTabview, name: str) -> None:
    # CTkTabview.set() hides the other tabs 100 ms later, which can hide a tab selected
    # (or renamed) in the meantime; selecting again once that has passed keeps it shown
    tabs.set(name)
    tabs.after(150, lambda: tabs.get() == name and tabs.set(name))


class HelpWindow(ctk.CTkToplevel):
    """Explains the modes; hidden rather than destroyed when closed, and reused."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.title("Intentional help")
        self.geometry("760x600")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.sections = ctk.CTkTabview(self)
        self.sections.pack(fill="both", expand=True, padx=10, pady=10)
        for name, text in help_text.SECTIONS.items():
            box = ctk.CTkTextbox(self.sections.add(name), wrap="word", font=ctk.CTkFont(size=13))
            box.pack(fill="both", expand=True)
            box.insert("1.0", text)
            box.configure(state="disabled")

    def show(self, section: str) -> None:
        self.deiconify()
        select_tab(self.sections, section)
        # on Windows a new CTkToplevel can open behind its parent
        self.after(200, self.lift)
        self.focus()


class App(ctk.CTk):
    def __init__(self, project: Path | None = None) -> None:
        super().__init__()
        self.title(f"Intentional {__version__}")
        self.geometry("960x820")
        self.minsize(760, 660)

        self.runner = JobRunner()
        self.running = False
        self.run_buttons: list[ctk.CTkButton] = []
        self.job_title = ""
        self.job_issues: list[actions.Issue] = []
        self.job_tables: list[actions.Table] = []
        self.output_dir: Path | None = None
        self.issues_tab = "Issues"
        self.help_window: HelpWindow | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._style_tables()
        self._build_project_row(project or Path.cwd())
        self._build_tabs()
        self._build_results()
        self.bind("<F1>", lambda _event: self._show_help())
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
            row=0, column=3, padx=(10, 0), pady=6
        )
        self.help_menu = tk.Menu(self, tearoff=0)
        self.help_menu.add_command(label="Help", accelerator="F1", command=self._show_help)
        self.help_menu.add_separator()
        self.help_menu.add_command(label="About Intentional", command=self._show_about)
        help_button = ctk.CTkButton(
            frame,
            text="?",
            width=28,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=lambda: self._open_help_menu(help_button),
        )
        help_button.grid(row=0, column=4, **PAD)

    def _build_tabs(self) -> None:
        tabs = ctk.CTkTabview(self, height=210)
        tabs.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 0))
        self.mode_tabs = tabs
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

    def _build_results(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        head.grid_columnconfigure(0, weight=1)
        self.headline = ctk.CTkLabel(
            head, text="Ready", anchor="w", font=ctk.CTkFont(size=15, weight="bold")
        )
        self.headline.grid(row=0, column=0, sticky="ew")
        self.open_button = ctk.CTkButton(
            head, text="Open folder", width=110, command=self._open_output
        )
        self.open_button.grid(row=0, column=1)
        self.open_button.grid_remove()

        progress = ctk.CTkFrame(frame, fg_color="transparent")
        progress.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 0))
        progress.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(progress)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.progress_label = ctk.CTkLabel(progress, text="", text_color="gray", width=200, anchor="e")
        self.progress_label.grid(row=0, column=1, padx=(10, 0))

        self.tiles_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.tiles_frame.grid(row=2, column=0, sticky="ew", padx=10)
        # created once and reused: recreating CTk widgets per job slowed later jobs dramatically
        self.tiles: list[tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = []
        for column in range(6):
            tile = ctk.CTkFrame(self.tiles_frame, corner_radius=8)
            value = ctk.CTkLabel(tile, text="", font=ctk.CTkFont(size=22, weight="bold"))
            value.pack(padx=18, pady=(8, 0))
            caption = ctk.CTkLabel(tile, text="", text_color="gray")
            caption.pack(padx=18, pady=(0, 8))
            tile.grid(row=0, column=column, padx=(0, 8), pady=8)
            tile.grid_remove()
            self.tiles.append((tile, value, caption))

        self.result_tabs = ctk.CTkTabview(frame)
        self.result_tabs.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        issues_tab = self.result_tabs.add(self.issues_tab)
        details_tab = self.result_tabs.add("Details")
        log_tab = self.result_tabs.add("Log")

        issues, self.issues_table = self._table(issues_tab, ["Level", "Row", "Message"])
        issues.pack(fill="both", expand=True)

        self.details_frame = ctk.CTkScrollableFrame(details_tab, fg_color="transparent")
        self.details_frame.pack(fill="both", expand=True)
        self.details_frame.grid_columnconfigure(0, weight=1)
        self.details_empty = ctk.CTkLabel(self.details_frame, text="Nothing to show yet.", text_color="gray")
        self.details_tables: list[tuple[ctk.CTkLabel, ctk.CTkFrame, ttk.Treeview]] = []

        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(0, weight=1)
        self.log = ctk.CTkTextbox(log_tab, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.log.grid(row=0, column=0, sticky="nsew")
        for level, color in LEVEL_COLORS.items():
            self.log.tag_config(level, foreground=color)
        self.log.configure(state="disabled")
        ctk.CTkButton(log_tab, text="Clear", width=70, command=self._clear_log).grid(
            row=1, column=0, sticky="e", pady=(6, 0)
        )

    def _style_tables(self) -> None:
        """Match ttk tables, which CustomTkinter does not theme, to the current appearance."""
        dark = ctk.get_appearance_mode() == "Dark"
        theme = ctk.ThemeManager.theme
        pick = lambda colors: colors[1] if dark else colors[0]  # noqa: E731
        background = pick(theme["CTkTextbox"]["fg_color"])
        foreground = pick(theme["CTkLabel"]["text_color"])
        row_height = tkfont.nametofont("TkDefaultFont").metrics("linespace") + 8
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            TABLE_STYLE,
            background=background,
            fieldbackground=background,
            foreground=foreground,
            rowheight=row_height,
            borderwidth=0,
            bordercolor=background,
            lightcolor=background,
            darkcolor=background,
        )
        style.configure(
            f"{TABLE_STYLE}.Heading",
            background=pick(theme["CTkFrame"]["top_fg_color"]),
            foreground=foreground,
            relief="flat",
        )
        style.map(
            TABLE_STYLE,
            background=[("selected", pick(theme["CTkButton"]["fg_color"]))],
            foreground=[("selected", "white")],
        )

    def _table(
        self, parent, columns: list[str], height: int = 8
    ) -> tuple[ctk.CTkFrame, ttk.Treeview]:
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        table = ttk.Treeview(
            container, columns=columns, show="headings", height=height, style=TABLE_STYLE
        )
        for column in columns:
            table.heading(column, text=column, anchor="w")
            table.column(column, anchor="w", width=160)
        for level, color in LEVEL_COLORS.items():
            table.tag_configure(level, foreground=color)
        table.bind("<Configure>", lambda _event: self._fit_columns(table))
        # a small height lets short tables shrink; the grid stretches it to the table
        scrollbar = ctk.CTkScrollbar(container, command=table.yview, height=16)
        table.configure(yscrollcommand=scrollbar.set)
        table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return container, table

    def _open_help_menu(self, button: ctk.CTkButton) -> None:
        # right-aligned under the button, as the button sits in the window's corner
        x = button.winfo_rootx() + button.winfo_width() - self.help_menu.winfo_reqwidth()
        y = button.winfo_rooty() + button.winfo_height()
        try:
            self.help_menu.tk_popup(x, y)
        finally:
            self.help_menu.grab_release()

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About Intentional",
            f"Intentional {__version__}\n\n"
            "Creates Dialogflow ES intents from config and training phrase files.\n\n"
            "https://github.com/andrewjstuart/intentional-py",
            parent=self,
        )

    def _show_help(self) -> None:
        # the first time starts with the overview; after that, the section for the current tab
        if self.help_window is None:
            self.help_window = HelpWindow(self)
            section = next(iter(help_text.SECTIONS))
        else:
            section = self.mode_tabs.get()
        self.help_window.show(section if section in help_text.SECTIONS else next(iter(help_text.SECTIONS)))

    @staticmethod
    def _fit_columns(table: ttk.Treeview) -> None:
        """Size columns to their contents; the last column takes the remaining width."""
        columns = list(table["columns"])
        if not columns:
            return
        font = tkfont.nametofont("TkDefaultFont")
        rows = [table.item(item, "values") for item in table.get_children()]
        used = 0
        for index, column in enumerate(columns[:-1]):
            texts = [column] + [str(row[index]) for row in rows if index < len(row)]
            width = min(max(font.measure(text) for text in texts) + 24, 320)
            table.column(column, width=width, stretch=False)
            used += width
        table.column(columns[-1], width=max(table.winfo_width() - used - 4, 200), stretch=True)

    def _select_result_tab(self, name: str) -> None:
        select_tab(self.result_tabs, name)

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
        self.job_title = title
        self.job_issues = []
        self.job_tables = []
        self.output_dir = None
        self.open_button.grid_remove()
        self._show_tiles([])
        self._show_issues([])
        self._show_details([])
        self._select_result_tab("Log")
        self._log("info", f"── {title} ──")
        self.headline.configure(text=f"{title}…", text_color=("gray10", "gray90"))
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
            if level in LEVEL_COLORS:
                self.job_issues.append(actions.issue(level, text))
        elif kind == "table":
            columns, rows, level = data
            self._log(level, " | ".join(columns))
            for row in rows:
                self._log(level, "    " + " | ".join(row))
            # single-column tables are titled lists (duplicates, 'uh'/'um' phrases)
            title, columns = (columns[0], ["Phrase"]) if len(columns) == 1 else ("NL config", columns)
            self.job_tables.append((title, columns, rows))
            if level in LEVEL_COLORS:
                self.job_issues.append(("warning", "", f"{title} ({len(rows)}), listed under Details"))
        elif kind == "progress_start":
            _, total = data
            self.progress.set(0)
            self.progress_label.configure(text=f"0/{total}")
        elif kind == "progress":
            done, total = data
            self.progress.set(done / total if total else 1)
            self.progress_label.configure(text=f"{done}/{total}")
        elif kind == "confirm":
            question, answer, answered = data
            self._show_details(self.job_tables)
            self._select_result_tab("Details")
            self.update_idletasks()
            answer["value"] = messagebox.askyesno(
                "Intentional", f"{question}?\n\nThe phrases are listed under Details.", parent=self
            )
            answered.set()
        elif kind == "done":
            self._finish(data[0])
        elif kind == "failed":
            self._fail(data[0])

    def _finish(self, result: actions.Result) -> None:
        issues = self.job_issues + actions.result_issues(result)
        warnings = sum(level == "warning" for level, _, _ in issues)
        ok, text = actions.headline(self.job_title, result, warnings)
        self.headline.configure(
            text=f"{'✔' if ok else '⚠'} {text}",
            text_color=("gray10", "gray90") if ok else LEVEL_COLORS["warning"],
        )
        self._log("info", text)
        self._show_tiles(actions.tiles(result))
        self._show_issues(issues)
        self._show_details(actions.detail_tables(result) + self.job_tables)
        folder = actions.output_folder(result)
        if folder is not None and folder.is_dir():
            self.output_dir = folder
            self.open_button.grid()
        self._select_result_tab(self.issues_tab if issues else "Details")
        self._set_running(False)

    def _fail(self, text: str) -> None:
        self._log("error", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if text.startswith("Traceback"):
            failures = [f"Unexpected error: {lines[-1]}. The full details are in the Log."]
        else:
            # 'Configuration validation failed:' is followed by one '- Row N: ...' line per problem
            failures = [line[2:] for line in lines if line.startswith("- ")] or [" ".join(lines)]
        self.job_issues.extend(actions.issue("error", failure) for failure in failures)
        self.headline.configure(text=f"✖ {self.job_title} failed", text_color=LEVEL_COLORS["error"])
        self._show_issues(self.job_issues)
        self._show_details(self.job_tables)
        self._select_result_tab(self.issues_tab)
        self._set_running(False)

    def _show_tiles(self, figures: list[tuple[str, str]]) -> None:
        for index, (tile, value, caption) in enumerate(self.tiles):
            if index < len(figures):
                caption.configure(text=figures[index][0])
                value.configure(text=figures[index][1])
                tile.grid()
            else:
                tile.grid_remove()

    def _show_issues(self, issues: list[actions.Issue]) -> None:
        self.issues_table.delete(*self.issues_table.get_children())
        for level, row, message in issues:
            self.issues_table.insert("", "end", values=(LEVEL_NAMES[level], row, message), tags=(level,))
        self._fit_columns(self.issues_table)
        errors = sum(level == "error" for level, _, _ in issues)
        warnings = len(issues) - errors
        counts = [f"{errors} error{'s' * (errors != 1)}"] * bool(errors)
        counts += [f"{warnings} warning{'s' * (warnings != 1)}"] * bool(warnings)
        name = f"Issues ({', '.join(counts)})" if counts else "Issues"
        if name != self.issues_tab:
            self.result_tabs.rename(self.issues_tab, name)
            self.issues_tab = name

    def _show_details(self, tables: list[actions.Table]) -> None:
        # widgets are reused between jobs for the same reason as the tiles
        while len(self.details_tables) < len(tables):
            title = ctk.CTkLabel(self.details_frame, anchor="w", font=ctk.CTkFont(weight="bold"))
            container, table = self._table(self.details_frame, [""])
            self.details_tables.append((title, container, table))
        if tables:
            self.details_empty.grid_remove()
        else:
            self.details_empty.grid(row=0, column=0, sticky="w", **PAD)
        for index, (title, container, table) in enumerate(self.details_tables):
            if index >= len(tables):
                title.grid_remove()
                container.grid_remove()
                continue
            name, columns, rows = tables[index]
            title.configure(text=name)
            table.delete(*table.get_children())
            table.configure(columns=columns, height=max(1, min(len(rows), 8)))
            for column in columns:
                table.heading(column, text=column, anchor="w")
                table.column(column, anchor="w", width=160)
            for row in rows:
                table.insert("", "end", values=row)
            self._fit_columns(table)
            title.grid(row=index * 2, column=0, sticky="ew", padx=4, pady=(10, 2))
            container.grid(row=index * 2 + 1, column=0, sticky="ew", padx=4)

    def _open_output(self) -> None:
        if self.output_dir is None:
            return
        try:
            actions.open_folder(self.output_dir)
        except OSError as error:
            messagebox.showerror("Intentional", f"Could not open {self.output_dir}:\n{error}", parent=self)

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
