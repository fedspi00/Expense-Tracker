"""Modal dialogs: transaction add/edit, category add/edit, profile add/edit."""
import tkinter as tk
import customtkinter as ctk
from datetime import date
from typing import Optional, Dict, Callable

from theme import *
from widgets import DateField


def _entry(parent, placeholder="", width=320, initial=""):
    e = ctk.CTkEntry(parent, fg_color=INPUT_BG, border_color=BORDER,
                     text_color=TEXT, placeholder_text=placeholder,
                     placeholder_text_color=TEXT_MUTED,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                     width=width, height=40, corner_radius=RADIUS_SM)
    if initial:
        e.insert(0, initial)
    return e


def _label(parent, text, size=11, color=TEXT_DIM, bold=True):
    return ctk.CTkLabel(parent, text=text,
                        font=ctk.CTkFont(family=FONT_FAMILY, size=size,
                                         weight="bold" if bold else "normal"),
                        text_color=color)


def _btn(parent, text, command, color=ACCENT, hover=ACCENT_H,
         text_color=TEXT, width=140):
    return ctk.CTkButton(parent, text=text, command=command,
                         fg_color=color, hover_color=hover,
                         text_color=text_color,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                         width=width, height=40, corner_radius=RADIUS_SM)


class _BaseDialog(ctk.CTkToplevel):
    """Common chrome: card background, centering, Esc to close."""

    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=CARD)
        self.grab_set()
        self.lift()
        self.focus_force()
        self.bind("<Escape>", lambda _: self.destroy())

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")

    def _footer(self, save_cmd, pady=(10, 26)):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=pady)
        _btn(btn_frame, "Cancel", self.destroy, color=CARD2, hover=HOVER,
             text_color=TEXT_DIM, width=120).pack(side="left")
        _btn(btn_frame, "Save", save_cmd, width=150).pack(side="right")


# ─────────────────────────────────────────────────────────────────────────────
# Transaction Dialog
# ─────────────────────────────────────────────────────────────────────────────

class TransactionDialog(_BaseDialog):
    def __init__(self, parent, db, profile_id: int,
                 on_save: Callable, transaction: Optional[Dict] = None):
        self.db = db
        self.profile_id = profile_id
        self.on_save = on_save
        self.transaction = transaction
        self.is_edit = transaction is not None
        super().__init__(parent, "Edit Transaction" if self.is_edit else "Add Transaction")

        self._build()
        self._center(parent)
        self.bind("<Return>", lambda _: self._save())

    def _build(self):
        pad = {"padx": 28, "pady": 7}
        currency = self.db.get_profile_currency(self.profile_id)

        title = "Edit Transaction" if self.is_edit else "New Transaction"
        _label(self, title, size=19, color=TEXT).pack(padx=28, pady=(26, 16), anchor="w")

        # Type toggle — selected color follows income / expense
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.pack(fill="x", **pad)
        _label(type_frame, "TYPE").pack(anchor="w", pady=(0, 6))

        initial_type = self.transaction["type"] if self.is_edit else "expense"
        self.type_var = ctk.StringVar(value=initial_type)
        self._seg = ctk.CTkSegmentedButton(
            type_frame, values=["income", "expense"],
            variable=self.type_var,
            fg_color=INPUT_BG,
            unselected_color=INPUT_BG, unselected_hover_color=HOVER,
            text_color=TEXT_DIM, text_color_disabled=TEXT_DIM,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            height=38, corner_radius=RADIUS_SM,
            command=self._on_type_change
        )
        self._seg.pack(fill="x")
        self._tint_type_toggle(initial_type)

        # Amount — the star of the form
        amt_frame = ctk.CTkFrame(self, fg_color="transparent")
        amt_frame.pack(fill="x", **pad)
        _label(amt_frame, "AMOUNT").pack(anchor="w", pady=(0, 6))
        amt_box = ctk.CTkFrame(amt_frame, fg_color=INPUT_BG, corner_radius=RADIUS_SM,
                               border_width=1, border_color=BORDER, height=52)
        amt_box.pack(fill="x")
        amt_box.pack_propagate(False)
        ctk.CTkLabel(amt_box, text=currency, text_color=TEXT_MUTED,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")
                     ).pack(side="left", padx=(16, 6))
        initial_amt = f"{self.transaction['amount']:.10g}" if self.is_edit else ""
        self.amount_entry = ctk.CTkEntry(
            amt_box, fg_color="transparent", border_width=0,
            text_color=TEXT, placeholder_text="0.00",
            placeholder_text_color=TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=21, weight="bold"))
        if initial_amt:
            self.amount_entry.insert(0, initial_amt)
        self.amount_entry.pack(side="left", fill="x", expand=True, padx=(0, 14))

        # Category
        cat_frame = ctk.CTkFrame(self, fg_color="transparent")
        cat_frame.pack(fill="x", **pad)
        _label(cat_frame, "CATEGORY").pack(anchor="w", pady=(0, 6))
        self._cat_var = ctk.StringVar()
        self._cat_menu = ctk.CTkOptionMenu(
            cat_frame, variable=self._cat_var,
            fg_color=INPUT_BG, button_color=INPUT_BG, button_hover_color=HOVER,
            text_color=TEXT, dropdown_fg_color=CARD2,
            dropdown_text_color=TEXT, dropdown_hover_color=HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            height=40, corner_radius=RADIUS_SM
        )
        self._cat_menu.pack(fill="x")
        self._refresh_categories()

        # Date — calendar picker
        date_frame = ctk.CTkFrame(self, fg_color="transparent")
        date_frame.pack(fill="x", **pad)
        _label(date_frame, "DATE").pack(anchor="w", pady=(0, 6))
        initial_date = self.transaction["date"] if self.is_edit else None
        self.date_field = DateField(date_frame, initial=initial_date)
        self.date_field.pack(fill="x")

        # Description
        desc_frame = ctk.CTkFrame(self, fg_color="transparent")
        desc_frame.pack(fill="x", **pad)
        _label(desc_frame, "DESCRIPTION  ·  optional").pack(anchor="w", pady=(0, 6))
        initial_desc = self.transaction.get("description", "") if self.is_edit else ""
        self.desc_entry = _entry(desc_frame, "e.g. Monthly rent", initial=initial_desc)
        self.desc_entry.pack(fill="x")

        # Error label
        self.error_var = ctk.StringVar()
        ctk.CTkLabel(self, textvariable=self.error_var, text_color=EXPENSE,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12)
                     ).pack(padx=28, anchor="w")

        self._footer(self._save)
        # Start in the amount field, but never yank the caret out of a field
        # the user has already clicked into while the window was settling.
        self.amount_entry.focus_set()
        self.after(120, self._focus_amount_if_idle)

    def _focus_amount_if_idle(self):
        """Second focus attempt for when the window manager steals focus during
        the open animation — skipped if the user got there first."""
        if not self.winfo_exists():
            return
        if self.grab_current() not in (None, self):
            return                       # the calendar popup owns input
        current = self.focus_get()
        if current is None or current is self:
            self.amount_entry.focus_set()

    def _tint_type_toggle(self, type_: str):
        color = INCOME if type_ == "income" else EXPENSE
        self._seg.configure(selected_color=mix(color, "#000000", 0.45),
                            selected_hover_color=mix(color, "#000000", 0.55))

    def _on_type_change(self, _=None):
        self._tint_type_toggle(self.type_var.get())
        self._refresh_categories()

    def _refresh_categories(self):
        t = self.type_var.get()
        cats = self.db.get_categories(self.profile_id, t)
        names = [c["name"] for c in cats]
        self._cats_map = {c["name"]: c for c in cats}
        self._cat_menu.configure(values=names if names else ["—"])
        if self.is_edit and self.transaction.get("category_name") in self._cats_map:
            self._cat_var.set(self.transaction["category_name"])
        elif names:
            self._cat_var.set(names[0])
        else:
            self._cat_var.set("—")

    def _save(self):
        raw_amount = self.amount_entry.get().strip().replace(",", ".")
        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.error_var.set("Amount must be a positive number.")
            return

        cat_name = self._cat_var.get()
        if cat_name == "—" or cat_name not in self._cats_map:
            self.error_var.set("Please select a valid category.")
            return

        cat = self._cats_map[cat_name]
        desc = self.desc_entry.get().strip()
        type_ = self.type_var.get()
        tx_date = self.date_field.get()

        if self.is_edit:
            self.db.update_transaction(self.transaction["id"], cat["id"],
                                       amount, desc, tx_date, type_)
        else:
            self.db.add_transaction(self.profile_id, cat["id"],
                                    amount, desc, tx_date, type_)

        self.on_save()
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Category Dialog
# ─────────────────────────────────────────────────────────────────────────────

class CategoryDialog(_BaseDialog):
    def __init__(self, parent, db, profile_id: int,
                 on_save: Callable, category: Optional[Dict] = None,
                 preset_type: str = "expense"):
        self.db = db
        self.profile_id = profile_id
        self.on_save = on_save
        self.category = category
        self.is_edit = category is not None
        self.selected_color = category["color"] if self.is_edit else PRESET_COLORS[8]
        super().__init__(parent, "Edit Category" if self.is_edit else "New Category")

        self._build(preset_type)
        self._center(parent)
        self.bind("<Return>", lambda _: self._save())

    def _build(self, preset_type):
        pad = {"padx": 28, "pady": 7}
        title = "Edit Category" if self.is_edit else "New Category"
        _label(self, title, size=19, color=TEXT).pack(padx=28, pady=(26, 16), anchor="w")

        # Type (only when creating)
        if not self.is_edit:
            type_frame = ctk.CTkFrame(self, fg_color="transparent")
            type_frame.pack(fill="x", **pad)
            _label(type_frame, "TYPE").pack(anchor="w", pady=(0, 6))
            self.type_var = ctk.StringVar(value=preset_type)
            ctk.CTkSegmentedButton(
                type_frame, values=["income", "expense"],
                variable=self.type_var,
                fg_color=INPUT_BG, selected_color=ACCENT, selected_hover_color=ACCENT_H,
                unselected_color=INPUT_BG, unselected_hover_color=HOVER,
                text_color=TEXT_DIM,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                height=38, corner_radius=RADIUS_SM,
                command=lambda _: self._toggle_budget_row()
            ).pack(fill="x")
        else:
            self.type_var = ctk.StringVar(value=self.category["type"])

        # Name
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.pack(fill="x", **pad)
        _label(name_frame, "NAME").pack(anchor="w", pady=(0, 6))
        initial_name = self.category["name"] if self.is_edit else ""
        self.name_entry = _entry(name_frame, "Category name", initial=initial_name)
        self.name_entry.pack(fill="x")
        self.name_entry.bind("<KeyRelease>", self._update_preview)

        # Monthly budget (expense categories only)
        currency = self.db.get_profile_currency(self.profile_id)
        self._budget_frame = ctk.CTkFrame(self, fg_color="transparent")
        _label(self._budget_frame,
               "MONTHLY BUDGET  ·  optional").pack(anchor="w", pady=(0, 6))
        initial_budget = ""
        if self.is_edit:
            b = self.db.get_budget(self.profile_id, self.category["id"])
            if b:
                initial_budget = f"{b:.10g}"
        self.budget_entry = _entry(self._budget_frame,
                                   f"e.g. 300 ({currency}, leave empty for none)",
                                   initial=initial_budget)
        self.budget_entry.pack(fill="x")
        self._budget_pad = pad
        self._toggle_budget_row()

        # Color picker
        color_frame = ctk.CTkFrame(self, fg_color="transparent")
        color_frame.pack(fill="x", **pad)
        self._color_frame = color_frame          # anchor for the budget row toggle
        _label(color_frame, "COLOR").pack(anchor="w", pady=(0, 6))

        grid = ctk.CTkFrame(color_frame, fg_color="transparent")
        grid.pack(anchor="w")
        self._color_btns = []
        for i, col in enumerate(PRESET_COLORS):
            btn = tk.Button(grid, bg=col, width=2, height=1, relief="flat",
                            cursor="hand2", bd=0)
            btn.configure(command=lambda c=col, b=btn: self._select_color(c, b))
            btn.grid(row=i // 8, column=i % 8, padx=3, pady=3, ipadx=4, ipady=4)
            self._color_btns.append((col, btn))

        # Highlight current color
        self._selected_btn = None
        for col, btn in self._color_btns:
            if col == self.selected_color:
                btn.configure(relief="solid", bd=2, highlightbackground=TEXT,
                              highlightthickness=2)
                self._selected_btn = btn
                break

        # Preview chip
        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.pack(fill="x", padx=28, pady=(4, 2))
        _label(preview_frame, "PREVIEW").pack(anchor="w", pady=(0, 6))
        self.preview = ctk.CTkFrame(preview_frame, fg_color=self.selected_color,
                                    corner_radius=20, width=96, height=30)
        self.preview.pack(anchor="w")
        self.preview_lbl = ctk.CTkLabel(
            self.preview, text=(self.category["name"][:14] if self.is_edit else "Category"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#0a0a10")
        self.preview_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Error
        self.error_var = ctk.StringVar()
        ctk.CTkLabel(self, textvariable=self.error_var, text_color=EXPENSE,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12)
                     ).pack(padx=28, anchor="w", pady=2)

        self._footer(self._save, pady=(6, 26))

    def _toggle_budget_row(self):
        """Budget applies to expense categories only."""
        if self.type_var.get() == "expense":
            if not self._budget_frame.winfo_ismapped():
                # During _build the color picker doesn't exist yet — pack plainly;
                # afterwards anchor before it so the row returns to its slot.
                if hasattr(self, "_color_frame"):
                    self._budget_frame.pack(fill="x", before=self._color_frame,
                                            **self._budget_pad)
                else:
                    self._budget_frame.pack(fill="x", **self._budget_pad)
        else:
            self._budget_frame.pack_forget()

    def _select_color(self, color: str, btn):
        self.selected_color = color
        if self._selected_btn:
            self._selected_btn.configure(relief="flat", bd=0)
        btn.configure(relief="solid", bd=2)
        self._selected_btn = btn
        self.preview.configure(fg_color=color)

    def _update_preview(self, _=None):
        name = self.name_entry.get().strip() or "Category"
        self.preview_lbl.configure(text=name[:14])

    def _parse_budget(self):
        """Returns (ok, value_or_None)."""
        if self.type_var.get() != "expense":
            return True, None
        raw = self.budget_entry.get().strip().replace(",", ".")
        if not raw:
            return True, None
        try:
            val = float(raw)
            if val <= 0:
                raise ValueError
            return True, val
        except ValueError:
            return False, None

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            self.error_var.set("Category name cannot be empty.")
            return
        ok, budget = self._parse_budget()
        if not ok:
            self.error_var.set("Budget must be a positive number (or empty).")
            return

        if self.is_edit:
            try:
                self.db.update_category(self.category["id"], name, self.selected_color)
            except Exception as e:
                self.error_var.set(f"Could not save: {e}")
                return
            cid = self.category["id"]
        else:
            type_ = self.type_var.get()
            try:
                cid = self.db.add_category(self.profile_id, name, type_, self.selected_color)
            except Exception as e:
                self.error_var.set(f"Could not save: {e}")
                return

        if self.type_var.get() == "expense":
            self.db.set_budget(self.profile_id, cid, budget)

        self.on_save()
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Profile Dialog
# ─────────────────────────────────────────────────────────────────────────────

class ProfileDialog(_BaseDialog):
    def __init__(self, parent, db, on_save: Callable, profile: Optional[Dict] = None):
        self.db = db
        self.on_save = on_save
        self.profile = profile
        self.is_edit = profile is not None
        super().__init__(parent, "Edit Profile" if self.is_edit else "New Profile")

        self._build()
        self._center(parent)
        self.bind("<Return>", lambda _: self._save())

    def _build(self):
        title = "Edit Profile" if self.is_edit else "New Profile"
        _label(self, title, size=19, color=TEXT).pack(padx=28, pady=(26, 16), anchor="w")

        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.pack(fill="x", padx=28, pady=7)
        _label(name_frame, "PROFILE NAME").pack(anchor="w", pady=(0, 6))
        initial_name = self.profile["name"] if self.is_edit else ""
        self.name_entry = _entry(name_frame, "e.g. Personal", initial=initial_name)
        self.name_entry.pack(fill="x")

        cur_frame = ctk.CTkFrame(self, fg_color="transparent")
        cur_frame.pack(fill="x", padx=28, pady=7)
        _label(cur_frame, "CURRENCY").pack(anchor="w", pady=(0, 6))
        initial_cur = self.profile["currency"] if self.is_edit else "EUR"
        self.cur_var = ctk.StringVar(value=initial_cur)
        ctk.CTkOptionMenu(cur_frame, variable=self.cur_var, values=CURRENCIES,
                          fg_color=INPUT_BG, button_color=INPUT_BG,
                          button_hover_color=HOVER, text_color=TEXT,
                          dropdown_fg_color=CARD2, dropdown_text_color=TEXT,
                          dropdown_hover_color=HOVER,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                          height=40, corner_radius=RADIUS_SM).pack(fill="x")

        self.error_var = ctk.StringVar()
        ctk.CTkLabel(self, textvariable=self.error_var, text_color=EXPENSE,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12)
                     ).pack(padx=28, anchor="w", pady=2)

        self._footer(self._save)

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            self.error_var.set("Profile name cannot be empty.")
            return
        cur = self.cur_var.get()
        try:
            if self.is_edit:
                self.db.update_profile(self.profile["id"], name, cur)
            else:
                self.db.add_profile(name, cur)
        except Exception as e:
            self.error_var.set(f"Could not save: {e}")
            return
        self.on_save()
        self.destroy()
