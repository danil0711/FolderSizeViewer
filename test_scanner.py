from pathlib import Path

import threading

from src.cache import FolderCache
from src.scanner import FolderScanner

# создаём кэш
cache = FolderCache(Path("folder_cache.db"))

# проверяем кэш
path = Path(r"D:\HTML")
cached = cache.get(path)
if cached:
    print("From cache:", cached.size_bytes, "bytes")
else:
    # если нет в кэше, сканируем
    cancel_event = threading.Event()
    scanner = FolderScanner(cancel_event=cancel_event)
    result = scanner.scan(path)

    # сохраняем в кэш
    cache.save(result)
    print("Scanned:", result.size_bytes, "bytes")

cache.close()
