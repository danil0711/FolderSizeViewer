import os
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ScanResult:
    path: Path
    size_bytes: int
    file_count: int
    cancelled: bool
    error_count: int


class FolderScanner:
    def __init__(
        self,
        cancel_event: Optional[threading.Event] = None,
        progress_cb: Optional[Callable[[Path, int, int], None]] = None,
    ) -> None:
        self.cancel_event = cancel_event or threading.Event()
        self.progress_cb = progress_cb

    def _is_safe_dir(self, entry: os.DirEntry) -> bool:
        """Проверка безопасности входа в каталог (не symlink, не junction)"""
        try:
            # Если папка - ссылка на другую папку, не анализируем её.
            if entry.is_symlink():
                return False
            stat = entry.stat(follow_symlinks=False)
            # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
            if stat.st_file_attributes & 0x400:
                return False
            return True
        except OSError:
            return False

    def scan(self, root: Path) -> ScanResult:
        """Рекурсивный обход каталога"""
        total_size = 0
        total_files = 0
        errors = 0

        stack: list[Path] = [root]

        while stack:
            if self.cancel_event.is_set():
                return ScanResult(
                    path=root,
                    size_bytes=total_size,
                    file_count=total_files,
                    cancelled=True,
                    error_count=errors,
                )

            current = stack.pop()

            try:
                with os.scandir(current) as it:
                    for entry in it:
                        if self.cancel_event.is_set():
                            break

                        try:
                            if entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                total_size += stat.st_size
                                total_files += 1
                            elif entry.is_dir(follow_symlinks=False):
                                if self._is_safe_dir(entry):
                                    stack.append(Path(entry.path))
                        except (PermissionError, FileNotFoundError):
                            errors += 1
                            continue
            except (PermissionError, FileNotFoundError):
                errors += 1
                continue

            if self.progress_cb:
                self.progress_cb(current, total_size, total_files)

        return ScanResult(
            path=root,
            size_bytes=total_size,
            file_count=total_files,
            cancelled=False,
            error_count=errors,
        )
