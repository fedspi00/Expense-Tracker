"""Transactions view – filter, list, add/edit/delete, CSV export."""
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from datetime import date

from theme import *
from dialogs import TransactionDialog


def _lbl(parent, text, size=12, color=TEXT, bold=False):
    return ctk.CTkLabel(parent, text=text, text_color=color, anchor="w",
                        font=ctk.CTkFont(family=FONT_FAMILY, size=size,
                                         weight="bold" if bold else "normal"))


class TransactionsView(ctk.CTkFrame):
    def __init__(self, parent, db, profile_id: int, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.db = db
        self.profile_id = profile_id
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        today = date.today()
        self._month_var = ctk.StringVar(value="All")
        self._year_var  = ctk.StringVar(value=str(today.year))
        self._type_var  = ctk.StringVar(value="All")
        self._cat_var   = ctk.StringVar(value="All")
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._load())

        # Sorting state (default: newest first)
        self._sort_col = "date"
        self._sort_reverse = True

        self._selected_id: int | None = None
        self._tx_map: dict = {}

        self._build()
        self._load()

    def _category_values(self) -> list:
        names = sorted({c["name"] for c in self.db.get_categories(self.profile_id)})
        return ["All"] + names

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        top.grid_columnconfigure(99, weight=1)

        _lbl(top, "Transactions", size=22, bold=True).grid(
            row=0, column=0, sticky="w", padx=(0, 24))

        # Filters
        self._build_filter_pill(top, "Month", 1,
                                ["All"] + MONTH_NAMES, self._month_var)
        self._build_filter_pill(top, "Year",  2,
                                ["All"] + [str(y) for y in range(date.today().year + 1, 2018, -1)],
                                self._year_var)
        self._build_filter_pill(top, "Type",  3,
                                ["All", "income", "expense"], self._type_var)
        self._cat_menu = self._build_filter_pill(
            top, "Category", 4, self._category_values(), self._cat_var)

        # Search
        search = ctk.CTkEntry(top, textvariable=self._search_var,
                              fg_color=CARD, border_color=BORDER,
                              text_color=TEXT, placeholder_text="Search…",
                              placeholder_text_color=TEXT_MUTED,
                              font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                              height=36, corner_radius=RADIUS_SM, width=180)
        search.grid(row=0, column=5, padx=(10, 0))

        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.grid(row=0, column=100, sticky="e")
        ctk.CTkButton(btns, text="↓ CSV", fg_color=CARD, hover_color=HOVER,
                      text_color=TEXT_DIM, border_width=1, border_color=BORDER,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      height=36, corner_radius=RADIUS_SM, width=80,
                      command=self._export_csv).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="+ Add", fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=TEXT,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                      height=36, corner_radius=RADIUS_SM, width=100,
                      command=self._add).pack(side="left")

        # Table area
        table_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        table_card.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 20))
        table_card.grid_rowconfigure(1, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        # Table header
        hdr = ctk.CTkFrame(table_card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self._count_lbl = _lbl(hdr, "", size=12, color=TEXT_DIM)
        self._count_lbl.pack(side="left")
        # Action buttons (shown when row selected)
        self._edit_btn = ctk.CTkButton(hdr, text="Edit", width=80, height=30,
                                       fg_color=CARD2, hover_color=HOVER, text_color=TEXT,
                                       font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                       corner_radius=6, command=self._edit)
        self._del_btn  = ctk.CTkButton(hdr, text="Delete", width=80, height=30,
                                       fg_color=EXPENSE_BG, hover_color=EXPENSE_BG_H,
                                       text_color=EXPENSE,
                                       font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                       corner_radius=6, command=self._delete)
        self._edit_btn.pack(side="right", padx=(4, 0))
        self._del_btn.pack(side="right")
        self._edit_btn.pack_forget()
        self._del_btn.pack_forget()

        # Treeview
        self._build_tree(table_card)

    def _build_filter_pill(self, parent, label: str, col: int, values: list, var):
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS_SM)
        frame.grid(row=0, column=col, padx=(0, 6))
        _lbl(frame, label, size=10, color=TEXT_DIM).pack(side="left", padx=(10, 4), pady=6)
        menu = ctk.CTkOptionMenu(frame, variable=var, values=values,
                          fg_color=CARD, button_color=CARD, button_hover_color=HOVER,
                          text_color=TEXT, dropdown_fg_color=CARD2,
                          dropdown_text_color=TEXT, dropdown_hover_color=HOVER,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          height=28, width=110, corner_radius=6,
                          command=lambda _: self._load())
        menu.pack(side="left", padx=(0, 4), pady=4)
        return menu

    def _build_tree(self, parent):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Tx.Treeview",
                        background=CARD, foreground=TEXT,
                        fieldbackground=CARD, borderwidth=0, rowheight=44,
                        font=(FONT_FAMILY, 13))
        style.configure("Tx.Treeview.Heading",
                        background=CARD, foreground=TEXT_DIM,
                        borderwidth=0, font=(FONT_FAMILY, 11))
        style.map("Tx.Treeview",
                  background=[("selected", HOVER)],
                  foreground=[("selected", TEXT)])
        style.layout("Tx.Treeview", [("Tx.Treeview.treearea", {"sticky": "nswe"})])

        cols = ("date", "type", "category", "description", "amount")
        self._tree = ttk.Treeview(parent, columns=cols, show="headings",
                                  style="Tx.Treeview", selectmode="browse")
        self._heading_text = {
            "date": "Date", "type": "Type", "category": "Category",
            "description": "Description", "amount": "Amount",
        }
        for c in cols:
            anchor = "e" if c == "amount" else "w"
            self._tree.heading(c, text=self._heading_text[c], anchor=anchor,
                               command=lambda col=c: self._sort_by(col))
        self._tree.column("date",        width=100, anchor="w", stretch=False)
        self._tree.column("type",        width=85,  anchor="w", stretch=False)
        self._tree.column("category",    width=140, anchor="w", stretch=False)
        self._tree.column("description", anchor="w", minwidth=100)
        self._tree.column("amount",      width=110, anchor="e", stretch=False)

        self._tree.tag_configure("income",  foreground=INCOME)
        self._tree.tag_configure("expense", foreground=EXPENSE)

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        sb.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._edit())

    # ── Data ─────────────────────────────────────────────────────────────────

    def _sort_by(self, col: str):
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            # Amount and date feel most useful starting high → low
            self._sort_reverse = col in ("amount", "date")
        self._load()

    def _update_headings(self):
        for c, base in self._heading_text.items():
            arrow = ""
            if c == self._sort_col:
                arrow = "  ↓" if self._sort_reverse else "  ↑"
            self._tree.heading(c, text=base + arrow)

    def _sort_transactions(self, txs: list) -> list:
        keys = {
            "date":        lambda t: t["date"],
            "type":        lambda t: t["type"],
            "category":    lambda t: t["category_name"].lower(),
            "description": lambda t: (t.get("description") or "").lower(),
            "amount":      lambda t: t["amount"],
        }
        key = keys.get(self._sort_col, keys["date"])
        return sorted(txs, key=key, reverse=self._sort_reverse)

    def _load(self):
        txs = self._current_filtered()
        self._update_headings()
        currency = self.db.get_profile_currency(self.profile_id)

        for row in self._tree.get_children():
            self._tree.delete(row)
        self._tx_map.clear()
        self._selected_id = None
        self._hide_actions()

        for tx in txs:
            sign = "+" if tx["type"] == "income" else "−"
            amt  = f"{sign} {currency} {tx['amount']:,.2f}"
            iid  = self._tree.insert("", "end",
                                     values=(tx["date"], tx["type"].capitalize(),
                                             tx["category_name"],
                                             tx.get("description", "")[:55] or "—",
                                             amt),
                                     tags=(tx["type"],))
            self._tx_map[iid] = tx

        count = len(txs)
        self._count_lbl.configure(text=f"{count} transaction{'s' if count != 1 else ''}")

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            self._selected_id = self._tx_map.get(sel[0], {}).get("id")
            self._show_actions()
        else:
            self._selected_id = None
            self._hide_actions()

    def _show_actions(self):
        self._edit_btn.pack(side="right", padx=(4, 0))
        self._del_btn.pack(side="right")

    def _hide_actions(self):
        self._edit_btn.pack_forget()
        self._del_btn.pack_forget()

    # ── Export ────────────────────────────────────────────────────────────────

    def _current_filtered(self) -> list:
        """The transaction list exactly as currently filtered and sorted."""
        month_str = self._month_var.get()
        year_str  = self._year_var.get()
        type_str  = self._type_var.get()
        cat_str   = self._cat_var.get()
        search    = self._search_var.get().strip()
        month = MONTH_NAMES.index(month_str) + 1 if month_str in MONTH_NAMES else None
        year  = int(year_str) if year_str != "All" else None
        type_ = type_str if type_str != "All" else None
        txs = self.db.get_transactions(self.profile_id, month, year, type_, search)
        if cat_str != "All":
            txs = [t for t in txs if t["category_name"] == cat_str]
        return self._sort_transactions(txs)

    def _export_csv(self):
        txs = self._current_filtered()
        if not txs:
            messagebox.showinfo("Export CSV", "Nothing to export with the current filters.",
                                parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Export transactions", parent=self,
            defaultextension=".csv",
            initialfile=f"transactions_{date.today().isoformat()}.csv",
            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        currency = self.db.get_profile_currency(self.profile_id)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["date", "type", "category", "description",
                            "amount", "currency"])
                for t in txs:
                    w.writerow([t["date"], t["type"], t["category_name"],
                                t.get("description", ""), f"{t['amount']:.2f}", currency])
        except OSError as e:
            messagebox.showerror("Export CSV", f"Could not write file:\n{e}", parent=self)
            return
        messagebox.showinfo("Export CSV",
                            f"Exported {len(txs)} transaction{'s' if len(txs) != 1 else ''} to:\n{path}",
                            parent=self)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _add(self):
        TransactionDialog(self, self.db, self.profile_id, on_save=self._load)

    def _edit(self):
        if not self._selected_id:
            return
        sel = self._tree.selection()
        if not sel:
            return
        tx = self._tx_map.get(sel[0])
        if tx:
            TransactionDialog(self, self.db, self.profile_id,
                              on_save=self._load, transaction=tx)

    def _delete(self):
        if not self._selected_id:
            return
        sel = self._tree.selection()
        if not sel:
            return
        tx = self._tx_map.get(sel[0], {})
        desc = tx.get("description") or tx.get("category_name", "")
        ans = messagebox.askyesno(
            "Delete Transaction",
            f"Delete transaction '{desc}' ({tx.get('date', '')})?\nThis cannot be undone.",
            parent=self)
        if ans:
            self.db.delete_transaction(self._selected_id)
            self._load()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def set_profile(self, profile_id: int):
        self.profile_id = profile_id
        # Refresh category filter for the new profile's categories
        self._cat_menu.configure(values=self._category_values())
        if self._cat_var.get() not in self._category_values():
            self._cat_var.set("All")
        self._load()

    def refresh(self):
        self._load()
