# Security policy

## Supported versions

Only the latest tagged minor release receives security fixes during V1.

## Secrets and personal media

- Keep credentials in `.env.local`, a secret manager, or runtime environment.
- Never commit voice samples, avatar media, model weights, resolved local paths,
  outputs, or consent records containing personal details.
- Treat all downloaded models, fonts, music, stock media, and avatar inputs as
  untrusted until their source, checksum, and license are reviewed.
- Remote workers must use HTTPS and a rotated worker token. Do not expose Docker,
  PostgreSQL, Duix, or provider management ports directly to the internet.

## Avatar consent gate

An avatar-enabled profile is invalid without a `consent_manifest` reference.
The manifest remains outside the public repository. Consent must cover the
intended identity, voice, use, territory, and duration.

## Reporting

Report vulnerabilities privately through the GitHub repository security tab.
Do not include API keys, personal media, or production database exports.

