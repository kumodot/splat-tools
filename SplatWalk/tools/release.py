#!/usr/bin/env python3
"""Cut a new SplatWalk build.

    python tools/release.py 0.5.1

Renames the single-file app, bumps the version everywhere it is written,
stamps the build time into it, archives the previous build and points the
Pages entry at the new one.

This exists because it was done by hand and went wrong: five separate sets of
changes all shipped stamped v0.5.0, so reloading the page could not tell you
whether you were looking at the newest code or at something from an hour ago.
A version is only useful if it moves every single time the file does.
"""
import io
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

SW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SW)
ARCHIVE = os.path.join(ROOT, "archive", "SplatWalk")


def read(p):
    with io.open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def current_build():
    names = [f for f in os.listdir(SW) if re.match(r"^SplatWalk_v[\d.]+\.html$", f)]
    if len(names) != 1:
        sys.exit("expected exactly one SplatWalk_v*.html in %s, found %d" % (SW, len(names)))
    name = names[0]
    return name, re.search(r"v([\d.]+)\.html$", name).group(1)


def main():
    if len(sys.argv) != 2 or not re.match(r"^\d+\.\d+\.\d+$", sys.argv[1]):
        sys.exit("usage: release.py <major.minor.patch>")
    new = sys.argv[1]
    name, old = current_build()
    if new == old:
        sys.exit("%s is already the current version" % new)

    src = os.path.join(SW, name)
    dst = os.path.join(SW, "SplatWalk_v%s.html" % new)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    text = read(src)
    n = text.count(old)
    text = text.replace(old, new)

    # A build stamp alongside the version, so even a forgotten bump leaves
    # something on screen that changes when the file does.
    if "const APP_BUILT" in text:
        text = re.sub(r'const APP_BUILT = "[^"]*";', 'const APP_BUILT = "%s";' % stamp, text)
    else:
        text = text.replace('const APP_VERSION = "%s";' % new,
                            'const APP_VERSION = "%s";\nconst APP_BUILT = "%s";' % (new, stamp))
    write(dst, text)
    os.remove(src)
    print("  app        %s -> %s  (%d version strings, built %s)" % (name, os.path.basename(dst), n, stamp))

    os.makedirs(ARCHIVE, exist_ok=True)
    # The archived copy keeps the version it shipped as, not the new one.
    write(os.path.join(ARCHIVE, name), read(dst).replace(new, old))
    print("  archived   %s" % os.path.join("archive", "SplatWalk", name))

    for rel in ["index.html", os.path.join("SplatWalk", "README.md")]:
        p = os.path.join(ROOT, rel)
        t = read(p)
        c = t.count(old)
        write(p, t.replace(old, new))
        print("  %-10s %d bumped" % (os.path.basename(rel), c))

    for test in ["syntax.mjs", "refs.mjs", "chain.mjs"]:
        r = subprocess.run(["node", os.path.join("test", test)], cwd=SW,
                           capture_output=True, text=True)
        tail = [l for l in r.stdout.strip().split("\n") if l.strip()][-1:]
        print("  %-10s %s" % (test, tail[0] if tail else "(no output)"))
        if r.returncode != 0:
            sys.exit("  %s FAILED, fix it before releasing" % test)

    print("\nv%s is ready. Remaining: commit it." % new)


if __name__ == "__main__":
    main()
