# Runtime modes

## CPU

Use for onboarding and machines without NVIDIA. Requires Git, Python 3.11, uv,
FFmpeg, and FFprobe for native execution, or Docker for the isolated profile.
Run `studio smoke --duration 20` before adding external providers.

## NVIDIA

Require both host `nvidia-smi` and a successful container GPU check. Use the
Compose NVIDIA override. Keep GPU workloads in a separate worker image; do not
install CUDA packages into the CPU/API image.

## Cloud

Use a single Ubuntu NVIDIA VM in V1. Bind the API to localhost unless TLS or a
private network is already configured. Workers connect outbound over HTTP(S);
do not expose PostgreSQL or Docker.

## Commands

```text
studio doctor --mode cpu|nvidia|cloud --json
studio init --workspace <absolute-path> --mode <mode>
studio resolve --workspace <absolute-path>
studio smoke --workspace <absolute-path> --duration 20
studio project create --title <title> --narration-file <file> --workspace <path>
studio run <project-spec.json> --workspace <path>
studio provider check moneyprinter|duix
```

