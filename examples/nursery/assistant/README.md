# Openclaude nursery assistant

This directory is the working directory for the openclaw nursery assistant. 

1. The brain: how clause code logs in 

- when you run openclaw onboard, select Anthropic as the provider
- If you have a claude subscription, run `claude setup-token` in the terminal. This generats a temporary security token you can paste into OpenClaw. 
- pay as you go: use the `sk-ant-...` API key from the anthroipc console. OpenClaw stores this in a restricted file at ~/.openclaw/openclaw.json

2. Security: protecting keys 

- sandboxing: during setup, enable docker sandboxing. It can only see files in `assistant/`. It definitely shouldn't be able to see `~/.ssh` etc. 

- However the key should be visible (openclaw.json), BUT it should be added to the `.clawdignore` file, just like `.gitignore`. Add `.env`, `*.key` and `config.json` to it. The AI should be "blind" to these files and unable to read or upload them. 

- In the `openclas.json`, set `"confirmation_required": true` for the `terminal` and `frappe_api` tools. The bot will have to ask: "I am about to create 10 batch records, proceed?". 

3. The "Plan for the Day" feature summary

To get a "what is the plan today" response you use the heartbeat and memory systems.

- Heartbeat logic: configure a heartbeat in `openclaw.json` to run eg on some schedule that is also testable (in a test this might be every 1m). 
- The routine: 1. the bot wakes up and runs a "Search" skill across the frappe db (eg `GET /api/resource/Nursery Batch?filters=[["status", "=", "Collected"]]`). 2. It compares those results against the Protocols in your `CONTEXT.md`. 3. IT summarizes the gaps (eg "10 specis from yesterday have no batch IDs"). 4. It sens the messages before the user even asks, as a digest and then breaks it down based on user response/reply. 

4. Testing

- Phase 1: Use `openclaw chat` and type "What is the plan today?" and watch it print the api calls its trying to make. Continue via a realisic scenario converstaion. OR start by ingesting a couple of species/collections and then proceeding to the plan. 

- Phase 2: Whatsapp. Once the terminal tests pass, run `openclas channels login --channel whatsapp`. Scane the wr code.

## Appendix 

* This assistant uses [openclaw](https://docs.openclaw.ai/install/docker) with a custom cli agent. 
