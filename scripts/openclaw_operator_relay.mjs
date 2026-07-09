#!/usr/bin/env node
import fs from "node:fs";
import net from "node:net";
import { setTimeout as sleep } from "node:timers/promises";
import { pathToFileURL } from "node:url";

const redisHost = process.env.LYRA_OPERATOR_REDIS_HOST || "redis";
const redisPort = Number(process.env.LYRA_OPERATOR_REDIS_PORT || "6379");
const queueUserId = process.env.LYRA_OPERATOR_QUEUE_USER_ID || "1";
const queueKey = `notifications:pending:${queueUserId}`;
const processingKey =
  process.env.LYRA_OPERATOR_PROCESSING_QUEUE_KEY || `${queueKey}:processing`;
const deadLetterKey =
  process.env.LYRA_OPERATOR_DEAD_LETTER_QUEUE_KEY || `${queueKey}:dead_letter`;
const configPath =
  process.env.OPENCLAW_CONFIG_PATH || "/home/node/.openclaw/openclaw.json";
const pollTimeoutSeconds = Number(process.env.LYRA_OPERATOR_RELAY_BLPOP_TIMEOUT || "30");
const logPrefix = "[lyra-openclaw-relay]";

let socket = null;
let buffer = Buffer.alloc(0);

function log(message) {
  console.log(`${new Date().toISOString()} ${logPrefix} ${message}`);
}

export function sanitizeRelayReason(value) {
  return String(value || "unknown")
    .slice(0, 240)
    .replace(/bot[A-Za-z0-9:_-]+/g, "bot[redacted]")
    .replace(/(token|botToken|authorization|api[_-]?key)=([^&\s]+)/gi, "$1=[redacted]")
    .replace(/(message|payload|raw)=([^&\s]+)/gi, "$1=[redacted]");
}

function readTelegramConfig() {
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const telegram = config.channels?.telegram || {};
  const token = process.env.TELEGRAM_BOT_TOKEN || telegram.botToken;
  const chatIds = [
    process.env.LYRA_OPERATOR_TELEGRAM_CHAT_ID,
    process.env.TELEGRAM_CHAT_ID,
    ...(telegram.allowFrom || []),
    ...(telegram.execApprovals?.approvers || []),
  ].filter(Boolean);
  const uniqueChatIds = [...new Set(chatIds.map((value) => String(value)))];
  if (!token) {
    throw new Error("Telegram bot token missing");
  }
  if (!uniqueChatIds.length) {
    throw new Error("Telegram operator chat id missing");
  }
  return { token, chatIds: uniqueChatIds };
}

function encodeResp(args) {
  return Buffer.from(
    `*${args.length}\r\n` +
      args
        .map((arg) => {
          const value = String(arg);
          return `$${Buffer.byteLength(value)}\r\n${value}\r\n`;
        })
        .join(""),
    "utf8",
  );
}

async function connectRedis() {
  if (socket && !socket.destroyed) {
    return socket;
  }
  socket = net.createConnection({ host: redisHost, port: redisPort });
  socket.setNoDelay(true);
  socket.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
  });
  socket.on("close", () => {
    socket = null;
    buffer = Buffer.alloc(0);
  });
  await new Promise((resolve, reject) => {
    socket.once("connect", resolve);
    socket.once("error", reject);
  });
  return socket;
}

function readLine(offset) {
  const end = buffer.indexOf("\r\n", offset);
  if (end === -1) {
    return null;
  }
  return [buffer.toString("utf8", offset, end), end + 2];
}

function parseResp(offset = 0) {
  if (buffer.length <= offset) {
    return null;
  }
  const prefix = String.fromCharCode(buffer[offset]);
  if (prefix === "+") {
    const line = readLine(offset + 1);
    return line ? { value: line[0], next: line[1] } : null;
  }
  if (prefix === "-") {
    const line = readLine(offset + 1);
    if (!line) return null;
    throw new Error(`Redis error: ${line[0]}`);
  }
  if (prefix === ":") {
    const line = readLine(offset + 1);
    return line ? { value: Number(line[0]), next: line[1] } : null;
  }
  if (prefix === "$") {
    const line = readLine(offset + 1);
    if (!line) return null;
    const length = Number(line[0]);
    if (length === -1) {
      return { value: null, next: line[1] };
    }
    const start = line[1];
    const end = start + length;
    if (buffer.length < end + 2) {
      return null;
    }
    return {
      value: buffer.toString("utf8", start, end),
      next: end + 2,
    };
  }
  if (prefix === "*") {
    const line = readLine(offset + 1);
    if (!line) return null;
    const count = Number(line[0]);
    if (count === -1) {
      return { value: null, next: line[1] };
    }
    const values = [];
    let next = line[1];
    for (let i = 0; i < count; i += 1) {
      const parsed = parseResp(next);
      if (!parsed) return null;
      values.push(parsed.value);
      next = parsed.next;
    }
    return { value: values, next };
  }
  throw new Error(`Unsupported Redis RESP prefix: ${prefix}`);
}

async function redisCommand(args) {
  const conn = await connectRedis();
  conn.write(encodeResp(args));
  for (;;) {
    const parsed = parseResp(0);
    if (parsed) {
      buffer = buffer.subarray(parsed.next);
      return parsed.value;
    }
    await sleep(25);
  }
}

export function createRelayOperations({
  redisCommand: command,
  queueKey: pendingQueueKey = queueKey,
  processingKey: activeProcessingKey = processingKey,
  deadLetterKey: activeDeadLetterKey = deadLetterKey,
  pollTimeoutSeconds: activePollTimeoutSeconds = pollTimeoutSeconds,
  log: writeLog = log,
  now = () => new Date(),
} = {}) {
  if (typeof command !== "function") {
    throw new Error("redisCommand dependency is required");
  }

  async function restoreProcessingQueue() {
    let restored = 0;
    for (;;) {
      const raw = await command(["RPOPLPUSH", activeProcessingKey, pendingQueueKey]);
      if (!raw) {
        break;
      }
      restored += 1;
    }
    if (restored > 0) {
      writeLog(`restored_processing count=${restored}`);
    }
    return restored;
  }

  async function takePending() {
    return command([
      "BRPOPLPUSH",
      pendingQueueKey,
      activeProcessingKey,
      String(activePollTimeoutSeconds),
    ]);
  }

  async function ackProcessing(raw) {
    const removed = await command(["LREM", activeProcessingKey, "1", raw]);
    if (Number(removed) !== 1) {
      writeLog(`ack_missing_processing removed=${removed}`);
    }
    return Number(removed);
  }

  async function requeueProcessing(raw, reason) {
    const removed = await command(["LREM", activeProcessingKey, "1", raw]);
    const safeReason = sanitizeRelayReason(reason);
    if (Number(removed) === 1) {
      await command(["LPUSH", pendingQueueKey, raw]);
      writeLog(`requeued reason=${safeReason}`);
      return Number(removed);
    }
    writeLog(`requeue_missing_processing removed=${removed} reason=${safeReason}`);
    return Number(removed);
  }

  async function deadLetterProcessing(raw, reason) {
    const removed = await command(["LREM", activeProcessingKey, "1", raw]);
    const safeReason = sanitizeRelayReason(reason);
    const entry = JSON.stringify(
      {
        raw,
        reason: safeReason,
        moved_at: now().toISOString(),
      },
      null,
      0,
    );
    await command(["LPUSH", activeDeadLetterKey, entry]);
    writeLog(`dead_lettered removed=${removed} reason=${safeReason}`);
    return Number(removed);
  }

  return {
    restoreProcessingQueue,
    takePending,
    ackProcessing,
    requeueProcessing,
    deadLetterProcessing,
  };
}

const defaultOperations = createRelayOperations({ redisCommand });

async function restoreProcessingQueue() {
  return defaultOperations.restoreProcessingQueue();
}

async function takePending() {
  return defaultOperations.takePending();
}

async function ackProcessing(raw) {
  return defaultOperations.ackProcessing(raw);
}

async function requeueProcessing(raw, reason) {
  return defaultOperations.requeueProcessing(raw, reason);
}

async function deadLetterProcessing(raw, reason) {
  return defaultOperations.deadLetterProcessing(raw, reason);
}

export function relayText(payload) {
  if (payload && typeof payload.message === "string" && payload.message.trim()) {
    return payload.message.trim();
  }
  const type = payload?.type || "unknown";
  const source = payload?.source || "unknown";
  return `[warn] [openclaw.relay] Barzakh operator notification lacked message text. type=${type} source=${source}`;
}

async function sendTelegram(token, chatIds, text) {
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  for (const chatId of chatIds) {
    const body = new URLSearchParams({
      chat_id: chatId,
      text,
      disable_web_page_preview: "true",
    });
    const response = await fetch(url, { method: "POST", body });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || json.ok === false) {
      throw new Error(`Telegram send failed status=${response.status} chat=${chatId}`);
    }
  }
}

export async function processPendingRaw(
  raw,
  telegram,
  operations,
  {
    sendTelegram: sendTelegramFn = sendTelegram,
    sleep: sleepFn = sleep,
    log: writeLog = log,
  } = {},
) {
  if (!raw) {
    return "empty";
  }
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    await operations.deadLetterProcessing(raw, `malformed_json:${error.name}`);
    await sleepFn(5000);
    return "dead_lettered";
  }

  try {
    const text = relayText(payload);
    await sendTelegramFn(telegram.token, telegram.chatIds, text);
    await operations.ackProcessing(raw);
    writeLog(`sent type=${payload.type || "unknown"} source=${payload.source || "unknown"}`);
    return "sent";
  } catch (error) {
    await operations.requeueProcessing(raw, `send_failed:${sanitizeRelayReason(error.message)}`);
    await sleepFn(5000);
    return "requeued";
  }
}

async function main() {
  const telegram = readTelegramConfig();
  await restoreProcessingQueue();
  log(
    `started queue=${queueKey} processing=${processingKey} dead_letter=${deadLetterKey} redis=${redisHost}:${redisPort} chats=${telegram.chatIds.length}`,
  );

  for (;;) {
    try {
      const raw = await takePending();
      if (!raw) {
        continue;
      }
      await processPendingRaw(raw, telegram, defaultOperations);
      await sleep(250);
    } catch (error) {
      log(`error=${error.message}`);
      if (socket && !socket.destroyed) {
        socket.destroy();
      }
      await sleep(5000);
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(`${new Date().toISOString()} ${logPrefix} fatal=${error.message}`);
    process.exit(1);
  });
}
