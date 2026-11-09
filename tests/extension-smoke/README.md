# Unpacked extensions in Browser Source

The fork supports an experimental startup option with its pinned Chromium 150 CEF. Fully exit OBS, then launch the modified build with an absolute path to a trusted unpacked extension folder containing `manifest.json`. The path can include spaces or Korean characters. Commas separate directories in Chromium and are rejected here. A scene cannot turn the option on. One selected extension can act on any matching URL in the OBS browser profile.

```powershell
cd "C:\Program Files\obs-studio\bin\64bit"
.\obs64.exe "--obs-browser-extension=C:\OBS Extensions\local-probe"
```

Close OBS and restart without that option to disable the extension. The `--disable-extensions` switch takes precedence. Browser Source uses off-screen rendering. The Chrome Web Store, CRX installer, toolbar, and popup UI are outside this loader's scope. Test the APIs your extension uses with this build.

## Local check

1. From this repository, run `python -m http.server 8021 --bind 127.0.0.1 --directory tests/extension-smoke/site`.
2. Launch OBS with the full path to `tests/extension-smoke/extension` and create a Browser Source for `http://127.0.0.1:8021/extension-smoke.html`.
3. The page reports content script execution, a reply from the MV3 service worker and a blocked network request independently. A working network rule displays **Network rule: yes**. Repeat after restarting without the option. All three indicators should read **no**. The fixture only targets loopback.

## Linux CEF integration test

With the Linux x86_64 CEF archive pinned in OBS Studio's CMakePresets.json extracted, install a C++20 compiler, nlohmann-json3-dev, libcef's normal Linux runtime dependencies, Xvfb, and xauth. Run from the browser plugin repository.

```sh
xvfb-run -a python3 tests/extension-smoke/run-linux.py "$CEF_ROOT_DIR"
```

The harness compiles the actual BrowserApp, opens a windowless CEF browser using its global request context, and checks the same temporary profile across four launches. The test requires the network rule to block the probe only while explicitly selected. It reports content-script and worker results separately because Alloy support varies by capability. Use `--policy-only` to run the command-line cases without a graphical session.
