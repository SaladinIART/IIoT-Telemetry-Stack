---
project_name: "NEXUS — IIoT-Telemetry-Stack"
owner: "Maintainer"
visibility_intent: "public"
security_mode: "public"
secret_storage_location: "Use central security-safe storage only"
rotation_policy: "public_secret"
notes: "Update this profile before repo visibility changes."
---

# Security Profile

This repo is protected by Security Safe.

## Operating rules

- Do not commit raw secrets.
- Use the central security-safe repo for secret generation and tracking.
- Keep `visibility_intent` current if the repo moves from private to public.
- Treat hook blocks as real security feedback.

