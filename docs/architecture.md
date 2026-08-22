# Architecture

## Control plane

FastAPI owns projects, runs, worker registration, leases, health endpoints, and
the compact HTML task view. PostgreSQL is the source of truth in Compose. The
native CLI can use SQLite for isolated development and direct project runs.

Workers connect outbound to the API, acquire a time-limited lease, execute a
project from its frozen profile, and report completion. A worker never requires
direct external access to PostgreSQL or Docker.

## Configuration

Configuration precedence is:

```text
built-in neutral defaults → workspace profile → project override → CLI override
```

The validated profile and runtime are serialized canonically and hashed. Every
project stores both the JSON and digest. Downstream artifacts are reusable only
when the relevant input and profile hashes remain unchanged.

## Artifact contract

Each artifact records URI, media type, byte length, SHA-256, and source stage.
The local implementation accepts only paths below the configured artifact root.
An S3-compatible implementation can preserve the same public contract.

## Pipeline invariants

- Narration master audio is the sole timing authority.
- Audio changes invalidate captions, motion, avatar, render, and delivery.
- Failed or stale upstream stages stop downstream work.
- Avatar synthesis reuses the approved narration master and must not create a
  second voice track.
- Delivery always includes manifest and QC; publishing requires human review.

## Provider isolation

MoneyPrinterTurbo and Duix run as external services. Creator IP Studio depends
only on their documented HTTP surface. Image tags or source commits must be
pinned by deployment owners; provider upgrades run contract tests before use.

