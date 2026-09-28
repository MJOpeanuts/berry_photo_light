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
            from picamera2.previews import qt as picamera2_qt
        except ImportError as exc:
            raise RuntimeError(
                "Picamera2 et son aperçu Qt sont requis. Consultez README.md."
            ) from exc

        preview_backends = self._preview_backends(picamera2_qt)
        if not preview_backends:
            raise RuntimeError(
                "Aucun widget de prévisualisation Qt Picamera2 n'est disponible."
            )

        errors: list[tuple[str, Exception]] = []
        for label, preview_cls in preview_backends:
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
                self._preview_widget = self._create_preview_widget(preview_cls, camera)
                camera.start()
                return self._preview_widget
            except Exception as exc:
                errors.append((label, exc))
                self.close()

        formatted_errors = "; ".join(f"{label}: {exc}" for label, exc in errors)
        raise RuntimeError(f"Impossible de démarrer la prévisualisation ({formatted_errors}).")

    @staticmethod
    def _preview_backends(picamera2_qt: Any) -> list[tuple[str, Any]]:
        backends: list[tuple[str, Any]] = []
        gl_preview = getattr(picamera2_qt, "QGlPicamera2", None)
        if gl_preview is not None:
            backends.append(("OpenGL", gl_preview))

        software_preview = getattr(picamera2_qt, "QPicamera2", None)
        if software_preview is not None and software_preview is not gl_preview:
            backends.append(("logiciel", software_preview))
        return backends

    @staticmethod
    def _create_preview_widget(preview_cls: Any, camera: Any) -> Any:
        try:
            return preview_cls(camera, width=1024, height=768, keep_ar=True)
        except TypeError:
            widget = preview_cls(camera)
            resize = getattr(widget, "resize", None)
            if callable(resize):
                resize(1024, 768)
            return widget

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
