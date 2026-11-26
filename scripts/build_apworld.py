#!/usr/bin/env python3
"""Build oddworld_exoddus.apworld from apworld/oddworld_exoddus.

Usage: build_apworld.py [out_dir]       (default: build/)

An .apworld is a zip with the world's folder at its root. Tests and bytecode are left out.
"""
import os
import sys
import zipfile

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apworld", "oddworld_exoddus")
SKIP_DIRS = {"__pycache__", "test"}


def main(out_dir="build"):
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "oddworld_exoddus.apworld")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(SRC):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if name.endswith(".pyc"):
                    continue
                path = os.path.join(root, name)
                z.write(path, os.path.join("oddworld_exoddus", os.path.relpath(path, SRC)))
    print(f"{out}: {os.path.getsize(out)} bytes")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:])
