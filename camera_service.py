"""Picamera2 lifecycle and high-resolution capture."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class CameraService:
    """Own the single Picamera2 instance used by preview and still capture."""

    def __init__(self) -> None:
        self._camera: Any | None = None
        self._preview_widget: Any | None = None

    def start_preview(self) -> Any:
        """Start a low-resolution preview and return its Qt widget."""
        try:
            from picamera2 import Picamera2
            from picamera2.previews.qt import QGlPicamera2
        except ImportError as exc:
            raise RuntimeError(
                "Picamera2 et son aperçu Qt sont requis. Consultez README.md."
            ) from exc

        if self._camera is None:
            self._camera = Picamera2()

        camera = self._camera
        try:
            if camera.started:
                camera.stop()
            preview_config = camera.create_preview_configuration(
                main={"size": (1024, 768)},
                transform=self._camera_transform(),
            )
            camera.configure(preview_config)
            self._preview_widget = QGlPicamera2(
                camera,
                width=1024,
                height=768,
                keep_ar=True,
            )
            camera.start()
            return self._preview_widget
        except Exception:
            self.close()
            raise

    @staticmethod
    def _camera_transform() -> Any:
        try:
            from libcamera import Transform

            return Transform(vflip=True, hflip=False)
        except ImportError:
            return None

    def capture_hd(self, filename: Path) -> None:
        """Capture using Picamera2's still configuration at sensor resolution."""
        if self._camera is None or not self._camera.started:
            raise RuntimeError("La caméra n'est pas démarrée.")

        filename.parent.mkdir(parents=True, exist_ok=True)
        try:
            still_config = self._camera.create_still_configuration(
                transform=self._camera_transform(),
            )
            # Picamera2 restores the running preview configuration after capture.
            self._camera.switch_mode_and_capture_file(still_config, str(filename))
            if not filename.is_file() or filename.stat().st_size == 0:
                raise RuntimeError("La caméra n'a pas produit de fichier photo.")
        except Exception:
            try:
                filename.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def stop_preview(self) -> None:
        """Stop sensor streaming while leaving the service reusable."""
        if self._camera is not None:
            try:
                if self._camera.started:
                    self._camera.stop()
            finally:
                self._preview_widget = None

    def close(self) -> None:
        """Release camera resources on exit or after initialization failure."""
        camera, self._camera = self._camera, None
        self._preview_widget = None
        if camera is not None:
            try:
                if camera.started:
                    camera.stop()
            finally:
                camera.close()
