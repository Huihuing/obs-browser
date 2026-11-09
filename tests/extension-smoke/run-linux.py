"""Build and run the fork's BrowserApp against an extracted OBS Linux x86_64 CEF bundle."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
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


def check_policy(exe, first, second):
    option = f"--obs-browser-extension={first}"
    missing = str(Path(second) / "missing")
    cases = [
        ("default", [], [], []),
        ("CLI directory", [option], [], [first]),
        ("missing manifest", [f"--obs-browser-extension={Path(first).parent}"], [], []),
        ("relative directory", ["--obs-browser-extension=relative/path"], [], []),
        ("explicit disable", [option, "--disable-extensions"], [], []),
        ("raw loader", [f"--load-extension={first}"], [], []),
        ("raw exception", [f"--disable-extensions-except={first}"], [], []),
        ("two checked directories", [], [first, second], [first, second]),
        ("order and duplicates", [], [second, first, second], [second, first]),
        ("missing checked directory", [], [missing, first], [first]),
        ("no valid checked directory", [], [missing], []),
        ("CLI overrides checklist", [option], [second], [first]),
        ("invalid CLI overrides checklist", ["--obs-browser-extension=invalid"], [first, second], []),
        ("empty CLI overrides checklist", ["--obs-browser-extension="], [second], []),
        ("explicit disable overrides checklist", ["--disable-extensions"], [first, second], []),
        ("manual comma-separated override rejected", [f"{option},{second}"], [first], []),
    ]
    for name, flags, saved, allowed in cases:
        env = dict(os.environ, OBS_PROBE_SAVED_EXTENSIONS=json.dumps(saved))
        result = subprocess.check_output([exe, "--check-policy", *flags], env=env, text=True).strip()
        expected = f"disabled={int(not allowed)} allow={','.join(allowed)} load="
        if result != expected:
            raise RuntimeError(f"{name}: expected {expected!r}, got {result!r}")
        print(f"Policy passed: {name}", flush=True)


def check_osr(exe, first, second, profile):
    failures = []
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE / "site"))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/extension-smoke.html"
        env = dict(os.environ, OBS_PROBE_URL=url, OBS_PROBE_PROFILE=str(profile))
        option = f"--obs-browser-extension={first}"
        for name, args, saved, expect_first, expect_second in [
            ("fresh profile", [], [], False, False),
            ("both checked", [], [first, second], True, True),
            ("only first checked", [], [first], True, False),
            ("only second checked", [], [second], False, True),
            ("no boxes checked", [], [], False, False),
            ("CLI overrides checklist", [option], [second], True, False),
            ("explicit disable", ["--disable-extensions"], [first, second], False, False),
        ]:
            run = subprocess.run(
                [exe, "--disable-gpu", *args], env=dict(env, OBS_PROBE_SAVED_EXTENSIONS=json.dumps(saved)),
                text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=45,
            )
            match = re.search(r"^Content script: (yes|no) \| Worker: (yes|no) \| Network rule: (yes|no) \| Second: (yes|no)$",
                              run.stdout, re.MULTILINE)
            if not match or run.returncode:
                failures.append(f"{name}: CEF exit {run.returncode}\n{run.stdout}")
                continue
            print(f"{name}: {match[0]}", flush=True)
            expected = ("yes" if expect_first else "no",) * 3 + ("yes" if expect_second else "no",)
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
        first = shutil.copytree(FIXTURE / "extension", destination / "첫 번째 확장").as_posix()
        second = shutil.copytree(FIXTURE / "extension-b", destination / "두 번째 확장").as_posix()
        executable = build(args.cef_root.resolve(), destination)
        check_policy(executable, first, second)
        if not args.policy_only:
            check_osr(executable, first, second, destination / "profile")
