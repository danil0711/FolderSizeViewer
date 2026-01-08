import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
)
from PySide6.QtCore import Qt, QTimer

from cache import FolderCache
from worker import ScanWorker
from scanner import ScanResult


class MainWindow(QMainWindow):
    def __init__(self, folder_to_scan: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Folder Size Viewer")
        self.resize(500, 400)

        self.folder_to_scan = folder_to_scan

        # --- Cache & Worker ---
        self.cache = FolderCache(Path("folder_cache.db"))
        self.worker = ScanWorker(
            cache=self.cache,
            on_progress=self._on_progress,
            on_result=self._on_result,
        )

        # --- UI layout ---
        self._build_ui()

        # --- Start scanning immediately if folder provided ---
        if self.folder_to_scan:
            QTimer.singleShot(0, lambda: self.start_scan(self.folder_to_scan))

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # --- Path label ---
        self.path_label = QLabel("No folder selected")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.path_label)

        # --- Table ---
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # --- Status bar ---
        self.status_bar = QLabel("Ready")
        layout.addWidget(self.status_bar)

    # ---------- Actions ----------

    def start_scan(self, folder: Path) -> None:
        """Начинает сканирование заданной папки"""
        self.path_label.setText(str(folder))
        self._populate_table(folder)

        # Запрос worker на сканирование каждой подпапки
        for row in range(self.table.rowCount()):
            subfolder_name = self.table.item(row, 0).text()
            subfolder_path = folder / subfolder_name

            cached = self.worker.request_scan(subfolder_path)
            if cached:
                self.table.setItem(row, 1, QTableWidgetItem(str(cached.size_bytes)))
                self.table.setItem(row, 2, QTableWidgetItem("cached"))
            else:
                self.table.setItem(row, 2, QTableWidgetItem("calculating"))

    def _populate_table(self, folder: Path) -> None:
        """Отображает подпапки"""
        self.table.setRowCount(0)
        try:
            subfolders = [p for p in folder.iterdir() if p.is_dir()]
        except Exception as e:
            self.status_bar.setText(f"Error: {e}")
            return

        for sub in subfolders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(sub.name))
            self.table.setItem(row, 1, QTableWidgetItem("—"))
            self.table.setItem(row, 2, QTableWidgetItem("idle"))

        self.status_bar.setText(f"{len(subfolders)} folders found")

    # ---------- Callbacks from worker ----------

    def _on_progress(self, path: Path, size: int, files: int) -> None:
        """Вызывается из worker-потока при прогрессе"""
        # Находим строку в таблице
        for row in range(self.table.rowCount()):
            subfolder_name = self.table.item(row, 0).text()
            if path.name == subfolder_name:
                self.table.setItem(row, 1, QTableWidgetItem(str(size)))
                self.table.setItem(row, 2, QTableWidgetItem("calculating"))

    def _on_result(self, result: ScanResult) -> None:
        """Вызывается, когда worker закончил сканирование"""
        for row in range(self.table.rowCount()):
            subfolder_name = self.table.item(row, 0).text()
            if result.path.name == subfolder_name:
                self.table.setItem(row, 1, QTableWidgetItem(str(result.size_bytes)))
                self.table.setItem(row, 2, QTableWidgetItem("done"))


def run() -> None:
    app = QApplication(sys.argv)

    folder = None
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])

    window = MainWindow(folder_to_scan=folder)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
