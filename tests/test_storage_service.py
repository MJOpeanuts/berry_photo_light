from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from storage_service import Destination, StorageService


class StorageServiceTests(unittest.TestCase):
    def test_local_destination_is_writable(self):
        with TemporaryDirectory() as tmp:
            destination = Destination("local", Path(tmp) / "photos")
            ok, message = StorageService.check_writable(destination)
            self.assertTrue(ok, message)
            self.assertTrue(destination.root.is_dir())

    def test_photo_path_is_dated_and_unique_to_microseconds(self):
        destination = Destination("local", Path("/photos"))
        timestamp = datetime(2026, 9, 28, 10, 15, 41, 123456)
        path = StorageService.new_photo_path(destination, timestamp)
        self.assertEqual(path, Path("/photos/2026-09-28/photo_20260928_101541_123456.jpg"))


if __name__ == "__main__":
    unittest.main()
