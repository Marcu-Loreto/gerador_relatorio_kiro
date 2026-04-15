"""Database layer — supports PostgreSQL (Supabase) and SQLite fallback.

Detects DATABASE_URL:
  - starts with 'postgresql://' or 'postgres://' → psycopg2
  - otherwise → sqlite3 (local dev fallback)
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_USE_PG = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

# ── SQLite fallback path ───────────────────────────────────────────────────
_SQLITE_PATH = os.environ.get("SQLITE_DB_PATH", "reports/relatorios.db")


# ── Connection helpers ─────────────────────────────────────────────────────

class _Row(dict):
    """Dict that also supports attribute-style access (mimics sqlite3.Row)."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    if _USE_PG:
        with _pg_connection() as conn:
            yield conn
    else:
        with _sqlite_connection() as conn:
            yield conn


@contextmanager
def _pg_connection():
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def _sqlite_connection():
    os.makedirs(os.path.dirname(_SQLITE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _exec(conn, sql: str, params=()) -> Any:
    """Execute SQL with correct placeholder style (%s for PG, ? for SQLite)."""
    if _USE_PG:
        sql = sql.replace("?", "%s")
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _fetchone(conn, sql: str, params=()) -> Optional[dict]:
    cur = _exec(conn, sql, params)
    row = cur.fetchone()
    if row is None:
        return None
    if _USE_PG:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return dict(row)


def _fetchall(conn, sql: str, params=()) -> list[dict]:
    cur = _exec(conn, sql, params)
    rows = cur.fetchall()
    if _USE_PG:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


# ── Schema ─────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
        if _USE_PG:
            _init_pg(conn)
        else:
            _init_sqlite(conn)


def _init_pg(conn) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id          TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            file_type   TEXT NOT NULL,
            file_size   INTEGER,
            word_count  INTEGER,
            uploaded_at TEXT NOT NULL,
            file_path   TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id              TEXT PRIMARY KEY,
            document_id     TEXT NOT NULL,
            document_name   TEXT NOT NULL,
            report_type     TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'generated',
            quality_score   REAL,
            md_path         TEXT,
            csv_path        TEXT,
            xlsx_path       TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type)")
    conn.commit()


def _init_sqlite(conn) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id          TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            file_type   TEXT NOT NULL,
            file_size   INTEGER,
            word_count  INTEGER,
            uploaded_at TEXT NOT NULL,
            file_path   TEXT
        );
        CREATE TABLE IF NOT EXISTS reports (
            id              TEXT PRIMARY KEY,
            document_id     TEXT NOT NULL,
            document_name   TEXT NOT NULL,
            report_type     TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'generated',
            quality_score   REAL,
            md_path         TEXT,
            csv_path        TEXT,
            xlsx_path       TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);
    """)
    for col in ("csv_path", "xlsx_path"):
        try:
            conn.execute(f"ALTER TABLE reports ADD COLUMN {col} TEXT")
        except Exception:
            pass


# ── Documents ──────────────────────────────────────────────────────────────

def save_document(doc: dict) -> None:
    sql = """
        INSERT INTO documents (id, filename, file_type, file_size, word_count, uploaded_at, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            filename=EXCLUDED.filename, file_type=EXCLUDED.file_type,
            file_size=EXCLUDED.file_size, word_count=EXCLUDED.word_count,
            file_path=EXCLUDED.file_path
    """ if _USE_PG else """
        INSERT OR REPLACE INTO documents
            (id, filename, file_type, file_size, word_count, uploaded_at, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        doc["document_id"], doc["filename"], doc["file_type"],
        doc.get("file_size", 0), doc.get("word_count"),
        datetime.utcnow().isoformat(), doc.get("file_path", ""),
    )
    with get_connection() as conn:
        _exec(conn, sql, params)


# ── Reports ────────────────────────────────────────────────────────────────

def save_report(report: dict) -> None:
    now = datetime.utcnow().isoformat()
    sql = """
        INSERT INTO reports
            (id, document_id, document_name, report_type, status,
             quality_score, md_path, csv_path, xlsx_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=EXCLUDED.status, quality_score=EXCLUDED.quality_score,
            md_path=EXCLUDED.md_path, csv_path=EXCLUDED.csv_path,
            xlsx_path=EXCLUDED.xlsx_path, updated_at=EXCLUDED.updated_at
    """ if _USE_PG else """
        INSERT OR REPLACE INTO reports
            (id, document_id, document_name, report_type, status,
             quality_score, md_path, csv_path, xlsx_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        report["report_id"], report["document_id"], report.get("document_name", ""),
        report["report_type"], report.get("status", "generated"),
        report.get("quality_score"), report.get("md_path", ""),
        report.get("csv_path"), report.get("xlsx_path"),
        report.get("created_at", now), now,
    )
    with get_connection() as conn:
        _exec(conn, sql, params)


def update_report_content(report_id: str, md_path: str, status: str = "edited") -> None:
    with get_connection() as conn:
        _exec(conn,
              "UPDATE reports SET md_path=?, status=?, updated_at=? WHERE id=?",
              (md_path, status, datetime.utcnow().isoformat(), report_id))


def get_report(report_id: str) -> Optional[dict]:
    with get_connection() as conn:
        return _fetchone(conn, "SELECT * FROM reports WHERE id=?", (report_id,))


def list_reports(
    search: Optional[str] = None,
    report_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = "SELECT * FROM reports WHERE 1=1"
    params: list = []
    if search:
        query += " AND (document_name LIKE ? OR report_type LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if report_type:
        query += " AND report_type = ?"
        params.append(report_type)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_connection() as conn:
        return _fetchall(conn, query, params)


def count_reports(search: Optional[str] = None, report_type: Optional[str] = None) -> int:
    query = "SELECT COUNT(*) FROM reports WHERE 1=1"
    params: list = []
    if search:
        query += " AND (document_name LIKE ? OR report_type LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if report_type:
        query += " AND report_type = ?"
        params.append(report_type)
    with get_connection() as conn:
        cur = _exec(conn, query, params)
        return cur.fetchone()[0]


def delete_report(report_id: str) -> bool:
    with get_connection() as conn:
        cur = _exec(conn, "DELETE FROM reports WHERE id=?", (report_id,))
        return cur.rowcount > 0
