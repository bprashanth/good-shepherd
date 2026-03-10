# OpenClaw Nursery Assistant

This directory contains the Nursery Assistant configuration for OpenClaw.

## What Works Right Now

The reliable path is:
1. Docker setup
2. Codex provider configuration
3. Telegram channel enable + pairing
4. Run the TUI

WhatsApp is currently not working in this setup.

## Docker Setup

From this directory:

```console
docker compose build
docker compose up -d
```

Useful commands:

```console
docker compose ps
docker compose logs -f openclaw-gateway
docker compose restart openclaw-gateway
```

## Codex Configuration

Configure provider credentials in OpenClaw during onboarding.

Options:
- Subscription flow: run `setup-token` and paste the temporary token into OpenClaw. 
- API key flow: use your provider API key and store it via OpenClaw config.

From [docs](https://docs.openclaw.ai/install/docker)
```
If you pick OpenAI Codex OAuth in the wizard, it opens a browser URL and tries to capture a callback on http://127.0.0.1:1455/auth/callback. In Docker or headless setups that callback can show a browser error. Copy the full redirect URL you land on and paste it back into the wizard to finish auth.
```

## Security Considerations

- Enable Docker sandboxing during setup so the agent is limited to `assistant/` and cannot access sensitive paths like `~/.ssh`.
- Keep credentials in `openclaw.json`, but block secret files from agent access via `.clawdignore` (at minimum: `.env`, `*.key`, `config.json`).
- In `openclaw.json`, set `"confirmation_required": true` for `terminal` and `frappe_api` so write actions always require explicit approval.

## Telegram Setup (Verified)

Run these commands exactly:

```console
docker compose run --rm openclaw-cli plugins enable telegram
```

Expected result includes: `Enabled plugin "telegram". Restart the gateway to apply.`

```console
docker compose run --rm openclaw-cli channels add --channel telegram --token <token>
```

Expected result includes: `Added Telegram account "default".`

```console
docker compose run --rm openclaw-cli pairing approve telegram <pairing code from telegram>
```

Then run the TUI:

```console
docker compose exec -it openclaw-gateway node dist/index.js tui
```

## Adding Packages

Quick steps:
- Add package names to `OPENCLAW_DOCKER_APT_PACKAGES` in `.env`.
- Rebuild and restart: `docker compose down && docker compose build && docker compose up -d`.
- Verify import: `docker compose exec openclaw-gateway python3 -c "import <module>"`.

See [docs/PACKAGES.md](docs/PACKAGES.md) for full details.

## Heartbeat Plan Routine

- Configure a heartbeat schedule in `openclaw.json` (use a short interval like every 1 minute for testing).
- On each run, the assistant searches Frappe (for example, collected batches), compares results with protocol rules in `CONTEXT.md`, summarizes gaps, and sends a digest proactively.
- Follow-up responses should break the digest into actionable next steps based on user replies.

## Notes

- If plugin or channel changes do not appear, restart gateway:

```console
docker compose restart openclaw-gateway
```

- Keep assistant behavior and API constraints in `SKILL.md` and `CONTEXT.md`.
