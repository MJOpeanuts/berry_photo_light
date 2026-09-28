#!/bin/sh
set -eu

APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DESKTOP_DIR=${XDG_DESKTOP_DIR:-"$HOME/Desktop"}
mkdir -p "$DESKTOP_DIR"

python3 - "$APP_DIR" "$DESKTOP_DIR/Berry Photo Light.desktop" <<'PYTHON'
import shlex
import sys
from pathlib import Path

app_dir, launcher = sys.argv[1:]
command = f"cd {shlex.quote(app_dir)} && exec ./run.sh"
# Desktop Entry Exec uses double quotes for a single argument; escape its metacharacters.
command = command.replace("\\", "\\\\").replace('"', '\"').replace("$", "\\$").replace("`", "\\`")
Path(launcher).write_text(
    "[Desktop Entry]\n"
    "Version=1.0\n"
    "Type=Application\n"
    "Name=Berry Photo Light\n"
    "Comment=Preview and capture HD photos\n"
    f'Exec=/bin/sh -c "{command}"\n'
    "Terminal=false\n"
    "Categories=Graphics;Photography;\n",
    encoding="utf-8",
)
PYTHON
chmod +x "$DESKTOP_DIR/Berry Photo Light.desktop"
printf 'Raccourci créé : %s\n' "$DESKTOP_DIR/Berry Photo Light.desktop"
printf 'Si nécessaire, faites un clic droit puis « Autoriser le lancement ».\n'
