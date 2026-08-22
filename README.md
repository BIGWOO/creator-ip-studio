# Creator IP Studio

Creator IP Studio is a portable, resumable production line for narrated videos,
captions, visual composition, optional avatar lip-sync, quality checks, and
delivery packages. The public core remains neutral; personal identity and media
stay in an external workspace or private overlay repository.

## Current V1 capabilities

- Cross-platform `studio` CLI and FastAPI control plane
- Versioned Pydantic/JSON contracts and frozen profile hashes
- PostgreSQL-backed worker registration and expiring job leases
- Local `file://` artifact store with traversal protection and SHA-256 manifests
- No-key FFmpeg smoke video with audio, captions, cover, QC, and delivery manifest
- Optional HTTP adapters for MiniMax H3, MoneyPrinterTurbo, and Duix.Avatar
- CPU and NVIDIA Docker Compose profiles
- Codex Skill and plugin manifest

MoneyPrinterTurbo and Duix are not bundled. Their adapters preserve dependency,
CUDA, model, and licensing isolation.

MiniMax H3 is also installed as an isolated ComfyUI service. See
[MiniMax H3 provider](docs/minimax-h3.md) for the reproducible Windows/Linux
installer, model packs, smoke command, and one-prompt student setup.

## Local paths

The recommended Windows layout is:

```text
F:\CreatorIP\
├─ repos\creator-ip-studio
├─ repos\bigwoo-ip-studio
├─ repos\creator-ip-course
├─ workspace
├─ assets
├─ models
├─ cache
├─ deliveries
└─ runtime
```

Do not commit `.creator-ip/runtime.local.yaml`, `.env`, model weights, voice
samples, avatar media, generated videos, or machine-specific resolved profiles.

## Quick start

### Native Python

Requirements: Git, Python 3.11, uv, FFmpeg, and FFprobe.

```powershell
./scripts/bootstrap.ps1 -Mode cpu
./studio.ps1 init --workspace F:\CreatorIP\workspace
./studio.ps1 smoke --workspace F:\CreatorIP\workspace --duration 20
```

### Docker

```powershell
$env:CREATOR_IP_HOST_WORKSPACE='F:\CreatorIP\workspace'
docker compose up -d --build db api worker-cpu
```

Open <http://127.0.0.1:8080> for the compact task view or
<http://127.0.0.1:8080/docs> for the API.

For an NVIDIA worker:

```powershell
$env:CREATOR_IP_HOST_MODELS='F:\CreatorIP\models'
docker compose -f compose.yaml -f compose.nvidia.yaml up -d --build
```

## One-prompt installation

Give an agent this prompt:

```text
Install and use Creator IP Studio from:
https://github.com/BIGWOO/creator-ip-studio

Read README.md and the creator-ip-studio SKILL.md completely. Run doctor,
select CPU or NVIDIA mode from detected hardware, initialize a neutral external
workspace, and run the no-key smoke test. Ask before administrative changes,
large downloads, paid providers, credentials, or processing a real person's
image or voice. Return the health report and generated test-video path.
```

## Project workflow

```powershell
./studio.ps1 project create `
  --title "My episode" `
  --narration-file F:\CreatorIP\workspace\narration.txt `
  --workspace F:\CreatorIP\workspace

./studio.ps1 run `
  F:\CreatorIP\workspace\.creator-ip\projects\my-episode.json `
  --workspace F:\CreatorIP\workspace
```

The resulting project contains frozen configuration, per-stage manifests,
audio, captions, renders, QC, and a delivery package.

## Provider boundaries

- MoneyPrinterTurbo is called as an optional external HTTP service. Start and
  version it separately, then run `studio provider check moneyprinter`.
- Duix.Avatar is a large optional GPU service. Install it only after reviewing
  its model terms and recording the subject's consent. Run
  `studio provider check duix` before submitting any media.
- MiniMax H3 uses a pinned external ComfyUI runtime. Run
  `studio provider check minimax-h3` and use `provider h3-generate` for draft or
  quality scene generation. Its default model download is approximately 43 GB.
- No social network upload is performed by V1. Delivery metadata is marked
  `requires-human-review`.

See [architecture](docs/architecture.md), [cloud deployment](docs/cloud.md),
and [security](SECURITY.md) for operational details.

## Development

```powershell
uv sync --extra dev --extra tts
uv run ruff check .
uv run pytest
docker build -t creator-ip-studio:test .
```

This project is licensed under Apache-2.0. Third-party integrations retain their
own licenses and model terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
