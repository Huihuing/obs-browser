"""Build and run the fork's BrowserApp against an extracted OBS Linux x86_64 CEF bundle."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Thread

FIXTURE = Path(__file__).resolve().parent
REPO = FIXTURE.parents[1]


def build(cef, destination):
    for directory in ("Release", "Resources"):
        for item in (cef / directory).iterdir():
            link = destination / item.name
            if not link.exists():
                link.symlink_to(item)
    exe = destination / "obs-browser-probe"
    subprocess.run([
        "g++", "-std=c++20", "-O1", "-DNDEBUG", "-DUSE_X11", "-I", str(REPO), "-I", str(cef),
        str(FIXTURE / "browser-probe.cpp"), str(REPO / "browser-app.cpp"),
        str(REPO / "browser-dummy-client.cpp"),
        str(cef / "build/libcef_dll_wrapper/libcef_dll_wrapper.a"),
        "-L", str(destination), "-lcef", "-Wl,-rpath,$ORIGIN", "-o", str(exe),
    ], check=True)
    return exe


def check_policy(exe, extension):
    option = f"--obs-browser-extension={extension}"
    other = extension.parent / "other extension"
    shutil.copytree(extension, other)
    cases = [
        ("default", [], "", ""),
        ("CLI directory", [option], "", str(extension)),
        ("missing manifest", [f"--obs-browser-extension={extension.parent}"], "", ""),
        ("relative directory", ["--obs-browser-extension=relative/path"], "", ""),
        ("explicit disable", [option, "--disable-extensions"], "", ""),
        ("raw loader", [f"--load-extension={extension}"], "", ""),
        ("raw exception", [f"--disable-extensions-except={extension}"], "", ""),
        ("saved directory", [], str(other), str(other)),
        ("missing saved directory", [], str(other / "missing"), ""),
        ("CLI overrides saved", [option], str(other), str(extension)),
        ("invalid CLI overrides saved", ["--obs-browser-extension=invalid"], str(other), ""),
        ("empty CLI overrides saved", ["--obs-browser-extension="], str(other), ""),
        ("explicit disable overrides saved", ["--disable-extensions"], str(other), ""),
    ]
    for name, flags, saved, allowed in cases:
        env = dict(os.environ, OBS_PROBE_SAVED_EXTENSION=saved)
        result = subprocess.check_output([exe, "--check-policy", *flags], env=env, text=True).strip()
        expected = f"disabled={int(not allowed)} allow={allowed} load="
        if result != expected:
            raise RuntimeError(f"{name}: expected {expected!r}, got {result!r}")
        print(f"Policy passed: {name}", flush=True)


def check_osr(exe, extension, profile):
    failures = []
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE / "site"))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/extension-smoke.html"
        env = dict(os.environ, OBS_PROBE_URL=url, OBS_PROBE_PROFILE=str(profile))
        option = f"--obs-browser-extension={extension}"
        for name, args, saved, enabled in [
            ("default", [], "", False), ("enabled", [option], "", True),
            ("explicit disable", [option, "--disable-extensions"], "", False),
            ("saved selection", [], str(extension), True),
            ("restart without selection", [], "", False),
        ]:
            run = subprocess.run(
                [exe, "--disable-gpu", *args], env=dict(env, OBS_PROBE_SAVED_EXTENSION=saved),
                text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=45,
            )
            match = re.search(r"^Content script: (yes|no) \| Worker: (yes|no) \| Network rule: (yes|no)$",
                              run.stdout, re.MULTILINE)
            if not match or run.returncode:
                failures.append(f"{name}: CEF exit {run.returncode}\n{run.stdout}")
                continue
            print(f"{name}: {match[0]}", flush=True)
            expected = ("yes", "yes", "yes") if enabled else ("no", "no", "no")
            if match.groups() != expected:
                failures.append(f"Unexpected result in {name}: {match[0]}")
        server.shutdown()
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cef_root", type=Path)
    parser.add_argument("--policy-only", action="store_true", help="test CEF command lines without a display")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        destination = Path(temp)
        extension = destination / "선택한 extension"
        shutil.copytree(FIXTURE / "extension", extension)
        executable = build(args.cef_root.resolve(), destination)
        check_policy(executable, extension)
        if not args.policy_only:
            check_osr(executable, extension, destination / "profile")
