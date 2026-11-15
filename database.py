import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

DEFAULT_DB_PATH = str(Path.home() / "ExpenseTracker" / "data.db")

INCOME_DEFAULTS = [
    ("Salary",      "#4ade80"),
    ("Freelance",   "#22d3ee"),
    ("Gifts",       "#fbbf24"),
    ("Refunds",     "#60a5fa"),
    ("Investments", "#a78bfa"),
    ("Rental",      "#34d399"),
    ("Other Income","#94a3b8"),
]
EXPENSE_DEFAULTS = [
    ("Housing",       "#f87171"),
    ("Utilities",     "#fb923c"),
    ("Groceries",     "#facc15"),
    ("Dining",        "#a3e635"),
    ("Transportation","#38bdf8"),
    ("Clothing",      "#c084fc"),
    ("Healthcare",    "#f472b6"),
    ("Entertainment", "#fb7185"),
    ("Subscriptions", "#818cf8"),
    ("Travel",        "#2dd4bf"),
    ("Education",     "#7dd3fc"),
    ("Other Expenses","#94a3b8"),
]


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_defaults()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS profiles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                currency   TEXT NOT NULL DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name       TEXT NOT NULL,
                type       TEXT NOT NULL CHECK(type IN ('income','expense')),
                color      TEXT NOT NULL DEFAULT '#818cf8',
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                UNIQUE(profile_id, name, type)
            );
            CREATE TABLE IF NOT EXISTS balance_snapshots (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id       INTEGER NOT NULL,
                year             INTEGER NOT NULL,
                month            INTEGER NOT NULL,
                opening_balance  REAL    NOT NULL DEFAULT 0,
                UNIQUE(profile_id, year, month),
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id  INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                amount      REAL    NOT NULL,
                UNIQUE(profile_id, category_id),
                FOREIGN KEY (profile_id)  REFERENCES profiles(id)   ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id  INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                amount      REAL    NOT NULL,
                description TEXT    DEFAULT '',
                date        DATE    NOT NULL,
                type        TEXT    NOT NULL CHECK(type IN ('income','expense')),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id)  REFERENCES profiles(id)  ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
            );
        """)
        self.conn.commit()

    def _seed_defaults(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM profiles")
        if cur.fetchone()[0] > 0:
            return
        cur.execute("INSERT INTO profiles (name, currency) VALUES (?,?)", ("Personal", "EUR"))
        pid = cur.lastrowid
        for name, color in INCOME_DEFAULTS:
            cur.execute("INSERT INTO categories(profile_id,name,type,color) VALUES(?,?,'income',?)", (pid, name, color))
        for name, color in EXPENSE_DEFAULTS:
            cur.execute("INSERT INTO categories(profile_id,name,type,color) VALUES(?,?,'expense',?)", (pid, name, color))
        cur.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('active_profile_id',?)", (str(pid),))
        self.conn.commit()

    # ── Profiles ────────────────────────────────────────────────────────────

    def get_profiles(self) -> List[Dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM profiles ORDER BY name")]

    def add_profile(self, name: str, currency: str = "EUR") -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO profiles(name,currency) VALUES(?,?)", (name, currency))
        pid = cur.lastrowid
        for n, c in INCOME_DEFAULTS:
            cur.execute("INSERT INTO categories(profile_id,name,type,color) VALUES(?,?,'income',?)", (pid, n, c))
        for n, c in EXPENSE_DEFAULTS:
            cur.execute("INSERT INTO categories(profile_id,name,type,color) VALUES(?,?,'expense',?)", (pid, n, c))
        self.conn.commit()
        return pid

    def update_profile(self, pid: int, name: str, currency: str):
        self.conn.execute("UPDATE profiles SET name=?,currency=? WHERE id=?", (name, currency, pid))
        self.conn.commit()

    def delete_profile(self, pid: int):
        self.conn.execute("DELETE FROM profiles WHERE id=?", (pid,))
        self.conn.commit()

    def get_active_profile_id(self) -> Optional[int]:
        row = self.conn.execute("SELECT value FROM settings WHERE key='active_profile_id'").fetchone()
        if row:
            try:
                return int(row[0])
            except (ValueError, TypeError):
                pass
        row = self.conn.execute("SELECT id FROM profiles LIMIT 1").fetchone()
        return row[0] if row else None

    def set_active_profile(self, pid: int):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('active_profile_id',?)", (str(pid),))
        self.conn.commit()

    def get_profile_currency(self, pid: int) -> str:
        row = self.conn.execute("SELECT currency FROM profiles WHERE id=?", (pid,)).fetchone()
        return row[0] if row else "EUR"

    # ── Categories ──────────────────────────────────────────────────────────

    def get_categories(self, pid: int, type_filter: Optional[str] = None) -> List[Dict]:
        if type_filter:
            rows = self.conn.execute(
                "SELECT * FROM categories WHERE profile_id=? AND type=? ORDER BY name", (pid, type_filter))
        else:
            rows = self.conn.execute(
                "SELECT * FROM categories WHERE profile_id=? ORDER BY type,name", (pid,))
        return [dict(r) for r in rows]

    def add_category(self, pid: int, name: str, type_: str, color: str = "#818cf8") -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO categories(profile_id,name,type,color) VALUES(?,?,?,?)", (pid, name, type_, color))
        self.conn.commit()
        return cur.lastrowid

    def update_category(self, cid: int, name: str, color: str):
        self.conn.execute("UPDATE categories SET name=?,color=? WHERE id=?", (name, color, cid))
        self.conn.commit()

    def delete_category(self, cid: int) -> bool:
        """Returns False if category has transactions."""
        row = self.conn.execute("SELECT COUNT(*) FROM transactions WHERE category_id=?", (cid,)).fetchone()
        if row[0] > 0:
            return False
        self.conn.execute("DELETE FROM categories WHERE id=?", (cid,))
        self.conn.commit()
        return True

    def category_transaction_count(self, cid: int) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM transactions WHERE category_id=?", (cid,)).fetchone()[0]

    # ── Budgets (monthly limit per expense category) ────────────────────────

    def get_budget(self, pid: int, cid: int) -> Optional[float]:
        row = self.conn.execute(
            "SELECT amount FROM budgets WHERE profile_id=? AND category_id=?",
            (pid, cid)).fetchone()
        return row[0] if row else None

    def set_budget(self, pid: int, cid: int, amount: Optional[float]):
        """Set the monthly budget for a category; None or <= 0 removes it."""
        if amount is None or amount <= 0:
            self.conn.execute(
                "DELETE FROM budgets WHERE profile_id=? AND category_id=?", (pid, cid))
        else:
            self.conn.execute(
                "INSERT INTO budgets(profile_id,category_id,amount) VALUES(?,?,?) "
                "ON CONFLICT(profile_id,category_id) DO UPDATE SET amount=excluded.amount",
                (pid, cid, amount))
        self.conn.commit()

    def get_budget_progress(self, pid: int, month: int, year: int) -> List[Dict]:
        """Budgeted expense categories with the amount spent in the given month,
        sorted by how much of the budget is used (most critical first)."""
        rows = self.conn.execute("""
            SELECT c.id, c.name, c.color, b.amount AS budget,
                   COALESCE((SELECT SUM(t.amount) FROM transactions t
                             WHERE t.category_id = c.id AND t.type = 'expense'
                               AND strftime('%m', t.date) = ?
                               AND strftime('%Y', t.date) = ?), 0) AS spent
            FROM budgets b JOIN categories c ON b.category_id = c.id
            WHERE b.profile_id = ? AND c.type = 'expense'
        """, (f"{month:02d}", str(year), pid))
        result = [dict(r) for r in rows]
        result.sort(key=lambda r: r["spent"] / r["budget"] if r["budget"] else 0,
                    reverse=True)
        return result

    # ── Transactions ────────────────────────────────────────────────────────

    def get_transactions(self, pid: int, month: Optional[int] = None,
                         year: Optional[int] = None, type_filter: Optional[str] = None,
                         search: str = "") -> List[Dict]:
        q = """
            SELECT t.*, c.name AS category_name, c.color AS category_color
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.profile_id = ?
        """
        params: list = [pid]
        if month:
            q += " AND strftime('%m', t.date) = ?"
            params.append(f"{month:02d}")
        if year:
            q += " AND strftime('%Y', t.date) = ?"
            params.append(str(year))
        if type_filter:
            q += " AND t.type = ?"
            params.append(type_filter)
        if search:
            q += " AND (t.description LIKE ? OR c.name LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY t.date DESC, t.created_at DESC"
        return [dict(r) for r in self.conn.execute(q, params)]

    def add_transaction(self, pid: int, cid: int, amount: float,
                        description: str, date: str, type_: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO transactions(profile_id,category_id,amount,description,date,type) VALUES(?,?,?,?,?,?)",
            (pid, cid, amount, description, date, type_))
        self.conn.commit()
        return cur.lastrowid

    def update_transaction(self, tid: int, cid: int, amount: float,
                           description: str, date: str, type_: str):
        self.conn.execute("""
            UPDATE transactions SET category_id=?,amount=?,description=?,date=?,type=?,
            updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (cid, amount, description, date, type_, tid))
        self.conn.commit()

    def delete_transaction(self, tid: int):
        self.conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
        self.conn.commit()

    # ── Analytics ───────────────────────────────────────────────────────────

    def get_total_summary(self, pid: int, month: Optional[int] = None,
                          year: Optional[int] = None) -> Dict:
        q = "SELECT type, SUM(amount) as total FROM transactions WHERE profile_id=?"
        params: list = [pid]
        if month:
            q += " AND strftime('%m',date)=?"
            params.append(f"{month:02d}")
        if year:
            q += " AND strftime('%Y',date)=?"
            params.append(str(year))
        q += " GROUP BY type"
        res = {r["type"]: r["total"] for r in self.conn.execute(q, params)}
        inc = res.get("income", 0) or 0
        exp = res.get("expense", 0) or 0
        return {"income": inc, "expenses": exp, "balance": inc - exp}

    def get_monthly_summary(self, pid: int, year: int) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT strftime('%m', date) as month, type, SUM(amount) as total
            FROM transactions WHERE profile_id=? AND strftime('%Y',date)=?
            GROUP BY month, type ORDER BY month
        """, (pid, str(year)))
        return [dict(r) for r in rows]

    def get_category_totals(self, pid: int, month: Optional[int] = None,
                            year: Optional[int] = None, type_filter: Optional[str] = None) -> List[Dict]:
        q = """
            SELECT c.name, c.color, t.type, SUM(t.amount) as total
            FROM transactions t JOIN categories c ON t.category_id=c.id
            WHERE t.profile_id=?
        """
        params: list = [pid]
        if month:
            q += " AND strftime('%m',t.date)=?"
            params.append(f"{month:02d}")
        if year:
            q += " AND strftime('%Y',t.date)=?"
            params.append(str(year))
        if type_filter:
            q += " AND t.type=?"
            params.append(type_filter)
        q += " GROUP BY c.id ORDER BY total DESC"
        return [dict(r) for r in self.conn.execute(q, params)]

    # ── Opening balance / wealth ─────────────────────────────────────────────

    def get_opening_balance(self, pid: int, year: int, month: int) -> float:
        row = self.conn.execute(
            "SELECT opening_balance FROM balance_snapshots WHERE profile_id=? AND year=? AND month=?",
            (pid, year, month)).fetchone()
        return row[0] if row else 0.0

    def set_opening_balance(self, pid: int, year: int, month: int, amount: float):
        self.conn.execute(
            "INSERT OR REPLACE INTO balance_snapshots(profile_id,year,month,opening_balance) "
            "VALUES(?,?,?,?)", (pid, year, month, amount))
        self.conn.commit()

    def get_wealth_over_time(self, pid: int, year: int) -> List[Dict]:
        """Monthly opening balance, net change and closing balance for all 12 months."""
        monthly = self.get_monthly_summary(pid, year)
        income_by_m: dict = {}
        expense_by_m: dict = {}
        for row in monthly:
            m = int(row["month"])
            if row["type"] == "income":
                income_by_m[m] = row["total"]
            else:
                expense_by_m[m] = row["total"]
        result = []
        for m in range(1, 13):
            opening  = self.get_opening_balance(pid, year, m)
            income   = income_by_m.get(m, 0.0)
            expenses = expense_by_m.get(m, 0.0)
            result.append({
                "month":           m,
                "opening_balance": opening,
                "income":          income,
                "expenses":        expenses,
                "net_change":      income - expenses,
                "closing_balance": opening + income - expenses,
            })
        return result

    def get_years_with_data(self, pid: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT DISTINCT strftime('%Y',date) as y FROM transactions WHERE profile_id=? ORDER BY y DESC", (pid,))
        years = [int(r[0]) for r in rows if r[0]]
        if not years:
            from datetime import date
            years = [date.today().year]
        return years

    # ── Settings ────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
        self.conn.commit()

    def close(self):
        self.conn.close()
