---
name: creator-ip-studio
description: Inspect, bootstrap, run, resume, and troubleshoot Creator IP Studio video-production workspaces on Windows, Linux, macOS, or a single cloud GPU VM. Use for repeatable narrated-video, caption, render, QC, delivery, MoneyPrinterTurbo adapter, or optional Duix avatar workflows.
---

# Creator IP Studio

Use the repository scripts and `studio` CLI as the source of operational truth.
Do not reproduce installation logic in a prompt or write personal configuration
back into the public plugin.

## Workflow

1. Locate the repository root three directories above this file and read its
   `README.md` before the first installation or upgrade.
2. Run `studio doctor --json` before changing the machine. Select `cpu` unless a
   working NVIDIA device is detected; select `cloud` only for a remote Linux VM.
3. Initialize a neutral external workspace with `studio init`. Existing profiles
   and runtime files must not be overwritten.
4. Resolve and freeze the selected profile before production.
5. For a fresh setup, run the no-key 20-second smoke test and return the health
   report, video, QC, and manifest paths.
6. On failure, resume from the failed stage or rerun only the invalidated stages.

## Approval gates

Pause immediately before system-level installation, administrative elevation,
driver or WSL changes, downloads larger than 5 GB, paid services, credential
entry, cloud resource creation, publication, or processing a real person's image
or voice. Explain the exact action, expected disk/network/cost impact, and how to
reverse it.

Avatar work requires a consent manifest and an explicit provider choice. Duix is
optional and must remain a separate service; never bundle or redistribute its
model weights. V1 produces publishing assets but does not upload them.

## Routing

- For mode selection, prerequisites, and commands, read
  [references/modes.md](references/modes.md).
- Before remote workers, credentials, personal media, or Duix, read
  [references/safety.md](references/safety.md).

