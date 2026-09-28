"""Picamera2 lifecycle and high-resolution capture."""

from __future__ import annotations

import inspect
import re
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

        for index, (label, preview_cls) in enumerate(preview_backends):
            if self._camera is None:
                self._camera = Picamera2()

            camera = self._camera
            try:
                if getattr(camera, "started", False):
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
                should_retry = (
                    index == 0
                    and len(preview_backends) > 1
                    and label == "OpenGL"
                    and self._is_egl_preview_error(exc)
                )
                self.close()
                if should_retry:
                    continue
                raise

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
            signature = inspect.signature(preview_cls)
        except (TypeError, ValueError):
            signature = None

        preview_kwargs = {"width": 1024, "height": 768, "keep_ar": True}
        if signature is not None:
            try:
                signature.bind_partial(camera, **preview_kwargs)
            except TypeError:
                signature = None

        if signature is not None:
            return preview_cls(camera, **preview_kwargs)

        try:
            return preview_cls(camera, **preview_kwargs)
        except TypeError as exc:
            if not CameraService._is_argument_binding_type_error(exc):
                raise

        widget = preview_cls(camera)
        resize = getattr(widget, "resize", None)
        if callable(resize):
            resize(1024, 768)
        return widget

    @staticmethod
    def _is_egl_preview_error(exc: Exception) -> bool:
        seen: set[int] = set()
        current: BaseException | None = exc
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if CameraService._matches_egl_surface_error(current):
                return True
            current = current.__cause__ or current.__context__
        return False

    @staticmethod
    def _matches_egl_surface_error(exc: BaseException) -> bool:
        message = CameraService._normalize_error_message(exc)
        surface_creation_error = (
            "eglcreatewindowsurface" in message
            or "eglcreateplatformwindowsurface" in message
        )
        known_egl_surface_errors = (
            "eglbadalloc",
            "eglbadmatch",
            "eglbadnativewindow",
            "eglbadconfig",
            "eglbadattribute",
            "failedtocreate",
        )
        return surface_creation_error and any(
            token in message for token in known_egl_surface_errors
        )

    @staticmethod
    def _normalize_error_message(exc: BaseException) -> str:
        raw_message = f"{type(exc).__name__}: {exc}".lower()
        return re.sub(r"[^a-z0-9]+", "", raw_message)

    @staticmethod
    def _is_argument_binding_type_error(exc: TypeError) -> bool:
        message = str(exc).lower()
        binding_markers = (
            "unexpected keyword argument",
            "takes no keyword arguments",
            "positional arguments but",
            "required positional argument",
        )
        return any(marker in message for marker in binding_markers)

    @staticmethod
    def _camera_transform() -> Any:
        try:
            from libcamera import Transform

            return Transform(vflip=True, hflip=False)
        except ImportError:
            return None

    def capture_hd(self, filename: Path) -> None:
        """Capture using Picamera2's still configuration at sensor resolution."""
        if self._camera is None or not getattr(self._camera, "started", False):
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
                if getattr(self._camera, "started", False):
                    self._camera.stop()
            finally:
                self._preview_widget = None

    def close(self) -> None:
        """Release camera resources on exit or after initialization failure."""
        camera, self._camera = self._camera, None
        self._preview_widget = None
        if camera is not None:
            try:
                if getattr(camera, "started", False):
                    camera.stop()
            finally:
                camera.close()
