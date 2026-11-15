"""Dashboard view – wealth banner, summary cards, budgets, recent transactions, donut chart."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from datetime import date
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from theme import *
from dialogs import TransactionDialog


def _lbl(parent, text, size=12, color=TEXT, bold=False, anchor="w"):
    return ctk.CTkLabel(parent, text=text, text_color=color, anchor=anchor,
                        font=ctk.CTkFont(family=FONT_FAMILY, size=size,
                                         weight="bold" if bold else "normal"))


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, db, profile_id: int, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.db = db
        self.profile_id = profile_id
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        today = date.today()
        self._month = today.month
        self._year = today.year

        self._build()
        self._load()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build(self):
        # ── Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=PAD_PAGE, pady=(24, 12))
        top.grid_columnconfigure(1, weight=1)

        title_frame = ctk.CTkFrame(top, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")
        _lbl(title_frame, "Dashboard", size=22, bold=True).pack(side="left", padx=(0, 20))

        # Month navigation
        nav = ctk.CTkFrame(top, fg_color=CARD, corner_radius=RADIUS_SM)
        nav.grid(row=0, column=1, sticky="w")
        ctk.CTkButton(nav, text="‹", width=32, height=32, fg_color="transparent",
                      hover_color=HOVER, text_color=TEXT,
                      font=ctk.CTkFont(size=18, weight="bold"),
                      command=self._prev_month).pack(side="left", padx=4, pady=4)
        self._period_lbl = _lbl(nav, "", size=14, bold=True)
        self._period_lbl.pack(side="left", padx=8)
        ctk.CTkButton(nav, text="›", width=32, height=32, fg_color="transparent",
                      hover_color=HOVER, text_color=TEXT,
                      font=ctk.CTkFont(size=18, weight="bold"),
                      command=self._next_month).pack(side="left", padx=4, pady=4)

        # Add button
        ctk.CTkButton(top, text="+  Add Transaction", fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                      height=38, corner_radius=RADIUS_SM,
                      command=self._add_transaction).grid(row=0, column=2, sticky="e")

        # ── Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=HOVER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=PAD_PAGE, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)

        # ── Wealth banner (opening balance → net → closing)
        self._wealth_card = self._build_wealth_banner(scroll)

        # Summary cards
        self._cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._cards_frame.pack(fill="x", pady=(0, 20))
        for i in range(3):
            self._cards_frame.grid_columnconfigure(i, weight=1)
        self._income_card  = self._make_card(self._cards_frame, 0, "INCOME",     INCOME,  "↑")
        self._expense_card = self._make_card(self._cards_frame, 1, "EXPENSES",   EXPENSE, "↓")
        self._balance_card = self._make_card(self._cards_frame, 2, "NET CHANGE", BALANCE_POS, "±")

        # Main area (transactions + chart)
        main_row = ctk.CTkFrame(scroll, fg_color="transparent")
        main_row.pack(fill="both", expand=True)
        main_row.grid_columnconfigure(0, weight=3)
        main_row.grid_columnconfigure(1, weight=2)
        main_row.grid_rowconfigure(0, weight=1)

        # Recent transactions
        tx_card = ctk.CTkFrame(main_row, fg_color=CARD, corner_radius=RADIUS,
                               border_width=1, border_color=BORDER)
        tx_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tx_card.grid_rowconfigure(1, weight=1)
        tx_card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(tx_card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        _lbl(hdr, "Recent Transactions", size=15, bold=True).pack(side="left")
        ctk.CTkButton(hdr, text="View all →", fg_color="transparent",
                      hover_color=HOVER, text_color=ACCENT_LITE,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      height=28, command=lambda: self.app.show_view("transactions")
                      ).pack(side="right")

        # Treeview
        self._tree_frame = ctk.CTkFrame(tx_card, fg_color="transparent")
        self._tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 14))
        self._build_tree(self._tree_frame)

        # Chart card
        chart_card = ctk.CTkFrame(main_row, fg_color=CARD, corner_radius=RADIUS,
                                  border_width=1, border_color=BORDER)
        chart_card.grid(row=0, column=1, sticky="nsew")
        chart_card.grid_rowconfigure(1, weight=1)
        chart_card.grid_rowconfigure(2, weight=0)
        chart_card.grid_columnconfigure(0, weight=1)
        _lbl(chart_card, "Expenses by Category", size=15, bold=True).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        self._chart_frame = ctk.CTkFrame(chart_card, fg_color="transparent")
        self._chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))
        self._legend_frame = ctk.CTkFrame(chart_card, fg_color="transparent")
        self._legend_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        self._mpl_fig = None
        self._mpl_canvas = None

        # ── Budgets card
        budget_card = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=RADIUS,
                                   border_width=1, border_color=BORDER)
        budget_card.pack(fill="x", pady=(20, 0))
        bhdr = ctk.CTkFrame(budget_card, fg_color="transparent")
        bhdr.pack(fill="x", padx=20, pady=(16, 4))
        _lbl(bhdr, "Budgets", size=15, bold=True).pack(side="left")
        ctk.CTkButton(bhdr, text="Manage →", fg_color="transparent",
                      hover_color=HOVER, text_color=ACCENT_LITE,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      height=28, command=lambda: self.app.show_view("categories")
                      ).pack(side="right")
        self._budget_list = ctk.CTkFrame(budget_card, fg_color="transparent")
        self._budget_list.pack(fill="x", padx=20, pady=(4, 16))

    def _make_card(self, parent, col: int, title: str, color: str, icon: str):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER)
        card.grid(row=0, column=col, sticky="ew",
                  padx=(0 if col == 0 else 8, 8 if col < 2 else 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        _lbl(top_row, title, size=11, color=TEXT_DIM, bold=True).pack(side="left")
        icon_bg = ctk.CTkFrame(top_row, fg_color=tint(color), corner_radius=20, width=32, height=32)
        icon_bg.pack(side="right")
        icon_bg.pack_propagate(False)
        _lbl(icon_bg, icon, size=16, color=color).place(relx=0.5, rely=0.5, anchor="center")

        val_lbl = _lbl(inner, "—", size=26, color=color, bold=True)
        val_lbl.pack(anchor="w", pady=(8, 0))

        sub_lbl = _lbl(inner, "this month", size=11, color=TEXT_MUTED)
        sub_lbl.pack(anchor="w")

        return {"card": card, "val": val_lbl, "sub": sub_lbl, "color": color}

    def _build_tree(self, parent):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview",
                        background=CARD, foreground=TEXT,
                        fieldbackground=CARD, borderwidth=0, rowheight=40,
                        font=(FONT_FAMILY, 12))
        style.configure("Dash.Treeview.Heading",
                        background=CARD, foreground=TEXT_DIM,
                        borderwidth=0, font=(FONT_FAMILY, 11))
        style.map("Dash.Treeview",
                  background=[("selected", HOVER)],
                  foreground=[("selected", TEXT)])
        style.layout("Dash.Treeview", [("Dash.Treeview.treearea", {"sticky": "nswe"})])

        cols = ("date", "category", "description", "amount")
        self._tree = ttk.Treeview(parent, columns=cols, show="headings",
                                  style="Dash.Treeview", height=10, selectmode="browse")
        self._tree.heading("date",        text="Date")
        self._tree.heading("category",    text="Category")
        self._tree.heading("description", text="Description")
        self._tree.heading("amount",      text="Amount")
        self._tree.column("date",        width=95,  anchor="w", stretch=False)
        self._tree.column("category",    width=130, anchor="w", stretch=False)
        self._tree.column("description", width=180, anchor="w")
        self._tree.column("amount",      width=90,  anchor="e", stretch=False)

        self._tree.tag_configure("income",  foreground=INCOME)
        self._tree.tag_configure("expense", foreground=EXPENSE)

        sb = ttk.Scrollbar(parent, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)

    # ── Wealth banner ────────────────────────────────────────────────────────

    def _build_wealth_banner(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 16))
        card.grid_columnconfigure(1, weight=1)
        card.grid_columnconfigure(3, weight=1)
        card.grid_columnconfigure(5, weight=1)

        # Header row
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 0))
        _lbl(hdr, "WEALTH OVERVIEW", size=11, color=TEXT_DIM, bold=True).pack(side="left")
        self._eye_btn = ctk.CTkButton(
            hdr, text="Show", width=52, height=26,
            fg_color=CARD2, hover_color=HOVER, text_color=TEXT_DIM,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), corner_radius=RADIUS_SM,
            command=self._toggle_balance_visibility)
        self._eye_btn.pack(side="right", padx=(8, 0))
        _lbl(hdr, "Opening balance + monthly activity = closing balance",
             size=10, color=TEXT_MUTED).pack(side="right")

        # Three-column layout: [Opening] → [Net Change] → [Closing]
        cols = ctk.CTkFrame(card, fg_color="transparent")
        cols.pack(fill="x", padx=20, pady=(8, 18))
        for i in range(5):
            cols.grid_columnconfigure(i, weight=1 if i % 2 == 0 else 0)

        # Opening balance column (editable)
        open_col = ctk.CTkFrame(cols, fg_color=CARD2, corner_radius=12)
        open_col.grid(row=0, column=0, sticky="nsew", pady=0)
        open_col.grid_columnconfigure(0, weight=1)

        _lbl(open_col, "OPENING BALANCE", size=10, color=TEXT_DIM, bold=True).pack(
            padx=14, pady=(12, 4), anchor="w")

        # Display mode
        disp_row = ctk.CTkFrame(open_col, fg_color="transparent")
        disp_row.pack(fill="x", padx=14, pady=(0, 12))
        self._opening_lbl = _lbl(disp_row, "—", size=20, color=TEXT, bold=True)
        self._opening_lbl.pack(side="left")
        self._edit_open_btn = ctk.CTkButton(
            disp_row, text="✎", width=28, height=28,
            fg_color="transparent", hover_color=HOVER, text_color=TEXT_DIM,
            font=ctk.CTkFont(size=14), corner_radius=6,
            command=self._enter_edit_mode)
        self._edit_open_btn.pack(side="left", padx=(8, 0))

        # Edit mode (hidden initially)
        self._edit_frame = ctk.CTkFrame(open_col, fg_color="transparent")
        self._opening_entry = ctk.CTkEntry(
            self._edit_frame, fg_color=INPUT_BG, border_color=ACCENT,
            text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            height=36, corner_radius=RADIUS_SM, width=140)
        self._opening_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(self._edit_frame, text="✓", width=32, height=36,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                      font=ctk.CTkFont(size=14), corner_radius=RADIUS_SM,
                      command=self._save_opening_balance).pack(side="left", padx=(0, 4))
        ctk.CTkButton(self._edit_frame, text="✕", width=32, height=36,
                      fg_color=CARD2, hover_color=HOVER, text_color=TEXT_DIM,
                      font=ctk.CTkFont(size=14), corner_radius=RADIUS_SM,
                      command=self._exit_edit_mode).pack(side="left")
        # Bind Enter key
        self._opening_entry.bind("<Return>", lambda _: self._save_opening_balance())
        self._opening_entry.bind("<Escape>", lambda _: self._exit_edit_mode())

        # Arrow separator
        _lbl(cols, "→", size=22, color=TEXT_MUTED, anchor="center").grid(
            row=0, column=1, padx=12)

        # Net change column
        net_col = ctk.CTkFrame(cols, fg_color=CARD2, corner_radius=12)
        net_col.grid(row=0, column=2, sticky="nsew")
        _lbl(net_col, "NET CHANGE", size=10, color=TEXT_DIM, bold=True).pack(
            padx=14, pady=(12, 4), anchor="w")
        self._net_lbl = _lbl(net_col, "—", size=20, bold=True)
        self._net_lbl.pack(padx=14, pady=(0, 4), anchor="w")
        self._net_sub = _lbl(net_col, "income − expenses", size=10, color=TEXT_MUTED)
        self._net_sub.pack(padx=14, pady=(0, 12), anchor="w")

        # Arrow separator
        _lbl(cols, "=", size=22, color=TEXT_MUTED, anchor="center").grid(
            row=0, column=3, padx=12)

        # Closing balance column
        close_col = ctk.CTkFrame(cols, fg_color=CARD2, corner_radius=12)
        close_col.grid(row=0, column=4, sticky="nsew")
        _lbl(close_col, "CLOSING BALANCE", size=10, color=TEXT_DIM, bold=True).pack(
            padx=14, pady=(12, 4), anchor="w")
        self._closing_lbl = _lbl(close_col, "—", size=22, bold=True)
        self._closing_lbl.pack(padx=14, pady=(0, 4), anchor="w")
        self._closing_sub = _lbl(close_col, "end of month", size=10, color=TEXT_MUTED)
        self._closing_sub.pack(padx=14, pady=(0, 12), anchor="w")

        self._edit_mode = False
        self._balances_hidden = True   # balances hidden by default for privacy
        return card

    def _enter_edit_mode(self):
        self._edit_mode = True
        # Swap display → edit
        self._opening_lbl.pack_forget()
        self._edit_open_btn.pack_forget()
        # Populate entry with raw number
        current = self._current_opening
        self._opening_entry.delete(0, "end")
        self._opening_entry.insert(0, f"{current:.2f}")
        self._edit_frame.pack(padx=14, pady=(0, 12), anchor="w")
        self._opening_entry.focus_set()
        self._opening_entry.select_range(0, "end")

    def _exit_edit_mode(self):
        self._edit_mode = False
        self._edit_frame.pack_forget()
        self._opening_lbl.pack(side="left")
        self._edit_open_btn.pack(side="left", padx=(8, 0))

    def _save_opening_balance(self):
        raw = self._opening_entry.get().strip().replace(",", ".")
        try:
            amount = float(raw)
        except ValueError:
            return
        self.db.set_opening_balance(self.profile_id, self._year, self._month, amount)
        self._exit_edit_mode()
        self._load()

    def _toggle_balance_visibility(self):
        self._balances_hidden = not self._balances_hidden
        self._eye_btn.configure(text="Show" if self._balances_hidden else "Hide")
        # Re-render with current cached values
        currency = self.db.get_profile_currency(self.profile_id)
        summary  = self.db.get_total_summary(self.profile_id, self._month, self._year)
        self._update_wealth_display(currency, summary)

    def _update_wealth_display(self, currency: str, summary: dict):
        opening = self.db.get_opening_balance(self.profile_id, self._year, self._month)
        net     = summary["balance"]           # income - expenses
        closing = opening + net
        self._current_opening = opening

        sign = "+" if net >= 0 else ""
        net_color     = INCOME if net >= 0 else EXPENSE
        closing_color = INCOME if closing >= 0 else EXPENSE

        if self._balances_hidden:
            self._opening_lbl.configure(text="••••••", text_color=TEXT_DIM)
            self._net_lbl.configure(text="••••••", text_color=TEXT_DIM)
            self._closing_lbl.configure(text="••••••", text_color=TEXT_DIM)
        else:
            self._opening_lbl.configure(text=f"{currency} {opening:,.2f}", text_color=TEXT)
            self._net_lbl.configure(text=f"{sign}{currency} {net:,.2f}", text_color=net_color)
            self._closing_lbl.configure(text=f"{currency} {closing:,.2f}", text_color=closing_color)

    # ── Data loading ─────────────────────────────────────────────────────────

    def _load(self):
        self._period_lbl.configure(
            text=f"{MONTH_NAMES[self._month-1]} {self._year}")

        currency = self.db.get_profile_currency(self.profile_id)
        summary = self.db.get_total_summary(self.profile_id, self._month, self._year)

        def fmt(v): return f"{currency} {v:,.2f}"

        # Wealth banner
        self._update_wealth_display(currency, summary)

        bal_color = INCOME if summary["balance"] >= 0 else EXPENSE
        self._income_card["val"].configure(text=fmt(summary["income"]),  text_color=INCOME)
        self._expense_card["val"].configure(text=fmt(summary["expenses"]), text_color=EXPENSE)
        self._balance_card["val"].configure(text=fmt(summary["balance"]),  text_color=bal_color)

        # Recent transactions (last 15)
        txs = self.db.get_transactions(self.profile_id, self._month, self._year)[:15]
        for row in self._tree.get_children():
            self._tree.delete(row)
        for tx in txs:
            sign = "+" if tx["type"] == "income" else "-"
            amt_str = f"{sign}{currency} {tx['amount']:,.2f}"
            self._tree.insert("", "end",
                              values=(tx["date"], tx["category_name"],
                                      tx.get("description", "")[:40], amt_str),
                              tags=(tx["type"],))

        # Donut chart + budgets
        self._draw_donut(currency)
        self._load_budgets(currency)

    def _draw_donut(self, currency: str):
        cat_totals = self.db.get_category_totals(
            self.profile_id, self._month, self._year, "expense")

        # Clear old chart
        if self._mpl_canvas:
            self._mpl_canvas.get_tk_widget().destroy()
        if self._mpl_fig:
            import matplotlib.pyplot as plt
            plt.close(self._mpl_fig)

        w = self._chart_frame.winfo_width() or 260
        fig = Figure(figsize=(max(w / 100, 2.4), 2.4), dpi=100,
                     facecolor=CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(CARD)
        fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

        # Fold the tail into an "Other" slice so the ring, the center total
        # and the legend percentages all share the same denominator.
        entries = list(cat_totals[:8]) if cat_totals else []
        if len(cat_totals) > 8:
            rest = sum(r["total"] for r in cat_totals[8:])
            entries.append({"name": "Other", "color": "#94a3b8", "total": rest})

        if entries:
            sizes  = [r["total"] for r in entries]
            colors = [r["color"] for r in entries]
            total  = sum(r["total"] for r in cat_totals)
            ax.pie(sizes, labels=None, colors=colors, startangle=140,
                   wedgeprops={"width": 0.40, "linewidth": 2, "edgecolor": CARD})
            # Center hero number — total spent this month
            ax.text(0, 0.10, f"{total:,.0f}", ha="center", va="center",
                    color=TEXT, fontsize=17, fontweight="bold")
            ax.text(0, -0.22, f"{currency} spent", ha="center", va="center",
                    color=TEXT_DIM, fontsize=9)
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=TEXT_DIM, fontsize=13, transform=ax.transAxes)
            ax.axis("off")
            entries = []

        self._mpl_fig = fig
        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvas = canvas

        # ── CTk legend ────────────────────────────────────────────────────
        for w in self._legend_frame.winfo_children():
            w.destroy()

        total = sum(r["total"] for r in entries)
        for r in entries:
            row = ctk.CTkFrame(self._legend_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            swatch = ctk.CTkFrame(row, fg_color=r["color"],
                                  width=10, height=10, corner_radius=3)
            swatch.pack(side="left", padx=(0, 6))
            swatch.pack_propagate(False)

            name_lbl = ctk.CTkLabel(row, text=r["name"],
                                    text_color=TEXT, anchor="w",
                                    font=ctk.CTkFont(family=FONT_FAMILY, size=11))
            name_lbl.pack(side="left", fill="x", expand=True)

            pct = (r["total"] / total * 100) if total else 0
            ctk.CTkLabel(row, text=f"{pct:.0f}%  ({currency} {r['total']:,.2f})",
                         text_color=TEXT_DIM, anchor="e",
                         font=ctk.CTkFont(family=FONT_FAMILY, size=11)
                         ).pack(side="right")

    # ── Budgets ──────────────────────────────────────────────────────────────

    def _load_budgets(self, currency: str):
        for w in self._budget_list.winfo_children():
            w.destroy()

        budgets = self.db.get_budget_progress(self.profile_id, self._month, self._year)
        if not budgets:
            _lbl(self._budget_list,
                 "No budgets yet — edit an expense category to set a monthly limit.",
                 size=12, color=TEXT_MUTED).pack(anchor="w", pady=6)
            return

        for b in budgets:
            ratio = b["spent"] / b["budget"] if b["budget"] else 0
            over  = ratio > 1.0
            near  = ratio >= 0.85
            bar_color = EXPENSE if over else WARNING if near else b["color"]

            row = ctk.CTkFrame(self._budget_list, fg_color="transparent")
            row.pack(fill="x", pady=5)
            row.grid_columnconfigure(1, weight=1)

            # Name + dot
            left = ctk.CTkFrame(row, fg_color="transparent", width=170)
            left.grid(row=0, column=0, sticky="w")
            dot = ctk.CTkFrame(left, fg_color=b["color"], corner_radius=5,
                               width=10, height=10)
            dot.pack(side="left", padx=(0, 8))
            dot.pack_propagate(False)
            _lbl(left, b["name"], size=12).pack(side="left")

            # Progress bar
            bar = ctk.CTkProgressBar(row, height=8, corner_radius=4,
                                     fg_color=CARD2, progress_color=bar_color)
            bar.set(min(ratio, 1.0))
            bar.grid(row=0, column=1, sticky="ew", padx=14)

            # Numbers
            status = f"{currency} {b['spent']:,.0f} of {b['budget']:,.0f}"
            if over:
                status += f"  ·  over by {currency} {b['spent'] - b['budget']:,.0f}"
            _lbl(row, status, size=11,
                 color=EXPENSE if over else WARNING if near else TEXT_DIM
                 ).grid(row=0, column=2, sticky="e")

    # ── Navigation ───────────────────────────────────────────────────────────

    def _prev_month(self):
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._load()

    def _next_month(self):
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._load()

    def _add_transaction(self):
        TransactionDialog(self, self.db, self.profile_id, on_save=self._load)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def set_profile(self, profile_id: int):
        self.profile_id = profile_id
        self._load()

    def refresh(self):
        self._load()
