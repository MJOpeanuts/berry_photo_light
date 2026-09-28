"""Background Qt worker for a still capture and disk write."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from camera_service import CameraService


class CaptureWorker(QThread):
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, camera: CameraService, filename: Path) -> None:
        super().__init__()
        self._camera = camera
        self._filename = filename

    def run(self) -> None:
        try:
            self._camera.capture_hd(self._filename)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(str(self._filename))
