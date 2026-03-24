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

### Container Skills

| Skill | Purpose |
|-------|---------|
| `grocery-memory` | Analyzes delivery history, extracts preferences, maintains grocery profile |
| `shopping-planner` | Orchestrates full order workflow with parallel subagents |
| `fridge-tracker` | Estimates current fridge/pantry contents using consumption models |
| `receipt-scanner` | Extracts items from store receipt photos and updates fridge state |

### Key Files

| File | Purpose |
|------|---------|
| `src/index.ts` | Orchestrator: state, message loop, agent invocation |
| `src/container-runner.ts` | Spawns agent containers with Rohlik credentials |
| `container/Dockerfile` | Container image with rohlik-mcp installed |
| `container/agent-runner/src/index.ts` | Agent SDK config with Rohlik MCP server |
| `groups/global/CLAUDE.md` | Agent persona and behavior instructions |
| `container/skills/` | Container skills (grocery-memory, shopping-planner, fridge-tracker) |

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
