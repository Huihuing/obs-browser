#!/usr/bin/env bash
set -euo pipefail

preset=${1:?pass the Studio CMakePresets.json path}
test_dir=$(cd -- "$(dirname -- "$0")" && pwd)
sudo apt-get update -qq
sudo apt-get install -y nlohmann-json3-dev xvfb xauth libnss3 libgbm1 libasound2t64
spec=$(jq -c '.configurePresets[] | select(.name == "dependencies") | .vendor["obsproject.com/obs-studio"].dependencies.cef' "$preset")
version=$(jq -r .version <<< "$spec")
revision=$(jq -r '.revision["ubuntu-x86_64"] // empty' <<< "$spec")
file="cef_binary_${version}_linux_x86_64${revision:+_v$revision}.tar.xz"
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
curl --fail --location --retry 2 "$(jq -r .baseUrl <<< "$spec")/$file" -o "$tmp/cef.tar.xz"
echo "$(jq -r '.hashes["ubuntu-x86_64"]' <<< "$spec")  $tmp/cef.tar.xz" | sha256sum --check
mkdir "$tmp/cef"
tar -xJf "$tmp/cef.tar.xz" --strip-components=1 -C "$tmp/cef"
xvfb-run -a python3 "$test_dir/run-linux.py" "$tmp/cef"
