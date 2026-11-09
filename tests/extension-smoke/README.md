# Unpacked extensions in Browser Source

Open **Tools → Browser Extensions…** in the modified build. **Add extension folder…** registers a folder containing `manifest.json` and checks it. **Find in parent folder…** lists its immediate extension subfolders so you can check the ones you trust. Check the extensions you want to run, confirm the selection, and restart OBS. You can uncheck a folder to keep it in the list for later. Each enabled extension can access matching pages across Browser Sources and Browser Docks according to its permissions.

The command line can select a single folder for one launch, overriding the saved checklist. For example, on Windows

```powershell
cd "C:\Program Files\obs-studio\bin\64bit"
.\obs64.exe "--obs-browser-extension=C:\OBS Extensions\local-probe"
```

Without a launch override, OBS loads the checked folders. A folder that has disappeared is skipped. `--disable-extensions` always wins. A missing or invalid override disables extensions for that launch. Folder paths may contain spaces and Korean characters. Commas are reserved by Chromium. Browser Source uses off-screen rendering. The Chrome Web Store, CRX installer, toolbar, and popup UI are outside this loader's scope. Test the APIs your extension uses with this build.

## Local check

1. From this repository, run `python -m http.server 8021 --bind 127.0.0.1 --directory tests/extension-smoke/site`.
2. Create a Browser Source for `http://127.0.0.1:8021/extension-smoke.html`. Add the folders `tests/extension-smoke/extension` and `tests/extension-smoke/extension-b` to the extension list.
3. Check both folders, confirm, and restart OBS. The first extension provides the content script, worker reply, and network rule. The second extension supplies its own **Second** marker. All four indicators should show **yes**.
4. Uncheck just the first folder and restart. Only **Second** should show **yes**. Reverse the selection and restart to see just the first three indicators. Uncheck both and restart to see all four read **no**.


## Linux CEF integration test

With the Linux x86_64 CEF archive pinned in OBS Studio's CMakePresets.json extracted, install a C++20 compiler, nlohmann-json3-dev, libcef's normal Linux runtime dependencies, Xvfb, and xauth. Run from the browser plugin repository.

```sh
xvfb-run -a python3 tests/extension-smoke/run-linux.py "$CEF_ROOT_DIR"
```

The harness compiles the fork's BrowserApp and opens a windowless CEF browser with its global request context. It checks the same temporary profile across launches with both extensions enabled, either one alone, and neither, then checks both command-line overrides. Use `--policy-only` to run the command-line cases without a graphical session.
