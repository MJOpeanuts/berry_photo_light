import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_main_module():
    pyqt5_module = types.ModuleType("PyQt5")
    qtcore_module = types.ModuleType("PyQt5.QtCore")
    qtwidgets_module = types.ModuleType("PyQt5.QtWidgets")

    class Qt:
        AlignLeft = 1
        AlignRight = 2
        AlignCenter = 4
        AlignVCenter = 8

    class Signal:
        def connect(self, _callback):
            return None

    class BaseWidget:
        def __init__(self, *args, **kwargs):
            self._enabled = True

        def setObjectName(self, *_args, **_kwargs):
            return None

        def setAlignment(self, *_args, **_kwargs):
            return None

        def setWordWrap(self, *_args, **_kwargs):
            return None

        def setStyleSheet(self, *_args, **_kwargs):
            return None

        def setContentsMargins(self, *_args, **_kwargs):
            return None

        def setSpacing(self, *_args, **_kwargs):
            return None

        def addWidget(self, *_args, **_kwargs):
            return None

        def addLayout(self, *_args, **_kwargs):
            return None

        def addStretch(self, *_args, **_kwargs):
            return None

        def setParent(self, *_args, **_kwargs):
            return None

        def setEnabled(self, value):
            self._enabled = value

        def setAccessibleName(self, *_args, **_kwargs):
            return None

        def setToolTip(self, *_args, **_kwargs):
            return None

        def showFullScreen(self):
            return None

    class QApplication(BaseWidget):
        def exec_(self):
            return 0

        def setApplicationName(self, *_args, **_kwargs):
            return None

    class QMainWindow(BaseWidget):
        def setWindowTitle(self, *_args, **_kwargs):
            return None

        def setMinimumSize(self, *_args, **_kwargs):
            return None

        def takeCentralWidget(self):
            return None

        def setCentralWidget(self, *_args, **_kwargs):
            return None

        def close(self):
            return None

    class QPushButton(BaseWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.clicked = Signal()

    class QFileDialog:
        @staticmethod
        def getExistingDirectory(*_args, **_kwargs):
            return ""

    class QMessageBox:
        @staticmethod
        def information(*_args, **_kwargs):
            return None

    qtcore_module.Qt = Qt
    qtwidgets_module.QApplication = QApplication
    qtwidgets_module.QFileDialog = QFileDialog
    qtwidgets_module.QFrame = BaseWidget
    qtwidgets_module.QHBoxLayout = BaseWidget
    qtwidgets_module.QLabel = BaseWidget
    qtwidgets_module.QMainWindow = QMainWindow
    qtwidgets_module.QMessageBox = QMessageBox
    qtwidgets_module.QPushButton = QPushButton
    qtwidgets_module.QVBoxLayout = BaseWidget
    qtwidgets_module.QWidget = BaseWidget

    capture_worker_module = types.ModuleType("capture_worker")

    class CaptureWorker:
        pass

    capture_worker_module.CaptureWorker = CaptureWorker

    camera_service_module = types.ModuleType("camera_service")

    class CameraService:
        pass

    camera_service_module.CameraService = CameraService

    storage_service_module = types.ModuleType("storage_service")

    class Destination:
        def __init__(self, label, root, removable=False):
            self.label = label
            self.root = Path(root)
            self.removable = removable

    class StorageService:
        def list_destinations(self):
            return []

    storage_service_module.Destination = Destination
    storage_service_module.StorageService = StorageService

    with patch.dict(
        sys.modules,
        {
            "PyQt5": pyqt5_module,
            "PyQt5.QtCore": qtcore_module,
            "PyQt5.QtWidgets": qtwidgets_module,
            "capture_worker": capture_worker_module,
            "camera_service": camera_service_module,
            "storage_service": storage_service_module,
        },
    ):
        sys.modules.pop("main", None)
        return importlib.import_module("main")


class DummyButton:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, value):
        self.enabled = value


class DummyStatus:
    def __init__(self):
        self.text = ""
        self.style = ""

    def setText(self, value):
        self.text = value

    def setStyleSheet(self, value):
        self.style = value


class DummyWorker:
    def __init__(self):
        self.deleted = False

    def deleteLater(self):
        self.deleted = True


class DummyCamera:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1


class DummyEvent:
    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = _load_main_module()

    def _window(self):
        window = object.__new__(self.main.MainWindow)
        window._camera = DummyCamera()
        window._worker = None
        window._close_requested = False
        return window

    def test_close_event_closes_immediately_without_worker(self):
        window = self._window()
        event = DummyEvent()

        window.closeEvent(event)

        self.assertEqual(window._camera.closed, 1)
        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)

    def test_close_event_waits_for_capture_completion(self):
        window = self._window()
        window._worker = DummyWorker()
        window._capture_button = DummyButton()
        window._back_button = DummyButton()
        window._quit_button = DummyButton()
        window._status = DummyStatus()
        event = DummyEvent()

        window.closeEvent(event)

        self.assertTrue(window._close_requested)
        self.assertTrue(event.ignored)
        self.assertFalse(event.accepted)
        self.assertEqual(window._camera.closed, 0)
        self.assertFalse(window._capture_button.enabled)
        self.assertFalse(window._back_button.enabled)
        self.assertFalse(window._quit_button.enabled)
        self.assertIn("fermeture automatique", window._status.text)

    def test_worker_finished_closes_after_deferred_close_request(self):
        window = self._window()
        worker = DummyWorker()
        window._worker = worker
        window._capture_button = DummyButton()
        window._close_requested = True
        window.close_called = False

        def _close():
            window.close_called = True

        window.close = _close

        window._worker_finished()

        self.assertIsNone(window._worker)
        self.assertTrue(worker.deleted)
        self.assertTrue(window._capture_button.enabled)
        self.assertTrue(window.close_called)


if __name__ == "__main__":
    unittest.main()
