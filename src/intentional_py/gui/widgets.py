"""Styling and table helpers shared by the GUI windows."""

import tkinter.font as tkfont
from tkinter import ttk

import customtkinter as ctk

PAD = {"padx": 10, "pady": 6}
LEVEL_COLORS = {"warning": "#d18b00", "error": "#d64545"}
LEVEL_NAMES = {"warning": "\u26a0 Warning", "error": "\u2716 Error"}
TABLE_STYLE = "Results.Treeview"


def select_tab(tabs: ctk.CTkTabview, name: str) -> None:
    # CTkTabview.set() hides the other tabs 100 ms later, which can hide a tab selected
    # (or renamed) in the meantime; selecting again once that has passed keeps it shown
    tabs.set(name)
    tabs.after(150, lambda: tabs.get() == name and tabs.set(name))


def style_tables(root: ctk.CTk) -> None:
    """Match ttk tables, which CustomTkinter does not theme, to the current appearance."""
    dark = ctk.get_appearance_mode() == "Dark"
    theme = ctk.ThemeManager.theme
    pick = lambda colors: colors[1] if dark else colors[0]  # noqa: E731
    background = pick(theme["CTkTextbox"]["fg_color"])
    foreground = pick(theme["CTkLabel"]["text_color"])
    row_height = tkfont.nametofont("TkDefaultFont").metrics("linespace") + 8
    style = ttk.Style(root)
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


def make_table(parent, columns: list[str], height: int = 8) -> tuple[ctk.CTkFrame, ttk.Treeview]:
    """A styled table with a scrollbar and colour tags for warning and error rows."""
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid_columnconfigure(0, weight=1)
    container.grid_rowconfigure(0, weight=1)
    table = ttk.Treeview(container, columns=columns, show="headings", height=height, style=TABLE_STYLE)
    set_columns(table, columns)
    for level, color in LEVEL_COLORS.items():
        table.tag_configure(level, foreground=color)
    table.bind("<Configure>", lambda _event: fit_columns(table))
    # a small height lets short tables shrink; the grid stretches it to the table
    scrollbar = ctk.CTkScrollbar(container, command=table.yview, height=16)
    table.configure(yscrollcommand=scrollbar.set)
    table.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    return container, table


def set_columns(table: ttk.Treeview, columns: list[str]) -> None:
    table.configure(columns=columns)
    for column in columns:
        table.heading(column, text=column, anchor="w")
        table.column(column, anchor="w", width=160)


def fit_columns(table: ttk.Treeview, max_width: int = 320) -> None:
    """Size columns to their contents; the last column takes the remaining width."""
    columns = list(table["columns"])
    if not columns:
        return
    font = tkfont.nametofont("TkDefaultFont")
    rows = [table.item(item, "values") for item in table.get_children()]
    used = 0
    for index, column in enumerate(columns[:-1]):
        texts = [column] + [str(row[index]) for row in rows if index < len(row)]
        width = min(max(font.measure(text) for text in texts) + 24, max_width)
        table.column(column, width=width, stretch=False)
        used += width
    table.column(columns[-1], width=max(table.winfo_width() - used - 4, 200), stretch=True)
