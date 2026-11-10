#!/usr/bin/env python3
"""Install a Linux SmartGit launcher with a stable, application-specific machine ID.

This remaps ID files only. It is not a general security sandbox: home, devices,
network, D-Bus and other hardware information remain accessible.
"""

import argparse
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile


MARKER = "# Managed by smartgit_private_id.py"
SMARTGIT = Path("/usr/share/smartgit/bin/smartgit.sh")
SYSTEM_DESKTOP = Path("/usr/share/applications/syntevo-smartgit.desktop")
LAUNCHER = r'''#!/bin/bash
# Managed by smartgit_private_id.py
set -euo pipefail
state_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
id_file="$state_dir/machine-id"
if [[ ! -f "$id_file" ]] || ! [[ $(cat -- "$id_file") =~ ^[0-9a-f]{32}$ ]]; then
  echo "Invalid private machine-id: $id_file" >&2
  exit 1
fi
mounts=(--bind / / --dev-bind /dev /dev --unshare-pid --proc /proc
        --ro-bind "$id_file" /etc/machine-id)
# Resolve host symlinks first; /var/lib/dbus/machine-id commonly aliases /etc.
for path in /var/lib/dbus/machine-id /etc/hostid; do
  if [[ -e "$path" ]]; then
    target="$(readlink -f -- "$path")"
    if [[ "$target" != /etc/machine-id ]]; then
      mounts+=(--ro-bind "$id_file" "$target")
    fi
  fi
done
case "${1:-}" in
  --check)
    shift
    set -- /bin/sh -c '
      for path in /etc/machine-id /var/lib/dbus/machine-id /etc/hostid; do
        if [ -e "$path" ]; then
          cmp -s "$1" "$path" || exit 1
        fi
      done
      echo "Private machine-id mapping verified"
    ' sh "$id_file"
    ;;
  --exec)
    shift
    if [[ $# == 0 ]]; then
      echo "--exec requires a command" >&2
      exit 1
    fi
    ;;
  *) set -- /usr/share/smartgit/bin/smartgit.sh "$@" ;;
esac
exec bwrap "${mounts[@]}" -- "$@"
'''


def paths():
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return (config / "smartgit-private",
            data / "applications/syntevo-smartgit.desktop")


def refresh_desktop(desktop):
    tool = shutil.which("update-desktop-database")
    if tool:
        result = subprocess.run([tool, str(desktop.parent)], capture_output=True)
        if result.returncode:
            print("Warning: desktop database refresh failed", file=sys.stderr)


def remove_legacy_desktops(desktop, launcher):
    candidates = (desktop.parent / "smartgit-private.desktop",
                  Path.home() / "Desktop/SmartGit-Private.desktop")
    expected_exec = f'Exec="{launcher}" %u'
    for legacy in candidates:
        try:
            if legacy.is_file() and expected_exec in legacy.read_text().splitlines():
                legacy.unlink()
                print(f"Removed legacy desktop entry: {legacy}")
        except (OSError, UnicodeError) as error:
            print(f"Warning: could not clean up {legacy}: {error}", file=sys.stderr)


def install(state, desktop, machine_id):
    if not shutil.which("bwrap"):
        raise ValueError("Install bubblewrap (bwrap) first")
    if not SMARTGIT.is_file() or not SYSTEM_DESKTOP.is_file():
        raise ValueError("Expected SmartGit installation under /usr/share/smartgit")
    launcher = state / "launch"
    backup = state / "original.desktop"
    # Refuse to replace unrelated files in our private installation directory.
    if launcher.exists() and MARKER not in launcher.read_text():
        raise ValueError(f"Unmanaged launcher already exists: {launcher}")
    current = desktop.read_text() if desktop.exists() else None
    if current is not None and MARKER not in current and backup.exists():
        raise ValueError("Desktop override changed; preserve it before reinstalling")
    id_file = state / "machine-id"
    value = machine_id or (id_file.read_text().strip() if id_file.exists()
                           else secrets.token_hex(16))
    if not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("machine-id must be 32 lowercase hexadecimal characters")
    # Desktop Exec quoting has two escaping layers. Reject unusual XDG paths
    # rather than producing an ambiguous launcher entry.
    if any(char in str(launcher) for char in '\\"`$%\n\r'):
        raise ValueError("Unsupported special character in configuration path")
    source = SYSTEM_DESKTOP.read_text()
    source, count = re.subn(r"^Exec=.*$", lambda _: f'Exec="{launcher}" %u',
                           source, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected exactly one Exec entry in SmartGit desktop file")
    # Probe in /tmp first so a denied namespace leaves the installation intact.
    with tempfile.TemporaryDirectory(prefix="smartgit-private-check-") as temporary:
        probe = Path(temporary)
        (probe / "machine-id").write_text(value + "\n")
        (probe / "launch").write_text(LAUNCHER)
        (probe / "launch").chmod(0o700)
        subprocess.run([str(probe / "launch"), "--check"], check=True)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Reinstall preserves the ID unless --machine-id explicitly replaces it.
    id_file.write_text(value + "\n")
    id_file.chmod(0o600)
    launcher.write_text(LAUNCHER)
    launcher.chmod(0o700)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    if current is not None and MARKER not in current:
        backup.write_text(current)
        backup.chmod(0o600)
    desktop.write_text(MARKER + "\n" + source)
    remove_legacy_desktops(desktop, launcher)
    refresh_desktop(desktop)
    print(f"Installed launcher: {launcher}")
    print(f"Private machine-id: {id_file}")
    print(f"Desktop override: {desktop}")
    print("Exit all running SmartGit instances, then start it from the application menu.")
    print("Existing machine-bound credentials may require reactivation.")


def uninstall(state, desktop):
    if desktop.exists():
        if MARKER not in desktop.read_text():
            raise ValueError("Desktop override is not managed by this script")
        backup = state / "original.desktop"
        if backup.exists():
            shutil.copyfile(backup, desktop)
            backup.unlink()
        else:
            desktop.unlink()
        refresh_desktop(desktop)
    # Retain the stable private ID and launcher for existing terminal workflows.
    print("Restored desktop launch behavior; private ID and launcher retained.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="Install or update the private launcher")
    setup.add_argument("--machine-id", help="Explicit fixed 32-character lowercase hex ID")
    commands.add_parser("check", help="Check mappings without launching SmartGit")
    commands.add_parser("uninstall", help="Restore the previous desktop entry")
    args = parser.parse_args()
    state, desktop = paths()
    try:
        if sys.platform != "linux":
            raise ValueError("Only Linux is supported")
        if not state.is_absolute() or not desktop.is_absolute():
            raise ValueError("XDG directories must be absolute")
        if args.command == "install":
            install(state, desktop, args.machine_id)
        elif args.command == "check":
            subprocess.run([str(state / "launch"), "--check"], check=True)
        else:
            uninstall(state, desktop)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
