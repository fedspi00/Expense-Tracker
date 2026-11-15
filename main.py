"""
TrackIt! – main entry point.
Run with:  python3 main.py
Or double-click:  run.command  (after running install.sh once)
"""
import sys
import os
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

import customtkinter as ctk
from PIL import ImageTk

import auth
from theme import *
from database import Database
from icon import create_app_icon
from dashboard_view    import DashboardView
from transactions_view import TransactionsView
from categories_view   import CategoriesView
from analytics_view    import AnalyticsView
from settings_view     import SettingsView

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_VERSION = "2.0.0"

# ─────────────────────────────────────────────────────────────────────────────

NAV_ITEMS = [
    ("dashboard",    "▦",  "Dashboard"),
    ("transactions", "⇄",  "Transactions"),
    ("categories",   "❖",  "Categories"),
    ("analytics",    "◔",  "Analytics"),
    ("settings",     "⚙",  "Settings"),
]

VIEW_MAP = {
    "dashboard":    DashboardView,
    "transactions": TransactionsView,
    "categories":   CategoriesView,
    "analytics":    AnalyticsView,
    "settings":     SettingsView,
}


def _get_db_path() -> str:
    config_file = Path.home() / ".expense_tracker" / "config.txt"
    if config_file.exists():
        p = config_file.read_text().strip()
        if p and os.path.exists(os.path.dirname(p)):
            return p
    return str(Path.home() / "ExpenseTracker" / "data.db")


# ─────────────────────────────────────────────────────────────────────────────
# Lock screen — Touch ID gate shown over the whole window
# ─────────────────────────────────────────────────────────────────────────────

class LockScreen(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=BG, corner_radius=0)
        self.app = app
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()
        self._result = None      # set from the auth background thread
        self._waiting = False
        # Steal keyboard focus and events from whatever lies underneath —
        # a Tk local grab restricts pointer events, focus stops keystrokes.
        self.after(10, self._secure)

        box = ctk.CTkFrame(self, fg_color="transparent")
        box.place(relx=0.5, rely=0.44, anchor="center")

        try:
            img = create_app_icon(256)
            self._logo = ctk.CTkImage(light_image=img, dark_image=img, size=(88, 88))
            ctk.CTkLabel(box, image=self._logo, text="").pack(pady=(0, 20))
        except Exception:
            pass

        ctk.CTkLabel(box, text="TrackIt! is locked",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=21, weight="bold"),
                     text_color=TEXT).pack()
        self._status = ctk.CTkLabel(box, text="Use Touch ID to unlock",
                                    font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                                    text_color=TEXT_DIM)
        self._status.pack(pady=(6, 22))

        self._unlock_btn = ctk.CTkButton(
            box, text="Unlock with Touch ID", command=self._attempt,
            fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            width=230, height=44, corner_radius=RADIUS_SM)
        self._unlock_btn.pack()

        self._quit_btn = ctk.CTkButton(
            box, text="Quit", command=self.app._on_close,
            fg_color="transparent", hover_color=HOVER,
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=230, height=32,
            corner_radius=RADIUS_SM)
        self._quit_btn.pack(pady=(10, 0))

        # Block Tab traversal from walking focus back to occluded widgets
        for w in (self, self._unlock_btn, self._quit_btn):
            w.bind("<Tab>", lambda e: "break")
            w.bind("<Shift-Tab>", lambda e: "break")

        self.after(500, self._attempt)

    def _secure(self, tries: int = 10):
        try:
            self.grab_set()
            self.focus_set()
        except tk.TclError:
            if tries > 0:
                self.after(50, lambda: self._secure(tries - 1))

    def _attempt(self):
        if self._waiting:
            return
        self._waiting = True
        self._result = None
        self._status.configure(text="Waiting for Touch ID…", text_color=TEXT_DIM)
        self._unlock_btn.configure(state="disabled")
        # macOS renders this as "<app name> is trying to <reason>."
        auth.authenticate("unlock your budget", self._on_result)
        self._poll()

    def _on_result(self, success: bool, msg: str):
        # Called from a background thread — just record; the Tk loop polls.
        self._result = (success, msg)

    def _poll(self):
        if not self.winfo_exists():
            return
        if self._result is None:
            self.after(100, self._poll)
            return
        success, msg = self._result
        self._waiting = False
        if success:
            self.app._on_unlocked()
        else:
            self._status.configure(text=msg or "Authentication failed — try again",
                                   text_color=EXPENSE)
            self._unlock_btn.configure(state="normal")


# ─────────────────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TrackIt!")
        self.geometry("1280x800")
        self.minsize(960, 640)
        self.configure(fg_color=BG)

        # ── App icon (window + dock) ──────────────────────────────────────
        try:
            _icon_img = create_app_icon(256)
            self._app_icon = ImageTk.PhotoImage(_icon_img)
            self.iconphoto(True, self._app_icon)
            # macOS dock icon via pyobjc (optional, silently skipped if absent)
            if sys.platform == "darwin":
                try:
                    import io, AppKit, Foundation
                    buf = io.BytesIO()
                    _icon_img.save(buf, format="PNG")
                    ns_data  = Foundation.NSData.dataWithBytes_length_(
                        buf.getvalue(), len(buf.getvalue()))
                    ns_image = AppKit.NSImage.alloc().initWithData_(ns_data)
                    AppKit.NSApplication.sharedApplication().setApplicationIconImage_(ns_image)
                except Exception:
                    pass  # pyobjc not installed – dock icon stays as default Python icon
        except Exception:
            pass  # PIL issue – non-critical

        # Try to set a nice Mac icon / dock name
        try:
            self.createcommand("::tk::mac::Quit", self._on_close)
        except Exception:
            pass

        self.db = Database(_get_db_path())
        self.current_profile_id = self.db.get_active_profile_id()
        self.views: dict = {}
        self._current_view_id: str | None = None
        self._locked = False
        self._lock_screen: LockScreen | None = None

        self._build_layout()
        self._build_sidebar()
        self._build_content()

        # Keyboard shortcuts
        self.bind_all("<Command-n>", lambda _: self._quick_add())
        self.bind_all("<Command-r>", lambda _: self._refresh_current())
        self.bind_all("<Command-l>", lambda _: self.lock())

        self.show_view("dashboard")
        self._update_profile_menu()

        if self._should_lock():
            self.lock()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0, minsize=232)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, width=232, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(5 + len(NAV_ITEMS), weight=1)
        self._sidebar = sidebar

        # Logo — the actual app icon, rendered small
        logo = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo.grid(row=0, column=0, padx=20, pady=(26, 20), sticky="w")
        try:
            img = create_app_icon(128)
            self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
            ctk.CTkLabel(logo, image=self._logo_img, text="").pack(side="left", padx=(0, 10))
        except Exception:
            ctk.CTkLabel(logo, text="◈",
                         font=ctk.CTkFont(family=FONT_FAMILY, size=28),
                         text_color=ACCENT).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(logo, text="TrackIt!",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
                     text_color=TEXT).pack(side="left")

        # Separator
        ctk.CTkFrame(sidebar, height=1, fg_color=BORDER).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        # Profile selector
        prof_frame = ctk.CTkFrame(sidebar, fg_color=CARD, corner_radius=RADIUS_SM)
        prof_frame.grid(row=2, column=0, padx=14, pady=(0, 20), sticky="ew")
        ctk.CTkLabel(prof_frame, text="PROFILE",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                     text_color=TEXT_MUTED).pack(padx=12, pady=(10, 3), anchor="w")

        profiles = self.db.get_profiles()
        names = [p["name"] for p in profiles]
        active = next((p["name"] for p in profiles
                       if p["id"] == self.current_profile_id), names[0] if names else "—")
        self._profile_var = ctk.StringVar(value=active)
        self._profile_menu = ctk.CTkOptionMenu(
            prof_frame, variable=self._profile_var,
            values=names or ["—"],
            fg_color=CARD, button_color=CARD, button_hover_color=HOVER,
            text_color=TEXT, dropdown_fg_color=SIDEBAR_BG,
            dropdown_text_color=TEXT, dropdown_hover_color=HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            corner_radius=8, height=36,
            command=self._on_profile_change)
        self._profile_menu.pack(padx=8, pady=(0, 8), fill="x")

        # Nav buttons
        self._nav_btns: dict = {}
        for i, (vid, icon, label) in enumerate(NAV_ITEMS):
            btn = self._make_nav_btn(sidebar, vid, icon, label)
            btn.grid(row=3 + i, column=0, padx=10, pady=2, sticky="ew")
            self._nav_btns[vid] = btn

        # Version
        ctk.CTkLabel(sidebar, text=f"v{APP_VERSION}",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                     text_color=TEXT_MUTED).grid(
            row=3 + len(NAV_ITEMS) + 1, column=0, padx=20, pady=14, sticky="sw")

    def _make_nav_btn(self, parent, view_id: str, icon: str, label: str):
        frame = ctk.CTkFrame(parent, fg_color="transparent",
                             cursor="hand2", corner_radius=RADIUS_SM)
        frame.grid_columnconfigure(2, weight=1)

        indicator = ctk.CTkFrame(frame, width=3, height=28,
                                 fg_color="transparent", corner_radius=2)
        indicator.grid(row=0, column=0, sticky="ns", padx=(4, 0), pady=5)

        icon_lbl = ctk.CTkLabel(frame, text=icon,
                                font=ctk.CTkFont(size=16), text_color=TEXT_DIM, width=26)
        icon_lbl.grid(row=0, column=1, padx=(8, 6), pady=9)

        text_lbl = ctk.CTkLabel(frame, text=label, anchor="w",
                                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                                text_color=TEXT_DIM)
        text_lbl.grid(row=0, column=2, sticky="w", pady=9, padx=(0, 12))

        def click(_=None): self.show_view(view_id)
        def enter(_=None):
            if self._current_view_id != view_id:
                frame.configure(fg_color=HOVER)
        def leave(_=None):
            if self._current_view_id != view_id:
                frame.configure(fg_color="transparent")

        for w in (frame, indicator, icon_lbl, text_lbl):
            w.bind("<Button-1>", click)
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

        # Store refs for activation
        frame._indicator = indicator
        frame._icon_lbl  = icon_lbl
        frame._text_lbl  = text_lbl
        return frame

    def _build_content(self):
        self._content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

    # ── Navigation ───────────────────────────────────────────────────────────

    def show_view(self, view_id: str):
        # Update sidebar state — active item gets a tinted pill + accent bar
        for vid, btn in self._nav_btns.items():
            active = vid == view_id
            btn.configure(fg_color=ACCENT_BG if active else "transparent")
            btn._indicator.configure(fg_color=ACCENT if active else "transparent")
            btn._icon_lbl.configure(text_color=ACCENT_LITE if active else TEXT_DIM)
            btn._text_lbl.configure(text_color=TEXT if active else TEXT_DIM)

        # Hide all views
        for v in self.views.values():
            v.grid_remove()

        # Create or reveal view
        if view_id not in self.views:
            cls = VIEW_MAP[view_id]
            view = cls(self._content, self.db, self.current_profile_id, self)
            view.grid(row=0, column=0, sticky="nsew")
            self.views[view_id] = view
        else:
            self.views[view_id].grid()
            self.views[view_id].refresh()

        self._current_view_id = view_id

    # ── Profile ───────────────────────────────────────────────────────────────

    def _on_profile_change(self, name: str):
        profiles = self.db.get_profiles()
        p = next((x for x in profiles if x["name"] == name), None)
        if p:
            self.current_profile_id = p["id"]
            self.db.set_active_profile(p["id"])
            for view in self.views.values():
                view.set_profile(p["id"])

    def refresh_profiles(self):
        profiles = self.db.get_profiles()
        names = [p["name"] for p in profiles]
        self._profile_menu.configure(values=names or ["—"])
        active = next((p["name"] for p in profiles
                       if p["id"] == self.current_profile_id), names[0] if names else "—")
        self._profile_var.set(active)

    def _update_profile_menu(self):
        self.refresh_profiles()

    # ── Touch ID lock ─────────────────────────────────────────────────────────

    def _should_lock(self) -> bool:
        if os.environ.get("TRACKIT_SKIP_LOCK") == "1":
            return False
        if self.db.get_setting("touch_id_lock", "1") != "1":
            return False
        return auth.auth_available()

    def lock(self):
        """Cover the window with the Touch ID lock screen (also Cmd+L)."""
        if self._locked:
            return
        if not auth.auth_available():
            messagebox.showwarning(
                "TrackIt!",
                "Can't lock: Touch ID / password authentication is unavailable "
                "on this Mac, so the app could never be unlocked.", parent=self)
            return
        self._locked = True
        # Close any open dialogs/popups — separate Toplevels would float above
        # the lock screen and their grab would block its buttons.
        stack = list(self.winfo_children())
        while stack:
            w = stack.pop()
            if isinstance(w, tk.Toplevel):
                w.destroy()               # also releases its grab
            else:
                stack.extend(w.winfo_children())
        self._lock_screen = LockScreen(self)

    def _on_unlocked(self):
        self._locked = False
        if self._lock_screen is not None:
            try:
                self._lock_screen.grab_release()
            except tk.TclError:
                pass
            self._lock_screen.destroy()
            self._lock_screen = None

    # ── Shortcuts ─────────────────────────────────────────────────────────────

    def _quick_add(self):
        """Cmd+N: open add transaction from any view."""
        if self._locked or self.grab_current() is not None:
            return   # locked, or a modal dialog / popup is already open
        from dialogs import TransactionDialog
        def on_save():
            if self._current_view_id in self.views:
                self.views[self._current_view_id].refresh()
        TransactionDialog(self, self.db, self.current_profile_id, on_save=on_save)

    def _refresh_current(self):
        if self._locked:
            return
        if self._current_view_id and self._current_view_id in self.views:
            self.views[self._current_view_id].refresh()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_close(self):
        self.db.close()
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = App()
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
