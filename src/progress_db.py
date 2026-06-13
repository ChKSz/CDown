import os
import json
import sqlite3
from typing import List, Optional


class ProgressDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".",
            exist_ok=True,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    song_id TEXT PRIMARY KEY,
                    name TEXT,
                    artist TEXT,
                    album TEXT,
                    url TEXT,
                    file_path TEXT,
                    cover_url TEXT,
                    total_size INTEGER DEFAULT 0,
                    downloaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    error TEXT DEFAULT '',
                    level TEXT DEFAULT 'jymaster',
                    lrc TEXT DEFAULT '',
                    tlyric TEXT DEFAULT ''
                )
            """)

    def save_task(self, task):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO downloads
                (song_id, name, artist, album, url, file_path, cover_url, total_size, downloaded, status, error, level, lrc, tlyric)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task.song_id,
                    task.name,
                    task.artist,
                    task.album,
                    task.url,
                    task.file_path,
                    task.cover_url,
                    task.total_size,
                    task.downloaded,
                    task.status.value,
                    task.error,
                    task.level,
                    task.lrc,
                    task.tlyric,
                ),
            )

    def save_tasks(self, tasks):
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO downloads
                (song_id, name, artist, album, url, file_path, cover_url, total_size, downloaded, status, error, level, lrc, tlyric)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    (
                        t.song_id,
                        t.name,
                        t.artist,
                        t.album,
                        t.url,
                        t.file_path,
                        t.cover_url,
                        t.total_size,
                        t.downloaded,
                        t.status.value,
                        t.error,
                        t.level,
                        t.lrc,
                        t.tlyric,
                    )
                    for t in tasks
                ],
            )

    def get_task(self, song_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM downloads WHERE song_id = ?", (song_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tasks_by_status(self, status: str) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM downloads WHERE status = ?", (status,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_tasks(self) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM downloads")
            return [dict(row) for row in cursor.fetchall()]

    def delete_task(self, song_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM downloads WHERE song_id = ?", (song_id,))

    def clear_completed(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM downloads WHERE status = 'completed'")

    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM downloads")
