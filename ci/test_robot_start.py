"""Regression tests for startup manifest synchronization (no ROS/pixi required)."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


START_SCRIPT = Path(__file__).resolve().parents[1] / "debian/genbu-robot-start"


class RobotStartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.workspace = self.root / "workspace"
        self.config.mkdir()
        self.workspace.mkdir()
        for name in ("pixi.toml", "pixi.lock"):
            (self.config / name).write_text(f"configured {name}\n")
        self.args = self.root / "args"
        self.bash_env = self.root / "bash_env"
        self.bash_env.write_text(
            'source() { [[ "$1" == /etc/ros/setup.bash ]]; }\n'
            'exec() { printf "%s\\n" "$@" > "$GENBU_TEST_ARGS"; }\n'
        )

    def start(self, workspace=None):
        return subprocess.run(
            ["bash", str(START_SCRIPT)],
            env={
                **os.environ,
                "BASH_ENV": str(self.bash_env),
                "GENBU_PIXI_SRC": str(self.config),
                "GENBU_PIXI_DIR": str(workspace or self.workspace),
                "GENBU_PIXI_ENV": "robot",
                "GENBU_TEST_ARGS": str(self.args),
            },
            capture_output=True,
            text=True,
        )

    def assert_independent_copies(self):
        for name in ("pixi.toml", "pixi.lock"):
            source = self.config / name
            target = self.workspace / name
            self.assertFalse(target.is_symlink())
            self.assertFalse(source.samefile(target))
            self.assertEqual(source.read_text(), target.read_text())

    def test_legacy_links_are_replaced_even_when_source_is_older(self):
        for kind in ("symlink", "hardlink", "dangling"):
            with self.subTest(kind=kind):
                for name in ("pixi.toml", "pixi.lock"):
                    source = self.config / name
                    target = self.workspace / name
                    target.unlink(missing_ok=True)
                    os.utime(source, (1, 1))
                    if kind == "hardlink":
                        target.hardlink_to(source)
                    else:
                        target.symlink_to(
                            source if kind == "symlink" else self.root / "missing"
                        )
                result = self.start()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_independent_copies()

    def test_first_start_and_repeated_start(self):
        for _ in range(2):
            result = self.start()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_independent_copies()
        self.assertEqual(
            self.args.read_text().splitlines(),
            [
                "/usr/local/bin/pixi", "run", "--manifest-path",
                str(self.workspace / "pixi.toml"), "-e", "robot",
                "/bin/bash", "-euo", "pipefail", "-c",
                "set +u; source /etc/ros/setup.bash; set -u; "
                "exec ros2 launch genbu_bringup robot.launch.xml",
            ],
        )

    def test_regular_files_keep_timestamp_update_behavior(self):
        for source_newer in (False, True):
            with self.subTest(source_newer=source_newer):
                for name in ("pixi.toml", "pixi.lock"):
                    (self.workspace / name).write_text("workspace version\n")
                    os.utime(self.workspace / name, (100, 100))
                    os.utime(self.config / name, (200, 200) if source_newer else (1, 1))
                result = self.start()
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in ("pixi.toml", "pixi.lock"):
                    expected = (
                        (self.config / name).read_text()
                        if source_newer else "workspace version\n"
                    )
                    self.assertEqual((self.workspace / name).read_text(), expected)

    def test_same_directory_is_rejected_without_changing_config(self):
        alias = self.root / "alias"
        alias.symlink_to(self.config, target_is_directory=True)
        for workspace in (self.config, alias):
            with self.subTest(workspace=workspace):
                result = self.start(workspace)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("must be separate directories", result.stderr)
                self.assertFalse(self.args.exists())
                self.assertEqual(
                    (self.config / "pixi.toml").read_text(), "configured pixi.toml\n"
                )

    def test_setup_script_may_reference_unset_variables(self):
        self.bash_env.write_text(
            'source() { [[ "$1" == /etc/ros/setup.bash ]] && '
            '[ -n "$COLCON_TRACE_UNSET_FOR_TEST" ] || true; }\n'
            'exec() { [[ $- == *u* ]] && '
            'printf "%s\\n" "$@" > "$GENBU_TEST_ARGS"; }\n'
        )
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.args.exists())

    def test_copy_failure_prevents_launch(self):
        result = self.start(self.root / "missing-workspace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cp:", result.stderr)
        self.assertFalse(self.args.exists())


if __name__ == "__main__":
    unittest.main()
