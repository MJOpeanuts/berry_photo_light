import json
import os
import shlex
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parent.parent


class ShellScriptTests(unittest.TestCase):
    def test_scripts_are_executable(self):
        for name in ("run.sh", "install_desktop.sh"):
            path = REPO_ROOT / name
            self.assertTrue(path.exists())
            self.assertTrue(os.access(path, os.X_OK), f"{name} should be executable")

    def test_run_script_uses_python3_with_main_py(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app_dir = tmp_path / "app dir"
            app_dir.mkdir()
            shutil.copy2(REPO_ROOT / "run.sh", app_dir / "run.sh")
            (app_dir / "main.py").write_text("print('main')\n", encoding="utf-8")

            fake_bin = tmp_path / "bin"
            fake_bin.mkdir()
            argv_log = tmp_path / "argv.json"
            fake_python = fake_bin / "python3"
            fake_python.write_text(
                f"#!{sys.executable}\n"
                "import json\n"
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['ARGV_LOG']).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            env = os.environ.copy()
            env["ARGV_LOG"] = str(argv_log)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

            subprocess.run([str(app_dir / "run.sh"), "first", "second"], check=True, env=env)

            argv = json.loads(argv_log.read_text(encoding="utf-8"))
            self.assertEqual(argv, ["main.py", "first", "second"])

    def test_install_desktop_script_creates_launcher(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app_dir = tmp_path / "app dir"
            app_dir.mkdir()
            shutil.copy2(REPO_ROOT / "install_desktop.sh", app_dir / "install_desktop.sh")
            shutil.copy2(REPO_ROOT / "run.sh", app_dir / "run.sh")

            desktop_dir = tmp_path / "Desktop"
            env = os.environ.copy()
            env["HOME"] = str(tmp_path)
            env["XDG_DESKTOP_DIR"] = str(desktop_dir)

            subprocess.run([str(app_dir / "install_desktop.sh")], check=True, env=env)

            launcher = desktop_dir / "Berry Photo Light.desktop"
            self.assertTrue(launcher.exists())
            self.assertTrue(os.access(launcher, os.X_OK))

            self.assertEqual(
                launcher.read_text(encoding="utf-8"),
                "[Desktop Entry]\n"
                "Version=1.0\n"
                "Type=Application\n"
                "Name=Berry Photo Light\n"
                "Comment=Preview and capture HD photos\n"
                f'Exec=/bin/sh -c "cd {shlex.quote(str(app_dir))} && exec ./run.sh"\n'
                "Terminal=false\n"
                "Categories=Graphics;Photography;\n",
            )


if __name__ == "__main__":
    unittest.main()
