# Native approval dialog regression (Linux)

This probe loads the built browser plugin into its matching libobs and operates its real Qt review dialog. It checks the displayed code, initial keyboard focus, Return-to-cancel behavior, and the pending request produced by an explicit Yes. The host defers CEF startup, so rendering and script injection require a separate Browser Source test.

Build the fork's Linux OBS and browser plugin first. Set `OBS_SRC` and `OBS_BUILD` to the absolute paths of the OBS source and CMake build tree. From the browser repository, with Qt 6 Widgets development files, Xvfb, and xauth installed, run the following.

```sh
cmake -S tests/custom-javascript/native -B build-review \
  -Dlibobs_DIR="$OBS_BUILD/libobs" -DCMAKE_MODULE_PATH="$OBS_SRC/cmake/finders"
cmake --build build-review
QT_QPA_PLATFORM=offscreen xvfb-run -a build-review/review-test \
  "$OBS_BUILD/plugins/obs-browser/obs-browser.so" "$OBS_SRC/plugins/obs-browser/data"
```
