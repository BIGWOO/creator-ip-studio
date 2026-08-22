# Generic Ubuntu NVIDIA VM

## Host requirements

- Ubuntu 22.04 or 24.04
- Docker Engine and Compose plugin
- NVIDIA driver and NVIDIA Container Toolkit
- At least 100 GB free disk when enabling Duix
- HTTPS, firewall, and SSH access under the operator's control

## Deployment

Clone the repository, create `.env` from `.env.example`, replace
`CREATOR_IP_WORKER_TOKEN`, set durable host paths, then run:

```bash
docker compose \
  -f compose.yaml \
  -f compose.nvidia.yaml \
  -f deploy/cloud/compose.cloud.yaml \
  up -d --build
```

The cloud override removes localhost-only API binding. Put a TLS reverse proxy,
VPN, or SSH tunnel in front of the API before granting external access. Never
publish ports 5432, 8383, or the Docker socket.

Validate with:

```bash
docker compose exec api studio doctor --mode nvidia --json
docker compose exec api studio smoke --workspace /workspace --duration 20
```

For an S3-compatible artifact store, provision a private bucket and inject
credentials through the runtime secret manager. V1 ships the URI contract but
uses local volumes by default.

