<p align="center">
  <img src="assets/nanoclaw-logo.png" alt="Rohlik Claw" width="400">
</p>

<p align="center">
  A personal AI grocery assistant for <a href="https://www.rohlik.cz">Rohlik.cz</a>, built on <a href="https://github.com/qwibitai/nanoclaw">NanoClaw</a>.
</p>

> [!WARNING]
> This project is based on the unofficial [rohlik-mcp](https://github.com/tomaspavlin/rohlik-mcp) server, which uses a reverse-engineered Rohlik API. It is for personal use only.

---

## What Is This

Rohlik Claw is a customized [NanoClaw](https://github.com/qwibitai/nanoclaw) instance that turns Claude into a personal grocery shopping assistant. It connects to [Rohlik.cz](https://www.rohlik.cz) via the [rohlik-mcp](https://github.com/tomaspavlin/rohlik-mcp) server and manages your grocery orders through WhatsApp (or any other supported channel).

The agent learns your shopping habits over time — it tracks what you buy, estimates what's left in your fridge, finds relevant deals, and builds smart shopping lists.

## Features

- **Full Rohlik integration** — search products, add to cart, check delivery slots, browse discounts, view order history
- **Grocery memory** — learns your preferences, staple items, brand loyalty, and dietary restrictions from delivery history
- **Fridge tracking** — estimates what you have at home based on deliveries and consumption rates, with self-calibrating accuracy
- **Receipt scanning** — send a photo of a grocery receipt from any store (Albert, Lidl, Tesco, etc.) to update your fridge inventory with non-Rohlik purchases
- **Image understanding** — the agent can see and understand photos sent via WhatsApp
- **Shopping planner** — builds optimized orders combining fridge state, preferences, promotions, and meal planning
- **Meal suggestions** — recommends meals based on what's in your fridge and what you like to cook
- **Multi-channel messaging** — talk to your assistant from WhatsApp, Telegram, Discord, Slack, or Gmail
- **Container isolation** — agents run in sandboxed Linux containers, not on your host machine
- **Scheduled tasks** — set up restock reminders or recurring orders
- **Web access** — search and browse the web when needed

## Quick Start

### Prerequisites

- macOS or Linux
- Node.js 20+
- [Claude Code](https://claude.ai/download)
- [Apple Container](https://github.com/apple/container) (macOS) or [Docker](https://docker.com/products/docker-desktop) (macOS/Linux)
- A [Rohlik.cz](https://www.rohlik.cz) account

### Setup

```bash
git clone https://github.com/<your-username>/rohlik-claw.git
cd rohlik-claw
claude
```

Then run `/setup`. Claude Code handles dependencies, authentication, container setup, and service configuration.

You'll need to provide your Rohlik credentials in `.env`:

```bash
ROHLIK_USERNAME=your@email.com
ROHLIK_PASSWORD=your-password
ROHLIK_BASE_URL=https://www.rohlik.cz
```

## Usage

### Run it in the background

NanoClaw runs as a systemd user service (`nanoclaw.service`), installed by `/setup`. Once enabled, it starts automatically on login and restarts on crash.

```bash
systemctl --user start nanoclaw      # start
systemctl --user stop nanoclaw       # stop
systemctl --user restart nanoclaw    # restart
systemctl --user status nanoclaw     # current state + recent log lines
systemctl --user is-active nanoclaw  # one-word: "active" / "inactive"
systemctl --user is-enabled nanoclaw # "enabled" = starts on login
```

On macOS the equivalent is launchd — see [CLAUDE.md](CLAUDE.md#development) for `launchctl` commands.

By default systemd user services stop when you log out. To keep NanoClaw running across logouts (e.g. on a headless machine):

```bash
sudo loginctl enable-linger $USER
```

### Watch it

**Host process logs.** The systemd unit redirects stdout/stderr to log files in `logs/`, so app output does NOT show up in `journalctl` — only systemd lifecycle events do. Tail the files instead:

```bash
tail -f logs/nanoclaw.log                          # normal activity
tail -f logs/nanoclaw.error.log                    # errors
tail -f logs/nanoclaw.log logs/nanoclaw.error.log  # both at once
journalctl --user -u nanoclaw -f                   # only systemd start/stop/crash events
```

**Agent container logs.** Each conversation spawns an isolated container from the `nanoclaw-agent` image. To see what the agent is doing inside (tool calls, MCP traffic, Claude responses):

```bash
docker ps --filter "ancestor=nanoclaw-agent"            # currently running agents
docker ps -a --filter "ancestor=nanoclaw-agent"         # include exited ones
docker logs -f $(docker ps -q --filter "ancestor=nanoclaw-agent" | head -1)   # follow newest running agent
docker logs --tail 200 <container-name>                 # last 200 lines of a specific one
docker exec -it <container-name> bash                   # shell into a running agent (= Docker Desktop "open terminal")
```




Talk to the assistant with the trigger word (default: `@Andy`):

```
@Andy prepare a weekly grocery order
@Andy what do we need? anything running low?
@Andy I need milk and eggs
@Andy suggest some meals for this week
@Andy check what's on sale from the stuff we usually buy
@Andy order groceries for 5 days, we're having guests on Saturday
[photo of a receipt from Albert] @Andy add these to my fridge
```

### Order Types

The assistant detects what kind of order you need:

- **Full order** — "prepare a weekly order" — runs the full workflow: analyzes recent deliveries, checks fridge state, scans promotions, builds a smart cart proposal
- **Quick top-up** — "I need milk" — searches and adds items directly, no questions asked
- **Restock check** — "what do we need?" — shows what's running low based on fridge estimates

### How It Learns

The agent builds a grocery profile in `groups/<group>/grocery/` by analyzing your completed Rohlik deliveries:

| File | What It Tracks |
|------|---------------|
| `preferences.md` | Taste profile, brand preferences, dietary restrictions |
| `staples.md` | Always-buy items with quantities and Rohlik product IDs |
| `patterns.md` | Co-purchase patterns, seasonal trends, order frequency |
| `fridge-state.md` | Estimated current fridge/pantry contents |
| `meals.md` | Favorite meals and their ingredients |
| `spending.md` | Order costs and spending trends |
| `household.md` | Household size, dietary needs, budget |
| `delivery-log.md` | Processed delivery summaries |
| `planning-feedback.md` | Tracked corrections (promotes to preferences after 3+ repeats) |

Memory updates only from **completed deliveries**, never from planned carts. The agent also calibrates its fridge consumption estimates based on your actual reorder intervals.

## Architecture

Built on [NanoClaw](https://github.com/qwibitai/nanoclaw) — a single Node.js process with containerized Claude agents.

```
Channels --> SQLite --> Polling loop --> Container (Claude Agent SDK + Rohlik MCP) --> Response
```

The Rohlik MCP server is installed inside the agent container at build time. Credentials are passed as environment variables from `.env` through the container runner. The agent has access to all `mcp__rohlik__*` tools for interacting with Rohlik's API.

### Container lifecycle

Two layers with very different lifetimes:

1. **Host orchestrator** — the `node dist/index.js` process under systemd. Always on. Polls channels every 2s, watches IPC, runs the scheduler, routes outbound messages.
2. **Agent containers** — `nanoclaw-agent:latest` instances, spawned **on demand, per group** when a message arrives. Started with `docker run -i --rm` so they auto-delete on exit.

After replying, a container does NOT exit immediately. It stays warm for `IDLE_TIMEOUT` (default **30 min**, configurable via env — see `src/config.ts`) so follow-up messages reuse the same container instead of paying a cold start every time. After the idle period it self-terminates and Docker removes it.

One container per active group, not per message. Different groups get fully isolated containers (separate `.claude/` sessions, IPC dir, group folder mount).

**Security boundaries:**
- Project root is mounted **read-only** into the main group's container — the agent can read source but can't modify the host app.
- `.env` is shadowed with `/dev/null`; the container never reads secrets from the mounted file.
- All Anthropic API traffic is routed through a **credential proxy** on the host (port `3001`). The container only ever sees `ANTHROPIC_API_KEY=placeholder`; the proxy swaps in the real key on outgoing requests.
- Rohlik credentials *are* injected as env vars (the MCP server needs them).

### Container Skills

| Skill | Purpose |
|-------|---------|
| `grocery-memory` | Analyzes delivery history, extracts preferences, maintains grocery profile |
| `shopping-planner` | Orchestrates full order workflow with parallel subagents |
| `fridge-tracker` | Estimates current fridge/pantry contents using consumption models |
| `receipt-scanner` | Extracts items from store receipt photos and updates fridge state |
| `purchase-db` | Item-level purchase history in SQLite — spend, price trends, staples |

### Key Files

| File | Purpose |
|------|---------|
| `src/index.ts` | Orchestrator: state, message loop, agent invocation |
| `src/container-runner.ts` | Spawns agent containers with Rohlik credentials |
| `container/Dockerfile` | Container image with rohlik-mcp installed |
| `container/agent-runner/src/index.ts` | Agent SDK config with Rohlik MCP server |
| `groups/global/CLAUDE.md` | Agent persona and behavior instructions |
| `container/skills/` | Container skills (grocery-memory, shopping-planner, fridge-tracker, purchase-db) |
| `groups/{name}/grocery/purchases.db` | Item-level purchase history (SQLite, built by `purchase-db`) |
| `container/agents/` | Container subagents (product-scout on Haiku, meal-planner on Opus) |

## Customizing

NanoClaw doesn't use configuration files. To make changes, just tell Claude Code what you want:

- "Change the trigger word to @Claw"
- "Make responses shorter"
- "Add Telegram as a channel" (run `/add-telegram`)
- "Switch to Apple Container" (run `/convert-to-apple-container`)

The codebase is small enough that Claude can safely modify it.

## Development

```bash
npm run dev          # Run with hot reload
npm run build        # Compile TypeScript
./container/build.sh # Rebuild agent container (needed after Dockerfile changes)
```

## Upstream

This is a fork of [NanoClaw](https://github.com/qwibitai/nanoclaw). To pull upstream updates, run `/update-nanoclaw`.

## License

MIT
