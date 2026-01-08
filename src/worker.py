import threading
from pathlib import Path
from typing import Callable, Optional


from scanner import FolderScanner, ScanResult
from cache import FolderCache

ProgressCallback = Callable[[Path, int, int], None]
ResultCallback = Callable[[ScanResult], None]


class ScanWorker:
    """
    Управляет сканированием папок:
    - проверяет кеш
    - запускает сканер в фоне
    - сохраняет результат
    """
    
    def __init__(
        self,
        cache: FolderCache,
        on_progress: Optional[ProgressCallback] = None,
        on_result: Optional[ResultCallback] = None,
    ) -> None:
        self.cache = cache
        self.on_progress = on_progress
        self.on_result = on_result
        
        self._thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        
    
    def request_scan(self, path: Path) -> Optional[ScanResult]:
        
        
        # памятка для dev - 
        # пока один поток здесь, другой поток не может зайти в этот код with
        with self._lock:
            cached = self.cache.get(path)
            if cached:
                return cached
            
            
            # если уже что-то считается — отменяем
            self.cancel()
            
            
            # Новый флаг отмены (каждый запуск - новый флаг)
            self._cancel_event = threading.Event()
            
            scanner = FolderScanner(
                cancel_event=self._cancel_event,
                progress_cb=self._handle_progress,
            )
            
            self._thread = threading.Thread(
                target=self._run_scan,
                args=(scanner, path),
                daemon=True,
            )
            self._thread.start()

            return None
        
    def cancel(self) -> None:
        """Отменяет текущее сканирование"""
        if self._thread and self._thread.is_alive():
            self._cancel_event.set()

    def _run_scan(self, scanner: FolderScanner, path: Path) -> None:
        result = scanner.scan(path)

        if not result.cancelled:
            self.cache.save(result)

        if self.on_result:
            self.on_result(result)

    def _handle_progress(self, path: Path, size: int, files: int) -> None:
        if self.on_progress:
            self.on_progress(path, size, files)

    