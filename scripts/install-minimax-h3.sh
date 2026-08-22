#!/usr/bin/env bash
set -euo pipefail

script_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install_root="${MINIMAX_H3_INSTALL_ROOT:-$(dirname "$script_root")/comfyui-minimax-h3-provider}"
pack="creator"
download_models=false
start=false
skip_hashes=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-root) install_root="$2"; shift 2 ;;
    --pack) pack="$2"; shift 2 ;;
    --download-models) download_models=true; shift ;;
    --start) start=true; shift ;;
    --skip-hashes) skip_hashes=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ "$pack" =~ ^(creator|all)$ ]] || { echo "Pack must be creator or all" >&2; exit 2; }
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v uv >/dev/null || { echo "uv is required" >&2; exit 1; }
command -v nvidia-smi >/dev/null || { echo "An NVIDIA driver and GPU are required" >&2; exit 1; }

repository="https://github.com/BIGWOO/comfyui-minimax-h3-provider.git"
if [[ ! -d "$install_root/.git" ]]; then
  mkdir -p "$(dirname "$install_root")"
  git clone --filter=blob:none "$repository" "$install_root"
else
  origin="$(git -C "$install_root" remote get-url origin)"
  [[ "$origin" == "$repository" || "$origin" == "${repository%.git}" ]] || {
    echo "Existing directory has an unexpected origin: $origin" >&2
    exit 1
  }
  git -C "$install_root" pull --ff-only
fi

chmod +x "$install_root"/scripts/*.sh
"$install_root/scripts/setup.sh"
if [[ "$download_models" == true ]]; then
  args=(--pack "$pack")
  [[ "$skip_hashes" == true ]] && args+=(--skip-hash)
  "$install_root/scripts/download-models.sh" "${args[@]}"
fi
if [[ "$start" == true ]]; then
  "$install_root/scripts/start.sh" --profile main --background
fi
printf '{"provider_root":"%s","pack":"%s","models_requested":%s,"started":%s,"url":"http://127.0.0.1:8188"}\n' \
  "$install_root" "$pack" "$download_models" "$start"
