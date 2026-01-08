import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from scanner import ScanResult
import threading


class FolderCache:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        # Разрешаем использовать соединение из разных потоков
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Lock для безопасного доступа из разных потоков
        self._lock = threading.Lock()

        # Создаем таблицу один раз в конструкторе
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS folders (
                    path TEXT PRIMARY KEY,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    last_scanned TIMESTAMP NOT NULL
                )
                """
            )
            self._conn.commit()
        
        
        
    def get (self, path: Path) -> Optional[ScanResult]:
        """Возвращает ScanResult из кэша, если есть"""
        cursor = self._conn.execute(
            "SELECT size_bytes, file_count, last_scanned FROM folders WHERE path = ?", (str(path),)
        )
        row = cursor.fetchone()
        if row:
            size_bytes, file_count, last_scanned = row
            return ScanResult(
                path=path,
                size_bytes=size_bytes,
                file_count=file_count,
                cancelled=False,
                error_count=0
            )
        return None
    
    def save(self, result: ScanResult) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO folders (path, size_bytes, file_count, last_scanned)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    size_bytes=excluded.size_bytes,
                    file_count=excluded.file_count,
                    last_scanned=excluded.last_scanned
                """,
                (str(result.path), result.size_bytes, result.file_count, datetime.now())
            )
            self._conn.commit()
        
    def invalidate(self, path: Path) -> None:
        "Удаление записи из кеша"
        self._conn.execute("DELETE FROM folders WHERE path = ?", str(path),)
        self._conn.commit()
        
    def close(self) -> None:
        "Закрытие соединения с БД"
        self._conn.close()
        