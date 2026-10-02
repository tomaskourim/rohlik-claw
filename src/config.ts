import os from 'os';
import path from 'path';

import { readEnvFile } from './env.js';

// Read config values from .env (falls back to process.env).
// Secrets (API keys, tokens) are NOT read here — they are loaded only
// by the credential proxy (credential-proxy.ts), never exposed to containers.
const envConfig = readEnvFile([
  'ASSISTANT_NAME',
  'ASSISTANT_HAS_OWN_NUMBER',
  'ALLOW_NO_CHANNELS',
]);

export const ASSISTANT_NAME =
  process.env.ASSISTANT_NAME || envConfig.ASSISTANT_NAME || 'Andy';
export const ASSISTANT_HAS_OWN_NUMBER =
  (process.env.ASSISTANT_HAS_OWN_NUMBER ||
    envConfig.ASSISTANT_HAS_OWN_NUMBER) === 'true';
// A run with no channel is normally a misconfiguration and we exit rather than
// sit there unreachable. Set this when a channel is deliberately offline (e.g.
// WhatsApp waiting on a re-scan) and the scheduler should keep running anyway.
export const ALLOW_NO_CHANNELS =
  (process.env.ALLOW_NO_CHANNELS || envConfig.ALLOW_NO_CHANNELS) === 'true';
export const POLL_INTERVAL = 2000;
export const SCHEDULER_POLL_INTERVAL = 60000;

// Absolute paths needed for container mounts
const PROJECT_ROOT = process.cwd();
const HOME_DIR = process.env.HOME || os.homedir();

// Mount security: allowlist stored OUTSIDE project root, never mounted into containers
export const MOUNT_ALLOWLIST_PATH = path.join(
  HOME_DIR,
  '.config',
  'nanoclaw',
  'mount-allowlist.json',
);
export const SENDER_ALLOWLIST_PATH = path.join(
  HOME_DIR,
  '.config',
  'nanoclaw',
  'sender-allowlist.json',
);
export const STORE_DIR = path.resolve(PROJECT_ROOT, 'store');
export const GROUPS_DIR = path.resolve(PROJECT_ROOT, 'groups');
export const DATA_DIR = path.resolve(PROJECT_ROOT, 'data');

export const CONTAINER_IMAGE =
  process.env.CONTAINER_IMAGE || 'nanoclaw-agent:latest';
// Model for a group's main agent loop. Subagents in container/agents/ override
// this per task, so heavier or cheaper work doesn't move the main loop.
export const DEFAULT_AGENT_MODEL =
  process.env.DEFAULT_AGENT_MODEL || 'claude-sonnet-5';
export const CONTAINER_TIMEOUT = parseInt(
  process.env.CONTAINER_TIMEOUT || '1800000',
  10,
);
export const CONTAINER_MAX_OUTPUT_SIZE = parseInt(
  process.env.CONTAINER_MAX_OUTPUT_SIZE || '10485760',
  10,
); // 10MB default
export const CREDENTIAL_PROXY_PORT = parseInt(
  process.env.CREDENTIAL_PROXY_PORT || '3001',
  10,
);
export const IPC_POLL_INTERVAL = 1000;

// Watchdog deadlines (see watchdog.ts). A process that hangs without exiting
// is invisible to systemd, so both the startup path and the long-lived loops
// get a deadline that turns a hang into a restartable non-zero exit.
//
// These are deliberately far longer than the tick rates they watch (message
// loop every 2s, scheduler every 60s). The assistant is used a few times a
// day, so a wedge that goes unnoticed for twenty minutes costs nothing, while
// a tight deadline risks killing a process that was merely slow. Detect,
// don't police.
export const STARTUP_TIMEOUT = parseInt(
  process.env.STARTUP_TIMEOUT || '1200000',
  10,
); // 20min — outlasts any WhatsApp reconnect backoff, even on a bad network
export const LOOP_STALL_TIMEOUT = parseInt(
  process.env.LOOP_STALL_TIMEOUT || '1200000',
  10,
); // 20min — 20x the slowest loop's tick, so only a real wedge trips it
export const WATCHDOG_CHECK_INTERVAL = parseInt(
  process.env.WATCHDOG_CHECK_INTERVAL || '300000',
  10,
); // 5min — granularity of the stall check; nothing needs finer
export const IDLE_TIMEOUT = parseInt(process.env.IDLE_TIMEOUT || '1800000', 10); // 30min default — how long to keep container alive after last result
export const MAX_CONCURRENT_CONTAINERS = Math.max(
  1,
  parseInt(process.env.MAX_CONCURRENT_CONTAINERS || '5', 10) || 5,
);

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export const TRIGGER_PATTERN = new RegExp(
  `^@${escapeRegex(ASSISTANT_NAME)}\\b`,
  'i',
);

// Timezone for scheduled tasks (cron expressions, etc.)
// Uses system timezone by default
export const TIMEZONE =
  process.env.TZ || Intl.DateTimeFormat().resolvedOptions().timeZone;
