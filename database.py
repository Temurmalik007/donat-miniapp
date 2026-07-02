import sqlite3
from contextlib import contextmanager
from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                balance INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon_emoji TEXT DEFAULT '🎮',
                badge TEXT DEFAULT '',           -- masalan "Global", "AVTO"
                needs_player_id INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                player_id TEXT,
                price INTEGER NOT NULL,
                status TEXT DEFAULT 'kutilmoqda',   -- kutilmoqda / bajarildi / bekor_qilindi
                admin_comment TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                amount INTEGER NOT NULL,
                method TEXT NOT NULL,               -- click / payme
                receipt_file_id TEXT,
                status TEXT DEFAULT 'kutilmoqda',    -- kutilmoqda / tasdiqlandi / rad_etildi
                admin_comment TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            """
        )


# ---------- USERS ----------
def upsert_user(user_id: int, username: str, full_name: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name""",
            (user_id, username, full_name),
        )


def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def set_user_phone(user_id: int, phone: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET phone=? WHERE user_id=?", (phone, user_id))


def change_balance(user_id: int, delta: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (delta, user_id))


# ---------- CATEGORIES ----------
def get_categories():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order, id"
        ).fetchall()


def add_category(name, icon_emoji="🎮", badge="", needs_player_id=0):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO categories (name, icon_emoji, badge, needs_player_id) VALUES (?, ?, ?, ?)",
            (name, icon_emoji, badge, needs_player_id),
        )
        return cur.lastrowid


def get_category(category_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()


# ---------- PRODUCTS ----------
def get_products(category_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE category_id=? AND is_active=1 ORDER BY sort_order, id",
            (category_id,),
        ).fetchall()


def get_product(product_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()


def add_product(category_id, name, price):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO products (category_id, name, price) VALUES (?, ?, ?)",
            (category_id, name, price),
        )
        return cur.lastrowid


def update_product_price(product_id: int, new_price: int):
    with get_conn() as conn:
        conn.execute("UPDATE products SET price=? WHERE id=?", (new_price, product_id))


def update_product_name(product_id: int, new_name: str):
    with get_conn() as conn:
        conn.execute("UPDATE products SET name=? WHERE id=?", (new_name, product_id))


def delete_product(product_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE products SET is_active=0 WHERE id=?", (product_id,))


def get_all_products_with_category():
    with get_conn() as conn:
        return conn.execute(
            """SELECT p.id, p.name, p.price, c.name AS category_name
               FROM products p JOIN categories c ON c.id = p.category_id
               WHERE p.is_active=1
               ORDER BY c.sort_order, c.id, p.sort_order, p.id"""
        ).fetchall()


# ---------- ORDERS (balansdan avtomatik yechiladi) ----------
def create_order(user_id: int, product_id: int, price: int, player_id: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO orders (user_id, product_id, price, player_id) VALUES (?, ?, ?, ?)",
            (user_id, product_id, price, player_id),
        )
        conn.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id))
        return cur.lastrowid


def get_order(order_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()


def set_order_status(order_id: int, status: str, admin_comment: str = None):
    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if status == "bekor_qilindi" and order["status"] != "bekor_qilindi":
            # bekor qilinsa pul qaytariladi
            conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (order["price"], order["user_id"]))
        conn.execute(
            "UPDATE orders SET status=?, admin_comment=COALESCE(?, admin_comment), updated_at=datetime('now') WHERE id=?",
            (status, admin_comment, order_id),
        )


def get_user_orders(user_id: int, limit: int = 50):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()


# ---------- TOPUPS (hisob to'ldirish) ----------
def create_topup(user_id: int, amount: int, method: str, receipt_file_id: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO topups (user_id, amount, method, receipt_file_id) VALUES (?, ?, ?, ?)",
            (user_id, amount, method, receipt_file_id),
        )
        return cur.lastrowid


def get_topup(topup_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM topups WHERE id=?", (topup_id,)).fetchone()


def set_topup_status(topup_id: int, status: str, admin_comment: str = None):
    with get_conn() as conn:
        topup = conn.execute("SELECT * FROM topups WHERE id=?", (topup_id,)).fetchone()
        if status == "tasdiqlandi" and topup["status"] != "tasdiqlandi":
            conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (topup["amount"], topup["user_id"]))
        conn.execute(
            "UPDATE topups SET status=?, admin_comment=COALESCE(?, admin_comment), updated_at=datetime('now') WHERE id=?",
            (status, admin_comment, topup_id),
        )


def get_user_topups(user_id: int, limit: int = 50):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM topups WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
