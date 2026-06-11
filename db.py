import aiosqlite
 
DB_PATH = "movies.db"
 
# ───────────────────────────── INIT ─────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                caption TEXT,
                file_id TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                used_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                joined_at TEXT NOT NULL,
                lang TEXT DEFAULT 'uz'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium_users (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT NOT NULL,
                activated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                photo_file_id TEXT NOT NULL,
                tariff TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        # MIGRATION: eski DB ga lang ustuni qo'shish
        try:
            await db.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'uz'")
        except Exception:
            pass  # Ustun allaqachon mavjud
        await db.commit()
 
# ───────────────────────────── MOVIES ─────────────────────────────
async def upsert_movie(code: str, caption: str, file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO movies(code, caption, file_id)
            VALUES(?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                caption=excluded.caption,
                file_id=excluded.file_id
        """, (code, caption, file_id))
        await db.commit()
 
async def get_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT code, caption, file_id FROM movies WHERE code=?", (code,)
        )
        return await cur.fetchone()
 
async def delete_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM movies WHERE code=?", (code,))
        await db.commit()
 
async def get_all_movies():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT code, caption FROM movies ORDER BY code")
        return await cur.fetchall()
 
# ───────────────────────────── USAGE ─────────────────────────────
async def log_usage(user_id: int, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO usage_log (user_id, code, used_at) VALUES (?, ?, datetime('now'))",
            (user_id, code)
        )
        await db.commit()
 
async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT code, COUNT(*) as cnt
            FROM usage_log
            GROUP BY code
            ORDER BY cnt DESC
            LIMIT 20
        """)
        return await cur.fetchall()
 
# ───────────────────────────── USERS ─────────────────────────────
async def save_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, datetime('now'))",
            (user_id,)
        )
        await db.commit()
 
async def get_total_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0] if row else 0
 
async def get_subscription_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0] if row else 0
 
async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]
 
async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET lang=? WHERE user_id=?", (lang, user_id)
        )
        await db.commit()
 
async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT lang FROM users WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else "uz"
 
# ───────────────────────────── PREMIUM ─────────────────────────────
async def set_premium(user_id: int, days: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO premium_users (user_id, expires_at, activated_at)
            VALUES (?, datetime('now', ?), datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                expires_at = datetime('now', ?),
                activated_at = datetime('now')
        """, (user_id, f"+{days} days", f"+{days} days"))
        await db.commit()
 
async def is_premium(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT expires_at FROM premium_users
            WHERE user_id=? AND expires_at > datetime('now')
        """, (user_id,))
        return await cur.fetchone() is not None
 
async def get_premium_info(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT expires_at FROM premium_users
            WHERE user_id=? AND expires_at > datetime('now')
        """, (user_id,))
        return await cur.fetchone()
 
async def get_expiring_premium(days: int = 3):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT user_id, expires_at FROM premium_users
            WHERE expires_at > datetime('now')
              AND expires_at <= datetime('now', ?)
        """, (f"+{days} days",))
        return await cur.fetchall()
 
async def get_premium_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT COUNT(*) FROM premium_users
            WHERE expires_at > datetime('now')
        """)
        row = await cur.fetchone()
        return row[0] if row else 0
 
# ───────────────────────────── PAYMENTS ─────────────────────────────
async def save_payment(user_id: int, photo_file_id: str, tariff: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO payments (user_id, photo_file_id, tariff, status, created_at)
            VALUES (?, ?, ?, 'pending', datetime('now'))
        """, (user_id, photo_file_id, tariff))
        await db.commit()
        return cur.lastrowid
 
async def get_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, photo_file_id, tariff, status FROM payments WHERE id=?",
            (payment_id,)
        )
        return await cur.fetchone()
 
async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=? WHERE id=?", (status, payment_id)
        )
        await db.commit()