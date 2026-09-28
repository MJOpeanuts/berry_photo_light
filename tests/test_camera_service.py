import sys
import types
import unittest
from unittest.mock import patch

from camera_service import CameraService


class FakePicamera2:
    instances = []

    def __init__(self):
        self.started = False
        self.closed = False
        self.configured = None
        FakePicamera2.instances.append(self)

    def create_preview_configuration(self, **kwargs):
        return kwargs

    def configure(self, config):
        self.configured = config

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def close(self):
        self.closed = True


class FakeGlPreview:
    def __init__(self, camera, **kwargs):
        self.camera = camera
        self.kwargs = kwargs


class FakeSoftwarePreview:
    def __init__(self, camera):
        self.camera = camera
        self.size = None

    def resize(self, width, height):
        self.size = (width, height)


class FailingGlPreview:
    def __init__(self, camera, **kwargs):
        raise RuntimeError("EGLError(err = EGL_BAD_ALLOC)")


class CameraServiceTests(unittest.TestCase):
    def setUp(self):
        FakePicamera2.instances.clear()

    def _patch_picamera2(self, gl_preview, software_preview):
        picamera2_module = types.ModuleType("picamera2")
        picamera2_module.Picamera2 = FakePicamera2

        previews_module = types.ModuleType("picamera2.previews")
        qt_module = types.ModuleType("picamera2.previews.qt")
        qt_module.QGlPicamera2 = gl_preview
        qt_module.QPicamera2 = software_preview
        previews_module.qt = qt_module

        return patch.dict(
            sys.modules,
            {
                "picamera2": picamera2_module,
                "picamera2.previews": previews_module,
                "picamera2.previews.qt": qt_module,
            },
        )

    def test_start_preview_prefers_opengl_when_available(self):
        with self._patch_picamera2(FakeGlPreview, FakeSoftwarePreview):
            preview = CameraService().start_preview()

        self.assertIsInstance(preview, FakeGlPreview)
        self.assertEqual(len(FakePicamera2.instances), 1)
        self.assertTrue(FakePicamera2.instances[0].started)

    def test_start_preview_falls_back_to_software_preview_when_opengl_fails(self):
        with self._patch_picamera2(FailingGlPreview, FakeSoftwarePreview):
            preview = CameraService().start_preview()

        self.assertIsInstance(preview, FakeSoftwarePreview)
        self.assertEqual(preview.size, (1024, 768))
        self.assertEqual(len(FakePicamera2.instances), 2)
        self.assertTrue(FakePicamera2.instances[0].closed)
        self.assertTrue(FakePicamera2.instances[1].started)


if __name__ == "__main__":
    unittest.main()
