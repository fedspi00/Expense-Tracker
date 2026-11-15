"""Settings view – profile management, security, database location, currency."""
import os
import shutil
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path

import auth
from theme import *
from dialogs import ProfileDialog


def _lbl(parent, text, size=12, color=TEXT, bold=False, anchor="w"):
    return ctk.CTkLabel(parent, text=text, text_color=color, anchor=anchor,
                        font=ctk.CTkFont(family=FONT_FAMILY, size=size,
                                         weight="bold" if bold else "normal"))

def _section_title(parent, text: str):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=0, pady=(0, 12))
    ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(fill="x", pady=(0, 10))
    _lbl(frame, text, size=12, color=TEXT_DIM, bold=True).pack(anchor="w")


class SettingsView(ctk.CTkFrame):
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
        _lbl(top, "Settings", size=22, bold=True).pack(side="left")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=HOVER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)
        self._scroll = scroll

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._build_profiles_section()
        self._build_security_section()
        self._build_database_section()
        self._build_about_section()

    # ── Profiles ─────────────────────────────────────────────────────────────

    def _build_profiles_section(self):
        card = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        _lbl(hdr, "Profiles", size=16, bold=True).pack(side="left")
        ctk.CTkButton(hdr, text="+ New Profile", fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=TEXT,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      height=32, corner_radius=8, width=120,
                      command=self._add_profile).pack(side="right")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")

        profiles = self.db.get_profiles()
        active_id = self.db.get_active_profile_id()

        if not profiles:
            _lbl(card, "No profiles found.", size=12, color=TEXT_DIM).pack(padx=20, pady=12)
            return

        for p in profiles:
            self._make_profile_row(card, p, active_id)

    def _make_profile_row(self, parent, profile: dict, active_id: int):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=8)
        row.grid_columnconfigure(1, weight=1)

        # Active indicator
        dot_color = ACCENT if profile["id"] == active_id else CARD2
        dot = ctk.CTkFrame(row, fg_color=dot_color, corner_radius=6,
                           width=12, height=12)
        dot.grid(row=0, column=0, padx=(0, 12))
        dot.grid_propagate(False)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w")
        _lbl(info, profile["name"], size=14, bold=(profile["id"] == active_id)).pack(anchor="w")
        _lbl(info, f"Currency: {profile['currency']}", size=11, color=TEXT_DIM).pack(anchor="w")

        # Active badge
        if profile["id"] == active_id:
            badge = ctk.CTkFrame(row, fg_color=tint(ACCENT), corner_radius=10)
            badge.grid(row=0, column=2, padx=8)
            _lbl(badge, "Active", size=10, color=ACCENT_LITE, bold=True).pack(padx=10, pady=4)

        # Actions
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=3)

        if profile["id"] != active_id:
            ctk.CTkButton(btn_frame, text="Switch", width=70, height=28,
                          fg_color=CARD2, hover_color=HOVER, text_color=TEXT,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                          corner_radius=6,
                          command=lambda pid=profile["id"]: self._switch_profile(pid)
                          ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(btn_frame, text="Edit", width=60, height=28,
                      fg_color=CARD2, hover_color=HOVER, text_color=TEXT,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                      corner_radius=6,
                      command=lambda p=profile: self._edit_profile(p)).pack(side="left", padx=(0, 4))

        profiles = self.db.get_profiles()
        if len(profiles) > 1 and profile["id"] != active_id:
            ctk.CTkButton(btn_frame, text="Del", width=52, height=28,
                          fg_color="transparent", hover_color=EXPENSE_BG,
                          text_color=TEXT_DIM,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                          corner_radius=6,
                          command=lambda p=profile: self._delete_profile(p)).pack(side="left")

        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(fill="x", padx=0)

    def _add_profile(self):
        ProfileDialog(self, self.db, on_save=self._on_profile_saved)

    def _edit_profile(self, profile: dict):
        ProfileDialog(self, self.db, on_save=self._on_profile_saved, profile=profile)

    def _delete_profile(self, profile: dict):
        ans = messagebox.askyesno(
            "Delete Profile",
            f"Delete profile '{profile['name']}' and ALL its data?\nThis cannot be undone.",
            parent=self)
        if ans:
            self.db.delete_profile(profile["id"])
            self._on_profile_saved()

    def _switch_profile(self, pid: int):
        self.db.set_active_profile(pid)
        self.profile_id = pid
        self.app.current_profile_id = pid
        for view in self.app.views.values():
            view.set_profile(pid)
        self.app.refresh_profiles()
        self._load()

    def _on_profile_saved(self):
        self.app.refresh_profiles()
        self._load()

    # ── Security ─────────────────────────────────────────────────────────────

    def _build_security_section(self):
        card = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 16))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        _lbl(hdr, "Security", size=16, bold=True).pack(anchor="w")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=16)
        content.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(content, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w")
        _lbl(info, "Require Touch ID on launch", size=14).pack(anchor="w")
        _lbl(info, "Locks the app behind your Mac's fingerprint (or account password).",
             size=11, color=TEXT_DIM).pack(anchor="w")

        available = auth.auth_available()
        self._touch_var = ctk.BooleanVar(
            value=available and self.db.get_setting("touch_id_lock", "1") == "1")
        switch = ctk.CTkSwitch(content, text="", variable=self._touch_var,
                               progress_color=ACCENT, button_color=TEXT,
                               fg_color=CARD2, width=48,
                               command=self._toggle_touch_id)
        switch.grid(row=0, column=1, sticky="e")

        if not available:
            switch.configure(state="disabled")
            reason = ("Touch ID needs the pyobjc LocalAuthentication framework — "
                      "run install.sh again to add it."
                      if not auth.LA_AVAILABLE else
                      "No Touch ID or account password is available on this Mac.")
            _lbl(content, reason, size=11, color=WARNING).grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        else:
            ctk.CTkButton(content, text="Lock Now  (⌘L)", fg_color=CARD2,
                          hover_color=HOVER, text_color=TEXT,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          height=32, corner_radius=RADIUS_SM, width=130,
                          command=self.app.lock).grid(
                row=1, column=0, sticky="w", pady=(12, 0))

    def _toggle_touch_id(self):
        self.db.set_setting("touch_id_lock", "1" if self._touch_var.get() else "0")

    # ── Database ─────────────────────────────────────────────────────────────

    def _build_database_section(self):
        card = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 16))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        _lbl(hdr, "Database", size=16, bold=True).pack(anchor="w")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=16)

        _lbl(content,
             "The database file stores all your data. Moving it to Google Drive, iCloud or Dropbox\n"
             "enables automatic sync across devices.",
             size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, 12))

        # Current path
        path_row = ctk.CTkFrame(content, fg_color=INPUT_BG, corner_radius=8)
        path_row.pack(fill="x", pady=(0, 10))
        path_row.grid_columnconfigure(0, weight=1)
        db_path = self.db.db_path
        _lbl(path_row, db_path, size=12, color=TEXT_DIM).grid(
            row=0, column=0, sticky="w", padx=14, pady=10)

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(anchor="w")

        ctk.CTkButton(btn_row, text="Move Database…", fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=TEXT,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      height=34, corner_radius=8, width=160,
                      command=self._move_db).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_row, text="Open Folder", fg_color=CARD2, hover_color=HOVER,
                      text_color=TEXT,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      height=34, corner_radius=8, width=120,
                      command=lambda: os.system(f'open "{os.path.dirname(db_path)}"')
                      ).pack(side="left")

    def _move_db(self):
        current = self.db.db_path
        folder = filedialog.askdirectory(title="Choose folder for database", parent=self)
        if not folder:
            return
        new_path = os.path.join(folder, "expense_tracker.db")
        if new_path == current:
            return
        try:
            shutil.copy2(current, new_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not move database:\n{e}", parent=self)
            return

        # Save new path to config
        config_file = Path.home() / ".expense_tracker" / "config.txt"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text(new_path)

        messagebox.showinfo(
            "Database Moved",
            f"Database copied to:\n{new_path}\n\nPlease restart the app to use the new location.",
            parent=self)

    # ── About ─────────────────────────────────────────────────────────────────

    def _build_about_section(self):
        card = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 16))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        _lbl(hdr, "About", size=16, bold=True).pack(anchor="w")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(fill="x", padx=20, pady=16)

        rows = [
            ("App", "Expense Tracker"),
            ("Version", "2.0.0"),
            ("Built with", "Python · customtkinter · matplotlib · SQLite"),
            ("Database", self.db.db_path),
        ]
        for key, val in rows:
            r = ctk.CTkFrame(info, fg_color="transparent")
            r.pack(fill="x", pady=3)
            r.grid_columnconfigure(1, weight=1)
            _lbl(r, key, size=12, color=TEXT_DIM).grid(row=0, column=0, sticky="w", padx=(0, 20))
            _lbl(r, val, size=12, color=TEXT).grid(row=0, column=1, sticky="w")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def set_profile(self, profile_id: int):
        self.profile_id = profile_id
        self._load()

    def refresh(self):
        self._load()
