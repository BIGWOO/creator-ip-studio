# MiniMax H3 provider

Creator IP Studio integrates MiniMax H3 through a separately versioned ComfyUI
runtime. This keeps roughly 43-64 GB of model weights, CUDA packages, and custom
nodes outside the portable control-plane image.

## Presets

| Preset | Sampling | Purpose |
| --- | --- | --- |
| `draft` | Turbo LoRA 0.75, 4 steps, `er_sde` | Prompt and motion iteration |
| `quality` | FirstBlockCache Fast, 25 steps, `res_multistep` | Final scene generation |

Turbo and FirstBlockCache are intentionally not combined. The pinned RTX 3090
baseline produced a 512x288, 39-frame Turbo smoke clip in about 25 seconds and
an 864x480, 124-frame quality clip in about 183 seconds.

## Automated installation

Windows:

```powershell
./scripts/install-minimax-h3.ps1
# After explicit approval for the approximately 43 GB download:
./scripts/install-minimax-h3.ps1 -DownloadModels -Start
```

Linux/cloud:

```bash
./scripts/install-minimax-h3.sh
# After explicit approval for the approximately 43 GB download:
./scripts/install-minimax-h3.sh --download-models --start
```

The default `creator` pack contains FL2VA, both VAEs, the text encoder, and the
Turbo LoRA. Use `all` only when the Ref2VA modes are required.

## Health and smoke generation

```powershell
studio provider check minimax-h3
studio provider h3-generate `
  --prompt "A small red robot walks through a quiet studio, steady camera" `
  --preset draft `
  --width 512 --height 288 --frames 39 `
  --output ./h3-smoke.mp4
```

The adapter submits a pinned API workflow, polls `/history/{prompt_id}`, and
streams the resulting video through `/view` into the requested local path.

## Networking

The provider listens on `127.0.0.1:8188` by default. This is appropriate when
Creator IP Studio runs natively on the same host. A Docker worker cannot reach a
host service bound only to loopback; either run the worker natively or bind the
provider to a private interface and set `MINIMAX_H3_BASE_URL`. Never expose an
unauthenticated ComfyUI endpoint directly to the public internet.

## One-prompt student setup

```text
Install Creator IP Studio and its MiniMax H3 provider from:
https://github.com/BIGWOO/creator-ip-studio

Read README.md and docs/minimax-h3.md completely. Inspect GPU/VRAM, RAM, free
SSD space, NVIDIA driver, Git, Python, uv, and Docker if present. Require at
least 24 GB VRAM and 70 GB free space for the creator pack. Ask for approval
before downloading approximately 43 GB, changing firewall/system settings, or
using real-person media. Install the provider with the creator pack, keep it on
localhost, verify hashes and required ComfyUI nodes, then generate a synthetic
512x288, 39-frame Turbo draft smoke video. Return the exact versions, health
report, prompt ID, generation duration, and absolute output path.
```
