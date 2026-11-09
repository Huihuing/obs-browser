# Unpacked extensions in Browser Source

Open **Tools → Browser Extension…** in the modified build, choose the folder of one trusted unpacked extension containing `manifest.json`, then restart OBS. To turn it off, reopen the menu, select **Disable extension**, and restart. The setting is local to this OBS configuration. The extension can access matching pages across Browser Sources and Browser Docks according to its permissions.

The command line can override the saved folder for one launch. For example, on Windows:

```powershell
cd "C:\Program Files\obs-studio\bin\64bit"
.\obs64.exe "--obs-browser-extension=C:\OBS Extensions\local-probe"
```

Without a launch override, OBS uses the folder saved in the menu. `--disable-extensions` always wins. A missing or invalid override disables extensions for that launch. Folder paths may contain spaces and Korean characters. Commas are reserved by Chromium. Browser Source uses off-screen rendering. The Chrome Web Store, CRX installer, toolbar, and popup UI are outside this loader's scope. Test the APIs your extension uses with this build.

## Local check

1. From this repository, run `python -m http.server 8021 --bind 127.0.0.1 --directory tests/extension-smoke/site`.
2. Launch OBS with the full path to `tests/extension-smoke/extension` and create a Browser Source for `http://127.0.0.1:8021/extension-smoke.html`.
3. The page reports content script execution, a reply from the MV3 service worker and a blocked network request independently. With the fixture loaded, all three indicators should read **yes**. Repeat after clearing the saved folder and restarting without the option. All three indicators should read **no**. The fixture only targets loopback.

## Linux CEF integration test

With the Linux x86_64 CEF archive pinned in OBS Studio's CMakePresets.json extracted, install a C++20 compiler, nlohmann-json3-dev, libcef's normal Linux runtime dependencies, Xvfb, and xauth. Run from the browser plugin repository.

```sh
xvfb-run -a python3 tests/extension-smoke/run-linux.py "$CEF_ROOT_DIR"
```

The harness compiles the actual BrowserApp, opens a windowless CEF browser using its global request context, and checks the same temporary profile across five launches. Both the menu-configured and CLI-selected launches must inject the content script, receive the service worker reply, and block the matching network request. The default, explicit-disable, and subsequent unselected launches must report all three inactive. Use `--policy-only` to run the command-line cases without a graphical session.
