# Safety and privacy boundaries

- Secrets are runtime inputs. Never print, commit, or copy them into a project
  manifest, Skill, issue, log bundle, or generated lesson.
- Keep real voice, avatar, logo, customer content, model weights, and outputs out
  of the public repository.
- Reject artifact paths that escape the configured workspace.
- Require explicit confirmation before paid API calls, cloud allocation, social
  publishing, or downloads larger than 5 GB.
- An avatar-enabled profile is invalid without a consent-manifest reference.
- Report upstream provider failures at the adapter boundary. Do not silently
  replace the user's provider, voice, subject, or paid tier.
- For remote access, require TLS or a private tunnel and rotate worker tokens.

