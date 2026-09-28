"""Touch-friendly Berry Photo Light application for Raspberry Pi."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from camera_service import CameraService
from capture_worker import CaptureWorker
from storage_service import Destination, StorageService


STYLE = """
QWidget { background: #17191d; color: #f4f5f7; font-size: 20px; }
QLabel#title { font-size: 30px; font-weight: 700; }
QLabel#hint { color: #b5bac3; }
QPushButton { background: #30343b; border: 1px solid #555b66; border-radius: 12px;
              padding: 18px 22px; min-height: 52px; }
QPushButton:pressed { background: #454b55; }
QPushButton:disabled { color: #858a92; }
QPushButton#capture { background: #d71920; border: none; border-radius: 34px;
                      min-width: 68px; max-width: 68px; min-height: 68px; max-height: 68px; }
QPushButton#capture:pressed { background: #a90f16; }
QPushButton#back { min-width: 64px; max-width: 100px; min-height: 52px; }
QFrame#preview { background: #08090a; border: 1px solid #444a53; border-radius: 8px; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Berry Photo Light")
        self.setMinimumSize(800, 450)
        self.setStyleSheet(STYLE)
        self._storage = StorageService()
        self._camera = CameraService()
        self._destination: Destination | None = None
        self._worker: CaptureWorker | None = None
        self._close_requested = False
        self._show_destination_screen()

    def _set_screen(self, widget: QWidget) -> None:
        previous = self.takeCentralWidget()
        if previous is not None:
            previous.deleteLater()
        self.setCentralWidget(widget)

    def _show_destination_screen(self, error: str = "") -> None:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(18)

        top = QHBoxLayout()
        top.addStretch(1)
        self._quit_button = QPushButton("Quitter")
        self._quit_button.clicked.connect(self._request_close)
        top.addWidget(self._quit_button, 0, Qt.AlignRight)
        layout.addLayout(top)

        title = QLabel("Où enregistrer les photos ?")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("Choisissez le disque local ou une clé USB montée.")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        if error:
            message = QLabel(error)
            message.setStyleSheet("color: #ff8585;")
            message.setWordWrap(True)
            message.setAlignment(Qt.AlignCenter)
            layout.addWidget(message)

        destinations = self._storage.list_destinations()
        for destination in destinations:
            button = QPushButton(destination.label)
            button.clicked.connect(
                lambda _checked=False, target=destination: self._select_destination(target)
            )
            layout.addWidget(button)

        if len(destinations) == 1:
            usb_hint = QLabel("Aucune clé USB détectée. Vous pouvez choisir un autre dossier USB.")
            usb_hint.setObjectName("hint")
            usb_hint.setWordWrap(True)
            usb_hint.setAlignment(Qt.AlignCenter)
            layout.addWidget(usb_hint)
            choose_usb = QPushButton("Parcourir les dossiers…")
            choose_usb.clicked.connect(self._choose_usb_folder)
            layout.addWidget(choose_usb)

        layout.addStretch(1)
        self._set_screen(screen)

    def _choose_usb_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier de la clé USB")
        if not folder:
            return
        path = Path(folder)
        if not path.is_dir() or not os.path.ismount(path):
            self._show_destination_screen("Choisissez le point de montage de la clé USB.")
            return
        destination = Destination(f"Clé USB : {path.name}", path / "BerryPhotoLight", True)
        self._select_destination(destination)

    def _select_destination(self, destination: Destination) -> None:
        valid, message = self._storage.check_writable(destination)
        if not valid:
            self._show_destination_screen(message)
            return
        self._destination = destination
        try:
            self._show_capture_screen()
        except Exception as exc:
            self._show_destination_screen(f"Impossible de démarrer la caméra : {exc}")

    def _show_capture_screen(self) -> None:
        if self._destination is None:
            self._show_destination_screen()
            return

        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(18, 12, 18, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self._back_button = QPushButton("‹ Retour")
        self._back_button.setObjectName("back")
        self._back_button.clicked.connect(self._back_to_destination)
        top.addWidget(self._back_button, 0, Qt.AlignLeft)
        destination_label = QLabel(self._destination.label)
        destination_label.setObjectName("hint")
        destination_label.setAlignment(Qt.AlignCenter)
        top.addWidget(destination_label, 1)
        self._quit_button = QPushButton("Quitter")
        self._quit_button.clicked.connect(self._request_close)
        top.addWidget(self._quit_button, 0, Qt.AlignRight)
        layout.addLayout(top)

        try:
            preview = self._camera.start_preview()
        except Exception as exc:
            raise RuntimeError(f"Erreur de prévisualisation : {exc}") from exc
        preview.setParent(screen)
        layout.addWidget(preview, 1)

        self._status = QLabel("Cadrez la carte, puis prenez la photo.")
        self._status.setObjectName("hint")
        self._status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self._capture_button = QPushButton("")
        self._capture_button.setObjectName("capture")
        self._capture_button.setAccessibleName("Prendre une photo HD")
        self._capture_button.setToolTip("Prendre une photo HD")
        self._capture_button.clicked.connect(self._capture)
        bottom.addWidget(self._capture_button, 0, Qt.AlignCenter)
        bottom.addStretch(1)
        layout.addLayout(bottom)
        self._set_screen(screen)

    def _capture(self) -> None:
        if self._destination is None or self._worker is not None or self._close_requested:
            return
        valid, message = self._storage.check_writable(self._destination)
        if not valid:
            self._status.setText(message)
            self._status.setStyleSheet("color: #ff8585;")
            return

        filename = self._storage.new_photo_path(self._destination)
        self._capture_button.setEnabled(False)
        self._status.setStyleSheet("")
        self._status.setText("Capture HD en cours…")
        self._worker = CaptureWorker(self._camera, filename)
        self._worker.succeeded.connect(self._capture_succeeded)
        self._worker.failed.connect(self._capture_failed)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _capture_succeeded(self, filename: str) -> None:
        if hasattr(self, "_status"):
            self._status.setStyleSheet("color: #8ce99a;")
            self._status.setText(f"Photo enregistrée : {filename}")

    def _capture_failed(self, message: str) -> None:
        if hasattr(self, "_status"):
            self._status.setStyleSheet("color: #ff8585;")
            self._status.setText(f"Échec de la photo : {message}")

    def _worker_finished(self) -> None:
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.deleteLater()
        if self._close_requested:
            self._close_requested = False
            self.close()
            return
        if hasattr(self, "_capture_button"):
            self._capture_button.setEnabled(True)

    def _back_to_destination(self) -> None:
        if self._worker is not None or self._close_requested:
            QMessageBox.information(self, "Capture en cours", "Attendez la fin de l'enregistrement.")
            return
        self._camera.stop_preview()
        self._destination = None
        self._show_destination_screen()

    def _request_close(self) -> None:
        self.close()

    def _prepare_delayed_close(self) -> None:
        self._close_requested = True
        if hasattr(self, "_capture_button"):
            self._capture_button.setEnabled(False)
        if hasattr(self, "_back_button"):
            self._back_button.setEnabled(False)
        if hasattr(self, "_quit_button"):
            self._quit_button.setEnabled(False)
        if hasattr(self, "_status"):
            self._status.setStyleSheet("")
            self._status.setText("Capture HD en cours… fermeture automatique après l'enregistrement.")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if self._worker is not None:
            self._prepare_delayed_close()
            event.ignore()
            return
        self._camera.close()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Berry Photo Light")
    window = MainWindow()
    window.showFullScreen()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
