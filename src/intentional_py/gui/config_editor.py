"""Window for editing a config file as a table, with the same checks a build runs."""

import csv
import shutil
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from intentional_py import exceptions, models, user_settings, utils
from intentional_py import validate as validating
from intentional_py.gui import actions
from intentional_py.gui.widgets import LEVEL_NAMES, PAD, fit_columns, make_table

FIELDS = [
    "Intent",
    "Context",
    "Language",
    "Action",
    "Entities",
    "DTMF",
    "Machine learning",
]
ML_CHOICES = {"Default (on)": "", "TRUE": "TRUE", "FALSE": "FALSE"}


class EntityDialog(ctk.CTkToplevel):
    """Adds or edits one entity reference; created once and reused, like RowDialog."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.withdraw()
        self.title("Entity")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.on_save = None
        self.grid_columnconfigure(1, weight=1)
        self.type_input = ctk.CTkEntry(
            self, width=280, placeholder_text="e.g. sys.date or digits4"
        )
        self.type_input.grid(row=0, column=1, sticky="ew", **PAD)
        ctk.CTkLabel(self, text="Type").grid(row=0, column=0, sticky="w", **PAD)
        self.alias_input = ctk.CTkEntry(self, width=280, placeholder_text="optional")
        self.alias_input.grid(row=1, column=1, sticky="ew", **PAD)
        ctk.CTkLabel(self, text="Alias").grid(row=1, column=0, sticky="w", **PAD)
        self.required_var = ctk.BooleanVar(self, value=False)
        ctk.CTkCheckBox(self, text="Required", variable=self.required_var).grid(
            row=2, column=1, sticky="w", **PAD
        )
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", **PAD)
        ctk.CTkButton(
            buttons, text="Cancel", width=90, fg_color="gray", command=self._cancel
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(buttons, text="OK", width=90, command=self._save).grid(
            row=0, column=1
        )
        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self._cancel())

    def show(self, title: str, entity: models.Entity | None, on_save) -> None:
        self.title(title)
        self.on_save = on_save
        self.type_input.delete(0, "end")
        self.alias_input.delete(0, "end")
        if entity is not None:
            self.type_input.insert(0, entity.type.removeprefix("@"))
            if entity.aliased:
                self.alias_input.insert(0, entity.name)
            self.required_var.set(entity.required)
        else:
            self.required_var.set(False)
        self.deiconify()
        self.after(100, self.lift)
        self.grab_set()
        self.type_input.focus_set()

    def _save(self) -> None:
        on_save, self.on_save = self.on_save, None
        type_text = self.type_input.get().strip()
        if not type_text:
            self._cancel()
            return
        alias = self.alias_input.get().strip()
        text = f"{type_text}[{alias}]" if alias else type_text
        if self.required_var.get():
            text += "*"
        entity = models.Entity.parse(text)
        self._close()
        if on_save:
            on_save(entity)

    def _cancel(self) -> None:
        self.on_save = None
        self._close()

    def _close(self) -> None:
        self.grab_release()
        self.withdraw()


class RowDialog(ctk.CTkToplevel):
    """Edits one row; created once and reused, since recreating CTk widgets slows the app."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.withdraw()
        self.title("Config row")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.on_save = None
        self.entities: list[models.Entity] = []
        self.entity_dialog = EntityDialog(self)
        self.grid_columnconfigure(1, weight=1)
        self.inputs: dict[str, ctk.CTkEntry | ctk.CTkComboBox | ctk.CTkOptionMenu] = {}
        grid_row = 0
        for name in FIELDS:
            if name == "Entities":
                ctk.CTkLabel(self, text=name).grid(
                    row=grid_row, column=0, sticky="nw", **PAD
                )
                entities_frame, self.entities_table = make_table(
                    self, ["Type", "Alias", "Required"], height=4
                )
                entities_frame.grid(row=grid_row, column=1, sticky="ew", **PAD)
                self.entities_table.bind(
                    "<Double-1>", lambda _event: self._edit_entity()
                )
                self.entities_table.bind(
                    "<Delete>", lambda _event: self._delete_entity()
                )
                entity_buttons = ctk.CTkFrame(self, fg_color="transparent")
                entity_buttons.grid(row=grid_row + 1, column=1, sticky="w", padx=10)
                for column, (text, command) in enumerate(
                    [
                        ("Add", self._add_entity),
                        ("Edit", self._edit_entity),
                        ("Remove", self._delete_entity),
                    ]
                ):
                    ctk.CTkButton(
                        entity_buttons, text=text, width=70, command=command
                    ).grid(row=0, column=column, padx=(0, 6))
                grid_row += 2
                continue
            ctk.CTkLabel(self, text=name).grid(
                row=grid_row, column=0, sticky="w", **PAD
            )
            if name == "Language":
                languages = user_settings.load_language_settings()
                widget = ctk.CTkComboBox(
                    self, values=[*languages.languages, "dtmf"], width=360
                )
            elif name == "Machine learning":
                widget = ctk.CTkOptionMenu(self, values=list(ML_CHOICES), width=360)
            else:
                widget = ctk.CTkEntry(self, width=360)
            widget.grid(row=grid_row, column=1, sticky="ew", **PAD)
            self.inputs[name] = widget
            grid_row += 1
        ctk.CTkLabel(
            self,
            text="DTMF values are separated by |, e.g. 1|2. For entities: Add, double-click to edit, Delete to remove.",
            text_color="gray",
        ).grid(row=grid_row, column=0, columnspan=2, sticky="w", padx=10)
        grid_row += 1
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=grid_row, column=0, columnspan=2, sticky="e", **PAD)
        ctk.CTkButton(
            buttons, text="Cancel", width=90, fg_color="gray", command=self._cancel
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(buttons, text="OK", width=90, command=self._save).grid(
            row=0, column=1
        )
        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self._cancel())

    def show(self, title: str, values: list[str], on_save) -> None:
        self.title(title)
        self.on_save = on_save
        for name, value in zip(FIELDS, values, strict=True):
            if name == "Entities":
                self.entities = [
                    models.Entity.parse(part) for part in value.split("|") if part
                ]
                self._render_entities()
                continue
            widget = self.inputs[name]
            if isinstance(widget, ctk.CTkOptionMenu):
                label = next(
                    (k for k, v in ML_CHOICES.items() if v == value.upper()),
                    "Default (on)",
                )
                widget.set(label)
            elif isinstance(widget, ctk.CTkComboBox):
                widget.set(value)
            else:
                widget.delete(0, "end")
                widget.insert(0, value)
        self.deiconify()
        self.after(100, self.lift)
        self.grab_set()
        self.inputs["Intent"].focus_set()

    def _values(self) -> list[str]:
        values = []
        for name in FIELDS:
            if name == "Entities":
                values.append(
                    "|".join(entity.to_config_text() for entity in self.entities)
                )
                continue
            widget = self.inputs[name]
            value = widget.get().strip()
            values.append(ML_CHOICES[value] if name == "Machine learning" else value)
        return values

    def _render_entities(self) -> None:
        self.entities_table.delete(*self.entities_table.get_children())
        for entity in self.entities:
            self.entities_table.insert(
                "",
                "end",
                values=[
                    entity.type.removeprefix("@"),
                    entity.name if entity.aliased else "",
                    "Yes" if entity.required else "",
                ],
            )
        fit_columns(self.entities_table)

    def _selected_entity(self) -> int | None:
        selection = self.entities_table.selection()
        return self.entities_table.index(selection[0]) if selection else None

    def _add_entity(self) -> None:
        def save(entity: models.Entity) -> None:
            self.entities.append(entity)
            self._render_entities()

        self.entity_dialog.show("Add entity", None, save)

    def _edit_entity(self) -> None:
        index = self._selected_entity()
        if index is None:
            return

        def save(entity: models.Entity) -> None:
            self.entities[index] = entity
            self._render_entities()

        self.entity_dialog.show(f"Edit entity {index + 1}", self.entities[index], save)

    def _delete_entity(self) -> None:
        index = self._selected_entity()
        if index is not None:
            del self.entities[index]
            self._render_entities()

    def _save(self) -> None:
        on_save, self.on_save = self.on_save, None
        self._close()
        if on_save:
            on_save(self._values())

    def _cancel(self) -> None:
        self.on_save = None
        self._close()

    def _close(self) -> None:
        self.grab_release()
        self.withdraw()


class ConfigEditor(ctk.CTkToplevel):
    """Hidden rather than destroyed when closed, and reused for the next config."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.withdraw()
        self.geometry("1100x640")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.config_path: Path | None = None
        self.mode: str | None = None
        self.rows: list[list[str]] = []
        self.dirty = False
        self.dialog = RowDialog(self)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(4, weight=1)
        self.path_label = ctk.CTkLabel(
            self, text="", anchor="w", font=ctk.CTkFont(weight="bold")
        )
        self.path_label.grid(row=0, column=0, sticky="ew", **PAD)

        table_frame, self.table = make_table(self, ["#", *FIELDS], height=14)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        self.table.bind("<Double-1>", lambda _event: self._edit())
        self.table.bind("<Delete>", lambda _event: self._delete())

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", **PAD)
        for column, (text, command) in enumerate(
            [
                ("Add", self._add),
                ("Edit", self._edit),
                ("Duplicate", self._duplicate),
                ("Delete", self._delete),
                ("Move up", lambda: self._move(-1)),
                ("Move down", lambda: self._move(1)),
                ("Check", self._check),
            ]
        ):
            ctk.CTkButton(buttons, text=text, width=90, command=command).grid(
                row=0, column=column, padx=(0, 6)
            )
        buttons.grid_columnconfigure(7, weight=1)
        ctk.CTkButton(
            buttons, text="Close", width=90, fg_color="gray", command=self._close
        ).grid(row=0, column=8, padx=(6, 0))
        ctk.CTkButton(buttons, text="Save", width=90, command=self._save).grid(
            row=0, column=9, padx=(6, 0)
        )

        self.status = ctk.CTkLabel(self, text="", anchor="w", text_color="gray")
        self.status.grid(row=3, column=0, sticky="ew", padx=10)
        issues_frame, self.issues = make_table(
            self, ["Level", "Row", "Message"], height=5
        )
        issues_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # ----- opening and saving -----

    def open(self, config: Path, mode: str | None) -> None:
        if self.dirty and self.config_path != config and not self._confirm_discard():
            self._show()
            return
        if self.config_path != config or not self.dirty:
            try:
                rows = validating.read_config_rows(config) if config.exists() else []
            except exceptions.IntentionalException as error:
                messagebox.showerror(
                    "Intentional", actions.plain_text(str(error)), parent=self.master
                )
                return
            self.rows = [
                [cell.strip() for cell in row] + [""] * (7 - len(row)) for row in rows
            ]
            self.config_path, self.mode, self.dirty = config, mode, False
            self._render()
            self._check()
            if not config.exists():
                self.status.configure(
                    text=f"{config.name} does not exist yet; it is created when you save."
                )
        self._show()

    def _show(self) -> None:
        self.deiconify()
        self.after(200, self.lift)
        self.focus()

    def _save(self) -> None:
        if self.config_path is None:
            return
        try:
            if self.config_path.exists():
                backup = self.config_path.with_name(f"{self.config_path.name}.bak")
                with utils.file_errors(backup):
                    shutil.copy2(self.config_path, backup)
            with (
                utils.file_errors(self.config_path),
                self.config_path.open("w", encoding="utf-8", newline="") as file,
            ):
                csv.writer(file).writerows(self.rows)
        except exceptions.IntentionalException as error:
            messagebox.showerror(
                "Intentional", actions.plain_text(str(error)), parent=self
            )
            return
        self.dirty = False
        self._update_title()
        self._check()
        self.status.configure(
            text=f"Saved {len(self.rows)} rows. {self.status.cget('text')}"
        )

    def _confirm_discard(self) -> bool:
        return messagebox.askyesno(
            "Intentional",
            f"Discard the unsaved changes to {self.config_path.name}?",
            parent=self,
        )

    def _close(self) -> None:
        if self.dirty and not self._confirm_discard():
            return
        self.dirty = False
        self.dialog._cancel()
        self.withdraw()

    # ----- editing -----

    def _selected(self) -> int | None:
        selection = self.table.selection()
        return self.table.index(selection[0]) if selection else None

    def _changed(self, select: int | None = None) -> None:
        self.dirty = True
        self._render(select)
        self._check()

    def _add(self) -> None:
        after = self._selected()
        position = len(self.rows) if after is None else after + 1

        def insert(values: list[str]) -> None:
            self.rows.insert(position, values)
            self._changed(position)

        self.dialog.show(
            "Add row",
            [
                "",
                "",
                user_settings.load_language_settings().default_language,
                "",
                "",
                "",
                "",
            ],
            insert,
        )

    def _edit(self) -> None:
        index = self._selected()
        if index is None:
            return

        def update(values: list[str]) -> None:
            self.rows[index] = values
            self._changed(index)

        self.dialog.show(f"Edit row {index + 1}", list(self.rows[index]), update)

    def _duplicate(self) -> None:
        index = self._selected()
        if index is not None:
            self.rows.insert(index + 1, list(self.rows[index]))
            self._changed(index + 1)

    def _delete(self) -> None:
        index = self._selected()
        if index is not None:
            del self.rows[index]
            self._changed(min(index, len(self.rows) - 1) if self.rows else None)

    def _move(self, step: int) -> None:
        index = self._selected()
        target = None if index is None else index + step
        if target is not None and 0 <= target < len(self.rows):
            self.rows[index], self.rows[target] = self.rows[target], self.rows[index]
            self._changed(target)

    # ----- display -----

    def _update_title(self) -> None:
        name = self.config_path.name if self.config_path else ""
        self.title(f"Edit {name}{' *' if self.dirty else ''}")
        self.path_label.configure(text=str(self.config_path or ""))

    def _render(self, select: int | None = None) -> None:
        self._update_title()
        self.table.delete(*self.table.get_children())
        for number, row in enumerate(self.rows, start=1):
            self.table.insert("", "end", values=[number, *row])
        children = self.table.get_children()
        if select is not None and 0 <= select < len(children):
            self.table.selection_set(children[select])
            self.table.see(children[select])
        fit_columns(self.table, max_width=240)

    def _check(self) -> None:
        """Run the build's checks on the rows as they are now, and colour the rows with problems."""
        if self.config_path is None:
            return
        rules = user_settings.load_naming_rules()
        _, errors, warnings, _removals = validating.check_rows(
            self.rows, self.config_path.parent, self.mode, rules
        )
        issues = [actions.issue("error", e) for e in errors] + [
            actions.issue("warning", w) for w in warnings
        ]
        rows_with = {"error": set(), "warning": set()}
        for level, row, _ in issues:
            if row:
                rows_with[level].add(int(row) - 1)
        for index, item in enumerate(self.table.get_children()):
            level = (
                "error"
                if index in rows_with["error"]
                else "warning"
                if index in rows_with["warning"]
                else ""
            )
            self.table.item(item, tags=(level,) if level else ())
        self.issues.delete(*self.issues.get_children())
        for level, row, message in issues:
            self.issues.insert(
                "", "end", values=(LEVEL_NAMES[level], row, message), tags=(level,)
            )
        fit_columns(self.issues)
        if issues:
            text = f"{len(errors)} error(s) and {len(warnings)} warning(s), using the same checks as a build."
        else:
            text = "No problems found."
        self.status.configure(text=text + ("  Unsaved changes." if self.dirty else ""))
