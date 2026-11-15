"""Categories view – manage income and expense categories with color tags."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from theme import *
from dialogs import CategoryDialog


def _lbl(parent, text, size=12, color=TEXT, bold=False, anchor="w"):
    return ctk.CTkLabel(parent, text=text, text_color=color, anchor=anchor,
                        font=ctk.CTkFont(family=FONT_FAMILY, size=size,
                                         weight="bold" if bold else "normal"))


class CategoriesView(ctk.CTkFrame):
    def __init__(self, parent, db, profile_id: int, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.db = db
        self.profile_id = profile_id
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()
        self._load()

    def _build(self):
        # Header
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        top.grid_columnconfigure(1, weight=1)
        _lbl(top, "Categories", size=22, bold=True).grid(row=0, column=0, sticky="w")
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e")
        ctk.CTkButton(btn_frame, text="+ Income", fg_color=INCOME_BG, hover_color=INCOME_BG_H,
                      text_color=INCOME,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                      height=36, corner_radius=8, width=110,
                      command=lambda: self._add("income")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="+ Expense", fg_color=EXPENSE_BG, hover_color=EXPENSE_BG_H,
                      text_color=EXPENSE,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                      height=36, corner_radius=8, width=110,
                      command=lambda: self._add("expense")).pack(side="left")

        # Scrollable area
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=HOVER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        self._income_col  = self._make_section(scroll, "INCOME CATEGORIES",  INCOME,  0)
        self._expense_col = self._make_section(scroll, "EXPENSE CATEGORIES", EXPENSE, 1)

    def _make_section(self, parent, title: str, color: str, col: int):
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        frame.grid(row=0, column=col, sticky="nsew",
                   padx=(0 if col == 0 else 8, 0), pady=0)
        frame.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        dot = ctk.CTkFrame(hdr, fg_color=color, corner_radius=5,
                           width=10, height=10)
        dot.pack(side="left", padx=(0, 8))
        dot.pack_propagate(False)
        _lbl(hdr, title, size=12, color=TEXT_DIM, bold=True).pack(side="left")

        # Separator
        ctk.CTkFrame(frame, height=1, fg_color=BORDER).grid(
            row=1, column=0, sticky="ew", padx=0)

        # Cards list
        list_frame = ctk.CTkFrame(frame, fg_color="transparent")
        list_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=8)
        list_frame.grid_columnconfigure(0, weight=1)

        return {"frame": list_frame, "color": color, "type": "income" if color == INCOME else "expense"}

    def _load(self):
        for section in (self._income_col, self._expense_col):
            for w in section["frame"].winfo_children():
                w.destroy()
            cats = self.db.get_categories(self.profile_id, section["type"])
            if cats:
                for i, cat in enumerate(cats):
                    self._make_row(section["frame"], cat, i)
            else:
                _lbl(section["frame"], "No categories yet.", size=12,
                     color=TEXT_DIM).grid(padx=20, pady=12, sticky="w")

    def _make_row(self, parent, cat: dict, idx: int):
        row = ctk.CTkFrame(parent, fg_color="transparent", cursor="hand2", corner_radius=0)
        row.grid(row=idx * 2, column=0, sticky="ew")   # separators sit on odd rows
        row.grid_columnconfigure(1, weight=1)

        # Hover effect
        def on_enter(e): row.configure(fg_color=HOVER)
        def on_leave(e): row.configure(fg_color="transparent")
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

        # Color dot
        dot = ctk.CTkFrame(row, fg_color=cat["color"], corner_radius=12,
                           width=24, height=24)
        dot.grid(row=0, column=0, padx=(16, 10), pady=12)
        dot.grid_propagate(False)

        # Name (+ monthly budget for expense categories)
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w")
        _lbl(info, cat["name"], size=13, bold=False).pack(anchor="w")
        if cat["type"] == "expense":
            budget = self.db.get_budget(self.profile_id, cat["id"])
            if budget:
                currency = self.db.get_profile_currency(self.profile_id)
                _lbl(info, f"Budget: {currency} {budget:,.0f}/mo",
                     size=10, color=TEXT_MUTED).pack(anchor="w")

        # Transaction count badge
        count = self.db.category_transaction_count(cat["id"])
        if count > 0:
            badge = ctk.CTkFrame(row, fg_color=CARD2, corner_radius=10)
            badge.grid(row=0, column=2, padx=(4, 8))
            _lbl(badge, f"{count}", size=11, color=TEXT_DIM).pack(padx=8, pady=2)

        # Actions
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=(4, 12))

        ctk.CTkButton(btn_frame, text="Edit", width=52, height=26,
                      fg_color=CARD2, hover_color=HOVER, text_color=TEXT_DIM,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                      corner_radius=6,
                      command=lambda c=cat: self._edit(c)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_frame, text="Del", width=44, height=26,
                      fg_color="transparent", hover_color=EXPENSE_BG,
                      text_color=TEXT_DIM,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                      corner_radius=6,
                      command=lambda c=cat: self._delete(c)).pack(side="left")

        # Separator
        sep = ctk.CTkFrame(parent, height=1, fg_color=BORDER)
        sep.grid(row=idx * 2 + 1, column=0, sticky="ew")

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _add(self, preset_type: str):
        CategoryDialog(self, self.db, self.profile_id,
                       on_save=self._load, preset_type=preset_type)

    def _edit(self, cat: dict):
        CategoryDialog(self, self.db, self.profile_id,
                       on_save=self._load, category=cat)

    def _delete(self, cat: dict):
        count = self.db.category_transaction_count(cat["id"])
        if count > 0:
            messagebox.showwarning(
                "Cannot Delete",
                f"'{cat['name']}' has {count} transaction{'s' if count != 1 else ''}.\n"
                "Reassign or delete those transactions first.",
                parent=self)
            return
        ans = messagebox.askyesno(
            "Delete Category",
            f"Delete category '{cat['name']}'?\nThis cannot be undone.",
            parent=self)
        if ans:
            self.db.delete_category(cat["id"])
            self._load()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def set_profile(self, profile_id: int):
        self.profile_id = profile_id
        self._load()

    def refresh(self):
        self._load()
