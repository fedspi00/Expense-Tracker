"""Analytics view – pie charts and monthly bar chart."""
import customtkinter as ctk
from datetime import date
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from theme import *


def _lbl(parent, text, size=12, color=TEXT, bold=False, anchor="w"):
    return ctk.CTkLabel(parent, text=text, text_color=color, anchor=anchor,
                        font=ctk.CTkFont(family=FONT_FAMILY, size=size,
                                         weight="bold" if bold else "normal"))


def _apply_dark(fig, *axes):
    fig.patch.set_facecolor(CARD)
    for ax in axes:
        ax.set_facecolor(CARD)
        ax.tick_params(colors=TEXT_DIM, labelsize=10)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)


class AnalyticsView(ctk.CTkFrame):
    def __init__(self, parent, db, profile_id: int, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.db = db
        self.profile_id = profile_id
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        today = date.today()
        self._year_var  = ctk.StringVar(value=str(today.year))
        self._month_var = ctk.StringVar(value="All months")

        self._figs: list = []
        self._canvases: list = []

        self._build()
        self._load()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        top.grid_columnconfigure(1, weight=1)
        _lbl(top, "Analytics", size=22, bold=True).grid(row=0, column=0, sticky="w", padx=(0, 20))

        filter_frame = ctk.CTkFrame(top, fg_color=CARD, corner_radius=10)
        filter_frame.grid(row=0, column=1, sticky="w")

        _lbl(filter_frame, "Year", size=11, color=TEXT_DIM).pack(side="left", padx=(12, 4), pady=8)
        years = [str(y) for y in range(date.today().year, 2018, -1)]
        ctk.CTkOptionMenu(filter_frame, variable=self._year_var, values=years,
                          fg_color=CARD, button_color=CARD, button_hover_color=HOVER,
                          text_color=TEXT, dropdown_fg_color=CARD2,
                          dropdown_text_color=TEXT, dropdown_hover_color=HOVER,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          height=28, width=90, corner_radius=6,
                          command=lambda _: self._load()).pack(side="left", pady=4, padx=(0, 8))

        _lbl(filter_frame, "Month", size=11, color=TEXT_DIM).pack(side="left", padx=(4, 4), pady=8)
        months = ["All months"] + MONTH_NAMES
        ctk.CTkOptionMenu(filter_frame, variable=self._month_var, values=months,
                          fg_color=CARD, button_color=CARD, button_hover_color=HOVER,
                          text_color=TEXT, dropdown_fg_color=CARD2,
                          dropdown_text_color=TEXT, dropdown_hover_color=HOVER,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          height=28, width=130, corner_radius=6,
                          command=lambda _: self._load()).pack(side="left", pady=4, padx=(0, 12))

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=HOVER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)
        self._scroll = scroll

    def _clear_charts(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        for fig in self._figs:
            plt.close(fig)
        self._figs.clear()
        self._canvases.clear()

    # ── Data & Charts ────────────────────────────────────────────────────────

    def _load(self):
        self._clear_charts()
        self.update_idletasks()

        year = int(self._year_var.get())
        month_str = self._month_var.get()
        month = MONTH_NAMES.index(month_str) + 1 if month_str in MONTH_NAMES else None

        currency = self.db.get_profile_currency(self.profile_id)
        summary  = self.db.get_total_summary(self.profile_id, month, year)

        # ── Summary row
        self._draw_summary_row(summary, currency)

        # ── Pie charts row
        pie_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        pie_row.pack(fill="x", pady=(0, 16))
        pie_row.grid_columnconfigure(0, weight=1)
        pie_row.grid_columnconfigure(1, weight=1)

        income_data  = self.db.get_category_totals(self.profile_id, month, year, "income")
        expense_data = self.db.get_category_totals(self.profile_id, month, year, "expense")

        left_card  = self._make_chart_card(pie_row, "Income by Category",  0)
        right_card = self._make_chart_card(pie_row, "Expenses by Category", 1)
        self._draw_pie(left_card,  income_data,  currency)
        self._draw_pie(right_card, expense_data, currency)

        # ── Monthly trend bar chart + wealth line
        if month is None:
            bar_card = self._make_chart_card(self._scroll, f"Monthly Overview — {year}", None)
            monthly  = self.db.get_monthly_summary(self.profile_id, year)
            self._draw_bar(bar_card, monthly, currency)

            # ── Wealth over time
            wealth_card = self._make_chart_card(
                self._scroll, f"Wealth Over Time — {year}", None)
            wealth_data = self.db.get_wealth_over_time(self.profile_id, year)
            self._draw_wealth(wealth_card, wealth_data, currency)

    def _draw_summary_row(self, summary: dict, currency: str):
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        for i in range(3):
            row.grid_columnconfigure(i, weight=1)

        data = [
            ("TOTAL INCOME",  summary["income"],   INCOME,  "↑"),
            ("TOTAL EXPENSES",summary["expenses"],  EXPENSE, "↓"),
            ("NET BALANCE",   summary["balance"],
             INCOME if summary["balance"] >= 0 else EXPENSE, "="),
        ]
        for col, (title, value, color, icon) in enumerate(data):
            card = ctk.CTkFrame(row, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
            card.grid(row=0, column=col, sticky="ew",
                      padx=(0 if col == 0 else 8, 0))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=20, pady=16)
            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill="x")
            _lbl(top, title, size=10, color=TEXT_DIM, bold=True).pack(side="left")
            ib = ctk.CTkFrame(top, fg_color=tint(color), corner_radius=18,
                              width=30, height=30)
            ib.pack(side="right")
            ib.pack_propagate(False)
            _lbl(ib, icon, size=14, color=color).place(relx=0.5, rely=0.5, anchor="center")
            sign = "+" if value >= 0 else ""
            _lbl(inner, f"{sign}{currency} {value:,.2f}", size=24, color=color, bold=True).pack(
                anchor="w", pady=(8, 0))

    def _make_chart_card(self, parent, title: str, col):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        if col is not None:
            card.grid(row=0, column=col, sticky="nsew",
                      padx=(0 if col == 0 else 8, 0))
        else:
            card.pack(fill="x", pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        _lbl(card, title, size=15, bold=True).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 14))
        return content

    def _draw_pie(self, parent, data: list, currency: str):
        fig = Figure(figsize=(4.5, 3.4), dpi=100, facecolor=CARD)
        ax = fig.add_subplot(111)
        _apply_dark(fig, ax)
        fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.30)

        if data:
            # Fold the tail into "Other" so wedges + legend match the center total
            top = list(data[:7])
            rest = sum(r["total"] for r in data[7:])
            if rest > 0:
                top.append({"name": "Other", "color": "#94a3b8", "total": rest})
            labels = [r["name"][:14] for r in top]
            sizes  = [r["total"] for r in top]
            colors = [r["color"] for r in top]
            total  = sum(r["total"] for r in data)
            wedges, _ = ax.pie(
                sizes, labels=None, colors=colors, startangle=140,
                wedgeprops={"width": 0.40, "linewidth": 2, "edgecolor": CARD})
            # Center hero number
            ax.text(0, 0.10, f"{total:,.0f}", ha="center", va="center",
                    color=TEXT, fontsize=16, fontweight="bold")
            ax.text(0, -0.22, currency, ha="center", va="center",
                    color=TEXT_DIM, fontsize=9)
            ax.legend(wedges, [f"{l}  {currency} {s:,.0f}" for l, s in zip(labels, sizes)],
                      loc="upper center", bbox_to_anchor=(0.5, -0.02),
                      ncol=2, fontsize=9, frameon=False, labelcolor=TEXT_DIM)
        else:
            ax.text(0.5, 0.5, "No data for this period",
                    ha="center", va="center", color=TEXT_DIM,
                    fontsize=12, transform=ax.transAxes)
            ax.axis("off")

        self._embed(fig, parent)

    def _draw_bar(self, parent, monthly: list, currency: str):
        # Build 12-month arrays
        inc = [0.0] * 12
        exp = [0.0] * 12
        for row in monthly:
            m = int(row["month"]) - 1
            if row["type"] == "income":
                inc[m] = row["total"]
            else:
                exp[m] = row["total"]

        fig = Figure(figsize=(9, 3.6), dpi=100, facecolor=CARD)
        ax = fig.add_subplot(111)
        _apply_dark(fig, ax)
        fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.12)

        x = np.arange(12)
        w = 0.35
        ax.bar(x - w/2, inc, w, color=INCOME,  alpha=0.85, label="Income",   zorder=3)
        ax.bar(x + w/2, exp, w, color=EXPENSE, alpha=0.85, label="Expenses", zorder=3)

        short_months = [m[:3] for m in MONTH_NAMES]
        ax.set_xticks(x)
        ax.set_xticklabels(short_months, color=TEXT_DIM, fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"{currency} {v:,.0f}"))
        ax.tick_params(axis="y", labelcolor=TEXT_DIM, labelsize=9)
        ax.grid(axis="y", color=BORDER, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Balance line — same unit as the bars, so it shares the same axis
        balance = [i - e for i, e in zip(inc, exp)]
        ax.plot(x, balance, color=ACCENT_LITE, linewidth=2,
                marker="o", markersize=5, zorder=4, label="Balance")
        ax.axhline(0, color=BORDER, linewidth=1, zorder=0)
        ax.legend(frameon=False, labelcolor=TEXT_DIM, fontsize=10,
                  loc="upper left", ncol=3)

        self._embed(fig, parent)

    def _draw_wealth(self, parent, wealth_data: list, currency: str):
        """Area + line chart of opening / closing balance per month."""
        fig = Figure(figsize=(9, 3.4), dpi=100, facecolor=CARD)
        ax  = fig.add_subplot(111)
        _apply_dark(fig, ax)
        fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.12)

        months   = [d["month"] for d in wealth_data]
        opening  = [d["opening_balance"]  for d in wealth_data]
        closing  = [d["closing_balance"]  for d in wealth_data]

        has_data = any(d["opening_balance"] != 0 or d["income"] or d["expenses"]
                       for d in wealth_data)

        if has_data:
            x = np.arange(1, 13)
            # Shaded area between opening and closing
            ax.fill_between(x, opening, closing,
                            where=[c >= o for c, o in zip(closing, opening)],
                            color=INCOME, alpha=0.18, interpolate=True)
            ax.fill_between(x, opening, closing,
                            where=[c < o for c, o in zip(closing, opening)],
                            color=EXPENSE, alpha=0.18, interpolate=True)
            ax.plot(x, opening, color=TEXT_DIM, linewidth=1.5,
                    linestyle="--", marker="o", markersize=4, label="Opening")
            ax.plot(x, closing, color=ACCENT_LITE, linewidth=2.5,
                    marker="o", markersize=6, label="Closing", zorder=4)
            # Zero line
            ax.axhline(0, color=BORDER, linewidth=1, zorder=0)

            short_months = [m[:3] for m in MONTH_NAMES]
            ax.set_xticks(x)
            ax.set_xticklabels(short_months, color=TEXT_DIM, fontsize=10)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(
                lambda v, _: f"{currency} {v:,.0f}"))
            ax.tick_params(axis="y", labelcolor=TEXT_DIM, labelsize=9)
            ax.grid(axis="y", color=BORDER, linewidth=0.8, zorder=0)
            ax.set_axisbelow(True)
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.legend(frameon=False, labelcolor=TEXT_DIM, fontsize=10,
                      loc="upper left")
        else:
            ax.text(0.5, 0.5,
                    "Set an opening balance on the Dashboard to see wealth over time.",
                    ha="center", va="center", color=TEXT_DIM, fontsize=11,
                    transform=ax.transAxes, wrap=True)
            ax.axis("off")

        self._embed(fig, parent)

    def _embed(self, fig, parent):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._figs.append(fig)
        self._canvases.append(canvas)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def set_profile(self, profile_id: int):
        self.profile_id = profile_id
        self._load()

    def refresh(self):
        self._load()
