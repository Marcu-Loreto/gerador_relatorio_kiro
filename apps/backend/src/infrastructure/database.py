"""SQLite local database for report persistence."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

DB_PATH = os.environ.get("SQLITE_DB_PATH", "reports/relatorios.db")


def get_db_path() -> str:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connection."""
    conn = sqlite3.connect(get_db_path())
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


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
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
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            CREATE INDEX IF NOT EXISTS idx_reports_document
                ON reports(document_id);
            CREATE INDEX IF NOT EXISTS idx_reports_type
                ON reports(report_type);
            CREATE INDEX IF NOT EXISTS idx_reports_created
                ON reports(created_at DESC);
        """)
        # Migrate existing DBs that lack csv_path column
        try:
            conn.execute("ALTER TABLE reports ADD COLUMN csv_path TEXT")
        except Exception:
            pass  # column already exists


# ── Documents ──────────────────────────────────────────────────────────────

def save_document(doc: dict) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO documents
                (id, filename, file_type, file_size, word_count, uploaded_at, file_path)
            VALUES (:id, :filename, :file_type, :file_size, :word_count, :uploaded_at, :file_path)
        """, {
            "id": doc["document_id"],
            "filename": doc["filename"],
            "file_type": doc["file_type"],
            "file_size": doc.get("file_size", 0),
            "word_count": doc.get("word_count"),
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_path": doc.get("file_path", ""),
        })


# ── Reports ────────────────────────────────────────────────────────────────

def save_report(report: dict) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO reports
                (id, document_id, document_name, report_type, status,
                 quality_score, md_path, csv_path, created_at, updated_at)
            VALUES (:id, :document_id, :document_name, :report_type, :status,
                    :quality_score, :md_path, :csv_path, :created_at, :updated_at)
        """, {
            "id": report["report_id"],
            "document_id": report["document_id"],
            "document_name": report.get("document_name", ""),
            "report_type": report["report_type"],
            "status": report.get("status", "generated"),
            "quality_score": report.get("quality_score"),
            "md_path": report.get("md_path", ""),
            "csv_path": report.get("csv_path"),
            "created_at": report.get("created_at", now),
            "updated_at": now,
        })


def update_report_content(report_id: str, md_path: str, status: str = "edited") -> None:
    with get_connection() as conn:
        conn.execute("""
            UPDATE reports SET md_path=?, status=?, updated_at=? WHERE id=?
        """, (md_path, status, datetime.utcnow().isoformat(), report_id))


def get_report(report_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE id=?", (report_id,)
        ).fetchone()
        return dict(row) if row else None


def list_reports(
    search: Optional[str] = None,
    report_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List reports with optional search and filter."""
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
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


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
        return conn.execute(query, params).fetchone()[0]


def delete_report(report_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
        return cur.rowcount > 0
