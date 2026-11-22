#!/usr/bin/env python3
"""Build step_recorder.zip for upload to plugins.qgis.org / GitHub Releases.

Usage:  python3 scripts/build_zip.py
Checks metadata.txt for leftover placeholders, then zips only the plugin folder
(no tests, no __pycache__) with 'step_recorder/' as the single top-level folder.
"""
import configparser, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "step_recorder")

cp = configparser.ConfigParser(interpolation=None)
cp.read(os.path.join(PKG, "metadata.txt"), encoding="utf-8")
md = cp["general"]
problems = []
for key in ("author", "email", "homepage", "tracker", "repository"):
    v = md.get(key, "").strip()
    if not v or "YOUR" in v.upper() or v in ("Your Name", "your@email.com"):
        problems.append("metadata.txt: '%s' still needs a real value (%r)" % (key, v))
if problems:
    sys.exit("\n".join(problems) + "\n\nEdit step_recorder/metadata.txt and run again.")

out = os.path.join(ROOT, "step_recorder.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(PKG):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, ROOT))
print("Built %s (version %s)" % (out, md.get("version")))
