from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import smartgit_repair as repair


class RepairTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        (self.state / "machine-id").write_text("a" * 32 + "\n")

    def process(self, pid, args):
        proc = self.root / str(pid)
        proc.mkdir()
        (proc / "cmdline").write_bytes(b"\0".join(os.fsencode(a) for a in args))
        return proc

    def test_selects_exact_jar_argument_only(self):
        self.process(10, ["java", "-jar", "/usr/share/smartgit/lib/bootloader.jar"])
        self.process(11, ["bash", "-c", "java -jar /usr/share/smartgit/lib/bootloader.jar"])
        self.process(12, ["java", "-jar", "/other/bootloader.jar"])
        self.assertEqual([p.name for p in repair.smartgit_processes(self.root)], ["10"])

    def test_runtime_match_mismatch_and_missing(self):
        process = self.root / "20"
        target = process / "root/etc/machine-id"
        target.parent.mkdir(parents=True)
        target.write_text("a" * 32 + "\n")
        self.assertTrue(repair.runtime_matches(process, self.state))
        target.write_text("b" * 32 + "\n")
        self.assertFalse(repair.runtime_matches(process, self.state))
        target.unlink()
        with self.assertRaises(ValueError):
            repair.runtime_matches(process, self.state)

    def test_runtime_permission_denied_is_not_success(self):
        with patch.object(Path, "read_bytes", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                repair.runtime_matches(self.root / "20", self.state)

    def test_existing_mismatch_prevents_launch(self):
        with patch.object(repair.private, "paths", return_value=(self.state, self.root / "app.desktop")), \
             patch.object(repair.private, "install"), \
             patch.object(repair, "smartgit_processes", return_value=[self.root / "20"]), \
             patch.object(repair, "runtime_matches", return_value=False), \
             patch.object(repair.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                repair.repair()
            run.assert_not_called()

    def test_check_without_runtime_does_not_install(self):
        with patch.object(repair.private, "install") as install, \
             patch.object(repair, "smartgit_processes", return_value=[]):
            with self.assertRaises(ValueError):
                repair.repair(check_only=True)
            install.assert_not_called()


if __name__ == "__main__":
    unittest.main()
