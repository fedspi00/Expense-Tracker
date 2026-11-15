"""Reusable custom widgets — themed date field with a calendar popup."""
import calendar
import tkinter as tk
from datetime import date

import customtkinter as ctk

from theme import *

_WEEKDAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


class DateField(ctk.CTkFrame):
    """An entry-styled, read-only field that opens a calendar popup on click.

    Stores the date internally; `get()` returns the ISO string (YYYY-MM-DD)
    so it drops in where a text entry used to be.
    """

    def __init__(self, parent, initial: str | None = None, width: int = 320):
        super().__init__(parent, fg_color=INPUT_BG, corner_radius=RADIUS_SM,
                         border_width=1, border_color=BORDER,
                         width=width, height=40, cursor="hand2")
        # If an existing transaction carries an unparseable date, keep it as-is
        # (shown verbatim, saved unchanged) until the user explicitly picks one.
        self._raw: str | None = None
        try:
            self._date = date.fromisoformat(initial) if initial else date.today()
        except (ValueError, TypeError):
            self._date = date.today()
            self._raw = str(initial)
        self._popup = None

        self.pack_propagate(False)
        self._lbl = ctk.CTkLabel(self, text="", text_color=TEXT, anchor="w",
                                 font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self._lbl.pack(side="left", fill="x", expand=True, padx=(14, 4))
        self._chev = ctk.CTkLabel(self, text="▾", text_color=TEXT_DIM,
                                  font=ctk.CTkFont(size=12), cursor="hand2")
        self._chev.pack(side="right", padx=(0, 12))
        for w in (self, self._lbl, self._chev):
            w.bind("<Button-1>", self._toggle)
        self._render()

    # ── Public API ──────────────────────────────────────────────────────────

    def get(self) -> str:
        return self._raw if self._raw is not None else self._date.isoformat()

    def set(self, iso: str):
        try:
            self._date = date.fromisoformat(iso)
            self._raw = None
            self._render()
        except (ValueError, TypeError):
            pass

    # ── Internals ───────────────────────────────────────────────────────────

    def _render(self):
        self._lbl.configure(text=self._raw if self._raw is not None
                            else self._date.strftime("%a, %d %b %Y"))

    def _toggle(self, _=None):
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.close()
        else:
            self._popup = _CalendarPopup(self, self._date, self._on_pick)

    def _on_pick(self, d: date):
        self._date = d
        self._raw = None
        self._render()


class _CalendarPopup(tk.Toplevel):
    """Borderless month-calendar dropdown anchored under a DateField."""

    def __init__(self, anchor: DateField, selected: date, on_pick):
        super().__init__(anchor)
        self._anchor = anchor
        self._on_pick = on_pick
        self._selected = selected
        self._shown = date(selected.year, selected.month, 1)
        # Remember whichever window (e.g. the dialog) holds the grab, and which
        # field had the caret, so both can be handed back when the popup closes.
        try:
            self._prev_grab  = anchor.grab_current()
            self._prev_focus = anchor.focus_get()
        except tk.TclError:
            self._prev_grab = self._prev_focus = None

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=BORDER)  # 1px frame line around the panel

        panel = ctk.CTkFrame(self, fg_color=CARD2, corner_radius=0)
        panel.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_header(panel)
        self._grid_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._grid_frame.pack(padx=10, pady=(2, 4))
        self._build_grid()

        foot = ctk.CTkFrame(panel, fg_color="transparent")
        foot.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(foot, text="Today", height=28, corner_radius=RADIUS_SM,
                      fg_color="transparent", hover_color=HOVER,
                      text_color=ACCENT_LITE,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      command=lambda: self._pick(date.today())).pack(fill="x")

        self._place_near_anchor()
        self.bind("<Button-1>", self._on_click_anywhere)
        self.bind("<Escape>", lambda _: self.close())
        # Grab synchronously: any delay here leaves a window in which a click
        # lands on another field, and the popup then steals input from it.
        self.update_idletasks()
        self._take_grab()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_header(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        hdr.grid_columnconfigure(1, weight=1)

        def nav_btn(text, cmd, col):
            ctk.CTkButton(hdr, text=text, width=30, height=30,
                          fg_color="transparent", hover_color=HOVER,
                          text_color=TEXT_DIM, corner_radius=RADIUS_SM,
                          font=ctk.CTkFont(size=15, weight="bold"),
                          command=cmd).grid(row=0, column=col)

        nav_btn("‹", lambda: self._shift_month(-1), 0)
        self._title_lbl = ctk.CTkLabel(
            hdr, text="", text_color=TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self._title_lbl.grid(row=0, column=1)
        nav_btn("›", lambda: self._shift_month(1), 2)

    def _build_grid(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()
        self._title_lbl.configure(
            text=f"{MONTH_NAMES[self._shown.month - 1]} {self._shown.year}")

        for col, wd in enumerate(_WEEKDAYS):
            ctk.CTkLabel(self._grid_frame, text=wd, width=34, height=22,
                         text_color=TEXT_MUTED,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold")
                         ).grid(row=0, column=col, padx=1)

        today = date.today()
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._shown.year, self._shown.month)
        for r, week in enumerate(weeks, start=1):
            for c, d in enumerate(week):
                in_month = d.month == self._shown.month
                is_sel   = d == self._selected
                is_today = d == today
                btn = ctk.CTkButton(
                    self._grid_frame, text=str(d.day), width=34, height=30,
                    corner_radius=RADIUS_SM,
                    fg_color=ACCENT if is_sel else "transparent",
                    hover_color=ACCENT_H if is_sel else HOVER,
                    border_width=0 if (is_sel or not is_today) else 1,
                    border_color=ACCENT,
                    text_color=("#ffffff" if is_sel
                                else ACCENT_LITE if is_today
                                else TEXT if in_month else TEXT_MUTED),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12,
                                     weight="bold" if (is_sel or is_today) else "normal"),
                    command=lambda dd=d: self._pick(dd))
                btn.grid(row=r, column=c, padx=1, pady=1)

    def _place_near_anchor(self):
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = self._anchor.winfo_rootx()
        y = self._anchor.winfo_rooty() + self._anchor.winfo_height() + 6
        screen_h = self.winfo_screenheight()
        screen_w = self.winfo_screenwidth()
        if y + h > screen_h - 8:                       # open upward instead
            y = self._anchor.winfo_rooty() - h - 6
        x = max(8, min(x, screen_w - w - 8))
        self.geometry(f"+{x}+{y}")

    # ── Behaviour ───────────────────────────────────────────────────────────

    def _take_grab(self, tries: int = 5):
        """Grab events so clicks outside the popup reach us (and close it).

        If the grab can't be taken we close instead of lingering: an open but
        ungrabbed popup would later snatch input away from whatever the user
        moved on to.
        """
        try:
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            if tries > 0:
                self.after(20, lambda: self._take_grab(tries - 1))
            else:
                self.close()

    def _on_click_anywhere(self, e):
        x0, y0 = self.winfo_rootx(), self.winfo_rooty()
        if not (x0 <= e.x_root <= x0 + self.winfo_width()
                and y0 <= e.y_root <= y0 + self.winfo_height()):
            self.close()

    def _shift_month(self, delta: int):
        m = self._shown.month + delta
        y = self._shown.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        self._shown = date(y, m, 1)
        self._build_grid()

    def _pick(self, d: date):
        self._on_pick(d)
        self.close()

    def close(self):
        try:
            self.grab_release()
            if self._prev_grab is not None and self._prev_grab.winfo_exists():
                self._prev_grab.grab_set()
            # Put the caret back where it was so typing resumes normally
            if self._prev_focus is not None and self._prev_focus.winfo_exists():
                self._prev_focus.focus_set()
        except tk.TclError:
            pass
        if self._anchor.winfo_exists():
            self._anchor._popup = None
        self.destroy()
