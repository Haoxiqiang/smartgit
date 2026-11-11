#!/usr/bin/env python3
"""Repair the desktop launcher and verify the actual SmartGit JVM."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import smartgit_private_id as private


def smartgit_processes(proc=Path("/proc")):
    """Only select this user's JVM running this installation's bootloader."""
    jar = str(private.SMARTGIT.parent.parent / "lib/bootloader.jar")
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            args = (entry / "cmdline").read_bytes().split(b"\0")
            if any(args[i:i + 2] == [b"-jar", os.fsencode(jar)]
                   for i in range(len(args) - 1)):
                found.append(entry)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as error:
            raise ValueError(f"Cannot inspect process {entry.name}: {error}") from error
    return found


def runtime_matches(process, state):
    expected = (state / "machine-id").read_bytes().strip()
    if not re.fullmatch(rb"[0-9a-f]{32}", expected):
        raise ValueError("Invalid installed private machine-id")
    # Read the canonical mount target. Following an absolute dbus symlink from
    # /proc/PID/root would otherwise resolve against the inspector's own root.
    for name in ("etc/machine-id",):
        path = process / "root" / name
        try:
            if path.read_bytes().strip() != expected:
                return False
        except FileNotFoundError:
            if name == "etc/machine-id":
                raise ValueError(f"PID {process.name}: runtime ID is unavailable")
    return True


def verify_processes(processes, state):
    for process in processes:
        if not runtime_matches(process, state):
            raise ValueError(f"PID {process.name} is using another machine ID. "
                             "Exit SmartGit normally, then rerun ./repair-smartgit.sh")
        print(f"PID {process.name}: actual SmartGit runtime mapping verified")


def repair(check_only=False, timeout=20):
    state, desktop = private.paths()
    if not state.is_absolute() or not desktop.is_absolute():
        raise ValueError("XDG directories must be absolute")
    if check_only:
        processes = smartgit_processes()
        if not processes:
            raise ValueError("No running SmartGit JVM found; runtime not verified")
        verify_processes(processes, state)
        return
    private.install(state, desktop, None)
    processes = smartgit_processes()
    if processes:
        verify_processes(processes, state)
        return
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise ValueError("Desktop repaired; rerun inside your graphical session to launch")
    # Launch this exact desktop file rather than relying on shell cache or PATH.
    gio = private.shutil.which("gio")
    if not gio:
        raise ValueError("Desktop repaired; gio is required to verify desktop launch")
    log_path = state / "startup.log"
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as log:
        os.fchmod(log.fileno(), 0o600)
        subprocess.run([gio, "launch", str(desktop)], stdout=log,
                       stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                       start_new_session=True, check=True, timeout=10)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        processes = smartgit_processes()
        if processes:
            verify_processes(processes, state)
            time.sleep(3)
            processes = smartgit_processes()
            if not processes:
                raise ValueError(f"SmartGit exited during startup. See {log_path}")
            verify_processes(processes, state)
            print(f"Desktop launch verified: {desktop}")
            return
        time.sleep(0.5)
    raise ValueError(f"Desktop repaired, but no SmartGit JVM appeared. See {log_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify running JVM only")
    args = parser.parse_args()
    try:
        repair(args.check)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
