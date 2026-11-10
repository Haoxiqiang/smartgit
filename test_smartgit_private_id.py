"""Installer checks that do not launch SmartGit or require user namespaces."""

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import smartgit_private_id as private


class PrivateIdTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "config/smartgit-private"
        self.desktop = self.root / "data/applications/syntevo-smartgit.desktop"
        context = patch.object(Path, "home", return_value=self.root)
        context.start()
        self.addCleanup(context.stop)
        source = self.root / "system.desktop"
        source.write_text('[Desktop Entry]\nName=SmartGit\nExec="/original" %u\n')
        app = self.root / "smartgit.sh"
        app.touch()
        for name, value in (("SMARTGIT", app), ("SYSTEM_DESKTOP", source)):
            context = patch.object(private, name, value)
            context.start()
            self.addCleanup(context.stop)
        context = patch.object(private.shutil, "which", return_value="/usr/bin/bwrap")
        context.start()
        self.addCleanup(context.stop)
        context = patch.object(private.subprocess, "run")
        self.run = context.start()
        self.run.return_value.returncode = 0
        self.addCleanup(context.stop)

    def test_reinstall_and_restore_local_desktop(self):
        self.desktop.parent.mkdir(parents=True)
        self.desktop.write_text("existing user desktop\n")
        private.install(self.state, self.desktop, None)
        first_id = (self.state / "machine-id").read_bytes()
        self.assertRegex(first_id.decode(), r"^[0-9a-f]{32}\n$")
        self.assertEqual((self.state / "machine-id").stat().st_mode & 0o777, 0o600)
        private.install(self.state, self.desktop, None)
        self.assertEqual((self.state / "machine-id").read_bytes(), first_id)
        private.uninstall(self.state, self.desktop)
        self.assertEqual(self.desktop.read_text(), "existing user desktop\n")
        self.assertEqual((self.state / "machine-id").read_bytes(), first_id)

    def test_namespace_failure_leaves_configuration_unchanged(self):
        private.install(self.state, self.desktop, "1" * 32)
        previous = self.desktop.read_bytes()
        self.run.side_effect = subprocess.CalledProcessError(1, ["bwrap"])
        with self.assertRaises(subprocess.CalledProcessError):
            private.install(self.state, self.desktop, "2" * 32)
        self.assertEqual((self.state / "machine-id").read_text(), "1" * 32 + "\n")
        self.assertEqual(self.desktop.read_bytes(), previous)

    def test_invalid_id_writes_nothing(self):
        with self.assertRaises(ValueError):
            private.install(self.state, self.desktop, "invalid")
        self.assertFalse(self.state.exists())
        self.assertFalse(self.desktop.exists())

    def test_unmanaged_launcher_is_preserved(self):
        self.state.mkdir(parents=True)
        (self.state / "launch").write_text("unrelated launcher")
        with self.assertRaises(ValueError):
            private.install(self.state, self.desktop, None)
        self.assertEqual((self.state / "launch").read_text(), "unrelated launcher")

    def test_uninstall_without_previous_override(self):
        private.install(self.state, self.desktop, None)
        private.uninstall(self.state, self.desktop)
        self.assertFalse(self.desktop.exists())
        self.assertTrue((self.state / "machine-id").is_file())

    def legacy_desktops(self, command):
        entries = (self.desktop.parent / "smartgit-private.desktop",
                   self.root / "Desktop/SmartGit-Private.desktop")
        for entry in entries:
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text(f'[Desktop Entry]\nName=SmartGit (Private ID)\nExec="{command}" %u\n')
        return entries

    def test_install_removes_legacy_desktops_after_writing_override(self):
        entries = self.legacy_desktops(self.state / "launch")
        private.install(self.state, self.desktop, None)
        self.assertTrue(self.desktop.is_file())
        self.assertTrue((self.state / "launch").is_file())
        self.assertTrue(all(not entry.exists() for entry in entries))
        private.install(self.state, self.desktop, None)
        self.assertTrue(self.desktop.is_file())

    def test_install_preserves_unrelated_legacy_filenames(self):
        entries = self.legacy_desktops("/another/launcher")
        previous = [entry.read_bytes() for entry in entries]
        private.install(self.state, self.desktop, None)
        self.assertEqual([entry.read_bytes() for entry in entries], previous)

    def test_failed_install_preserves_legacy_desktops(self):
        entries = self.legacy_desktops(self.state / "launch")
        previous = [entry.read_bytes() for entry in entries]
        self.run.side_effect = subprocess.CalledProcessError(1, ["bwrap"])
        with self.assertRaises(subprocess.CalledProcessError):
            private.install(self.state, self.desktop, None)
        self.assertEqual([entry.read_bytes() for entry in entries], previous)


if __name__ == "__main__":
    unittest.main()
