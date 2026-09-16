#!/bin/sh
set -eu

release_wheel=https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/download/v0.4.0/geometric_function_atlas-0.4.0-py3-none-any.whl
package_spec=${GFA_PACKAGE_SPEC:-$release_wheel}
python_version=${GFA_PYTHON_VERSION:-3.12}
uv_install_dir=${UV_INSTALL_DIR:-"$HOME/.local/bin"}

if [ -t 1 ]; then
    bold='\033[1m'; cyan='\033[36m'; green='\033[32m'; muted='\033[2m'; reset='\033[0m'
else
    bold=''; cyan=''; green=''; muted=''; reset=''
fi

printf '%b\n' "${cyan}   ____  _____   _${reset}"
printf '%b\n' "${cyan}  / ___||  ___| / \\${reset}"
printf '%b\n' "${cyan} | |  _ | |_   / _ \\${reset}"
printf '%b\n' "${cyan} | |_| ||  _| / ___ \\${reset}"
printf '%b\n' "${cyan}  \\____||_|  /_/   \\_\\${reset}"
printf '%b\n\n' "${muted}Geometric Function Atlas installer${reset}"

step() { printf '%b\n' "${bold}[$1/4]${reset} $2"; }

step 1 "Install uv"
if command -v uv >/dev/null 2>&1; then
    uv_bin=$(command -v uv)
    printf '%b\n' "  ${green}ok${reset} uv is already installed"
else
    temp_dir=$(mktemp -d 2>/dev/null || mktemp -d -t gfa-install)
    trap 'rm -rf "$temp_dir"' EXIT HUP INT TERM
    installer="$temp_dir/uv-install.sh"
    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh -o "$installer"
    elif command -v wget >/dev/null 2>&1; then
        wget -q https://astral.sh/uv/install.sh -O "$installer"
    else
        printf '%s\n' "Error: curl or wget is required to download uv." >&2
        exit 1
    fi
    UV_INSTALL_DIR=$uv_install_dir UV_NO_MODIFY_PATH=1 sh "$installer"
    uv_bin="$uv_install_dir/uv"
fi

if [ ! -x "$uv_bin" ]; then
    printf '%s\n' "Error: uv was installed but could not be found." >&2
    exit 1
fi

step 2 "Install managed Python $python_version"
"$uv_bin" python install "$python_version"

step 3 "Install GFA CLI"
"$uv_bin" tool install --managed-python --python "$python_version" --force "$package_spec"
if ! "$uv_bin" tool update-shell >/dev/null 2>&1; then
    printf '%s\n' "PATH could not be updated automatically; open a new terminal after installation." >&2
fi

step 4 "Verify"
tool_bin=$("$uv_bin" tool dir --bin)
if [ ! -x "$tool_bin/gfa" ]; then
    printf '%s\n' "Error: gfa was installed but its executable was not found." >&2
    exit 1
fi
"$tool_bin/gfa" --version

printf '\n%b\n' "${green}${bold}GFA is ready.${reset}"
printf '%s\n' "Try: gfa walkthrough"
printf '%s\n' "Open a new terminal if gfa is not found in this one."
