"""Destination discovery and photo-file storage for Berry Photo Light."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Destination:
    """A writable destination presented to the operator."""

    label: str
    root: Path
    removable: bool = False


class StorageService:
    """Find destinations and create uniquely named, dated photo paths."""

    def __init__(self, local_root: Path | None = None) -> None:
        self.local_root = local_root or (Path.home() / "Pictures" / "BerryPhotoLight")

    def list_destinations(self) -> list[Destination]:
        destinations = [Destination("Disque local", self.local_root)]
        for mount_root in self._usb_mount_roots():
            try:
                mounts = sorted(path for path in mount_root.iterdir() if path.is_dir())
            except OSError:
                continue
            for mount in mounts:
                if not os.path.ismount(mount):
                    continue
                destinations.append(
                    Destination(f"Clé USB : {mount.name}", mount / "BerryPhotoLight", True)
                )
        return destinations

    @staticmethod
    def _usb_mount_roots() -> tuple[Path, ...]:
        username = os.environ.get("USER") or Path.home().name
        return (
            Path("/media") / username,
            Path("/run/media") / username,
        )

    @staticmethod
    def check_writable(destination: Destination) -> tuple[bool, str]:
        """Actually test write access, rather than relying only on permission bits."""
        try:
            destination.root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix=".berry-photo-light-check-",
                dir=destination.root,
                delete=True,
            ):
                pass
        except OSError as exc:
            return False, f"Destination indisponible ou non inscriptible : {exc}"
        return True, ""

    @staticmethod
    def new_photo_path(destination: Destination, now: datetime | None = None) -> Path:
        timestamp = now or datetime.now()
        day_folder = timestamp.strftime("%Y-%m-%d")
        filename = timestamp.strftime("photo_%Y%m%d_%H%M%S_%f.jpg")
        return destination.root / day_folder / filename
