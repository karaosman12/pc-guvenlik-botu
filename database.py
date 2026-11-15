import os
import sqlite3
import datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "security.db")
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")

class SecurityDatabase:
    """Yerel SQLite veritabanı ve olay arşivi yönetim sınıfı."""

    def __init__(self):
        os.makedirs(CAPTURES_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                image_path TEXT,
                screenshot_path TEXT,
                location_city TEXT,
                location_maps_url TEXT,
                location_source TEXT,
                cpu_percent REAL,
                ram_percent REAL,
                battery_status TEXT,
                email_status TEXT DEFAULT 'QUEUED',
                sent_at TEXT
            )
            """)
            conn.commit()

            try:
                conn.execute("ALTER TABLE security_events ADD COLUMN screenshot_path TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    def save_event(self, event_type, image_bytes=None, screenshot_bytes=None, location_info=None, system_stats=None, email_status="QUEUED"):
        """Olayı yerel SQLite veritabanına ve yakalanan görselleri diske kaydeder."""
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
        file_prefix = now.strftime("%Y%m%d_%H%M%S")
        safe_type = "".join(c for c in event_type if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')

        image_path = None
        if image_bytes:
            filename = f"{file_prefix}_{safe_type}_cam.jpg"
            image_path = os.path.join(CAPTURES_DIR, filename)
            try:
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
            except Exception:
                image_path = None

        screenshot_path = None
        if screenshot_bytes:
            screen_filename = f"{file_prefix}_{safe_type}_screen.jpg"
            screenshot_path = os.path.join(CAPTURES_DIR, screen_filename)
            try:
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot_bytes)
            except Exception:
                screenshot_path = None

        loc = location_info or {}
        stats = system_stats or {}

        with self._get_connection() as conn:
            cur = conn.execute("""
            INSERT INTO security_events (
                created_at, event_type, image_path, screenshot_path, location_city,
                location_maps_url, location_source, cpu_percent,
                ram_percent, battery_status, email_status, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp_str,
                event_type,
                image_path,
                screenshot_path,
                f"{loc.get('city', '')}, {loc.get('country', '')}".strip(', '),
                loc.get('maps_url', ''),
                loc.get('source', ''),
                stats.get('cpu', 0),
                stats.get('ram', 0),
                str(stats.get('battery', '')),
                email_status,
                timestamp_str if email_status == "SENT" else None
            ))
            conn.commit()
            return cur.lastrowid, image_path, screenshot_path

    def mark_event_sent(self, event_id):
        """Kuyruktaki bir olayın e-posta ile başarıyla iletildiğini günceller."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            conn.execute("""
            UPDATE security_events 
            SET email_status = 'SENT', sent_at = ?
            WHERE id = ?
            """, (now_str, event_id))
            conn.commit()

    def get_unsent_events(self):
        """Çevrimdışı kuyrukta bekleyen tüm olayları listeler."""
        with self._get_connection() as conn:
            cur = conn.execute("""
            SELECT * FROM security_events 
            WHERE email_status = 'QUEUED' 
            ORDER BY id ASC
            """)
            return [dict(row) for row in cur.fetchall()]

    def get_unsent_count(self):
        """Kuyrukta bekleyen olay sayısını döner."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM security_events WHERE email_status = 'QUEUED'")
            return cur.fetchone()[0]

    def get_recent_events(self, limit=15):
        """Son gerçekleşen olayları getirir."""
        with self._get_connection() as conn:
            cur = conn.execute("""
            SELECT id, created_at, event_type, email_status, location_city 
            FROM security_events 
            ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
