#!/bin/sh
set -eu

package_spec=${GFA_PACKAGE_SPEC:-geometric-function-atlas}
python_version=${GFA_PYTHON_VERSION:-3.12}
uv_install_dir=${UV_INSTALL_DIR:-"$HOME/.local/bin"}

if command -v uv >/dev/null 2>&1; then
    uv_bin=$(command -v uv)
else
    installer=$(mktemp "${TMPDIR:-/tmp}/uv-install.XXXXXX")
    trap 'rm -f "$installer"' EXIT HUP INT TERM
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh -o "$installer"
    elif command -v wget >/dev/null 2>&1; then
        wget -q https://astral.sh/uv/install.sh -O "$installer"
    else
        printf '%s\n' "Geometric Function Atlas requires curl or wget for its one-time installer." >&2
        exit 1
    fi
    UV_INSTALL_DIR=$uv_install_dir UV_NO_MODIFY_PATH=1 sh "$installer"
    uv_bin="$uv_install_dir/uv"
fi

"$uv_bin" tool install --managed-python --python "$python_version" --force "$package_spec"
if ! "$uv_bin" tool update-shell; then
    printf '%s\n' "Could not update your shell PATH automatically; restart your terminal after installation." >&2
fi
tool_bin=$("$uv_bin" tool dir --bin)
"$tool_bin/gfa" --version
printf '%s\n' "Installation complete. Restart your terminal, then run: gfa --help"
